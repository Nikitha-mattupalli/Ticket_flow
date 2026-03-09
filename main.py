"""
Ticketflow — FastAPI App
-------------------------
REST API skeleton with /ticket POST endpoint.

Endpoints:
    GET  /             → health check
    GET  /customers    → list all customers
    POST /ticket       → create a new ticket
    GET  /ticket/{id}  → get ticket by number
    PUT  /ticket/{id}/status → update ticket status

Setup:
    pip install fastapi uvicorn supabase python-dotenv

Run:
    uvicorn main:app --reload

    --reload means the server restarts automatically when you save changes.

Test:
    Open http://127.0.0.1:8000/docs  ← auto-generated interactive API docs
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os

# Allow imports from db/ folder
sys.path.append(os.path.join(os.path.dirname(__file__), "db"))

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from db_client import TicketflowDB

# ─────────────────────────────────────────────
# App instance
# ─────────────────────────────────────────────

app = FastAPI(
    title="Ticketflow API",
    description="Support ticket management with AI agent routing",
    version="0.1.0",
)

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
    """Returned after creating or fetching a ticket"""
    ticket_number: str
    title:         str
    category:      str
    priority:      str
    status:        str
    sla_due_at:    Optional[str]
    customer_email: Optional[str] = None
    order_number:   Optional[str] = None
    message:        Optional[str] = None


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


@app.post("/ticket", status_code=status.HTTP_201_CREATED,
          response_model=TicketResponse, tags=["Tickets"])
def create_ticket(body: CreateTicketRequest):
    """
    Create a new support ticket.

    - Looks up the customer by email (must exist)
    - Optionally links to an order by order_number
    - Auto-generates ticket_number (TKT-XXXXX)
    - sla_due_at is set automatically by the DB trigger
    """

    # 1. Look up customer
    customer = db.get_customer_by_email(body.customer_email)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with email '{body.customer_email}' not found. "
                   "Create the customer first."
        )

    # 2. Optionally resolve order_number → order_id
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

    # 3. Generate ticket number
    ticket_number = _generate_ticket_number()

    # 4. Create ticket
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

    return TicketResponse(
        ticket_number=ticket["ticket_number"],
        title=ticket["title"],
        category=ticket["category"],
        priority=ticket["priority"],
        status=ticket["status"],
        sla_due_at=str(ticket.get("sla_due_at", "")),
        customer_email=body.customer_email,
        order_number=body.order_number,
        message=f"Ticket {ticket_number} created successfully.",
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