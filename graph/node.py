#receive the graph state, extract ticket, call the supervisor agent and update the graphstate

from agents.supervisor.agent import SupervisorAgent
from graph.state import GraphState, WorkflowStatus

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
