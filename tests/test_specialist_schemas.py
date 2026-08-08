import unittest

from agents.escalation.schema import EscalationReason, EscalationResult
from agents.returns.schema import ReturnIssueCategory, ReturnsResult


class SpecialistSchemaTests(unittest.TestCase):
    def test_returns_result_supports_unknown_eligibility(self):
        result = ReturnsResult(
            issue_category=ReturnIssueCategory.RETURN_POLICY,
            eligible=None,
            confidence=0.7,
            requires_human=True,
            next_steps=["Verify the delivery date."],
            response_to_customer="We need your order details.",
            reasoning="Eligibility facts are missing.",
        )
        self.assertIsNone(result.eligible)

    def test_escalation_result_is_typed(self):
        result = EscalationResult(
            reason=EscalationReason.SECURITY,
            queue="trust-and-safety",
            urgency="urgent",
            summary_for_agent="Possible account takeover.",
            response_to_customer="A specialist will review this securely.",
            recommended_actions=["Review recent authentication events."],
        )
        self.assertEqual(result.reason, EscalationReason.SECURITY)


if __name__ == "__main__":
    unittest.main()
