"""
Mock Jira Router
-----------------
Simulates the Jira REST API locally for development and testing.
Used by the tech-agent when a customer ticket reveals an actual bug
that needs to be fixed by the engineering team.

Mounted at /mock/jira in main.py:
    POST   /mock/jira/issue              → create a Jira issue
    GET    /mock/jira/issue/{issue_key}  → fetch issue by key (e.g. TF-42)
    PUT    /mock/jira/issue/{issue_key}  → update issue status/assignee
    GET    /mock/jira/issues             → list all issues
    POST   /mock/jira/issue/{issue_key}/comment → add a comment
    DELETE /mock/jira/issues/clear       → wipe mock data between tests

Real Jira API:
    POST https://your-domain.atlassian.net/rest/api/3/issue
    Auth: Basic auth with email + API token

Swap to real Jira via .env:
    JIRA_BASE_URL=https://your-domain.atlassian.net/rest/api/3

When to create a Jira issue from Ticketflow:
    - tech-agent determines the issue is a reproducible bug
    - Ticket priority is urgent or high
    - Customer is enterprise tier
"""

import uuid
import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mock/jira", tags=["Mock: Jira"])

# ─────────────────────────────────────────────
# In-memory store
# ─────────────────────────────────────────────

_issues:  dict[str, dict] = {}   # issue_key → issue dict
_counter: dict[str, int]  = {"n": 1}   # auto-increment for TF-XXX keys


# ─────────────────────────────────────────────
# Schemas — match Jira REST API v3 shape
# ─────────────────────────────────────────────

class JiraIssueFields(BaseModel):
    """
    Core fields for a Jira issue.
    Mirrors: POST /rest/api/3/issue → body.fields
    """
    summary:      str  = Field(..., min_length=5, max_length=255,
                                description="Issue title / one-liner")
    description:  Optional[str]  = Field(None, description="Full description of the bug or task")
    issue_type:   str  = Field("Bug",
                                pattern="^(Bug|Task|Story|Epic|Incident)$")
    priority:     str  = Field("Medium",
                                pattern="^(Lowest|Low|Medium|High|Highest)$")
    labels:       Optional[list[str]]  = Field(default_factory=list)
    assignee:     Optional[str]        = Field(None, description="Assignee username or email")
    reporter:     Optional[str]        = Field(None, description="Reporter email")

    # Custom fields linking back to Ticketflow
    ticket_number: Optional[str] = Field(None, description="Ticketflow ticket e.g. TKT-2025-002")
    customer_tier: Optional[str] = Field(None, description="standard | premium | enterprise")
    affected_component: Optional[str] = Field(None, description="e.g. API, Webhooks, Auth, Billing")


class CreateIssueRequest(BaseModel):
    """
    Mirrors Jira POST /rest/api/3/issue
    Real body: {"fields": { ... }}
    """
    project_key: str         = Field("TF", description="Jira project key e.g. TF, ENG, OPS")
    fields:      JiraIssueFields

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "project_key": "TF",
                "fields": {
                    "summary":      "Webhook endpoint returning 500 after deployment",
                    "description":  "Customer Bob Mehta (enterprise) reports webhook 500 errors since March 7. Confirmed reproducible on our staging env. Missing env var in deployment config.",
                    "issue_type":   "Bug",
                    "priority":     "High",
                    "labels":       ["webhook", "regression", "customer-reported"],
                    "assignee":     "dev-team@ticketflow.com",
                    "reporter":     "tech-agent",
                    "ticket_number": "TKT-2025-002",
                    "customer_tier": "premium",
                    "affected_component": "Webhooks"
                }
            }]
        }
    }


class UpdateIssueRequest(BaseModel):
    """Body for PUT /mock/jira/issue/{key}"""
    status:   Optional[str] = Field(None,
                                    pattern="^(To Do|In Progress|In Review|Done|Won't Fix)$")
    assignee: Optional[str] = Field(None)
    priority: Optional[str] = Field(None,
                                    pattern="^(Lowest|Low|Medium|High|Highest)$")
    resolution: Optional[str] = Field(None,
                                      description="Fixed | Won't Fix | Duplicate | Cannot Reproduce")


class AddCommentRequest(BaseModel):
    """Body for POST /mock/jira/issue/{key}/comment"""
    body:   str = Field(..., min_length=1)
    author: str = Field("system")


# ─────────────────────────────────────────────
# Priority mapping — Ticketflow → Jira
# ─────────────────────────────────────────────

