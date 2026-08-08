from langchain_groq import ChatGroq

from agents.escalation.schema import EscalationResult
from config.settings import GROQ_MODEL
from graph.state import Ticket


class EscalationAgent:
    def __init__(self) -> None:
        model = ChatGroq(model=GROQ_MODEL, temperature=0, max_retries=2)
        self.structured_model = model.with_structured_output(EscalationResult)

    def invoke(self, ticket: Ticket) -> EscalationResult:
        return self.structured_model.invoke(
            f"""
Prepare a concise, factual handoff to a human support queue. Do not claim that
an external ticket or alert was created. Do not include secrets or unnecessary
personal data.

Subject: {ticket.subject}
Description: {ticket.description}
"""
        )
