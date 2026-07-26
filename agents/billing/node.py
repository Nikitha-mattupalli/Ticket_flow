from agents.billing.agent import BillingAgent
from graph.state import GraphState,WorkflowStatus
from retrieval.retriever import KnowledgeRetriever

billing_agent = BillingAgent()
billing_retriever = KnowledgeRetriever(
    domain="billing",
    top_k =3
)

def billing_node(state: GraphState) -> GraphState:
    ticket = state.ticket

    context = billing_retriever.retrieve(
        subject = ticket.subject,
        description=ticket.description
    )

    result = billing_agent.invoke(
        ticket = ticket,
        context=context
    )

    state.billing_result = result
    state.workflow_status = WorkflowStatus.COMPLETED

    return state

