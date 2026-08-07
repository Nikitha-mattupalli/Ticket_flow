from uuid import UUID
from langchain_core.tools import tool
from db.db_client import TicketflowDB
import os
import re
import stripe
from dotenv import load_dotenv
import resend

load_dotenv()
_db: TicketflowDB | None = None


def get_db() -> TicketflowDB:
    """Create the Supabase client only when a billing operation needs it."""
    global _db
    if _db is None:
        _db = TicketflowDB()
    return _db

@tool
def fetch_invoice(customer_id: str) -> dict:
    """
    Fetch the latest invoice for a customer using their Supabase UUID.

    Use this tool when investigating invoice amounts, billing status,
    overdue payments, or suspected duplicate charges.
    """

    try:
        # Validate UUID before querying Supabase
        UUID(customer_id)

        db = get_db()
        invoice = db.get_latest_invoice_for_customer(customer_id)

        if invoice is None:
            return {
                "success": True,
                "invoice_found": False,
                "message": f"No invoice found for customer {customer_id}.",
            }

        payments = db.get_payments_for_invoice(
            invoice_id=invoice["id"]
        )

        return {
            "success": True,
            "invoice_found": True,
            "invoice": invoice,
            "payments": payments
        }

    except ValueError:
        return {
            "success": False,
            "invoice_found": False,
            "error": "Invalid customer ID format.",
        }

    except Exception:
        return {
            "success": False,
            "invoice_found": False,
            "error": "Unable to retrieve invoice information.",
        }

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
REFUND_APPROVAL_THRESHOLD = 50_000

@tool
def process_refund(
    payment_intent_id: str,
    amount: int,
    reason: str = "requested_by_customer",
    human_approved: bool = False,
) -> dict:
    """
    Process a Stripe refund in test mode.

    Args:
        payment_intent_id: Stripe PaymentIntent ID beginning with 'pi_'.
        amount: Refund amount in the smallest currency unit.
        reason: Stripe refund reason.
    """

    allowed_reasons = {
        "duplicate",
        "fraudulent",
        "requested_by_customer",
    }

    if not stripe.api_key:
        return {
            "success": False,
            "approval_required": False,
            "error": "STRIPE_SECRET_KEY is not configured.",
        }

    if not payment_intent_id.startswith("pi_"):
        return {
            "success": False,
            "approval_required": False,
            "error": "Invalid Stripe PaymentIntent ID.",
        }

    if amount <= 0:
        return {
            "success": False,
            "approval_required": False,
            "error": "Refund amount must be greater than zero.",
        }

    if reason not in allowed_reasons:
        return {
            "success": False,
            "approval_required": False,
            "error": "Invalid refund reason.",
        }

    if amount > REFUND_APPROVAL_THRESHOLD and not human_approved:
        return {
            "success": False,
            "approval_required": True,
            "payment_intent_id": payment_intent_id,
            "amount": amount,
            "reason": reason,
            "message": "Refund requires human approval.",
        }

    try:
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            amount=amount,
            reason=reason,
            metadata={
                "source": "ticketflow_billing_agent",
            },
            idempotency_key=f"ticketflow-{payment_intent_id}-{amount}",
        )

        return {
            "success": True,
            "approval_required": False,
            "refund_id": refund.id,
            "payment_intent_id": refund.payment_intent,
            "amount": refund.amount,
            "currency": refund.currency,
            "status": refund.status,
            "reason": refund.reason,
        }

    except stripe.StripeError:
        return {
            "success": False,
            "approval_required": False,
            "error": "Stripe could not process the refund.",
        }


resend.api_key = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL",
    "Ticket Flow <onboarding@resend.dev>"
)  

def is_valid_email(email: str) -> bool:
    """
    Perform basic email-format validation.
    """

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email))

@tool
def send_confirmation(
    customer_email: str,
    subject: str,
    message: str,
) -> dict:
    """
    Send a billing confirmation email to a customer.

    Use this tool after a billing action, such as initiating a
    refund, confirming an invoice request, or explaining that
    human approval is required.
    """

    if not resend.api_key:
        return {
            "success": False,
            "error": "RESEND_API_KEY is not configured.",
        }

    if not is_valid_email(customer_email):
        return {
            "success": False,
            "error": "Invalid customer email address",
        }

    if not subject.strip():
        return {
            "success": False,
            "error": "Email subject cannot be empty",
        }

    if not message.strip():
        return {
            "success": False,
            "error": "Email message cannot be empty",
        }

    try:
        email_response = resend.Emails.send(
            {
                "from": RESEND_FROM_EMAIL,
                "to": [customer_email],
                "subject": subject,
                "text": message,
            }
        )

        return {
            "success": True,
            "email_id": email_response["id"],
            "recipient": customer_email,
            "subject": subject,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": "Unable to send confirmation email.",
            "error_type": type(exc).__name__,
        }