PRIORITY_MAP = {
    "urgent": "Highest",
    "high":   "High",
    "medium": "Medium",
    "low":    "Low",
}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _next_issue_key(project_key: str) -> str:
    """Generate sequential issue key e.g. TF-1, TF-2, TF-3"""
    key = f"{project_key}-{_counter['n']}"
    _counter['n'] += 1
    return key

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _build_issue(issue_key: str, project_key: str, fields: JiraIssueFields) -> dict:
    return {
        "id":          str(random.randint(10000, 99999)),
        "key":         issue_key,
        "url":         f"http://localhost:8000/mock/jira/issue/{issue_key}",
        "project":     project_key,
        "summary":     fields.summary,
        "description": fields.description,
        "issue_type":  fields.issue_type,
        "priority":    fields.priority,
        "status":      "To Do",
        "resolution":  None,
        "labels":      fields.labels or [],
        "assignee":    fields.assignee,
        "reporter":    fields.reporter,
        "comments":    [],
        # Custom Ticketflow fields
        "ticket_number":        fields.ticket_number,
        "customer_tier":        fields.customer_tier,
        "affected_component":   fields.affected_component,
        "created_at":  _now(),
        "updated_at":  _now(),
    }


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@router.post("/issue", status_code=201)
def create_issue(
    body: CreateIssueRequest,
    fail: bool = Query(False, description="Simulate Jira API error"),
):
    """
    Create a new Jira issue.
    Called by tech-agent when a customer ticket reveals a real bug.

    Simulates POST https://domain.atlassian.net/rest/api/3/issue

    Returns:
        issue_key  → e.g. TF-5  (use this to link back to the ticket)
        url        → link to the Jira issue
        status     → always 'To Do' on creation
    """
    if fail:
        raise HTTPException(
            status_code=400,
            detail={
                "errorMessages": [],
                "errors": {
                    "summary": "Field 'summary' cannot be empty.",
                    "project": "Project 'INVALID' does not exist."
                }
            }
        )

    issue_key = _next_issue_key(body.project_key)
    issue     = _build_issue(issue_key, body.project_key, body.fields)
    _issues[issue_key] = issue

    print(
        f"[mock-jira] issue {issue_key} created | "
        f"{body.fields.issue_type} | {body.fields.priority} | "
        f"'{body.fields.summary[:50]}' | "
        f"ticket={body.fields.ticket_number}"
    )

    return {
        "id":        issue["id"],
        "key":       issue_key,
        "url":       issue["url"],
        "issue":     issue,
        "message":   f"Issue {issue_key} created and assigned to engineering.",
    }


@router.get("/issue/{issue_key}")
def get_issue(issue_key: str):
    """
    Fetch a Jira issue by key e.g. TF-5.
    Simulates GET /rest/api/3/issue/{issueIdOrKey}
    """
    issue = _issues.get(issue_key.upper())
    if not issue:
        raise HTTPException(
            status_code=404,
            detail={
                "errorMessages": [f"Issue {issue_key} does not exist."],
                "errors": {}
            }
        )
    return {"issue": issue}


@router.put("/issue/{issue_key}")
def update_issue(issue_key: str, body: UpdateIssueRequest):
    """
    Update a Jira issue — status, assignee, priority, resolution.
    Simulates PUT /rest/api/3/issue/{issueIdOrKey}

    When status → Done:
        - resolution is set
        - Ticketflow can auto-resolve the linked customer ticket
    """
    issue = _issues.get(issue_key.upper())
    if not issue:
        raise HTTPException(
            status_code=404,
            detail={"errorMessages": [f"Issue {issue_key} does not exist."]}
        )

    if body.status:
        issue["status"] = body.status
    if body.assignee:
        issue["assignee"] = body.assignee
    if body.priority:
        issue["priority"] = body.priority
    if body.resolution:
        issue["resolution"] = body.resolution

    issue["updated_at"] = _now()
    _issues[issue_key.upper()] = issue

    # If resolved, check if a customer ticket should also be closed
    linked_ticket = issue.get("ticket_number")
    auto_resolve_note = None
    if body.status == "Done" and linked_ticket:
        auto_resolve_note = (
            f"Jira issue {issue_key} marked Done. "
            f"Consider auto-resolving customer ticket {linked_ticket}."
        )

    print(f"[mock-jira] issue {issue_key} updated → status={issue['status']}")

    return {
        "issue":            issue,
        "auto_resolve_hint": auto_resolve_note,
    }


@router.post("/issue/{issue_key}/comment", status_code=201)
def add_comment(issue_key: str, body: AddCommentRequest):
    """
    Add a comment to a Jira issue.
    Simulates POST /rest/api/3/issue/{issueIdOrKey}/comment

    Used by:
        - tech-agent: "Customer confirmed fix resolved the issue"
        - system:     "Linked to Ticketflow TKT-2025-002"
        - engineer:   "Root cause: missing env var. Fix deployed to prod."
    """
    issue = _issues.get(issue_key.upper())
    if not issue:
        raise HTTPException(
            status_code=404,
            detail={"errorMessages": [f"Issue {issue_key} does not exist."]}
        )

    comment = {
        "id":         len(issue["comments"]) + 1,
        "author":     body.author,
        "body":       body.body,
        "created_at": _now(),
    }
    issue["comments"].append(comment)
    issue["updated_at"] = _now()

    print(f"[mock-jira] comment added to {issue_key} by {body.author}")
    return {"comment": comment}


@router.get("/issues")
def list_issues(
    status:     Optional[str] = None,
    issue_type: Optional[str] = None,
    priority:   Optional[str] = None,
):
    """
    List all mock Jira issues with optional filters.
    Simulates GET /rest/api/3/search (JQL query endpoint)

    Example: GET /mock/jira/issues?status=To Do&priority=High
    """
    issues = list(_issues.values())

    if status:
        issues = [i for i in issues if i["status"] == status]
    if issue_type:
        issues = [i for i in issues if i["issue_type"] == issue_type]
    if priority:
        issues = [i for i in issues if i["priority"] == priority]

    return {
        "issues":      issues,
        "total":       len(issues),
        "startAt":     0,
        "maxResults":  len(issues),
    }


@router.delete("/issues/clear", status_code=204)
def clear_issues():
    """Dev-only: wipe all mock issues and reset counter."""
    _issues.clear()
    _counter["n"] = 1
    print("[mock-jira] all mock issues cleared, counter reset")