"""
Integration Test: POST /ticket → Celery fires → Supabase status updates
-------------------------------------------------------------------------
Tests the full async pipeline end to end:

    1. POST /ticket via HTTP          → API accepts, returns 202 + task_id
    2. Celery picks up task           → status: open → in_progress
    3. Agent processes ticket         → status: in_progress → waiting
    4. GET /ticket/{number}/status    → confirms final status in Supabase
    5. GET /task/{task_id}            → confirms Celery task SUCCESS
    6. GET /ticket/{number}           → confirms notes were written

Prerequisites:
    Terminal 1: docker start redis
    Terminal 2: celery -A tasks worker --loglevel=info --pool=solo
    Terminal 3: uvicorn main:app --reload

    Seed data must be loaded (python db/seed.py)

Run:
    python tests/test_integration.py

    # Verbose mode — prints full API responses
    python tests/test_integration.py --verbose

    # Skip cleanup — leaves test ticket in Supabase for manual inspection
    python tests/test_integration.py --no-cleanup
"""

import sys
import os
import time
import argparse
import requests
from datetime import datetime, timezone

# ── Allow running from any directory ────────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "db"))
from db_client import TicketflowDB

# ── Config ───────────────────────────────────────────────
BASE_URL        = "http://127.0.0.1:8000"
POLL_INTERVAL   = 1.0    # seconds between status polls
TASK_TIMEOUT    = 20     # seconds to wait for Celery task
STATUS_TIMEOUT  = 15     # seconds to wait for DB status change


# ════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
NC     = "\033[0m"

def ok(msg):    print(f"{GREEN}  ✅ {msg}{NC}")
def fail(msg):  print(f"{RED}  ❌ {msg}{NC}"); sys.exit(1)
def warn(msg):  print(f"{YELLOW}  ⚠  {msg}{NC}")
def info(msg):  print(f"{CYAN}  ·  {msg}{NC}")
def section(msg): print(f"\n{'═'*55}\n  {msg}\n{'═'*55}")

VERBOSE = False

def dump(label: str, data: dict):
    if VERBOSE:
        import json
        print(f"\n  [{label}]")
        print("  " + json.dumps(data, indent=2, default=str).replace("\n", "\n  "))


def get(path: str) -> dict:
    r = requests.get(f"{BASE_URL}{path}", timeout=10)
    return r.status_code, r.json()


def post(path: str, body: dict) -> tuple:
    r = requests.post(f"{BASE_URL}{path}", json=body, timeout=10)
    return r.status_code, r.json()


def put(path: str, body: dict) -> tuple:
    r = requests.put(f"{BASE_URL}{path}", json=body, timeout=10)
    return r.status_code, r.json()


