from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ReturnIssueCategory(str, Enum):
    RETURN_POLICY = "return_policy"
    DAMAGED_ITEM = "damaged_item"
    REPLACEMENT = "replacement"
    SHIPPING_DELAY = "shipping_delay"
    REFUND_AFTER_RETURN = "refund_after_return"
    OTHER = "other"


class ReturnsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_category: ReturnIssueCategory
    eligible: bool | None = Field(
        ..., description="Eligibility when verifiable; otherwise null."
    )
    confidence: float = Field(..., ge=0, le=1)
    requires_human: bool
    next_steps: list[str] = Field(..., min_length=1)
    response_to_customer: str
    reasoning: str
