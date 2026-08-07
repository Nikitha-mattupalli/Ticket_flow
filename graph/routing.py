from graph.state import GraphState
from agents.billing.schema import ApprovalStatus


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


def route_after_billing(state: GraphState) -> str:
    if state.pending_refund is None:
        return "complete"
    if state.approval_status == ApprovalStatus.PENDING:
        return "approval"
    return "refund"


def route_after_approval(state: GraphState) -> str:
    if state.approval_status == ApprovalStatus.APPROVED:
        return "refund"
    if state.approval_status == ApprovalStatus.REJECTED:
        return "rejected"
    raise ValueError("Approval node completed without an approval decision.")


def route_after_refund(state: GraphState) -> str:
    if state.refund_result and state.refund_result.get("success"):
        return "confirmation"
    return "failed"
