from agents.escalation.agent import EscalationAgent
from graph.state import GraphState, WorkflowStatus
from config.settings import settings
from tools.escalation_tools import create_escalation_ticket


escalation_agent = EscalationAgent()


def escalation_node(state: GraphState) -> dict:
    result = escalation_agent.invoke(state.ticket)
    update = {
        "escalation_result": result,
        "workflow_status": WorkflowStatus.WAITING_FOR_HUMAN,
        "error_message": None,
    }
    if settings.deliver_escalations:
        update["escalation_delivery_result"] = create_escalation_ticket.invoke(
            {
                "ticket_id": state.ticket.ticket_id,
                "subject": state.ticket.subject,
                "description": result.summary_for_agent,
                "priority": result.urgency,
            }
        )
    return update
