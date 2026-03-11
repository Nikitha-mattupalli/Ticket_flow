"""
Mock ShipStation Router
------------------------
Simulates the ShipStation API locally for development and testing.
Used by the returns-agent to generate shipping labels for return tickets.

Mounted at /mock/shipstation in main.py:
    POST  /mock/shipstation/label           → create a return shipping label
    GET   /mock/shipstation/label/{label_id}→ fetch label by ID
    GET   /mock/shipstation/labels          → list all labels
    GET   /mock/shipstation/track/{tracking}→ get tracking status
    DELETE /mock/shipstation/labels/clear   → wipe mock data between tests

Real ShipStation API:
    POST https://ssapi.shipstation.com/shipments/createlabel
    Auth: Basic auth with API key + secret

Swap to real ShipStation via .env:
    SHIPSTATION_BASE_URL=https://ssapi.shipstation.com

Usage in returns agent:
    label = create_return_label(order_number, customer_address)
    send_label_email(customer_email, label["label_url"])
"""

import uuid
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mock/shipstation", tags=["Mock: ShipStation"])

# ─────────────────────────────────────────────
# In-memory store
# ─────────────────────────────────────────────

_labels: dict[str, dict] = {}       # label_id → label dict
_tracking: dict[str, list] = {}     # tracking_number → events list


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class Address(BaseModel):
    name:       str
    street1:    str
    city:       str
    state:      str
    postal_code: str
    country:    str = "IN"
    phone:      Optional[str] = None


class CreateLabelRequest(BaseModel):
    """
    Mirrors ShipStation createLabel payload.
    Real API: POST https://ssapi.shipstation.com/shipments/createlabel
    """
    order_number:    str   = Field(..., description="Your order e.g. ORD-2025-003")
    ticket_number:   str   = Field(..., description="Return ticket e.g. TKT-2025-003")
    ship_from:       Address
    ship_to:         Address
    carrier_code:    str   = Field("fedex",
                                   description="fedex | ups | delhivery | bluedart")
    service_code:    str   = Field("standard",
                                   description="standard | express | overnight")
    weight_kg:       float = Field(1.0, gt=0, le=70)
    dimensions:      Optional[dict] = Field(
                         None,
                         description='{"length": 30, "width": 20, "height": 15, "unit": "cm"}'
                     )
    is_return_label: bool  = Field(True,  description="Always True for return shipments")
    insurance_amount: Optional[float] = Field(None, description="Declared value in INR")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "order_number":  "ORD-2025-003",
                "ticket_number": "TKT-2025-003",
                "ship_from": {
                    "name":        "Charlie Nair",
                    "street1":     "42 MG Road",
                    "city":        "Bengaluru",
                    "state":       "KA",
                    "postal_code": "560001",
                    "country":     "IN",
                    "phone":       "+91-9988776655"
                },
                "ship_to": {
                    "name":        "Ticketflow Returns Warehouse",
                    "street1":     "Plot 7, KIADB Industrial Area",
                    "city":        "Bengaluru",
                    "state":       "KA",
                    "postal_code": "562149",
                    "country":     "IN"
                },
                "carrier_code":    "bluedart",
                "service_code":    "standard",
                "weight_kg":       1.5,
                "is_return_label": True
            }]
        }
    }


class TrackingEvent(BaseModel):
    status:      str
    description: str
    location:    str
    timestamp:   str


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

CARRIER_PREFIXES = {
    "fedex":     "FDX",
    "ups":       "UPS",
    "delhivery": "DLV",
    "bluedart":  "BDT",
    "default":   "SHP",
}

CARRIER_RATES_INR = {
    ("fedex",     "standard"):  350.00,
    ("fedex",     "express"):   650.00,
    ("fedex",     "overnight"): 950.00,
    ("ups",       "standard"):  320.00,
    ("ups",       "express"):   600.00,
    ("delhivery", "standard"):  180.00,
    ("delhivery", "express"):   320.00,
    ("bluedart",  "standard"):  220.00,
    ("bluedart",  "express"):   420.00,
    ("bluedart",  "overnight"): 750.00,
}

ETA_DAYS = {
    "standard":  (3, 5),
    "express":   (1, 2),
    "overnight": (0, 1),
}


def _tracking_number(carrier: str) -> str:
    prefix = CARRIER_PREFIXES.get(carrier, CARRIER_PREFIXES["default"])
    return f"{prefix}{random.randint(1000000000, 9999999999)}"


def _label_url(label_id: str) -> str:
    """Fake PDF label URL — in real ShipStation this is a PDF download link."""
    return f"http://localhost:8000/mock/shipstation/label/{label_id}/download"


