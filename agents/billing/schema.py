from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class BillingIssueCategory(str, Enum):
    DUPLICATE_CHARGE = "duplicate_charge"
    INCORRECT_AMOUNT = "incorrect_amount"
    PAYMENT_FAILURE = "payment_failure"
    PAYMENT_NOT_RECEIVED = "payment_not_received"
    REFUND_REQUEST = "refund_request"
    REFUND_STATUS = "refund_status"
    INVOICE_REQUEST = "invoice_request"
    SUBSCRIPTION = "subscription"
    BILL_EXPLANATION = "bill_explanation"
    OTHER = "other"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    ESCALATED = "escalated"
    ACTION_REQUIRED = "action_required"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefundReason(str, Enum):
    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"
    BILLING_ERROR = "billing_error"
    SERVICE_ISSUE = "service_issue"


class RefundRequest(BaseModel):
    """
    Refund action proposed by the Billing Agent.
    """

    model_config = ConfigDict(extra="forbid")

    payment_id: str = Field(
        ...,
        description="Internal Supabase payment UUID.",
    )

    invoice_id: str = Field(
        ...,
        description="Internal Supabase invoice UUID.",
    )

    customer_id: str = Field(
        ...,
        description="Internal Supabase customer UUID.",
    )

    payment_intent_id: str = Field(
        ...,
        pattern=r"^pi_",
        description="Stripe PaymentIntent ID beginning with pi_.",
    )

    amount: int = Field(
        ...,
        gt=0,
        description=(
            "Refund amount in the smallest currency unit, "
            "such as paise or cents."
        ),
    )

    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Three-letter currency code such as INR or USD.",
    )

    reason: RefundReason = Field(
        ...,
        description="Reason for the proposed refund.",
    )


class BillingResult(BaseModel):
    """
    Structured decision returned by the Billing Agent.
    """

    model_config = ConfigDict(extra="forbid")

    issue_category: BillingIssueCategory = Field(
        ...,
        description="Category of the identified billing issue.",
    )

    resolution_status: ResolutionStatus = Field(
        ...,
        description="Current resolution status of the billing issue.",
    )

    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence in the Billing Agent's decision.",
    )

    requires_human: bool = Field(
        ...,
        description="Whether human intervention is required.",
    )

    response_to_customer: str = Field(
        ...,
        description="Proposed customer-facing response.",
    )

    reasoning: str = Field(
        ...,
        description="Concise explanation of the billing decision.",
    )

    proposed_refund: RefundRequest | None = Field(
        default=None,
        description=(
            "Refund proposed by the Billing Agent. "
            "None when no refund should be performed."
        ),
    )