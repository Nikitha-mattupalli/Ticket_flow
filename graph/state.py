##we define the graph here
#what all we need in the graph node

#ticket details, supervisor output details, other agent output results, retry, node count, error , status etc
# 
#  
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from agents.supervisor.schema import SupervisorDecision
from agents.billing.schema import BillingResult

class Ticket(BaseModel):
    ticket_id: str = Field(..., description="Unique identifier for the ticket")
    customer_id: str= Field(..., description="Unique identifier for the customer")
    subject: str = Field(..., description="Subject of the ticket")
    description: str = Field(..., description="Detailed description of the ticket")
    created_at:  datetime = Field(..., description="Timestamp when the ticket was created")

class WorkflowStatus(str, Enum):
    NEW = "new"
    ROUTED = "routed"
    PENDING = "pending"
    PROCESSING = "processing"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"

class GraphState(BaseModel):
    ticket: Ticket

    supervisor_decision: SupervisorDecision | None = Field(
        default=None,
        description="Decision made by the supervisor agent",
    )

    billing_result: BillingResult | None = Field(
        default=None,
        description="Result from the billing agent",
    )

    workflow_status: WorkflowStatus = WorkflowStatus.NEW

    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retry attempts",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if the workflow fails",
    )