def _eta(service_code: str) -> str:
    min_days, max_days = ETA_DAYS.get(service_code, (3, 5))
    eta_date = datetime.now(timezone.utc) + timedelta(
        days=random.randint(min_days, max_days)
    )
    return eta_date.strftime("%Y-%m-%d")


def _shipping_cost(carrier: str, service: str, weight_kg: float) -> float:
    base = CARRIER_RATES_INR.get((carrier, service), 250.00)
    # Add weight surcharge over 1kg
    extra = max(0, (weight_kg - 1.0)) * 40
    return round(base + extra, 2)


def _fake_tracking_events(tracking_number: str, carrier: str) -> list:
    """Generate a realistic initial tracking event."""
    return [
        {
            "status":      "label_created",
            "description": "Return shipping label created. Awaiting pickup.",
            "location":    "Origin",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        }
    ]


def _fake_delay(ms: int = 200) -> None:
    time.sleep(ms / 1000)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@router.post("/label", status_code=201)
def create_label(
    body: CreateLabelRequest,
    fail: bool = Query(False, description="Simulate ShipStation API error"),
):
    """
    Generate a return shipping label.

    Simulates POST https://ssapi.shipstation.com/shipments/createlabel

    Returns:
        label_id        → unique label identifier
        tracking_number → carrier tracking code
        label_url       → URL to download the PDF label
        carrier_code    → which carrier was used
        shipping_cost   → cost in INR
        eta             → estimated delivery date
    """
    _fake_delay(200)

    if fail:
        raise HTTPException(
            status_code=422,
            detail={
                "ExceptionMessage": "The address provided could not be verified.",
                "ExceptionType":    "InvalidAddressException",
            }
        )

    label_id        = str(uuid.uuid4())[:8].upper()
    tracking_number = _tracking_number(body.carrier_code)
    shipping_cost   = _shipping_cost(body.carrier_code, body.service_code, body.weight_kg)
    eta             = _eta(body.service_code)

    label = {
        "label_id":        label_id,
        "order_number":    body.order_number,
        "ticket_number":   body.ticket_number,
        "tracking_number": tracking_number,
        "carrier_code":    body.carrier_code,
        "service_code":    body.service_code,
        "label_url":       _label_url(label_id),
        "label_format":    "pdf",
        "ship_from":       body.ship_from.model_dump(),
        "ship_to":         body.ship_to.model_dump(),
        "weight_kg":       body.weight_kg,
        "shipping_cost":   shipping_cost,
        "currency":        "INR",
        "eta":             eta,
        "is_return_label": body.is_return_label,
        "status":          "label_created",
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "voided":          False,
    }

    _labels[label_id]          = label
    _tracking[tracking_number] = _fake_tracking_events(tracking_number, body.carrier_code)

    print(
        f"[mock-shipstation] label {label_id} created | "
        f"{body.order_number} | {body.carrier_code} | "
        f"tracking={tracking_number} | ₹{shipping_cost} | eta={eta}"
    )

    return {
        "label":    label,
        "message":  f"Return label generated. Email it to the customer to ship back {body.order_number}.",
    }


@router.get("/label/{label_id}")
def get_label(label_id: str):
    """Fetch a label by ID."""
    _fake_delay(80)
    label = _labels.get(label_id)
    if not label:
        raise HTTPException(
            status_code=404,
            detail={"ExceptionMessage": f"Label {label_id} not found"}
        )
    return {"label": label}


@router.get("/labels")
def list_labels():
    """List all mock labels."""
    _fake_delay(120)
    labels = list(_labels.values())
    return {"labels": labels, "count": len(labels)}


@router.get("/track/{tracking_number}")
def track_shipment(tracking_number: str):
    """
    Simulate tracking status for a shipment.
    In real ShipStation, tracking data comes from the carrier.
    """
    _fake_delay(150)

    events = _tracking.get(tracking_number)
    if not events:
        raise HTTPException(
            status_code=404,
            detail={"ExceptionMessage": f"Tracking number {tracking_number} not found"}
        )

    # Find the label for this tracking number
    label = next(
        (l for l in _labels.values() if l["tracking_number"] == tracking_number),
        None
    )

    return {
        "tracking_number": tracking_number,
        "carrier":         label["carrier_code"] if label else "unknown",
        "status":          events[-1]["status"],
        "eta":             label["eta"] if label else None,
        "events":          events,
    }


@router.delete("/labels/clear", status_code=204)
def clear_labels():
    """Dev-only: wipe all mock labels between test runs."""
    _labels.clear()
    _tracking.clear()
    print("[mock-shipstation] all mock labels cleared")