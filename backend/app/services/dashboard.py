"""Aggregate cases for clinic dashboard APIs (sessions + optional Postgres)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.agent.state import TriageState, latest_message
from app.services import memory


def _state_to_case(phone: str, state: TriageState) -> dict[str, Any]:
    messages = state.get("messages") or []
    slots = state.get("slots") or {}
    chief = slots.get("chief_complaint") or (messages[0] if messages else "")
    return {
        "phone": phone,
        "display_name": phone.replace("@c.us", "").replace("@g.us", ""),
        "priority": state.get("priority"),
        "confidence": state.get("confidence") or 0.0,
        "reasoning": state.get("reasoning") or "",
        "escalated": bool(state.get("escalated")),
        "slots_complete": bool(state.get("slots_complete")),
        "slots": slots,
        "routed_to": state.get("routed_to"),
        "message_count": len(messages),
        "last_message": latest_message(state),
        "pending_slot": state.get("pending_slot"),
        "reply": state.get("reply") or "",
    }


async def list_cases() -> list[dict[str, Any]]:
    phones = await memory.list_phones()
    cases: list[dict[str, Any]] = []
    for phone in phones:
        state = await memory.load(phone)
        if state.get("messages"):
            cases.append(_state_to_case(phone, state))
    priority_order = {"P1": 0, "P2": 1, "P3": 2}
    cases.sort(
        key=lambda c: (
            priority_order.get(c["priority"] or "", 99),
            -(c["confidence"] or 0),
        )
    )
    return cases


async def get_case(phone: str) -> dict[str, Any] | None:
    state = await memory.load(phone)
    if not state.get("messages"):
        return None
    case = _state_to_case(phone, state)
    case["messages"] = list(state.get("messages") or [])
    case["clarification_rounds"] = state.get("clarification_rounds") or 0
    return case


async def analytics_summary() -> dict[str, Any]:
    cases = await list_cases()
    by_priority: dict[str, int] = {"P1": 0, "P2": 0, "P3": 0, "unset": 0}
    escalated = 0
    complete = 0
    for c in cases:
        p = c.get("priority")
        if p in by_priority:
            by_priority[p] += 1
        else:
            by_priority["unset"] += 1
        if c.get("escalated"):
            escalated += 1
        if c.get("slots_complete"):
            complete += 1
    return {
        "total_cases": len(cases),
        "by_priority": by_priority,
        "escalated": escalated,
        "intake_complete": complete,
        "as_of": datetime.now(UTC).isoformat(),
    }


def list_db_messages(*, db: Session, phone: str, limit: int = 50) -> list[dict[str, Any]]:
    from app.models.message import Message
    from app.models.patient import Patient

    patient = db.scalar(select(Patient).where(Patient.phone == phone))
    if patient is None:
        return []

    rows = db.scalars(
        select(Message)
        .where(Message.patient_id == patient.id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    ).all()
    return [
        {
            "id": str(m.id),
            "direction": m.direction,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in reversed(rows)
    ]


def db_patient_stats(db: Session) -> dict[str, int]:
    from app.models.message import Message
    from app.models.patient import Patient

    patients = db.scalar(select(func.count()).select_from(Patient)) or 0
    messages = db.scalar(select(func.count()).select_from(Message)) or 0
    return {"patients": patients, "messages": messages}
