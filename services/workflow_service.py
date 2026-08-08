from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any

from langgraph.types import Command
from pydantic import BaseModel

from graph.state import GraphState, Ticket
from graph.workflow import build_workflow


@lru_cache(maxsize=1)
def get_workflow():
    """Reuse one compiled graph/checkpointer for the process lifetime."""
    return build_workflow()


def serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return serialize(value.model_dump())
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(item) for item in value]
    if hasattr(value, "value") and hasattr(value, "id"):
        return {"id": value.id, "value": serialize(value.value)}
    return value


def start_workflow(ticket: Ticket, thread_id: str | None = None) -> dict:
    selected_thread = thread_id or f"ticket-{ticket.ticket_id}"
    config = {"configurable": {"thread_id": selected_thread}}
    result = get_workflow().invoke(GraphState(ticket=ticket), config=config)
    return {
        "thread_id": selected_thread,
        "interrupted": bool(result.get("__interrupt__")),
        "state": serialize(result),
    }


def resume_workflow(
    thread_id: str,
    *,
    approved: bool,
    reviewer: str,
    comment: str | None = None,
) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = get_workflow().invoke(
        Command(
            resume={
                "approved": approved,
                "reviewer": reviewer,
                "comment": comment,
            }
        ),
        config=config,
    )
    return {
        "thread_id": thread_id,
        "interrupted": bool(result.get("__interrupt__")),
        "state": serialize(result),
    }
