"""
Seed Supabase: 20 Customers + 30 Orders
-----------------------------------------
Inserts realistic dummy data into Supabase.
Safe to re-run — skips existing records via ON CONFLICT.

Setup:
    pip install supabase python-dotenv faker

    In .env:
        SUPABASE_URL=https://your-project.supabase.co
        SUPABASE_KEY=your-service-role-key   ← use service role to bypass RLS

Run:
    python seed.py
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
# 2. Dummy data pools
# ─────────────────────────────────────────────

FIRST_NAMES = [
    "Aarav", "Priya", "Rohan", "Sneha", "Vikram",
    "Ananya", "Kiran", "Neha", "Arjun", "Pooja",
    "Rahul", "Deepa", "Siddharth", "Meera", "Aditya",
    "Kavya", "Nikhil", "Swathi", "Rajan", "Divya",
]

LAST_NAMES = [
    "Sharma", "Mehta", "Nair", "Iyer", "Patel",
    "Reddy", "Kumar", "Singh", "Joshi", "Gupta",
    "Shah", "Verma", "Pillai", "Rao", "Choudhary",
    "Bhat", "Mishra", "Shetty", "Pandey", "Menon",
]

CITIES = [
    "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Surat",
]

TIERS = ["standard", "standard", "standard", "premium", "premium", "enterprise"]

ORDER_STATUSES = [
    "pending", "confirmed", "shipped", "delivered",
    "delivered", "delivered", "cancelled", "refunded",
]

PRODUCTS = [
    ("Pro Plan — Monthly",    1999.00),
    ("Pro Plan — Annual",    19999.00),
    ("Team Plan — Monthly",   4999.00),
    ("Team Plan — Annual",   49999.00),
    ("Enterprise License",   99999.00),
    ("API Add-on",            2499.00),
    ("Storage Upgrade 100GB",  999.00),
    ("Priority Support",      7999.00),
    ("Custom Integration",   14999.00),
    ("Onboarding Package",    4499.00),
]

CURRENCIES = ["INR", "INR", "INR", "USD", "USD"]


def random_phone() -> str:
    return f"+91-{random.randint(7000000000, 9999999999)}"

def random_date(days_back: int = 365) -> str:
    delta = timedelta(days=random.randint(0, days_back))
    return (datetime.now(timezone.utc) - delta).isoformat()

def random_order_number(index: int) -> str:
    return f"ORD-2025-{str(index).zfill(3)}"


# ─────────────────────────────────────────────
# 3. Seed customers
# ─────────────────────────────────────────────

print("\n── Seeding 20 customers ──")

# Build 20 unique name combos
random.shuffle(FIRST_NAMES)
random.shuffle(LAST_NAMES)

customers_to_insert = []
for i in range(20):
    first = FIRST_NAMES[i]
    last  = LAST_NAMES[i]
    name  = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}@example.com"

    customers_to_insert.append({
        "name":  name,
        "email": email,
        "phone": random_phone(),
        "tier":  random.choice(TIERS),
    })

# Upsert — skip duplicates by email
res = supabase.table("customers").upsert(
    customers_to_insert,
    on_conflict="email",
    ignore_duplicates=True,
).execute()

inserted_customers = res.data
print(f"   Inserted : {len(inserted_customers)} customers")

# Fetch all customers to get their UUIDs for orders
all_customers = supabase.table("customers").select("id, name, email, tier").execute().data
print(f"   Total in DB : {len(all_customers)} customers")


# ─────────────────────────────────────────────
# 4. Seed orders
# ─────────────────────────────────────────────

print("\n── Seeding 30 orders ──")

# Get highest existing order number to avoid conflicts
existing_orders = supabase.table("orders").select("order_number").execute().data
existing_numbers = {o["order_number"] for o in existing_orders}

# Find a safe starting index
start_index = 1
while random_order_number(start_index) in existing_numbers:
    start_index += 1

orders_to_insert = []
customer_ids = [c["id"] for c in all_customers]

for i in range(30):
    product_name, base_price = random.choice(PRODUCTS)
    currency   = random.choice(CURRENCIES)
    amount     = base_price if currency == "INR" else round(base_price / 83, 2)
    status     = random.choice(ORDER_STATUSES)
    placed_at  = random_date(days_back=180)

    orders_to_insert.append({
        "customer_id":  random.choice(customer_ids),
        "order_number": random_order_number(start_index + i),
        "status":       status,
        "total_amount": amount,
        "currency":     currency,
        "notes":        f"{product_name}",
        "placed_at":    placed_at,
    })

res = supabase.table("orders").upsert(
    orders_to_insert,
    on_conflict="order_number",
    ignore_duplicates=True,
).execute()

inserted_orders = res.data
print(f"   Inserted : {len(inserted_orders)} orders")

all_orders = supabase.table("orders").select("id").execute().data
print(f"   Total in DB : {len(all_orders)} orders")


# ─────────────────────────────────────────────
# 5. Summary
# ─────────────────────────────────────────────

print("\n" + "=" * 55)
print("SEED SUMMARY")
print("=" * 55)

# Customers by tier
tier_counts = {}
for c in all_customers:
    tier_counts[c["tier"]] = tier_counts.get(c["tier"], 0) + 1

print("\nCustomers by tier:")
for tier, count in sorted(tier_counts.items()):
    print(f"  {tier:12} : {count}")

# Orders by status
all_orders_detail = supabase.table("orders").select("status, currency, total_amount").execute().data
status_counts = {}
for o in all_orders_detail:
    status_counts[o["status"]] = status_counts.get(o["status"], 0) + 1

print("\nOrders by status:")
for status, count in sorted(status_counts.items()):
    print(f"  {status:12} : {count}")

# Revenue summary
inr_total = sum(o["total_amount"] for o in all_orders_detail if o["currency"] == "INR")
usd_total = sum(o["total_amount"] for o in all_orders_detail if o["currency"] == "USD")
print(f"\nRevenue:")
print(f"  INR : ₹{inr_total:,.2f}")
print(f"  USD : ${usd_total:,.2f}")

print(f"\n{'=' * 55}")
print(f"✅ Done. Check your Supabase table editor to verify.")
print(f"{'=' * 55}")