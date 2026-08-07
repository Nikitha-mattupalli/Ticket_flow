from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TechnicalIssueCategory(str, Enum):
    LOGIN_ISSUE = "login_issue"
    PASSWORD_RESET = "password_reset"
    NETWORK_CONNECTIVITY = "network_connectivity"
    SERVICE_OUTAGE = "service_outage"
    API_TIMEOUT = "api_timeout"
    OTHER = "other"


class TechnicalResult(BaseModel):
    """Grounded troubleshooting decision produced by the Technical Agent."""

    model_config = ConfigDict(extra="forbid")

    issue_category: TechnicalIssueCategory
    confidence: float = Field(..., ge=0, le=1)
    requires_human: bool
    troubleshooting_steps: list[str] = Field(..., min_length=1)
    response_to_customer: str
    reasoning: str
