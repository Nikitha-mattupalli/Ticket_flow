import os

import requests
from langchain_core.tools import tool


@tool
def create_escalation_ticket(
    ticket_id: str,
    subject: str,
    description: str,
    priority: str,
) -> dict:
    """Create a Zendesk-shaped escalation ticket through the configured API."""
    base_url = os.getenv("ZENDESK_BASE_URL", "http://localhost:8000/mock/zendesk")
    try:
        response = requests.post(
            f"{base_url}/ticket",
            json={
                "external_id": ticket_id,
                "subject": subject,
                "description": description,
                "priority": priority if priority in {"low", "normal", "high", "urgent"} else "normal",
                "type": "incident",
                "tags": ["ticket-flow", "human-escalation"],
            },
            timeout=10,
        )
        response.raise_for_status()
        ticket = response.json()["ticket"]
        return {"success": True, "external_ticket_id": str(ticket["id"])}
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        return {
            "success": False,
            "error": "Escalation delivery failed.",
            "error_type": type(exc).__name__,
        }
