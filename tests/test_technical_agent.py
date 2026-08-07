import unittest

from agents.technical.schema import TechnicalIssueCategory, TechnicalResult


class TechnicalResultTests(unittest.TestCase):
    def test_typed_result_accepts_supported_category(self):
        result = TechnicalResult(
            issue_category=TechnicalIssueCategory.API_TIMEOUT,
            confidence=0.9,
            requires_human=False,
            troubleshooting_steps=["Retry with exponential backoff."],
            response_to_customer="Please retry the request.",
            reasoning="The symptoms match the API timeout guidance.",
        )
        self.assertEqual(result.issue_category, TechnicalIssueCategory.API_TIMEOUT)

    def test_confidence_is_bounded(self):
        with self.assertRaises(ValueError):
            TechnicalResult(
                issue_category=TechnicalIssueCategory.OTHER,
                confidence=1.1,
                requires_human=True,
                troubleshooting_steps=["Contact support."],
                response_to_customer="We need to investigate.",
                reasoning="The knowledge base does not cover this issue.",
            )


if __name__ == "__main__":
    unittest.main()
