"""
Ticketflow — FastAPI App
-------------------------
REST API with /ticket POST endpoint wired to Celery async task.

Endpoints:
    GET  /                         → health check
    GET  /customers                → list all customers
    POST /ticket                   → create ticket + queue background task
    GET  /ticket/{number}          → get ticket by number
    GET  /tickets                  → list open tickets
    PUT  /ticket/{number}/status   → update ticket status
    GET  /task/{task_id}           → check Celery task status

Setup:
    pip install fastapi uvicorn supabase celery redis python-dotenv

Run (3 terminals):
    Terminal 1:  docker start redis
    Terminal 2:  celery -A tasks worker --loglevel=info --pool=solo
    Terminal 3:  uvicorn main:app --reload

Test:
    Open http://127.0.0.1:8000/docs
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "db"))

import time
import uuid
import logging
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from db_client import TicketflowDB
from tasks import process_ticket, celery_app
from mocks.zendesk import router as zendesk_mock_router
from mocks.shipstation import router as shipstation_mock_router
from mocks.jira import router as jira_mock_router
from mocks.statuspage import router as statuspage_mock_router

# ─────────────────────────────────────────────
# App instance
# ─────────────────────────────────────────────

app = FastAPI(
    title="Ticketflow API",
    description="Support ticket management with AI agent routing",
    version="0.1.0",
)

# ─────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────
# Allows browsers (React, Next.js, etc.) to call this API.
# In production: replace ["*"] with your actual frontend URL.
#   e.g. ["https://app.ticketflow.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # dev: allow all origins
    allow_credentials=True,
    allow_methods=["*"],       # allow GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],       # allow Authorization, Content-Type, etc.
)

# ─────────────────────────────────────────────
# Request Logging Middleware
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ticketflow")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log every request and response with timing.

    Output format:
        2025-03-07 14:23:01  INFO  → POST /ticket
        2025-03-07 14:23:01  INFO  ← 202  POST /ticket  [143ms] req_id=a3f2b1c4
    """
    req_id    = str(uuid.uuid4())[:8]
    method    = request.method
    path      = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    logger.info(f"→ {method} {path}  client={client_ip}  req_id={req_id}")

    start    = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000   # ms

    status_code = response.status_code
    level       = logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(
        level,
        f"← {status_code}  {method} {path}  [{duration:.1f}ms]  req_id={req_id}"
    )

    # Attach req_id to response headers — useful for debugging
    response.headers["X-Request-ID"] = req_id
    return response

# Mount mock Zendesk router (development only)
# Remove or guard with ENV check in production
app.include_router(zendesk_mock_router)
app.include_router(shipstation_mock_router)
app.include_router(jira_mock_router)
app.include_router(statuspage_mock_router)

# Single shared DB instance
db = TicketflowDB()


# ─────────────────────────────────────────────
# Request / Response schemas (Pydantic)
# ─────────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    """Body for POST /ticket"""
    customer_email: EmailStr          = Field(...,   description="Customer's email address")
    title:          str               = Field(...,   min_length=5, max_length=200)
    description:    Optional[str]     = Field(None,  max_length=2000)
    category:       str               = Field("general",
                                              pattern="^(billing|tech|policy|escalation|general)$")
    priority:       str               = Field("medium",
                                              pattern="^(low|medium|high|urgent)$")
    order_number:   Optional[str]     = Field(None,  description="Link to existing order e.g. ORD-2025-001")
    tags:           Optional[list[str]] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customer_email": "alice@example.com",
                    "title": "Invoice shows wrong amount",
                    "description": "My invoice for March shows ₹14999 but I was charged ₹12999.",
                    "category": "billing",
                    "priority": "high",
                    "order_number": "ORD-2025-001",
                    "tags": ["invoice", "overcharge"]
                }
            ]
        }
    }


class UpdateStatusRequest(BaseModel):
    """Body for PUT /ticket/{ticket_number}/status"""
    status:      str            = Field(..., pattern="^(open|in_progress|waiting|resolved|closed)$")
    assigned_to: Optional[str] = Field(None, description="Agent name or ID")


