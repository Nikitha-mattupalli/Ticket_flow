#receive the graph state, extract ticket, call the supervisor agent and update the graphstate

from agents.supervisor.agent import SupervisorAgent
from graph.state import GraphState, WorkflowStatus
from retrieval.retriever import KnowledgeRetriever
from agents.billing.agent import BillingAgent
from agents.billing.schema import ApprovalStatus, BillingResult

billing_agent = BillingAgent()
billing_retriever = KnowledgeRetriever(domain="billing", top_k=3)
supervisor_agent = SupervisorAgent()

def supervisor_node(state: GraphState) -> GraphState:
    """
    Process the given GraphState through the Supervisor agent.

    Args:
        state (GraphState): The current state of the graph.

    Returns:
        GraphState: The updated state of the graph after processing by the Supervisor agent.
    """
    # Extract the ticket from the graph state
    ticket = state.ticket

    # Invoke the Supervisor agent with the extracted ticket
    supervisor_decision = supervisor_agent.invoke(ticket)

    # Update the graph state with the supervisor's decision and change workflow status
    state.supervisor_decision = supervisor_decision
    state.workflow_status = WorkflowStatus.ROUTED

    return state

def billing_node(state: GraphState) -> GraphState:

    ticket = state.ticket

    context = billing_retriever.retrieve(ticket.subject, ticket.description)

    billing_result = billing_agent.invoke(
        ticket=ticket,
        context=context
    )

    state.billing_result = billing_result

    if billing_result.proposed_refund is not None:

        state.pending_refund = billing_result.proposed_refund

        if billing_result.requires_human:
            state.approval_status = ApprovalStatus.PENDING
            state.workflow_status = WorkflowStatus.WAITING_FOR_HUMAN

        else:
            state.approval_status = ApprovalStatus.NOT_REQUIRED
            state.workflow_status = WorkflowStatus.PROCESSING

    else:

        state.pending_refund = None
        state.approval_status = ApprovalStatus.NOT_REQUIRED
        state.workflow_status = WorkflowStatus.COMPLETED

    return state
