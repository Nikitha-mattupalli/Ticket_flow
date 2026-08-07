from langchain_groq import ChatGroq

from agents.technical.schema import TechnicalResult
from config.settings import GROQ_MODEL
from graph.state import Ticket


class TechnicalAgent:
    """Small structured-output agent grounded in technical RAG context."""

    def __init__(self) -> None:
        model = ChatGroq(model=GROQ_MODEL, temperature=0, max_retries=2)
        self.structured_model = model.with_structured_output(TechnicalResult)

    def invoke(self, ticket: Ticket, context: str) -> TechnicalResult:
        prompt = f"""
You are Ticket Flow's technical support specialist.

Classify the issue and give safe, concise troubleshooting based only on the
provided knowledge-base context. Do not invent system status, account state,
or actions that were not performed. If the context is insufficient or the
steps require privileged access, set requires_human=true.

Valid categories: login_issue, password_reset, network_connectivity,
service_outage, api_timeout, other.

Ticket subject: {ticket.subject}
Ticket description: {ticket.description}

Knowledge-base context:
{context}
"""
        return self.structured_model.invoke(prompt)
