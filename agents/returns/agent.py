from langchain_groq import ChatGroq

from agents.returns.schema import ReturnsResult
from config.settings import GROQ_MODEL
from graph.state import Ticket


class ReturnsAgent:
    def __init__(self) -> None:
        model = ChatGroq(model=GROQ_MODEL, temperature=0, max_retries=2)
        self.structured_model = model.with_structured_output(ReturnsResult)

    def invoke(self, ticket: Ticket, context: str) -> ReturnsResult:
        return self.structured_model.invoke(
            f"""
You are Ticket Flow's returns specialist. Use only the supplied policy
context. Never claim that a label, replacement, or refund was created. Set
eligible=null and requires_human=true when order dates, condition, or delivery
details needed for eligibility are missing.

Ticket subject: {ticket.subject}
Ticket description: {ticket.description}

Returns policy context:
{context}
"""
        )
