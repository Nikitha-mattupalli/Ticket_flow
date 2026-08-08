from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EscalationReason(str, Enum):
    SECURITY = "security"
    LEGAL = "legal"
    SAFETY = "safety"
    REPEATED_FAILURE = "repeated_failure"
    CUSTOMER_REQUEST = "customer_request"
    OTHER = "other"


class EscalationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: EscalationReason
    queue: str
    urgency: str = Field(..., pattern="^(low|medium|high|urgent)$")
    summary_for_agent: str
    response_to_customer: str
    recommended_actions: list[str] = Field(..., min_length=1)
