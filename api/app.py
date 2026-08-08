import logging
import time
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.logging import configure_logging
from config.settings import settings
from graph.state import Ticket
from services.workflow_service import resume_workflow, start_workflow
from tasks import celery_app, process_langgraph_workflow


configure_logging()
logger = logging.getLogger("ticketflow.api")
app = FastAPI(title="Ticket Flow API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)

if settings.enable_mock_routes:
    from mocks.jira import router as jira_router
    from mocks.shipstation import router as shipstation_router
    from mocks.status_page import router as status_router
    from mocks.zendesk import router as zendesk_router

    app.include_router(jira_router)
    app.include_router(shipstation_router)
    app.include_router(status_router)
    app.include_router(zendesk_router)


class WorkflowRequest(BaseModel):
    ticket_id: str = Field(default_factory=lambda: str(uuid4()))
    customer_id: str
    subject: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=3, max_length=4000)
    created_at: datetime = Field(default_factory=datetime.now)
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    approved: bool
    reviewer: str = Field(..., min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=1000)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
        request_id,
    )
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ticket-flow", "version": "1.0.0"}


@app.post("/workflows", status_code=status.HTTP_202_ACCEPTED)
def create_workflow(body: WorkflowRequest) -> dict:
    try:
        return start_workflow(
            Ticket(**body.model_dump(exclude={"thread_id"})),
            thread_id=body.thread_id,
        )
    except Exception as exc:
        logger.exception("workflow_start_failed")
        raise HTTPException(status_code=500, detail="Workflow execution failed.") from exc


@app.post("/workflows/async", status_code=status.HTTP_202_ACCEPTED)
def create_async_workflow(body: WorkflowRequest) -> dict:
    ticket = Ticket(**body.model_dump(exclude={"thread_id"}))
    task = process_langgraph_workflow.delay(ticket.model_dump(mode="json"))
    return {"task_id": task.id, "status": "queued"}


@app.get("/tasks/{task_id}")
def task_status(task_id: str) -> dict:
    task = celery_app.AsyncResult(task_id)
    response = {"task_id": task_id, "status": task.status, "result": None}
    if task.successful():
        response["result"] = task.result
    elif task.failed():
        response["error"] = str(task.result)
    return response


@app.post("/workflows/{thread_id}/approval")
def approve_workflow(thread_id: str, body: ApprovalRequest) -> dict:
    try:
        return resume_workflow(
            thread_id,
            approved=body.approved,
            reviewer=body.reviewer,
            comment=body.comment,
        )
    except Exception as exc:
        logger.exception("workflow_resume_failed thread_id=%s", thread_id)
        raise HTTPException(status_code=409, detail="Workflow could not be resumed.") from exc
