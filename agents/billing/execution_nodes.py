from agents.billing.schema import ApprovalStatus
from graph.state import GraphState, WorkflowStatus
from tools.billing_tools import get_db, process_refund, send_confirmation
from config.settings import settings


def refund_execution_node(state: GraphState) -> dict:
    """Execute a proposed refund only after any required approval."""
    refund = state.pending_refund
    if refund is None:
        raise ValueError("Refund execution requested without a pending refund.")

    if state.approval_status not in {
        ApprovalStatus.NOT_REQUIRED,
        ApprovalStatus.APPROVED,
    }:
        raise ValueError("Refund execution requested before approval.")

    reason = refund.reason.value
    stripe_reason = (
        reason
        if reason in {"duplicate", "fraudulent", "requested_by_customer"}
        else "requested_by_customer"
    )
    if settings.persist_refunds and state.refund_record_id:
        get_db().update_refund_record(
            state.refund_record_id,
            {"status": "processing"},
        )

    result = process_refund.invoke(
        {
            "payment_intent_id": refund.payment_intent_id,
            "amount": refund.amount,
            "reason": stripe_reason,
            "human_approved": state.approval_status == ApprovalStatus.APPROVED,
        }
    )

    if result.get("success"):
        if settings.persist_refunds and state.refund_record_id:
            get_db().update_refund_record(
                state.refund_record_id,
                {
                    "status": "succeeded",
                    "stripe_refund_id": result.get("refund_id"),
                },
            )
        return {
            "refund_result": result,
            "workflow_status": WorkflowStatus.PROCESSING,
            "error_message": None,
        }

    if settings.persist_refunds and state.refund_record_id:
        get_db().update_refund_record(
            state.refund_record_id,
            {"status": "failed"},
        )
    return {
        "refund_result": result,
        "workflow_status": WorkflowStatus.FAILED,
        "error_message": result.get("error", "Refund execution failed."),
    }


def refund_confirmation_node(state: GraphState) -> dict:
    """Email the customer after Stripe confirms a successful refund."""
    if not state.refund_result or not state.refund_result.get("success"):
        raise ValueError("Refund confirmation requested without a successful refund.")

    customer = get_db().get_customer_by_id(state.ticket.customer_id)
    if not customer or not customer.get("email"):
        return {
            "confirmation_result": {
                "success": False,
                "error": "Customer email was not found.",
            },
            "workflow_status": WorkflowStatus.COMPLETED,
        }

    refund = state.pending_refund
    result = send_confirmation.invoke(
        {
            "customer_email": customer["email"],
            "subject": "Your refund has been processed",
            "message": (
                f"Your refund of {refund.amount} {refund.currency.upper()} "
                f"has been processed successfully. Refund reference: "
                f"{state.refund_result.get('refund_id', 'pending')}"
            ),
        }
    )
    return {
        "confirmation_result": result,
        "workflow_status": WorkflowStatus.COMPLETED,
    }
