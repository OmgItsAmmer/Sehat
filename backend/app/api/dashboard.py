"""REST API for the clinic web app (cases, analytics, simulated patient chat)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import dashboard, intake

router = APIRouter(prefix="/api", tags=["dashboard"])


class ChatMessageIn(BaseModel):
    phone: str = Field(..., min_length=3, description="WhatsApp chat id, e.g. 923001234567@c.us")
    body: str = Field(..., min_length=1, max_length=4096)


@router.get("/cases")
async def list_cases() -> dict[str, Any]:
    return {"cases": await dashboard.list_cases()}


@router.get("/cases/{phone:path}")
async def get_case(
    phone: str,
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    case = await dashboard.get_case(phone)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if db is not None:
        case["db_messages"] = dashboard.list_db_messages(db=db, phone=phone)
    else:
        case["db_messages"] = []
    return case


@router.get("/analytics")
async def analytics(
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    summary = await dashboard.analytics_summary()
    if db is not None:
        summary["database"] = dashboard.db_patient_stats(db)
    return summary


@router.get("/alerts/recent")
async def recent_alerts() -> dict[str, Any]:
    cases = await dashboard.list_cases()
    alerts = [c for c in cases if c.get("priority") in ("P1", "P2") or c.get("escalated")]
    return {"alerts": alerts[:20]}


@router.post("/chat/message")
async def send_chat_message(
    body: ChatMessageIn,
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    """Simulate an inbound WhatsApp message (patient chat UI in the web app)."""
    result = await intake.process_incoming_message(
        chat_id=body.phone,
        body=body.body,
        db=db,
        raw_payload=None,
    )
    return {
        "phone": body.phone,
        "priority": result.get("priority"),
        "confidence": result.get("confidence"),
        "reasoning": result.get("reasoning"),
        "escalated": result.get("escalated"),
        "slots_complete": result.get("slots_complete"),
        "slots": result.get("slots"),
        "reply": result.get("reply"),
        "pending_slot": result.get("pending_slot"),
        "messages": result.get("messages"),
    }
