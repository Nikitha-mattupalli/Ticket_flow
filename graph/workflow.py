from langgraph.graph import END, START, StateGraph

from agents.billing.approval_node import refund_approval_node
from agents.billing.execution_nodes import (
    refund_confirmation_node,
    refund_execution_node,
)
from agents.technical.node import technical_node
from agents.returns.node import returns_node
from agents.escalation.node import escalation_node
from graph.node import billing_node, supervisor_node
from graph.routing import (
    route_after_approval,
    route_after_billing,
    route_after_refund,
    route_ticket,
)
from graph.state import GraphState
from graph.checkpointing import create_checkpointer


def build_workflow(checkpointer=None):
    """
    Build and compile the Ticket Flow LangGraph.

    Build the resumable billing workflow with refund approval,
    execution, and customer confirmation.
    """

    workflow = StateGraph(GraphState)

    # ---------------------------------------------------------
    # Register nodes
    # ---------------------------------------------------------

    workflow.add_node(
        "supervisor",
        supervisor_node,
    )

    workflow.add_node(
        "billing",
        billing_node,
    )

    workflow.add_node("technical", technical_node)
    workflow.add_node("returns", returns_node)
    workflow.add_node("escalation", escalation_node)

    workflow.add_node(
        "refund_approval",
        refund_approval_node,
    )

    workflow.add_node("refund_execution", refund_execution_node)
    workflow.add_node("refund_confirmation", refund_confirmation_node)

    # ---------------------------------------------------------
    # Entry point
    # ---------------------------------------------------------

    workflow.add_edge(
        START,
        "supervisor",
    )

    # ---------------------------------------------------------
    # Supervisor routing
    # ---------------------------------------------------------

    workflow.add_conditional_edges(
        "supervisor",
        route_ticket,
        {
            "billing": "billing",

            "technical": "technical",
            "returns": "returns",
            "escalation": "escalation",
        },
    )

    # ---------------------------------------------------------
    # Billing routing
    # ---------------------------------------------------------

    workflow.add_conditional_edges(
        "billing",
        route_after_billing,
        {
            "approval": "refund_approval",
            "refund": "refund_execution",
            "complete": END,
        },
    )

    workflow.add_edge("technical", END)
    workflow.add_edge("returns", END)
    workflow.add_edge("escalation", END)

    workflow.add_conditional_edges(
        "refund_approval",
        route_after_approval,
        {
            "refund": "refund_execution",
            "rejected": END,
        },
    )

    workflow.add_conditional_edges(
        "refund_execution",
        route_after_refund,
        {
            "confirmation": "refund_confirmation",
            "failed": END,
        },
    )

    workflow.add_edge("refund_confirmation", END)

    # ---------------------------------------------------------
    # Checkpointer
    # ---------------------------------------------------------

    checkpointer = checkpointer or create_checkpointer()

    graph = workflow.compile(
        checkpointer=checkpointer,
    )

    return graph
