"""
Seed Supabase: 10 Test Invoices tied to Customers
---------------------------------------------------
Run migration 007_create_invoices.sql in Supabase first,
then run this script.

Setup:
    pip install supabase python-dotenv

    In .env:
        SUPABASE_URL=https://your-project.supabase.co
        SUPABASE_KEY=your-service-role-key

Run:
    python seed_invoices.py
"""

from dotenv import load_dotenv
load_dotenv()

import os
import random
from datetime import datetime, timedelta, timezone
from supabase import create_client


# ─────────────────────────────────────────────
# 1. Client
# ─────────────────────────────────────────────

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(url, key)
print("✅ Supabase connected")


# ─────────────────────────────────────────────
# 2. Fetch existing customers + orders
# ─────────────────────────────────────────────

customers = supabase.table("customers").select("id, name, email, tier").execute().data
orders    = supabase.table("orders").select("id, customer_id, order_number, total_amount, currency, status").execute().data

if not customers:
    print("❌ No customers found. Run seed.py first.")
    exit(1)

print(f"   Found {len(customers)} customers, {len(orders)} orders")

# Index orders by customer_id for quick lookup
orders_by_customer: dict[str, list] = {}
for o in orders:
    cid = o["customer_id"]
    orders_by_customer.setdefault(cid, []).append(o)


# ─────────────────────────────────────────────
# 3. Invoice number helper
# ─────────────────────────────────────────────

def next_invoice_number() -> str:
    """Find the next available INV-2025-XXX number."""
    existing = supabase.table("invoices").select("invoice_number").execute().data
    existing_nums = {e["invoice_number"] for e in existing}
    i = 1
    while True:
        candidate = f"INV-2025-{str(i).zfill(3)}"
        if candidate not in existing_nums:
            return candidate
        i += 1


def random_date_offset(base: datetime, days_min: int, days_max: int) -> str:
    delta = timedelta(days=random.randint(days_min, days_max))
    return (base + delta).isoformat()


# ─────────────────────────────────────────────
# 4. Define 10 test invoices
# ─────────────────────────────────────────────
# Mix of statuses, amounts, currencies, linked/unlinked orders

now = datetime.now(timezone.utc)

# Pick 10 customers (all if < 10, else random sample)
sample_customers = random.sample(customers, min(10, len(customers)))

INVOICE_TEMPLATES = [
    # (description,               subtotal,  currency, status,   days_issued_ago, days_due_from_issue, paid_offset_days)
    ("Pro Plan — Monthly",        1999.00,  "INR",    "paid",    30,  30,   5),
    ("Team Plan — Annual",       49999.00,  "INR",    "paid",    60,  30,  10),
    ("Enterprise License",       99999.00,  "INR",    "unpaid",  10,  30,  None),
    ("API Add-on",                2499.00,  "INR",    "overdue", 45,  14,  None),
    ("Storage Upgrade 100GB",      999.00,  "INR",    "paid",    20,  30,   3),
    ("Priority Support Package",  7999.00,  "INR",    "unpaid",   5,  30,  None),
    ("Custom Integration Setup", 14999.00,  "USD",    "paid",    90,  45,  15),
    ("Onboarding Package",        4499.00,  "INR",    "void",    15,  30,  None),
    ("Pro Plan — Annual",        19999.00,  "INR",    "overdue", 50,  14,  None),
    ("Team Plan — Monthly",       4999.00,  "USD",    "draft",    2,  30,  None),
]

invoices_to_insert = []

for idx, (customer, template) in enumerate(zip(sample_customers, INVOICE_TEMPLATES)):
    desc, subtotal, currency, status, days_ago, due_days, paid_offset = template

    issued_at = now - timedelta(days=days_ago)
    due_at    = issued_at + timedelta(days=due_days)
    paid_at   = (issued_at + timedelta(days=paid_offset)).isoformat() if paid_offset else None

    # Link to an existing order for this customer if available
    customer_orders = orders_by_customer.get(customer["id"], [])
    linked_order    = random.choice(customer_orders) if customer_orders else None

    # Adjust subtotal to match order amount if linked
    if linked_order and currency == linked_order["currency"]:
        subtotal = float(linked_order["total_amount"])

    invoice = {
        "customer_id":     customer["id"],
        "order_id":        linked_order["id"] if linked_order else None,
        "invoice_number":  f"INV-2025-{str(idx + 1).zfill(3)}",
        "status":          status,
        "subtotal":        subtotal,
        "tax_rate":        0.18 if currency == "INR" else 0.00,
        "currency":        currency,
        "description":     desc,
        "issued_at":       issued_at.isoformat(),
        "due_at":          due_at.isoformat(),
        "paid_at":         paid_at,
    }
    invoices_to_insert.append(invoice)


# ─────────────────────────────────────────────
# 5. Insert
# ─────────────────────────────────────────────

print("\n── Inserting 10 invoices ──")

res = supabase.table("invoices").upsert(
    invoices_to_insert,
    on_conflict="invoice_number",
    ignore_duplicates=True,
).execute()

inserted = res.data
print(f"   Inserted : {len(inserted)} invoices")


# ─────────────────────────────────────────────
# 6. Verify — print full summary table
# ─────────────────────────────────────────────

print("\n" + "=" * 80)
print("INVOICE SUMMARY")
print("=" * 80)
print(f"  {'Invoice':14} {'Customer':20} {'Status':8} {'Subtotal':>12} {'Tax':>10} {'Total':>12} {'Curr':5} {'Linked Order'}")
print("-" * 80)

all_invoices = supabase.table("invoices") \
    .select("*, customers(name), orders(order_number)") \
    .order("invoice_number") \
    .execute().data

for inv in all_invoices:
    customer_name = inv["customers"]["name"][:18] if inv.get("customers") else "?"
    order_num     = inv["orders"]["order_number"] if inv.get("orders") else "—"
    print(
        f"  {inv['invoice_number']:14} "
        f"{customer_name:20} "
        f"{inv['status']:8} "
        f"₹{inv['subtotal']:>10,.2f} "
        f"₹{inv['tax_amount']:>8,.2f} "
        f"₹{inv['total_amount']:>10,.2f} "
        f"{inv['currency']:5} "
        f"{order_num}"
    )

# Status breakdown
print(f"\n{'─' * 80}")
status_counts = {}
for inv in all_invoices:
    status_counts[inv["status"]] = status_counts.get(inv["status"], 0) + 1

print("Status breakdown:")
for status, count in sorted(status_counts.items()):
    print(f"  {status:8} : {count}")

# Total revenue collected (paid invoices)
paid = [i for i in all_invoices if i["status"] == "paid" and i["currency"] == "INR"]
collected = sum(i["total_amount"] for i in paid)
print(f"\nINR collected (paid invoices): ₹{collected:,.2f}")

overdue = [i for i in all_invoices if i["status"] == "overdue"]
print(f"Overdue invoices             : {len(overdue)}")

print(f"\n✅ Done. View in Supabase → Table Editor → invoices")