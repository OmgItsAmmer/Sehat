"""Aggregate cases for clinic dashboard — Redis sessions merged with Postgres history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.agent.state import TriageState, latest_message
from app.services import memory

CaseSource = Literal["session", "database", "both"]


def _state_to_case(
    phone: str, state: TriageState, *, source: CaseSource = "session"
) -> dict[str, Any]:
    messages = state.get("messages") or []
    slots = state.get("slots") or {}
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
        "awaiting_human_review": bool(state.get("awaiting_human_review")),
        "source": source,
    }


def _case_from_db_messages(phone: str, db_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a queue row from persisted WhatsApp messages when Redis session is empty."""
    inbound = [m["body"] for m in db_messages if m.get("direction") == "inbound"]
    outbound = [m["body"] for m in db_messages if m.get("direction") == "outbound"]
    last_inbound = inbound[-1] if inbound else ""
    last_outbound = outbound[-1] if outbound else ""
    return {
        "phone": phone,
        "display_name": phone.replace("@c.us", "").replace("@g.us", ""),
        "priority": None,
        "confidence": 0.0,
        "reasoning": "Persisted intake — no live triage session in Redis.",
        "escalated": False,
        "slots_complete": False,
        "slots": {},
        "routed_to": None,
        "message_count": len(db_messages),
        "last_message": last_inbound,
        "pending_slot": None,
        "reply": last_outbound,
        "awaiting_human_review": False,
        "source": "database",
    }


def _sort_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_order = {"P1": 0, "P2": 1, "P3": 2}

    def sort_key(c: dict[str, Any]) -> tuple:
        has_session = c.get("source") in ("session", "both")
        return (
            0 if has_session else 1,
            priority_order.get(c.get("priority") or "", 99),
            -(c.get("confidence") or 0),
        )

    cases.sort(key=sort_key)
    return cases


async def list_cases(*, db: Session | None = None) -> list[dict[str, Any]]:
    """Merge active Redis triage sessions with patients who only exist in Postgres."""
    by_phone: dict[str, dict[str, Any]] = {}

    for phone in await memory.list_phones():
        state = await memory.load(phone)
        if state.get("messages"):
            by_phone[phone] = _state_to_case(phone, state, source="session")

    if db is not None:
        from app.models.patient import Patient

        patients = db.scalars(select(Patient).order_by(desc(Patient.created_at))).all()
        for patient in patients:
            phone = patient.phone
            db_msgs = list_db_messages(db=db, phone=phone)
            if not db_msgs:
                continue
            if phone in by_phone:
                by_phone[phone]["source"] = "both"
                db_count = len(db_msgs)
                if db_count > (by_phone[phone].get("message_count") or 0):
                    by_phone[phone]["message_count"] = db_count
                if not by_phone[phone].get("last_message"):
                    inbound = [m["body"] for m in db_msgs if m["direction"] == "inbound"]
                    if inbound:
                        by_phone[phone]["last_message"] = inbound[-1]
            else:
                by_phone[phone] = _case_from_db_messages(phone, db_msgs)

    return _sort_cases(list(by_phone.values()))


async def get_case(phone: str, *, db: Session | None = None) -> dict[str, Any] | None:
    state = await memory.load(phone)
    if state.get("messages"):
        case = _state_to_case(phone, state, source="session")
        case["messages"] = list(state.get("messages") or [])
        case["clarification_rounds"] = state.get("clarification_rounds") or 0
        if db is not None:
            case["db_messages"] = list_db_messages(db=db, phone=phone)
            if case["db_messages"]:
                case["source"] = "both"
        else:
            case["db_messages"] = []
        return case

    if db is not None:
        db_msgs = list_db_messages(db=db, phone=phone)
        if db_msgs:
            case = _case_from_db_messages(phone, db_msgs)
            case["messages"] = [m["body"] for m in db_msgs if m["direction"] == "inbound"]
            case["clarification_rounds"] = 0
            case["db_messages"] = db_msgs
            return case

    return None


async def analytics_summary(*, db: Session | None = None) -> dict[str, Any]:
    cases = await list_cases(db=db)
    by_priority: dict[str, int] = {"P1": 0, "P2": 0, "P3": 0, "unset": 0}
    escalated = 0
    complete = 0
    from_db = 0
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
        if c.get("source") == "database":
            from_db += 1
    summary: dict[str, Any] = {
        "total_cases": len(cases),
        "by_priority": by_priority,
        "escalated": escalated,
        "intake_complete": complete,
        "database_only_cases": from_db,
        "as_of": datetime.now(UTC).isoformat(),
    }
    if db is not None:
        summary["database"] = db_patient_stats(db)
    return summary


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
