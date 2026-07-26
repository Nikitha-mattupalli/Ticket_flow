from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq

from agents.billing.prompt import BILLING_SYSTEM_PROMPT, READ_ONLY_BILLING_PROMPT
from agents.billing.schema import BillingResult
from config.settings import GROQ_MODEL
from graph.state import Ticket
from tools.billing_tools import (
    fetch_invoice,
    process_refund,
    send_confirmation,
)

load_dotenv()


class BillingAgent:
    def __init__(self) -> None:
        self.model = ChatGroq(
            model=GROQ_MODEL,
            temperature=0,
            max_retries=2,
        )

        # Stage 1: agent can call business tools.
        # Do not request structured output here.
        self.tool_agent = create_agent(
            model=self.model,
            tools=[
                fetch_invoice,
                process_refund,
                send_confirmation,
            ],
            system_prompt=BILLING_SYSTEM_PROMPT,
        )

        # Stage 2: separate model call formats the completed
        # investigation into BillingResult.
        self.result_formatter = self.model.with_structured_output(
            BillingResult,
            method="json_schema",
            strict=False
        )

    def invoke(
        self,
        ticket: Ticket,
        context: str,
    ) -> BillingResult:
        user_message = f"""
    Customer ticket

    Ticket ID: {ticket.ticket_id}
    Customer ID: {ticket.customer_id}
    Subject: {ticket.subject}
    Description: {ticket.description}

    Relevant billing knowledge:
    {context}

    Investigate the ticket using available tools.
    Use only verified tool results.
    """

        agent_result = self.tool_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ]
            }
        )

        transcript_parts = []

        for message in agent_result["messages"]:
            content = message.content

            if not isinstance(content, str):
                content = str(content)

            transcript_parts.append(
                f"{type(message).__name__}:\n{content}"
            )

        tool_transcript = "\n\n".join(transcript_parts)

        billing_result = self.result_formatter.invoke(
            f"""
    Generate the final structured BillingResult.

    Ticket:
    {user_message}

    Completed tool investigation:
    {tool_transcript}

    Important:
    - Never invent tool outcomes.
    - A single succeeded payment does not prove a duplicate charge.
    - If evidence is insufficient, use needs_more_information.
    """
        )

        return billing_result