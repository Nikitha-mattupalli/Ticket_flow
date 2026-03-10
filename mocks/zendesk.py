"""
Mock Zendesk Router
--------------------
Simulates the Zendesk API locally for development and testing.
No Zendesk account or API key needed.

Mounted at /mock/zendesk in main.py:
    POST   /mock/zendesk/ticket           → create a fake Zendesk ticket
    GET    /mock/zendesk/ticket/{zd_id}   → fetch a fake ticket by ID
    PUT    /mock/zendesk/ticket/{zd_id}   → update status
    GET    /mock/zendesk/tickets          → list all mock tickets

Behaves like the real Zendesk API:
    - Returns same response shape as Zendesk v2 API
    - Simulates network delay
    - Can simulate errors via ?fail=true query param

Usage in tasks.py (swap real for mock via env var):
    ZENDESK_BASE_URL=http://localhost:8000/mock/zendesk
"""

import uuid
import time
import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mock/zendesk", tags=["Mock: Zendesk"])

# ─────────────────────────────────────────────
# In-memory store (resets on server restart)
# Replace with Redis or DB if you need persistence
# ─────────────────────────────────────────────

_tickets: dict[str, dict] = {}   # zd_id → ticket dict


# ─────────────────────────────────────────────
# Schemas — match real Zendesk v2 API shape
# ─────────────────────────────────────────────

class ZendeskRequester(BaseModel):
    name:  str
    email: str

class ZendeskTicketRequest(BaseModel):
    """
    Mirrors the real Zendesk ticket creation payload.
    Real API: POST https://{subdomain}.zendesk.com/api/v2/tickets.json
              body: {"ticket": { ... }}
    """
    subject:     str                    = Field(..., min_length=3)
    description: Optional[str]         = Field(None)
    priority:    str                    = Field("normal",
                                                pattern="^(low|normal|high|urgent)$")
    type:        str                    = Field("problem",
                                                pattern="^(problem|incident|question|task)$")
    tags:        Optional[list[str]]   = Field(default_factory=list)
    requester:   Optional[ZendeskRequester] = None
    external_id: Optional[str]         = Field(None,
                                               description="Your internal ticket ID e.g. TKT-2025-006")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "subject":     "Invoice shows wrong amount",
                "description": "My invoice for March shows ₹14999 but I was charged ₹12999.",
                "priority":    "high",
                "type":        "problem",
                "tags":        ["billing", "invoice"],
                "requester":   {"name": "Alice Sharma", "email": "alice@example.com"},
                "external_id": "TKT-2025-006"
            }]
        }
    }


class ZendeskTicketUpdateRequest(BaseModel):
    status:   Optional[str] = Field(None,
                                    pattern="^(new|open|pending|hold|solved|closed)$")
    priority: Optional[str] = Field(None,
                                    pattern="^(low|normal|high|urgent)$")
    comment:  Optional[str] = Field(None, description="Add a comment on update")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _zendesk_id() -> int:
    """Zendesk uses integer IDs. Simulate that."""
    return random.randint(100000, 999999)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _fake_delay(ms: int = 120) -> None:
    """Simulate real API network latency."""
    time.sleep(ms / 1000)

def _build_ticket(zd_id: int, body: ZendeskTicketRequest) -> dict:
    """Build a Zendesk-shaped ticket dict."""
    return {
        "id":           zd_id,
        "url":          f"http://localhost:8000/mock/zendesk/ticket/{zd_id}",
        "external_id":  body.external_id,
        "subject":      body.subject,
        "description":  body.description,
        "status":       "new",
        "priority":     body.priority,
        "type":         body.type,
        "tags":         body.tags or [],
        "requester":    body.requester.model_dump() if body.requester else None,
        "created_at":   _now(),
        "updated_at":   _now(),
        "comments":     [],
    }


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@router.post("/ticket", status_code=201)
def create_zendesk_ticket(
    body: ZendeskTicketRequest,
    fail: bool = Query(False, description="Set true to simulate Zendesk API error"),
):
    """
    Simulate POST https://{subdomain}.zendesk.com/api/v2/tickets.json

    Returns the same response shape as the real Zendesk API.
    Use ?fail=true to test your error handling.
    """
    _fake_delay(120)   # simulate ~120ms network round trip

    if fail:
        raise HTTPException(
            status_code=422,
            detail={
                "error":       "RecordInvalid",
                "description": "Record validation errors",
                "details":     {"subject": [{"description": "Subject cannot be blank"}]}
            }
        )

    zd_id  = _zendesk_id()
    ticket = _build_ticket(zd_id, body)
    _tickets[str(zd_id)] = ticket

    print(f"[mock-zendesk] created ticket #{zd_id} — '{body.subject}' "
          f"(external_id={body.external_id})")

    # Real Zendesk wraps response in {"ticket": {...}}
    return {"ticket": ticket}


@router.get("/ticket/{zd_id}")
def get_zendesk_ticket(zd_id: str):
    """
    Simulate GET https://{subdomain}.zendesk.com/api/v2/tickets/{id}.json
    """
    _fake_delay(80)

    ticket = _tickets.get(zd_id)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail={"error": "RecordNotFound",
                    "description": f"Ticket {zd_id} not found"}
        )
    return {"ticket": ticket}


@router.put("/ticket/{zd_id}")
def update_zendesk_ticket(zd_id: str, body: ZendeskTicketUpdateRequest):
    """
    Simulate PUT https://{subdomain}.zendesk.com/api/v2/tickets/{id}.json
    """
    _fake_delay(100)

    ticket = _tickets.get(zd_id)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail={"error": "RecordNotFound",
                    "description": f"Ticket {zd_id} not found"}
        )

    if body.status:
        ticket["status"] = body.status
    if body.priority:
        ticket["priority"] = body.priority
    if body.comment:
        ticket["comments"].append({
            "id":         len(ticket["comments"]) + 1,
            "body":       body.comment,
            "created_at": _now(),
        })

    ticket["updated_at"] = _now()
    _tickets[zd_id] = ticket

    print(f"[mock-zendesk] updated ticket #{zd_id} → status={ticket['status']}")
    return {"ticket": ticket}


@router.get("/tickets")
def list_zendesk_tickets():
    """
    Simulate GET https://{subdomain}.zendesk.com/api/v2/tickets.json
    """
    _fake_delay(150)
    tickets = list(_tickets.values())
    return {
        "tickets": tickets,
        "count":   len(tickets),
        "next_page": None,
        "previous_page": None,
    }


@router.delete("/tickets/clear", status_code=204)
def clear_mock_tickets():
    """
    Dev-only: wipe all mock tickets from memory.
    Useful between test runs.
    """
    _tickets.clear()
    print("[mock-zendesk] all mock tickets cleared")