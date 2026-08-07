from datetime import datetime

from agents.billing.agent import BillingAgent
from graph.state import Ticket
from retrieval.retriever import KnowledgeRetriever


ticket = Ticket(
    ticket_id="TKT-001",
    customer_id="05f23ece-4627-4085-a257-d1cc4624e281",
    subject="I was charged twice for my subscription",
    description="I can see two successful payments for the same invoice.",
    created_at=datetime.now(),
)

retriever = KnowledgeRetriever(
    domain="billing",
)

context = retriever.retrieve(
    subject=ticket.subject,
    description=ticket.description,
)

print("=" * 60)
print("RAG CONTEXT")
print("=" * 60)
print(context)

agent = BillingAgent()

result = agent.invoke(
    ticket=ticket,
    context=context,
)

print("\n")
print("=" * 60)
print("BILLING RESULT")
print("=" * 60)
print(result)