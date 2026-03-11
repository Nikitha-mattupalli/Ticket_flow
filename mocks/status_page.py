"""
Mock StatusPage Router
-----------------------
Simulates a public status page API locally.
Used by the tech-agent to check if an issue is a known outage
before investigating a customer's specific problem.

Mounted at /mock/statuspage in main.py:
    GET    /mock/statuspage/status              → overall system status
    GET    /mock/statuspage/components          → status of each component
    GET    /mock/statuspage/incidents           → active incidents
    GET    /mock/statuspage/incidents/history   → past incidents
    POST   /mock/statuspage/incident            → create a new incident (internal)
    PUT    /mock/statuspage/incident/{id}       → update incident status
    DELETE /mock/statuspage/incidents/clear     → reset mock data

Real StatusPage (Atlassian):
    GET https://api.statuspage.io/v1/pages/{page_id}/summary
    Auth: API key header

Swap to real StatusPage via .env:
    STATUSPAGE_BASE_URL=https://api.statuspage.io/v1/pages/{page_id}
    STATUSPAGE_API_KEY=your-key

How tech-agent uses this:
    1. Customer raises ticket: "API is returning errors"
    2. tech-agent calls GET /mock/statuspage/status
    3. If status != "operational" → reply with known outage info
    4. If status == "operational" → investigate customer's account
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mock/statuspage", tags=["Mock: StatusPage"])


# ─────────────────────────────────────────────
# Component definitions — your service areas
# ─────────────────────────────────────────────

DEFAULT_COMPONENTS = [
    {"id": "comp-api",       "name": "API",               "group": "Core"},
    {"id": "comp-dashboard", "name": "Dashboard",          "group": "Core"},
    {"id": "comp-auth",      "name": "Authentication",     "group": "Core"},
    {"id": "comp-webhooks",  "name": "Webhooks",           "group": "Core"},
    {"id": "comp-db",        "name": "Database",           "group": "Infrastructure"},
    {"id": "comp-billing",   "name": "Billing & Payments", "group": "Services"},
    {"id": "comp-email",     "name": "Email Notifications","group": "Services"},
    {"id": "comp-cdn",       "name": "CDN & File Storage", "group": "Infrastructure"},
]

# Status options for components and incidents
COMPONENT_STATUSES = [
    "operational",
    "degraded_performance",
    "partial_outage",
    "major_outage",
    "under_maintenance",
]

INCIDENT_STATUSES = [
    "investigating",
    "identified",
    "monitoring",
    "resolved",
]

INCIDENT_IMPACTS = ["none", "minor", "major", "critical"]


# ─────────────────────────────────────────────
# In-memory state
# ─────────────────────────────────────────────

# Component status — starts all operational
_components: dict[str, dict] = {
    c["id"]: {**c, "status": "operational", "updated_at": _now() if False else ""}
    for c in DEFAULT_COMPONENTS
}

# Active and past incidents
_incidents: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init_components():
    for c in DEFAULT_COMPONENTS:
        _components[c["id"]] = {
            **c,
            "status":     "operational",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

_init_components()


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class CreateIncidentRequest(BaseModel):
    """Create a new incident — called when an outage is detected."""
    name:         str  = Field(..., min_length=5,
                                description="Short incident name e.g. 'API Latency Spike'")
    status:       str  = Field("investigating",
                                pattern="^(investigating|identified|monitoring|resolved)$")
    impact:       str  = Field("minor",
                                pattern="^(none|minor|major|critical)$")
    body:         str  = Field(...,
                                description="Detailed update message shown on status page")
    component_ids: list[str] = Field(...,
                                      description="Which components are affected")
    component_status: str = Field("degraded_performance",
                                   pattern="^(operational|degraded_performance|partial_outage|major_outage|under_maintenance)$")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name":             "Webhook Delivery Delays",
                "status":           "investigating",
                "impact":           "major",
                "body":             "We are investigating reports of webhook delivery failures. Engineers have been alerted and are investigating the root cause.",
                "component_ids":    ["comp-webhooks", "comp-api"],
                "component_status": "partial_outage"
            }]
        }
    }


class UpdateIncidentRequest(BaseModel):
    """Add an update to an existing incident."""
    status: str  = Field(...,
                          pattern="^(investigating|identified|monitoring|resolved)$")
    body:   str  = Field(..., description="Update message e.g. 'Root cause identified. Fix deploying.'")
    resolve_components: bool = Field(False,
                                      description="Set affected components back to operational")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _overall_status() -> str:
    """
    Derive overall system status from component statuses.
    Worst component status wins.
    """
    statuses = [c["status"] for c in _components.values()]
    if "major_outage"          in statuses: return "major_outage"
    if "partial_outage"        in statuses: return "partial_outage"
    if "degraded_performance"  in statuses: return "degraded_performance"
    if "under_maintenance"     in statuses: return "under_maintenance"
    return "operational"


def _status_label(status: str) -> str:
    return {
        "operational":          "All Systems Operational",
        "degraded_performance": "Degraded Performance",
        "partial_outage":       "Partial System Outage",
        "major_outage":         "Major System Outage",
        "under_maintenance":    "Under Maintenance",
    }.get(status, status)


def _active_incidents() -> list:
    return [i for i in _incidents.values() if i["status"] != "resolved"]


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@router.get("/status")
def get_status():
    """
    Overall system status — the main endpoint tech-agent checks first.

    Returns:
        status          → operational | degraded_performance | partial_outage | major_outage
        status_label    → human-readable string
        active_incidents→ list of ongoing incidents
        components      → per-component status
        checked_at      → timestamp of this check

    Usage in tech-agent:
        if response["status"] != "operational":
            reply with known outage info + ETA
        else:
            investigate customer's specific account
    """
    overall   = _overall_status()
    active    = _active_incidents()

    return {
        "status":           overall,
        "status_label":     _status_label(overall),
        "active_incidents": len(active),
        "incidents":        active,
        "components":       list(_components.values()),
        "checked_at":       _now(),
        "page": {
            "name":    "Ticketflow Status",
            "url":     "http://localhost:8000/mock/statuspage/status",
        }
    }


@router.get("/components")
def get_components(group: Optional[str] = None):
    """
    Per-component status breakdown.
    Optional filter: ?group=Core or ?group=Services
    """
    components = list(_components.values())
    if group:
        components = [c for c in components if c.get("group") == group]

    return {
        "components": components,
        "count":      len(components),
    }


@router.get("/incidents")
def get_incidents(include_resolved: bool = False):
    """
    List active incidents (or all incidents if include_resolved=true).
    """
    incidents = list(_incidents.values())
    if not include_resolved:
        incidents = [i for i in incidents if i["status"] != "resolved"]

    return {
        "incidents": incidents,
        "count":     len(incidents),
    }


@router.get("/incidents/history")
def get_incident_history(days: int = Query(7, ge=1, le=90)):
    """
    Past incidents in the last N days.
    Useful for showing customers recent reliability history.
    """
    cutoff    = datetime.now(timezone.utc) - timedelta(days=days)
    history   = [
        i for i in _incidents.values()
        if datetime.fromisoformat(i["created_at"]) >= cutoff
    ]
    return {
        "incidents": sorted(history, key=lambda x: x["created_at"], reverse=True),
        "count":     len(history),
        "days":      days,
    }


@router.post("/incident", status_code=201)
def create_incident(body: CreateIncidentRequest):
    """
    Create a new incident and update affected component statuses.
    Called internally when an outage is detected.

    In production this would be called by:
        - Your monitoring system (Datadog, Grafana)
        - An on-call engineer
        - An automated health check
    """
    incident_id = str(uuid.uuid4())[:8].upper()
    now         = _now()

    incident = {
        "id":             incident_id,
        "name":           body.name,
        "status":         body.status,
        "impact":         body.impact,
        "components":     body.component_ids,
        "updates": [
            {
                "status":     body.status,
                "body":       body.body,
                "created_at": now,
            }
        ],
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }
    _incidents[incident_id] = incident

    # Update affected component statuses
    for comp_id in body.component_ids:
        if comp_id in _components:
            _components[comp_id]["status"]     = body.component_status
            _components[comp_id]["updated_at"] = now

    print(
        f"[mock-statuspage] incident {incident_id} created | "
        f"{body.impact} | '{body.name}' | "
        f"components={body.component_ids}"
    )

    return {
        "incident":      incident,
        "overall_status": _status_label(_overall_status()),
        "message":        f"Incident {incident_id} created. Status page now shows '{body.impact}' impact.",
    }


@router.put("/incident/{incident_id}")
def update_incident(incident_id: str, body: UpdateIncidentRequest):
    """
    Add an update to an incident.
    When status → resolved, affected components go back to operational.

    Typical lifecycle:
        investigating → identified → monitoring → resolved
    """
    incident = _incidents.get(incident_id.upper())
    if not incident:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found."
        )

    now = _now()
    incident["status"]     = body.status
    incident["updated_at"] = now
    incident["updates"].append({
        "status":     body.status,
        "body":       body.body,
        "created_at": now,
    })

    # Resolve — set components back to operational
    if body.status == "resolved":
        incident["resolved_at"] = now
        if body.resolve_components:
            for comp_id in incident["components"]:
                if comp_id in _components:
                    _components[comp_id]["status"]     = "operational"
                    _components[comp_id]["updated_at"] = now

    _incidents[incident_id.upper()] = incident

    print(
        f"[mock-statuspage] incident {incident_id} → {body.status} | "
        f"components_resolved={body.resolve_components}"
    )

    return {
        "incident":       incident,
        "overall_status": _status_label(_overall_status()),
    }


@router.delete("/incidents/clear", status_code=204)
def clear_incidents():
    """Dev-only: wipe all incidents and reset all components to operational."""
    _incidents.clear()
    _init_components()
    print("[mock-statuspage] incidents cleared, all components reset to operational")