def wait_for_task(task_id: str, timeout: int) -> dict:
    """Poll GET /task/{id} until SUCCESS or FAILURE or timeout."""
    info(f"Polling task {task_id} (timeout={timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, data = get(f"/task/{task_id}")
        status = data.get("status")
        info(f"  task status = {status}")
        if status == "SUCCESS":
            return data
        if status == "FAILURE":
            fail(f"Celery task failed: {data.get('error')}")
        time.sleep(POLL_INTERVAL)
    fail(f"Task {task_id} did not complete within {timeout}s — is Celery worker running?")


def wait_for_ticket_status(ticket_number: str, expected: str, timeout: int) -> dict:
    """Poll GET /ticket/{number}/status until expected status or timeout."""
    info(f"Waiting for ticket {ticket_number} → status='{expected}' (timeout={timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, data = get(f"/ticket/{ticket_number}/status")
        current = data.get("status")
        info(f"  ticket status = {current}")
        if current == expected:
            return data
        time.sleep(POLL_INTERVAL)
    fail(
        f"Ticket {ticket_number} never reached status='{expected}' within {timeout}s.\n"
        f"  Last status: {current}\n"
        f"  Is Celery worker running?"
    )


# ════════════════════════════════════════════════════════
# Test cases
# ════════════════════════════════════════════════════════

def test_api_health():
    section("1. API Health Check")
    code, data = get("/")
    if code != 200:
        fail(f"API not responding — start uvicorn first (got {code})")
    ok(f"API is up — {data.get('service')} v{data.get('version')}")


def test_seed_data(db: TicketflowDB) -> dict:
    section("2. Seed Data Check")
    customers = db.list_customers()
    if not customers:
        fail("No customers found — run: python db/seed.py")
    ok(f"Found {len(customers)} customers in Supabase")

    # Pick first customer with a known email
    customer = customers[0]
    info(f"Using customer: {customer['name']} ({customer['email']}) [{customer['tier']}]")
    return customer


def test_post_ticket(customer: dict) -> tuple[str, str, str]:
    section("3. POST /ticket — Create Ticket")

    payload = {
        "customer_email": customer["email"],
        "title":          "Integration test — billing query on invoice",
        "description":    "This is an automated integration test ticket. Safe to delete.",
        "category":       "billing",
        "priority":       "high",
        "tags":           ["integration-test", "auto-generated"],
    }

    info(f"POSTing ticket for {customer['email']}...")
    code, data = post("/ticket", payload)
    dump("POST /ticket response", data)

    if code != 202:
        fail(f"Expected 202 Accepted, got {code}: {data}")

    ticket_number = data.get("ticket_number")
    ticket_id     = data.get("ticket_id")
    task_id       = data.get("task_id")

    if not ticket_number:
        fail(f"No ticket_number in response: {data}")
    if not ticket_id:
        fail(f"No ticket_id in response: {data}")
    if not task_id:
        fail(f"No task_id in response — is Celery wired in main.py?")

    ok(f"Ticket created: {ticket_number}")
    ok(f"ticket_id:      {ticket_id}")
    ok(f"task_id:        {task_id}")
    info(f"Initial status: {data.get('status')}")

    return ticket_number, ticket_id, task_id


def test_initial_status(ticket_number: str):
    section("4. Verify Initial Status = 'open'")

    code, data = get(f"/ticket/{ticket_number}/status")
    dump(f"GET /ticket/{ticket_number}/status", data)

    if code != 200:
        fail(f"Expected 200, got {code}")

    status = data.get("status")
    if status != "open":
        warn(f"Expected 'open' immediately after creation, got '{status}'")
        info("This is fine if Celery picked it up very fast")
    else:
        ok(f"Status is 'open' immediately after creation ✓")

    ok(f"ticket_id present: {bool(data.get('ticket_id'))}")
    ok(f"sla_due_at present: {bool(data.get('sla_due_at'))}")


def test_celery_task(task_id: str):
    section("5. Celery Task — Wait for SUCCESS")

    result = wait_for_task(task_id, timeout=TASK_TIMEOUT)
    dump("Task result", result)

    ok(f"Task completed with status: {result['status']}")

    task_result = result.get("result", {})
    if task_result:
        ok(f"Agent assigned:  {task_result.get('agent')}")
        ok(f"Final status:    {task_result.get('final_status')}")
        ok(f"Zendesk ID:      {task_result.get('zendesk_id', 'n/a')}")


def test_status_updated_in_supabase(ticket_number: str):
    section("6. Supabase Status Update — Verify 'waiting'")
    # After Celery completes, ticket should be 'waiting'
    data = wait_for_ticket_status(ticket_number, "waiting", timeout=STATUS_TIMEOUT)
    dump(f"Final status check", data)

    ok(f"Status updated to 'waiting' in Supabase ✓")
    ok(f"assigned_to: {data.get('assigned_to')}")
    ok(f"sla_breached: {data.get('sla_breached')}")


def test_notes_written(ticket_number: str, db: TicketflowDB):
    section("7. Ticket Notes — Verify Written by Worker")

    ticket = db.get_ticket_by_number(ticket_number)
    if not ticket:
        fail(f"Ticket {ticket_number} not found in Supabase")

    notes = db.get_notes_for_ticket(ticket["id"])
    dump("Notes", notes)

    if len(notes) < 2:
        fail(
            f"Expected at least 2 notes (routing + agent response), "
            f"found {len(notes)}. Is Celery worker running?"
        )

    ok(f"Found {len(notes)} notes written by Celery worker:")
    for note in notes:
        tag = "🔒 internal" if note["is_internal"] else "👤 customer"
        print(f"     [{tag}] {note['author']}: {note['body'][:70]}...")


def test_full_ticket_response(ticket_number: str):
    section("8. GET /ticket/{number} — Full Response")

    code, data = get(f"/ticket/{ticket_number}")
    dump(f"GET /ticket/{ticket_number}", data)

    if code != 200:
        fail(f"Expected 200, got {code}")

    ok(f"Full ticket fetch: 200 OK")
    ok(f"Title:    {data.get('title')}")
    ok(f"Status:   {data.get('status')}")
    ok(f"Category: {data.get('category')}")

    # Verify joined customer data came through
    customer_data = data.get("customers")
    if customer_data:
        ok(f"Customer join: {customer_data.get('name')} [{customer_data.get('tier')}]")
    else:
        warn("No joined customer data — check db_client select query")


def test_manual_resolve(ticket_number: str):
    section("9. PUT /ticket/{number}/status — Manual Resolve")

    code, data = put(f"/ticket/{ticket_number}/status", {
        "status":      "resolved",
        "assigned_to": "integration-test",
    })
    dump("PUT /status response", data)

    if code != 200:
        fail(f"Expected 200, got {code}")

    ok("Ticket manually resolved via API ✓")

    # Verify in DB
    code, data = get(f"/ticket/{ticket_number}/status")
    if data.get("status") != "resolved":
        fail(f"Expected 'resolved', got '{data.get('status')}'")
    ok("Confirmed status='resolved' in Supabase ✓")


def test_error_cases():
    section("10. Error Cases — 404 and 422")

    # Unknown customer
    code, data = post("/ticket", {
        "customer_email": "nobody@nowhere-fake.com",
        "title":          "This should return 404",
        "category":       "general",
        "priority":       "low",
    })
    if code == 404:
        ok("Unknown customer → 404 ✓")
    else:
        warn(f"Expected 404 for unknown customer, got {code}")

    # Title too short (Pydantic validation)
    code, data = post("/ticket", {
        "customer_email": "test@example.com",
        "title":          "Hi",
        "category":       "billing",
        "priority":       "low",
    })
    if code == 422:
        ok("Title too short → 422 Unprocessable ✓")
    else:
        warn(f"Expected 422 for short title, got {code}")

    # Invalid category
    code, data = post("/ticket", {
        "customer_email": "test@example.com",
        "title":          "Valid title here",
        "category":       "invalid_category",
        "priority":       "low",
    })
    if code == 422:
        ok("Invalid category → 422 Unprocessable ✓")
    else:
        warn(f"Expected 422 for invalid category, got {code}")


# ════════════════════════════════════════════════════════
# Cleanup
# ════════════════════════════════════════════════════════

def cleanup(ticket_number: str, db: TicketflowDB):
    section("Cleanup")
    try:
        db.client.table("ticket_notes") \
            .delete() \
            .eq("ticket_id",
                db.get_ticket_by_number(ticket_number)["id"]) \
            .execute()
        db.client.table("tickets") \
            .delete() \
            .eq("ticket_number", ticket_number) \
            .execute()
        ok(f"Deleted test ticket {ticket_number} and its notes from Supabase")
    except Exception as e:
        warn(f"Cleanup failed: {e}")
        info(f"Manual cleanup: DELETE FROM tickets WHERE ticket_number = '{ticket_number}';")


# ════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════

def main():
    global VERBOSE

    parser = argparse.ArgumentParser(description="Ticketflow integration tests")
    parser.add_argument("--verbose",    action="store_true", help="Print full API responses")
    parser.add_argument("--no-cleanup", action="store_true", help="Leave test ticket in Supabase")
    args = parser.parse_args()
    VERBOSE = args.verbose

    print(f"\n{'═'*55}")
    print(f"  Ticketflow Integration Test")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'═'*55}")
    print(f"  BASE_URL      : {BASE_URL}")
    print(f"  TASK_TIMEOUT  : {TASK_TIMEOUT}s")
    print(f"  STATUS_TIMEOUT: {STATUS_TIMEOUT}s")

    db             = TicketflowDB()
    ticket_number  = None

    try:
        test_api_health()
        customer       = test_seed_data(db)
        ticket_number, ticket_id, task_id = test_post_ticket(customer)
        test_initial_status(ticket_number)
        test_celery_task(task_id)
        test_status_updated_in_supabase(ticket_number)
        test_notes_written(ticket_number, db)
        test_full_ticket_response(ticket_number)
        test_manual_resolve(ticket_number)
        test_error_cases()

        print(f"\n{'═'*55}")
        print(f"{GREEN}  All integration tests passed ✅{NC}")
        print(f"{'═'*55}\n")

    except SystemExit:
        print(f"\n{'═'*55}")
        print(f"{RED}  Integration test FAILED ❌{NC}")
        print(f"{'═'*55}\n")
        print("  Checklist:")
        print("  [ ] docker start redis")
        print("  [ ] celery -A tasks worker --loglevel=info --pool=solo")
        print("  [ ] uvicorn main:app --reload")
        print("  [ ] python db/seed.py\n")

    finally:
        if ticket_number and not args.no_cleanup:
            cleanup(ticket_number, db)
        elif ticket_number:
            warn(f"Skipping cleanup — ticket {ticket_number} left in Supabase")


if __name__ == "__main__":
    main()