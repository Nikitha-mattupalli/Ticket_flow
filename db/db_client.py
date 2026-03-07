"""
Ticketflow — Supabase Python DB Client
----------------------------------------
A clean wrapper around supabase-py for all
CRUD operations on customers, orders, tickets, ticket_notes.

Setup:
    pip install supabase python-dotenv

    In .env add:
        SUPABASE_URL=https://your-project.supabase.co
        SUPABASE_KEY=your-anon-or-service-role-key

    Find these in Supabase → Project Settings → API

Usage:
    from db_client import TicketflowDB

    db = TicketflowDB()

    # customers
    customer = db.create_customer("Alice", "alice@example.com", tier="enterprise")
    customer = db.get_customer_by_email("alice@example.com")

    # tickets
    ticket = db.create_ticket(customer_id=customer["id"], title="Invoice wrong", category="billing")
    tickets = db.get_open_tickets()
    db.update_ticket_status(ticket["id"], "resolved")
"""

from dotenv import load_dotenv
load_dotenv()

import os
from typing import Optional
from supabase import create_client, Client


# ─────────────────────────────────────────────
# Client
# ─────────────────────────────────────────────

class TicketflowDB:

    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env\n"
                "Find them in Supabase → Project Settings → API"
            )

        self.client: Client = create_client(url, key)
        print("✅ Supabase connected")


    # ─────────────────────────────────────────
    # CUSTOMERS
    # ─────────────────────────────────────────

    def create_customer(
        self,
        name:  str,
        email: str,
        phone: Optional[str] = None,
        tier:  str = "standard",
    ) -> dict:
        """Insert a new customer. Returns the created row."""
        res = self.client.table("customers").insert({
            "name":  name,
            "email": email,
            "phone": phone,
            "tier":  tier,
        }).execute()
        return res.data[0]

    def get_customer_by_email(self, email: str) -> Optional[dict]:
        """Fetch a single customer by email."""
        res = self.client.table("customers") \
            .select("*") \
            .eq("email", email) \
            .limit(1) \
            .execute()
        data = res.data
        return data[0] if data else None

    def get_customer_by_id(self, customer_id: str) -> Optional[dict]:
        """Fetch a single customer by UUID."""
        res = self.client.table("customers") \
            .select("*") \
            .eq("id", customer_id) \
            .limit(1) \
            .execute()
        data = res.data
        return data[0] if data else None

    def list_customers(self, tier: Optional[str] = None) -> list:
        """List all customers, optionally filtered by tier."""
        query = self.client.table("customers").select("*")
        if tier:
            query = query.eq("tier", tier)
        return query.order("created_at", desc=True).execute().data


    # ─────────────────────────────────────────
    # ORDERS
    # ─────────────────────────────────────────

    def create_order(
        self,
        customer_id:   str,
        order_number:  str,
        total_amount:  float,
        currency:      str = "INR",
        status:        str = "pending",
        notes:         Optional[str] = None,
    ) -> dict:
        """Insert a new order. Returns the created row."""
        res = self.client.table("orders").insert({
            "customer_id":  customer_id,
            "order_number": order_number,
            "total_amount": total_amount,
            "currency":     currency,
            "status":       status,
            "notes":        notes,
        }).execute()
        return res.data[0]

    def get_order_by_number(self, order_number: str) -> Optional[dict]:
        """Fetch a single order by order_number e.g. ORD-2025-001."""
        res = self.client.table("orders") \
            .select("*") \
            .eq("order_number", order_number) \
            .limit(1) \
            .execute()
        data = res.data
        return data[0] if data else None

    def get_orders_for_customer(self, customer_id: str) -> list:
        """All orders belonging to a customer."""
        return self.client.table("orders") \
            .select("*") \
            .eq("customer_id", customer_id) \
            .order("placed_at", desc=True) \
            .execute().data

    def update_order_status(self, order_id: str, status: str) -> dict:
        """Update the status of an order. Returns updated row."""
        res = self.client.table("orders") \
            .update({"status": status}) \
            .eq("id", order_id) \
            .execute()
        return res.data[0]


    # ─────────────────────────────────────────
    # TICKETS
    # ─────────────────────────────────────────

    def create_ticket(
        self,
        customer_id:   str,
        ticket_number: str,
        title:         str,
        category:      str = "general",
        priority:      str = "medium",
        description:   Optional[str] = None,
        order_id:      Optional[str] = None,
        tags:          Optional[list] = None,
    ) -> dict:
        """Insert a new ticket. sla_due_at is auto-set by DB trigger."""
        res = self.client.table("tickets").insert({
            "customer_id":   customer_id,
            "order_id":      order_id,
            "ticket_number": ticket_number,
            "title":         title,
            "description":   description,
            "category":      category,
            "priority":      priority,
            "tags":          tags or [],
        }).execute()
        return res.data[0]

    def get_ticket_by_number(self, ticket_number: str) -> Optional[dict]:
        """Fetch a single ticket by ticket_number e.g. TKT-2025-001."""
        res = self.client.table("tickets") \
            .select("*, customers(name, email, tier), orders(order_number, status)") \
            .eq("ticket_number", ticket_number) \
            .limit(1) \
            .execute()
        data = res.data
        return data[0] if data else None

    def get_open_tickets(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list:
        """All open/in_progress tickets, optionally filtered."""
        query = self.client.table("tickets") \
            .select("*, customers(name, email, tier)") \
            .in_("status", ["open", "in_progress"])

        if category:
            query = query.eq("category", category)
        if priority:
            query = query.eq("priority", priority)

        return query.order("created_at", desc=True).execute().data

    def get_tickets_for_customer(self, customer_id: str) -> list:
        """All tickets raised by a specific customer."""
        return self.client.table("tickets") \
            .select("*") \
            .eq("customer_id", customer_id) \
            .order("created_at", desc=True) \
            .execute().data

    def update_ticket_status(
        self,
        ticket_id:   str,
        status:      str,
        assigned_to: Optional[str] = None,
    ) -> dict:
        """Update ticket status (and optionally assign to an agent)."""
        payload = {"status": status}
        if assigned_to:
            payload["assigned_to"] = assigned_to
        if status == "resolved":
            payload["resolved_at"] = "now()"

        res = self.client.table("tickets") \
            .update(payload) \
            .eq("id", ticket_id) \
            .execute()
        return res.data[0]

    def get_breached_tickets(self) -> list:
        """Tickets past their SLA deadline that are not yet resolved."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        return self.client.table("tickets") \
            .select("*, customers(name, email, tier)") \
            .lt("sla_due_at", now) \
            .not_.in_("status", ["resolved", "closed"]) \
            .order("sla_due_at") \
            .execute().data


    # ─────────────────────────────────────────
    # TICKET NOTES
    # ─────────────────────────────────────────

    def add_note(
        self,
        ticket_id:   str,
        author:      str,
        body:        str,
        is_internal: bool = True,
    ) -> dict:
        """Add an internal note or customer-visible reply to a ticket."""
        res = self.client.table("ticket_notes").insert({
            "ticket_id":   ticket_id,
            "author":      author,
            "body":        body,
            "is_internal": is_internal,
        }).execute()
        return res.data[0]

    def get_notes_for_ticket(
        self,
        ticket_id:        str,
        include_internal: bool = True,
    ) -> list:
        """Fetch all notes for a ticket, newest last."""
        query = self.client.table("ticket_notes") \
            .select("*") \
            .eq("ticket_id", ticket_id)

        if not include_internal:
            query = query.eq("is_internal", False)

        return query.order("created_at").execute().data


# ─────────────────────────────────────────────
# Quick smoke test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    db = TicketflowDB()

    print("\n── Customers ──")
    customers = db.list_customers()
    for c in customers:
        print(f"  {c['name']:15} | {c['tier']:10} | {c['email']}")

    print("\n── Open Tickets ──")
    tickets = db.get_open_tickets()
    for t in tickets:
        customer_name = t.get("customers", {}).get("name", "?") if t.get("customers") else "?"
        print(f"  {t['ticket_number']} | {t['priority']:6} | {t['category']:10} | {t['title'][:40]} | {customer_name}")

    print("\n── Breached SLA Tickets ──")
    breached = db.get_breached_tickets()
    if breached:
        for t in breached:
            print(f"  {t['ticket_number']} | due: {t['sla_due_at']} | {t['title']}")
    else:
        print("  No breached tickets (all within SLA)")

    print("\n── Ticket Notes: TKT-2025-002 ──")
    ticket = db.get_ticket_by_number("TKT-2025-002")
    if ticket:
        notes = db.get_notes_for_ticket(ticket["id"])
        for n in notes:
            print(f"  [{n['author']}] {n['body'][:60]}")