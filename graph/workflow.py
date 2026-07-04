#like a circuit board which connects every component

from graph.state import GraphState
from graph.node import supervisor_node
from graph.routing import route_ticket
from langgraph.graph import START, END, StateGraph

def billing_node(state: GraphState) -> GraphState:
    return state

def technical_node(state: GraphState) -> GraphState:
    return state

def returns_node(state: GraphState) -> GraphState:
    return state

def escalation_node(state: GraphState) -> GraphState:
    return state
workflow = StateGraph(GraphState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("billing", billing_node)
workflow.add_node("technical", technical_node)
workflow.add_node("returns", returns_node)
workflow.add_node("escalation", escalation_node)

workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor", route_ticket, {
        "billing": "billing",
        "technical": "technical",
        "returns": "returns",
        "escalation": "escalation"
    },   
)

workflow.add_edge("billing", END)
workflow.add_edge("technical", END) 
workflow.add_edge("returns", END)
workflow.add_edge("escalation", END)

graph = workflow.compile()