class TicketResponse(BaseModel):
    """Returned after creating a ticket"""
    ticket_id:      str            # UUID — use this to reference the ticket in code
    ticket_number:  str            # Human-readable e.g. TKT-2025-006
    title:          str
    category:       str
    priority:       str
    status:         str
    sla_due_at:     Optional[str]
    customer_email: Optional[str] = None
    order_number:   Optional[str] = None
    message:        Optional[str] = None
    task_id:        Optional[str] = None   # Celery task ID for polling


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Confirm the API is running."""
    return {"status": "ok", "service": "Ticketflow API", "version": "0.1.0"}


@app.get("/customers", tags=["Customers"])
def list_customers(tier: Optional[str] = None):
    """
    List all customers.
    Optional query param: ?tier=enterprise
    """
    customers = db.list_customers(tier=tier)
    return {"count": len(customers), "customers": customers}


@app.post("/ticket", status_code=status.HTTP_202_ACCEPTED,
          response_model=TicketResponse, tags=["Tickets"])
def create_ticket(body: CreateTicketRequest):
    """
    Create a support ticket and queue it for async agent processing.

    Flow:
        1. Validate request
        2. Save ticket to Supabase (status: open)
        3. Fire Celery task → returns immediately with task_id
        4. Worker picks up task → routes to agent → updates ticket in background

    Returns 202 Accepted (not 201) — ticket exists but processing is async.
    Poll GET /task/{task_id} to check processing status.
    """

    # 1. Look up customer
    customer = db.get_customer_by_email(body.customer_email)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer '{body.customer_email}' not found. Create the customer first."
        )

    # 2. Resolve optional order_number → order_id
    order_id = None
    if body.order_number:
        order = db.get_order_by_number(body.order_number)
        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Order '{body.order_number}' not found."
            )
        if order["customer_id"] != customer["id"]:
            raise HTTPException(
                status_code=400,
                detail=f"Order '{body.order_number}' does not belong to this customer."
            )
        order_id = order["id"]

    # 3. Save ticket to DB (status: open)
    ticket_number = _generate_ticket_number()

    ticket = db.create_ticket(
        customer_id=customer["id"],
        ticket_number=ticket_number,
        title=body.title,
        description=body.description,
        category=body.category,
        priority=body.priority,
        order_id=order_id,
        tags=body.tags or [],
    )

    # 4. Fire Celery task — returns instantly, worker runs in background
    task = process_ticket.delay(
        ticket_id=ticket["id"],
        ticket_number=ticket["ticket_number"],
        category=ticket["category"],
        priority=ticket["priority"],
    )

    return TicketResponse(
        ticket_id=ticket["id"],
        ticket_number=ticket["ticket_number"],
        title=ticket["title"],
        category=ticket["category"],
        priority=ticket["priority"],
        status=ticket["status"],
        sla_due_at=str(ticket.get("sla_due_at", "")),
        customer_email=body.customer_email,
        order_number=body.order_number,
        message=f"Ticket {ticket_number} created. Processing started (task_id={task.id}).",
        task_id=task.id,
    )


@app.get("/ticket/{ticket_number}", response_model=dict, tags=["Tickets"])
def get_ticket(ticket_number: str):
    """
    Fetch a single ticket by ticket number e.g. TKT-2025-001.
    Includes joined customer and order info.
    """
    ticket = db.get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket '{ticket_number}' not found."
        )
    return ticket


@app.get("/ticket/{ticket_number}/status", response_model=dict, tags=["Tickets"])
def get_ticket_status(ticket_number: str):
    """
    Lightweight status check for a ticket.
    Returns only the fields needed to track progress —
    faster than GET /ticket/{number} which fetches everything.

    Response includes:
        ticket_id      → UUID
        ticket_number  → e.g. TKT-2025-006
        status         → open | in_progress | waiting | resolved | closed
        priority       → low | medium | high | urgent
        assigned_to    → which agent is handling it (or null)
        sla_due_at     → SLA deadline
        sla_breached   → true if past due and not resolved
        resolved_at    → timestamp if resolved, else null
    """
    ticket = db.get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket '{ticket_number}' not found."
        )

    from datetime import datetime, timezone
    now         = datetime.now(timezone.utc)
    sla_due_at  = ticket.get("sla_due_at")
    resolved    = ticket["status"] in ("resolved", "closed")

    # Check if SLA is breached
    sla_breached = False
    if sla_due_at and not resolved:
        try:
            due = datetime.fromisoformat(sla_due_at.replace("Z", "+00:00"))
            sla_breached = now > due
        except Exception:
            pass

    return {
        "ticket_id":     ticket["id"],
        "ticket_number": ticket["ticket_number"],
        "status":        ticket["status"],
        "priority":      ticket["priority"],
        "assigned_to":   ticket.get("assigned_to"),
        "sla_due_at":    sla_due_at,
        "sla_breached":  sla_breached,
        "resolved_at":   ticket.get("resolved_at"),
    }


@app.get("/tickets", response_model=dict, tags=["Tickets"])
def list_open_tickets(
    category: Optional[str] = None,
    priority: Optional[str] = None,
):
    """
    List all open/in_progress tickets.
    Optional filters: ?category=billing&priority=urgent
    """
    tickets = db.get_open_tickets(category=category, priority=priority)
    return {"count": len(tickets), "tickets": tickets}


@app.put("/ticket/{ticket_number}/status", response_model=dict, tags=["Tickets"])
def update_ticket_status(ticket_number: str, body: UpdateStatusRequest):
    """
    Update the status of a ticket.
    Optionally assign to an agent.
    """
    ticket = db.get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket '{ticket_number}' not found."
        )

    updated = db.update_ticket_status(
        ticket_id=ticket["id"],
        status=body.status,
        assigned_to=body.assigned_to,
    )
    return {"message": f"Ticket {ticket_number} updated.", "ticket": updated}


@app.get("/task/{task_id}", response_model=dict, tags=["Tasks"])
def get_task_status(task_id: str):
    """
    Poll the status of a background Celery task.

    States:
        PENDING   → task queued, not yet picked up by worker
        STARTED   → worker is actively processing
        SUCCESS   → task completed — result contains agent response
        FAILURE   → task failed — result contains error message
    """
    task = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status":  task.status,
        "result":  None,
        "error":   None,
    }

    if task.status == "SUCCESS":
        response["result"] = task.result
    elif task.status == "FAILURE":
        response["error"] = str(task.result)
    elif task.status == "STARTED":
        response["result"] = task.info   # partial progress info

    return response


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _generate_ticket_number() -> str:
    """
    Generate next available TKT-XXXX-XXX number.
    Queries existing tickets to find the highest number.
    """
    from datetime import datetime
    year = datetime.now().year

    existing = db.client.table("tickets") \
        .select("ticket_number") \
        .like("ticket_number", f"TKT-{year}-%") \
        .order("ticket_number", desc=True) \
        .limit(1) \
        .execute().data

    if existing:
        last_num = int(existing[0]["ticket_number"].split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1

    return f"TKT-{year}-{str(next_num).zfill(3)}"


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)