import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", str(PROJECT_ROOT / "vector_stores"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "3"))


@dataclass(frozen=True)
class AppSettings:
    environment: str = os.getenv("TICKETFLOW_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    checkpointer_backend: str = os.getenv("CHECKPOINTER_BACKEND", "memory")
    checkpoint_db_path: str = os.getenv(
        "CHECKPOINT_DB_PATH", str(PROJECT_ROOT / "data" / "checkpoints.sqlite")
    )
    persist_refunds: bool = os.getenv("PERSIST_REFUNDS", "false").lower() == "true"
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    enable_mock_routes: bool = os.getenv("ENABLE_MOCK_ROUTES", "true").lower() == "true"
    deliver_escalations: bool = os.getenv("DELIVER_ESCALATIONS", "false").lower() == "true"


settings = AppSettings()
