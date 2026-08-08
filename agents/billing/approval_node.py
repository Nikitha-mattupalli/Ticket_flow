from langgraph.types import interrupt

from agents.billing.schema import ApprovalStatus
from graph.state import GraphState
from graph.state import WorkflowStatus
from config.settings import settings
from tools.billing_tools import get_db
from datetime import datetime, timezone


def refund_approval_node(state: GraphState) -> GraphState:
    refund = state.pending_refund

    if refund is None:
        raise ValueError(
            "Refund approval requested without a pending refund."
        )

    decision = interrupt(
        {
            "type": "refund_approval",
            "ticket_id": state.ticket.ticket_id,
            "customer_id": refund.customer_id,
            "invoice_id": refund.invoice_id,
            "payment_id": refund.payment_id,
            "payment_intent_id": refund.payment_intent_id,
            "amount": refund.amount,
            "currency": refund.currency,
            "reason": (
                refund.reason.value
                if hasattr(refund.reason, "value")
                else refund.reason),
            "question": "Approve this refund?",
        }
    )

    if not isinstance(decision, dict):
        raise ValueError(
            "Approval decision must be a dictionary."
        )

    approved = decision.get("approved")

    if not isinstance(approved, bool):
        raise ValueError(
            "Approval decision must contain an 'approved' boolean."
        )

    approval_status = (
        ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
    )
    if settings.persist_refunds and state.refund_record_id:
        get_db().update_refund_record(
            state.refund_record_id,
            {
                "status": "pending" if approved else "cancelled",
                "approved_by": decision.get("reviewer"),
                "approved_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "approval_reviewer": decision.get("reviewer"),
        "approval_comment": decision.get("comment"),
        "approval_status": approval_status,
        "workflow_status": (
            WorkflowStatus.PROCESSING
            if approved
            else WorkflowStatus.COMPLETED
        ),
    }
