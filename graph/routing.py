from graph.state import GraphState


def route_ticket(state: GraphState) -> str:
    """
    Determine the next node in the workflow based on the
    Supervisor's routing decision.
    """

    if state.supervisor_decision is None:
        raise ValueError(
            "Supervisor decision not found. Cannot determine next route."
        )

    return state.supervisor_decision.next_agent.value