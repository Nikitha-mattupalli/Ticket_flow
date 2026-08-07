from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from agents.billing.prompt import BILLING_SYSTEM_PROMPT, READ_ONLY_BILLING_PROMPT, BILLING_TOOL_SYSTEM_PROMPT
from agents.billing.schema import BillingResult
from config.settings import GROQ_MODEL
from graph.state import Ticket
from tools.billing_tools import (
    fetch_invoice,
    process_refund,
    send_confirmation,
)
from langchain_core.exceptions import OutputParserException

load_dotenv()

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from agents.billing.schema import (
    BillingIssueCategory,
    BillingResult,
    ResolutionStatus,
)


class BillingAgent:

    def __init__(self):

        self.model = ChatGroq(
            model=GROQ_MODEL,
            temperature=0,
            max_retries=2,
        )

        self.tool_agent = create_agent(
            model=self.model,
            tools=[
                fetch_invoice,
                # process_refund,
                # send_confirmation,
            ],
            system_prompt=BILLING_TOOL_SYSTEM_PROMPT,
        )

        self.result_formatter = self.model.with_structured_output(
            BillingResult,
            method="json_mode",
        )

    def _format_agent_messages(self, messages) -> str:
        """
        Convert agent messages into a clean transcript for the
        BillingResult structured-output formatter.
        """

        transcript_parts = []

        for message in messages:

            if isinstance(message, HumanMessage):
                content = self._normalise_content(message.content)

                if content:
                    transcript_parts.append(
                        f"Customer request:\n{content}"
                    )

            elif isinstance(message, AIMessage):
                tool_calls = getattr(message, "tool_calls", None) or []

                for tool_call in tool_calls:
                    tool_name = tool_call.get(
                        "name",
                        "unknown_tool",
                    )

                    tool_arguments = tool_call.get(
                        "args",
                        {},
                    )

                    transcript_parts.append(
                        "Tool invocation:\n"
                        f"Tool: {tool_name}\n"
                        f"Arguments: {tool_arguments}"
                    )

                content = self._normalise_content(message.content)

                if content:
                    transcript_parts.append(
                        f"Agent finding:\n{content}"
                    )

            elif isinstance(message, ToolMessage):
                content = self._normalise_content(message.content)

                tool_name = (
                    getattr(message, "name", None)
                    or "unknown_tool"
                )

                if content:
                    transcript_parts.append(
                        f"Tool result ({tool_name}):\n{content}"
                    )

        if not transcript_parts:
            return "No investigation messages were returned."

        return "\n\n---\n\n".join(transcript_parts)

    @staticmethod
    def _normalise_content(content) -> str:
        """
        Convert string or block-based message content into plain text.
        """

        if content is None:
            return ""

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts = []

            for item in content:
                if isinstance(item, str):
                    parts.append(item)

                elif isinstance(item, dict):
                    text = item.get("text")

                    if text:
                        parts.append(str(text))
                    else:
                        parts.append(str(item))

                else:
                    parts.append(str(item))

            return "\n".join(parts).strip()

        return str(content).strip()

    def invoke(
        self,
        ticket,
        context: str,
    ) -> BillingResult:

        investigation_prompt = f"""
Customer ID: {ticket.customer_id}

Ticket subject:
{ticket.subject}

Ticket description:
{ticket.description}

Knowledge-base context:
{context}

Investigate this billing issue using the available tools.

Rules:
- Use only verified data returned by tools.
- Do not invent customer, invoice, payment, or refund information.
- If a lookup fails, clearly state what could not be found.
- Do not return JSON during this investigation step.
- After completing the investigation, return a concise factual summary.
"""

        agent_result = self.tool_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": investigation_prompt,
                    }
                ]
            }
        )

        messages = agent_result.get("messages", [])

        transcript = self._format_agent_messages(
            messages
        )

        formatter_prompt = f"""
Return only one valid JSON object matching the BillingResult schema.

The JSON object must contain every field below:

{{
  "issue_category": "one valid BillingIssueCategory value",
  "resolution_status": "one valid ResolutionStatus value",
  "confidence": 0.0,
  "requires_human": false,
  "response_to_customer": "customer-facing response",
  "reasoning": "concise reasoning",
  "proposed_refund": null
}}

Valid issue_category values:
- duplicate_charge
- incorrect_amount
- payment_failure
- payment_not_received
- refund_request
- refund_status
- invoice_request
- subscription
- bill_explanation
- other

Valid resolution_status values:
- resolved
- needs_more_information
- escalated
- action_required

Rules:
- Never omit issue_category.
- Never omit resolution_status.
- Never omit any required BillingResult field.
- If the ticket reports a duplicate charge but records cannot be verified,
  use "issue_category": "duplicate_charge".
- If required customer or payment information is missing,
  use "resolution_status": "needs_more_information".
- In that case, set "requires_human": true.
- Set "proposed_refund": null unless a refund is fully supported by
  verified payment information.
- Return valid JSON only.
- Do not include Markdown or code fences.

Ticket:
Customer ID: {ticket.customer_id}
Subject: {ticket.subject}
Description: {ticket.description}

Knowledge context:
{context}

Investigation transcript:
{transcript}
"""

        try:
            billing_result = self.result_formatter.invoke(
                formatter_prompt
            )

        except OutputParserException:
            billing_result = BillingResult(
                issue_category=BillingIssueCategory.DUPLICATE_CHARGE,
                resolution_status=ResolutionStatus.NEEDS_MORE_INFORMATION,
                confidence=0.2,
                requires_human=True,
                response_to_customer=(
                    "We could not verify your billing records using the "
                    "provided customer ID. Please provide the correct "
                    "customer identifier so we can investigate further."
                ),
                reasoning=(
                    "The customer or payment records could not be verified, "
                    "so the reported duplicate charge cannot yet be confirmed."
                ),
                proposed_refund=None,
            )

        return billing_result