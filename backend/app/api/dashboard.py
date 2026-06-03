"""REST API for the clinic dashboard (WhatsApp + web chat cases)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import dashboard

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/cases")
async def list_cases(
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    return {"cases": await dashboard.list_cases(db=db)}


@router.get("/cases/{phone:path}")
async def get_case(
    phone: str,
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    case = await dashboard.get_case(phone, db=db)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    case.setdefault("db_messages", [])
    return case


@router.get("/analytics")
async def analytics(
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    return await dashboard.analytics_summary(db=db)


@router.get("/alerts/recent")
async def recent_alerts(
    db: Annotated[Session | None, Depends(get_db)],
) -> dict[str, Any]:
    cases = await dashboard.list_cases(db=db)
    alerts = [c for c in cases if c.get("priority") in ("P1", "P2") or c.get("escalated")]
    return {"alerts": alerts[:20]}


@router.post("/dev/clear-sessions")
async def clear_sessions() -> dict[str, str]:
    """
    Clear all triage sessions from Redis/in-memory.

    Use after wiping Postgres or when the queue shows stale cases.
    Does not delete database rows.
    """
    await dashboard.clear_all_sessions()
    return {"ok": "true", "message": "Cleared all WhatsApp and web chat sessions."}
