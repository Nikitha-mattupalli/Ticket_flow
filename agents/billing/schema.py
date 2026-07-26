#how the schema of the result of billing agent shiuld look like

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


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

class BillingResult(BaseModel):
    """
    Schema for the result of billing agent
    """
    model_config = ConfigDict(extra="forbid")

    issue_category: BillingIssueCategory = Field(..., description="The category of the billing issue")
    resolution_status: ResolutionStatus = Field(..., description="The resolution status for the billing issue")
    confidence: float = Field(ge=0,le=1, description="The confidence score of the resolution provided, between 0 and 1")
    requires_human: bool = Field(..., description="Indicates whether the billing issue requires human intervention (yes/no)")
    response_to_customer: str = Field(..., description="The response to be sent to the customer regarding the billing issue")
    reasoning: str = Field(..., description="The reasoning behind the resolution provided for the billing issue")

