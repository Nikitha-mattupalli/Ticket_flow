import unittest
from datetime import datetime
from unittest.mock import patch

from agents.escalation.node import escalation_node
from agents.escalation.schema import EscalationReason, EscalationResult
from agents.returns.node import returns_node
from agents.returns.schema import ReturnIssueCategory, ReturnsResult
from graph.state import GraphState, Ticket, WorkflowStatus


def state() -> GraphState:
    return GraphState(
        ticket=Ticket(
            ticket_id="ticket-1",
            customer_id="customer-1",
            subject="Damaged item",
            description="The item arrived damaged.",
            created_at=datetime.now(),
        )
    )


class SpecialistNodeTests(unittest.TestCase):
    @patch("agents.returns.node.returns_retriever.retrieve", return_value="policy")
    @patch("agents.returns.node.returns_agent.invoke")
    def test_returns_node(self, invoke, _retrieve):
        invoke.return_value = ReturnsResult(
            issue_category=ReturnIssueCategory.DAMAGED_ITEM,
            eligible=None,
            confidence=0.8,
            requires_human=True,
            next_steps=["Request photos."],
            response_to_customer="Please send photos.",
            reasoning="Damage requires verification.",
        )
        update = returns_node(state())
        self.assertEqual(update["workflow_status"], WorkflowStatus.COMPLETED)

    @patch("agents.escalation.node.escalation_agent.invoke")
    def test_escalation_node_waits_for_human(self, invoke):
        invoke.return_value = EscalationResult(
            reason=EscalationReason.SECURITY,
            queue="trust-and-safety",
            urgency="urgent",
            summary_for_agent="Possible takeover.",
            response_to_customer="A specialist will review this.",
            recommended_actions=["Review authentication logs."],
        )
        update = escalation_node(state())
        self.assertEqual(update["workflow_status"], WorkflowStatus.WAITING_FOR_HUMAN)


if __name__ == "__main__":
    unittest.main()
