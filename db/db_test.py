# # from db_client import TicketflowDB


# db = TicketflowDB()

# invoice = db.get_latest_invoice_for_customer(
#     customer_id="d1e81976-17c0-4548-abba-424b8af54810"
# )

# print(invoice)


import os

import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_test_payment() -> None:
    payment_intent = stripe.PaymentIntent.create(
        amount=235882,  # ₹2,358.82 in paise
        currency="inr",
        payment_method="pm_card_visa",
        payment_method_types=["card"],
        confirm=True,
        description="Ticket Flow duplicate-charge test payment",
        metadata={
            "invoice_id": "YOUR_SUPABASE_INVOICE_UUID",
            "customer_id": "YOUR_SUPABASE_CUSTOMER_UUID",
        },
    )

    print("PaymentIntent:", payment_intent.id)
    print("Status:", payment_intent.status)
    print("Amount:", payment_intent.amount)
    print("Currency:", payment_intent.currency)
    print("Latest charge:", payment_intent.latest_charge)


if __name__ == "__main__":
    create_test_payment()