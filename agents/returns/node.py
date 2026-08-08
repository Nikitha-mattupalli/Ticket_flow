from agents.returns.agent import ReturnsAgent
from graph.state import GraphState, WorkflowStatus
from retrieval.retriever import KnowledgeRetriever


returns_agent = ReturnsAgent()
returns_retriever = KnowledgeRetriever(domain="returns", top_k=3)


def returns_node(state: GraphState) -> dict:
    context = returns_retriever.retrieve(
        subject=state.ticket.subject,
        description=state.ticket.description,
    )
    result = returns_agent.invoke(ticket=state.ticket, context=context)
    return {
        "returns_result": result,
        "workflow_status": WorkflowStatus.COMPLETED,
        "error_message": None,
    }
