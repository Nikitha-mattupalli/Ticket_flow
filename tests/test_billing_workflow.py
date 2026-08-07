import unittest
from datetime import datetime
from unittest.mock import patch

from agents.billing.approval_node import refund_approval_node
from agents.billing.execution_nodes import (
    refund_confirmation_node,
    refund_execution_node,
)
from agents.billing.schema import ApprovalStatus, RefundReason, RefundRequest
from graph.routing import route_after_approval, route_after_billing, route_after_refund
from graph.state import GraphState, Ticket, WorkflowStatus


def make_state(*, approval_status=ApprovalStatus.NOT_REQUIRED) -> GraphState:
    return GraphState(
        ticket=Ticket(
            ticket_id="TKT-1",
            customer_id="customer-1",
            subject="Duplicate charge",
            description="I was charged twice.",
            created_at=datetime.now(),
        ),
        pending_refund=RefundRequest(
            payment_id="payment-1",
            invoice_id="invoice-1",
            customer_id="customer-1",
            payment_intent_id="pi_test_1",
            amount=60_000,
            currency="inr",
            reason=RefundReason.DUPLICATE,
        ),
        approval_status=approval_status,
    )


class BillingRoutingTests(unittest.TestCase):
    def test_billing_routes_all_three_cases(self):
        state = make_state()
        self.assertEqual(route_after_billing(state), "refund")
        state.approval_status = ApprovalStatus.PENDING
        self.assertEqual(route_after_billing(state), "approval")
        state.pending_refund = None
        self.assertEqual(route_after_billing(state), "complete")

    def test_approval_routes_approved_and_rejected(self):
        state = make_state(approval_status=ApprovalStatus.APPROVED)
        self.assertEqual(route_after_approval(state), "refund")
        state.approval_status = ApprovalStatus.REJECTED
        self.assertEqual(route_after_approval(state), "rejected")

    @patch("agents.billing.approval_node.interrupt")
    def test_approval_node_records_human_decision(self, interrupt):
        interrupt.return_value = {
            "approved": True,
            "reviewer": "demo-reviewer",
            "comment": "Verified duplicate payment",
        }

        update = refund_approval_node(
            make_state(approval_status=ApprovalStatus.PENDING)
        )

        self.assertEqual(update["approval_status"], ApprovalStatus.APPROVED)
        self.assertEqual(update["workflow_status"], WorkflowStatus.PROCESSING)
        self.assertEqual(update["approval_reviewer"], "demo-reviewer")


class RefundExecutionTests(unittest.TestCase):
    @patch("agents.billing.execution_nodes.process_refund")
    def test_approved_refund_executes_with_human_approval(self, tool):
        tool.invoke.return_value = {"success": True, "refund_id": "re_1"}
        state = make_state(approval_status=ApprovalStatus.APPROVED)

        update = refund_execution_node(state)

        self.assertEqual(update["workflow_status"], WorkflowStatus.PROCESSING)
        self.assertEqual(route_after_refund(GraphState.model_validate({**state.model_dump(), **update})), "confirmation")
        self.assertTrue(tool.invoke.call_args.args[0]["human_approved"])

    @patch("agents.billing.execution_nodes.process_refund")
    def test_failed_refund_stops_without_confirmation(self, tool):
        tool.invoke.return_value = {"success": False, "error": "Stripe failed"}
        update = refund_execution_node(make_state())
        self.assertEqual(update["workflow_status"], WorkflowStatus.FAILED)
        self.assertEqual(update["error_message"], "Stripe failed")

    @patch("agents.billing.execution_nodes.send_confirmation")
    @patch("agents.billing.execution_nodes.get_db")
    def test_successful_refund_sends_confirmation(self, get_db, send):
        get_db.return_value.get_customer_by_id.return_value = {
            "email": "customer@example.com"
        }
        send.invoke.return_value = {"success": True, "email_id": "email-1"}
        state = make_state()
        state.refund_result = {"success": True, "refund_id": "re_1"}

        update = refund_confirmation_node(state)

        self.assertEqual(update["workflow_status"], WorkflowStatus.COMPLETED)
        self.assertTrue(update["confirmation_result"]["success"])


if __name__ == "__main__":
    unittest.main()
