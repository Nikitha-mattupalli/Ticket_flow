"""
Ticketflow — Celery Tasks
--------------------------
Background tasks that store and update ticket status in Supabase
at every stage of processing.

Status lifecycle managed here:
    open → in_progress → waiting → resolved
                       ↘ failed (on error) → open (retry)

Start worker:
    celery -A tasks worker --loglevel=info --pool=solo
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os
import time
import traceback
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), "db"))

import requests
from celery import Celery
from db_client import TicketflowDB

# Swap this URL for real Zendesk in production:
# ZENDESK_BASE_URL = 'https://{subdomain}.zendesk.com/api/v2'
ZENDESK_BASE_URL = os.environ.get(
    'ZENDESK_BASE_URL', 'http://localhost:8000/mock/zendesk'
)

# ─────────────────────────────────────────────
# 1. Celery app
# ─────────────────────────────────────────────

celery_app = Celery(
    "ticketflow",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    task_acks_late=True,          # only ack after task completes (safer)
    task_reject_on_worker_lost=True,  # re-queue if worker dies mid-task
)


# ─────────────────────────────────────────────
# 2. Agent routing map
# ─────────────────────────────────────────────

CATEGORY_AGENT_MAP = {
    "billing":    "billing-agent",
    "tech":       "tech-agent",
    "policy":     "policy-agent",
    "escalation": "escalation-agent",
    "general":    "general-agent",
}

# SLA windows in hours by priority
SLA_HOURS = {
    "urgent": 4,
    "high":   8,
    "medium": 24,
    "low":    72,
}


# ─────────────────────────────────────────────
# 3. Status update helper
# ─────────────────────────────────────────────

def _update_status(db: TicketflowDB, ticket_id: str, ticket_number: str,
                   status: str, note: str, author: str = "system",
                   assigned_to: str = None, is_internal: bool = True) -> None:
    """
    Update ticket status in Supabase and add a note in one call.
    All status transitions go through this function for consistency.
    """
    db.update_ticket_status(
        ticket_id=ticket_id,
        status=status,
        assigned_to=assigned_to,
    )
    db.add_note(
        ticket_id=ticket_id,
        author=author,
        body=note,
        is_internal=is_internal,
    )
    print(f"[{ticket_number}] status → {status} | {note[:60]}")


# ─────────────────────────────────────────────
# 4. Main task
# ─────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.process_ticket",
    max_retries=2,          # retry up to 2 times on failure
    default_retry_delay=10, # wait 10s between retries
)
def process_ticket(self, ticket_id: str, ticket_number: str,
                   category: str, priority: str) -> dict:
    """
    Process a ticket through the full status lifecycle:

        open → in_progress → waiting → (resolved by agent/human)

    Supabase is updated at every transition so the status is
    always accurate regardless of which stage the task is at.

    Args:
        ticket_id:     UUID of the ticket row
        ticket_number: e.g. TKT-2025-006
        category:      billing | tech | policy | escalation | general
        priority:      low | medium | high | urgent
    """
    db = TicketflowDB()
    agent = CATEGORY_AGENT_MAP.get(category, "general-agent")

    try:

        # ── Stage 1: in_progress ──────────────────────────────────────
        # Ticket has been picked up by the worker
        self.update_state(
            state="STARTED",
            meta={"step": "routing", "ticket": ticket_number, "agent": agent}
        )

        _update_status(
            db, ticket_id, ticket_number,
            status="in_progress",
            assigned_to=agent,
            note=(
                f"Ticket picked up by worker. "
                f"Auto-routing to {agent} based on category='{category}', "
                f"priority='{priority}'."
            ),
            author="system",
            is_internal=True,
        )


        # ── Stage 2: agent processing ─────────────────────────────────
        # Simulate the agent doing work
        # Replace this block with your actual LangGraph agent call:
        #
        #   from agents.langgraph_agent import run_agent
        #   agent_result = run_agent(ticket_id, category, priority)
        #
        self.update_state(
            state="STARTED",
            meta={"step": "processing", "ticket": ticket_number, "agent": agent}
        )

        time.sleep(1)  # placeholder — remove when real agent is wired in

        agent_response = (
            f"Thank you for contacting support. Your {category} request "
            f"(Ticket {ticket_number}) has been received and assigned to our "
            f"{agent}. Based on your priority level '{priority}', "
            f"you can expect a response within {SLA_HOURS.get(priority, 24)} hours."
        )


        # ── Stage 3: sync to Zendesk ──────────────────────────────────
        self.update_state(
            state="STARTED",
            meta={"step": "syncing_zendesk", "ticket": ticket_number}
        )

        zd_ticket_id = None
        try:
            zd_resp = requests.post(
                f"{ZENDESK_BASE_URL}/ticket",
                json={
                    "subject":     ticket_number + " - " + category,
                    "description": agent_response,
                    "priority":    priority if priority in ('low','normal','high','urgent') else 'normal',
                    "type":        "problem",
                    "tags":        [category],
                    "external_id": ticket_number,
                },
                timeout=10,
            )
            if zd_resp.status_code == 201:
                zd_ticket_id = zd_resp.json()["ticket"]["id"]
                db.add_note(
                    ticket_id=ticket_id,
                    author="system",
                    body=f"Synced to Zendesk — ticket #{zd_ticket_id}",
                    is_internal=True,
                )
                print(f"[{ticket_number}] synced to Zendesk #{zd_ticket_id}")
            else:
                print(f"[{ticket_number}] Zendesk sync failed: {zd_resp.status_code}")
        except Exception as zd_err:
            print(f"[{ticket_number}] Zendesk unreachable: {zd_err} — continuing")

        # ── Stage 4: waiting ──────────────────────────────────────────
        # Agent has responded, waiting for customer or further action
        self.update_state(
            state="STARTED",
            meta={"step": "waiting", "ticket": ticket_number}
        )

        _update_status(
            db, ticket_id, ticket_number,
            status="waiting",
            assigned_to=agent,
            note=agent_response,
            author=agent,
            is_internal=False,  # customer-visible reply
        )

        # ── Done ──────────────────────────────────────────────────────
        result = {
            "ticket_number":   ticket_number,
            "ticket_id":       ticket_id,
            "agent":           agent,
            "final_status":    "waiting",
            "response":        agent_response,
            "zendesk_id":      zd_ticket_id,
            "processed_at":    datetime.now(timezone.utc).isoformat(),
        }

        print(f"[{ticket_number}] ✅ processing complete → waiting for customer")
        return result


    except Exception as exc:
        # ── Error handling ────────────────────────────────────────────
        # Log what went wrong, revert ticket to open so it can be retried

        error_msg = f"Processing failed: {str(exc)}"
        tb        = traceback.format_exc()

        print(f"[{ticket_number}] ❌ error: {error_msg}")
        print(tb)

        # Write error note to Supabase
        try:
            _update_status(
                db, ticket_id, ticket_number,
                status="open",          # revert — ticket needs attention
                note=f"[ERROR] {error_msg}. Retrying... (attempt {self.request.retries + 1}/3)",
                author="system",
                is_internal=True,
            )
        except Exception:
            pass  # don't let note-writing failure mask the original error

        # Retry if attempts remain, otherwise give up
        raise self.retry(exc=exc) if self.request.retries < self.max_retries \
              else exc


# ─────────────────────────────────────────────
# 5. Resolve task (called manually or by agent)
# ─────────────────────────────────────────────

@celery_app.task(name="tasks.resolve_ticket")
def resolve_ticket(ticket_id: str, ticket_number: str,
                   resolution: str, resolved_by: str) -> dict:
    """
    Mark a ticket as resolved.
    Can be triggered by an agent, human, or another task.
    """
    db = TicketflowDB()

    _update_status(
        db, ticket_id, ticket_number,
        status="resolved",
        assigned_to=resolved_by,
        note=f"Resolved: {resolution}",
        author=resolved_by,
        is_internal=False,
    )

    print(f"[{ticket_number}] ✅ resolved by {resolved_by}")

    return {
        "ticket_number": ticket_number,
        "status":        "resolved",
        "resolved_by":   resolved_by,
        "resolved_at":   datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────
# 6. Quick test (run directly to verify)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Firing test task — make sure worker is running")
    print("  celery -A tasks worker --loglevel=info --pool=solo\n")

    # Get a real ticket from DB to test with
    db   = TicketflowDB()
    tickets = db.get_open_tickets()

    if not tickets:
        print("No open tickets found. Run seed.py or POST /ticket first.")
        exit(1)

    t = tickets[0]
    print(f"Using ticket: {t['ticket_number']} | {t['category']} | {t['priority']}")

    result = process_ticket.delay(
        ticket_id=t["id"],
        ticket_number=t["ticket_number"],
        category=t["category"],
        priority=t["priority"],
    )

    print(f"Task ID : {result.id}")
    print(f"Status  : {result.status}")

    output = result.get(timeout=15)
    print(f"\nResult  : {output}")
    print(f"Status  : {result.status}")
    print(f"\nCheck Supabase → tickets → {t['ticket_number']}")
    print(f"  status should be : waiting")
    print(f"  assigned_to      : {CATEGORY_AGENT_MAP.get(t['category'])}")
    print(f"Check Supabase → ticket_notes for 2 new rows")