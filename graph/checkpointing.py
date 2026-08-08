from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from config.settings import settings


ALLOWED_CHECKPOINT_MODULES = [
    ("graph.state", "Ticket"),
    ("graph.state", "WorkflowStatus"),
    ("agents.supervisor.schema", "IntentType"),
    ("agents.supervisor.schema", "PriorityLevel"),
    ("agents.supervisor.schema", "Sentiment"),
    ("agents.supervisor.schema", "SupervisorDecision"),
    ("agents.billing.schema", "ApprovalStatus"),
    ("agents.billing.schema", "BillingIssueCategory"),
    ("agents.billing.schema", "ResolutionStatus"),
    ("agents.billing.schema", "RefundReason"),
    ("agents.billing.schema", "RefundRequest"),
    ("agents.billing.schema", "BillingResult"),
    ("agents.technical.schema", "TechnicalIssueCategory"),
    ("agents.technical.schema", "TechnicalResult"),
    ("agents.returns.schema", "ReturnIssueCategory"),
    ("agents.returns.schema", "ReturnsResult"),
    ("agents.escalation.schema", "EscalationReason"),
    ("agents.escalation.schema", "EscalationResult"),
]


def _serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_CHECKPOINT_MODULES)


def create_checkpointer(backend: str | None = None):
    selected = backend or settings.checkpointer_backend
    if selected == "memory":
        return InMemorySaver(serde=_serializer())
    if selected != "sqlite":
        raise ValueError(f"Unsupported checkpointer backend: {selected}")

    try:
        import sqlite3
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "SQLite checkpointing requires langgraph-checkpoint-sqlite."
        ) from exc

    path = Path(settings.checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(connection, serde=_serializer())
