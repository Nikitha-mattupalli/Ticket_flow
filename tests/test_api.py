import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("api.app.start_workflow")
    def test_create_workflow(self, start):
        start.return_value = {
            "thread_id": "thread-1",
            "interrupted": False,
            "state": {"workflow_status": "completed"},
        }
        response = self.client.post(
            "/workflows",
            json={
                "customer_id": "customer-1",
                "subject": "Cannot log in",
                "description": "The login page keeps returning an error.",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["thread_id"], "thread-1")

    @patch("api.app.resume_workflow")
    def test_resume_approval(self, resume):
        resume.return_value = {
            "thread_id": "thread-1",
            "interrupted": False,
            "state": {"approval_status": "approved"},
        }
        response = self.client.post(
            "/workflows/thread-1/approval",
            json={"approved": True, "reviewer": "reviewer-1"},
        )
        self.assertEqual(response.status_code, 200)
        resume.assert_called_once_with(
            "thread-1",
            approved=True,
            reviewer="reviewer-1",
            comment=None,
        )

    @patch("api.app.process_langgraph_workflow.delay")
    def test_async_workflow_is_queued(self, delay):
        delay.return_value.id = "task-1"
        response = self.client.post(
            "/workflows/async",
            json={
                "customer_id": "customer-1",
                "subject": "Damaged delivery",
                "description": "The delivered item is damaged.",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"task_id": "task-1", "status": "queued"})


if __name__ == "__main__":
    unittest.main()
