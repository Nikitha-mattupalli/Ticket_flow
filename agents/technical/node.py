from agents.technical.agent import TechnicalAgent
from graph.state import GraphState, WorkflowStatus
from retrieval.retriever import KnowledgeRetriever


technical_agent = TechnicalAgent()
technical_retriever = KnowledgeRetriever(domain="technical", top_k=3)


def technical_node(state: GraphState) -> dict:
    context = technical_retriever.retrieve(
        subject=state.ticket.subject,
        description=state.ticket.description,
    )
    result = technical_agent.invoke(ticket=state.ticket, context=context)
    return {
        "technical_result": result,
        "workflow_status": WorkflowStatus.COMPLETED,
        "error_message": None,
    }
