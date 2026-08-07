import unittest

from agents.billing.schema import ApprovalStatus
from graph.state import WorkflowStatus
from scripts.demo_workflow import run_scenario


class DemoWorkflowTests(unittest.TestCase):
    def test_approved_refund_executes_and_confirms(self):
        result = run_scenario("approval")
        self.assertEqual(result["approval_status"], ApprovalStatus.APPROVED)
        self.assertTrue(result["refund_result"]["success"])
        self.assertTrue(result["confirmation_result"]["success"])
        self.assertEqual(result["workflow_status"], WorkflowStatus.COMPLETED)

    def test_rejected_refund_never_executes(self):
        result = run_scenario("rejection")
        self.assertEqual(result["approval_status"], ApprovalStatus.REJECTED)
        self.assertIsNone(result.get("refund_result"))
        self.assertEqual(result["workflow_status"], WorkflowStatus.COMPLETED)

    def test_no_approval_refund_executes_and_confirms(self):
        result = run_scenario("no_approval")
        self.assertEqual(result["approval_status"], ApprovalStatus.NOT_REQUIRED)
        self.assertTrue(result["refund_result"]["success"])
        self.assertEqual(result["workflow_status"], WorkflowStatus.COMPLETED)

    def test_technical_ticket_returns_grounded_result(self):
        result = run_scenario("technical")
        self.assertIsNotNone(result["technical_result"])
        self.assertEqual(result["workflow_status"], WorkflowStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
