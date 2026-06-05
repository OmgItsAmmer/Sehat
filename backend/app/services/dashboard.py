"""Aggregate cases for clinic dashboard — Redis sessions merged with Postgres history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.agent.state import TriageState, latest_message
from app.channels import WEB_SESSION_ID_PREFIX
from app.services import memory, web_memory

CaseSource = Literal["session", "database", "both", "web"]


def is_web_session_id(phone: str) -> bool:
    return phone.startswith(WEB_SESSION_ID_PREFIX)


def _display_name(phone: str) -> str:
    if is_web_session_id(phone):
        short = phone[len(WEB_SESSION_ID_PREFIX) :][:8]
        return f"Web chat · {short}"
    return phone.replace("@c.us", "").replace("@g.us", "")


def _state_to_case(
    phone: str, state: TriageState, *, source: CaseSource = "session"
) -> dict[str, Any]:
    messages = state.get("messages") or []
    slots = state.get("slots") or {}
    appointment = None
    if slots.get("appointment_time"):
        appointment = {
            "date": slots.get("appointment_date"),
            "time": slots.get("appointment_time"),
            "doctor": state.get("routed_to"),
            "guest_code": state.get("guest_code"),
        }
    last_activity_at = state.get("last_activity_at")
    if not last_activity_at and messages:
        last_activity_at = datetime.now(UTC).isoformat()
    return {
        "phone": phone,
        "display_name": _display_name(phone),
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
        "last_activity_at": last_activity_at,
        "appointment": appointment,
        "appointment_booked": bool(state.get("appointment_booked")),
        "guest_code": state.get("guest_code"),
    }


def _parse_activity_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _max_message_at(db_messages: list[dict[str, Any]]) -> str | None:
    times = [_parse_activity_at(m.get("created_at")) for m in db_messages]
    valid = [t for t in times if t is not None]
    if not valid:
        return None
    return max(valid).isoformat()


def _patient_intake_snapshot(patient: Any) -> dict[str, Any]:
    """Intake fields persisted on the patient row (survives Redis expiry)."""
    slots = dict(getattr(patient, "intake_slots", None) or {})
    return {
        "slots": slots,
        "slots_complete": bool(getattr(patient, "slots_complete", False)),
        "pending_slot": getattr(patient, "pending_slot", None),
        "routed_to": getattr(patient, "routed_to", None),
        "priority": getattr(patient, "priority", None),
        "confidence": getattr(patient, "confidence", None),
        "reasoning": getattr(patient, "reasoning", None),
    }


def _apply_patient_intake(case: dict[str, Any], patient: Any | None) -> None:
    """Fill missing live-session intake fields from Postgres."""
    if patient is None:
        return
    snapshot = _patient_intake_snapshot(patient)
    if not case.get("slots") and snapshot["slots"]:
        case["slots"] = snapshot["slots"]
    if not case.get("slots_complete") and snapshot["slots_complete"]:
        case["slots_complete"] = snapshot["slots_complete"]
    if case.get("pending_slot") is None and snapshot["pending_slot"]:
        case["pending_slot"] = snapshot["pending_slot"]
    if not case.get("routed_to") and snapshot["routed_to"]:
        case["routed_to"] = snapshot["routed_to"]
    if not case.get("priority") and snapshot["priority"]:
        case["priority"] = snapshot["priority"]
    if not case.get("confidence") and snapshot["confidence"]:
        case["confidence"] = snapshot["confidence"]
    if not case.get("reasoning") and snapshot["reasoning"]:
        case["reasoning"] = snapshot["reasoning"]


def _case_from_db_messages(
    phone: str, db_messages: list[dict[str, Any]], *, patient: Any | None = None
) -> dict[str, Any]:
    """Build a queue row from persisted WhatsApp messages when Redis session is empty."""
    inbound = [m["body"] for m in db_messages if m.get("direction") == "inbound"]
    outbound = [m["body"] for m in db_messages if m.get("direction") == "outbound"]
    last_inbound = inbound[-1] if inbound else ""
    last_outbound = outbound[-1] if outbound else ""
    intake = _patient_intake_snapshot(patient) if patient is not None else {}
    slots = intake.get("slots") or {}
    return {
        "phone": phone,
        "display_name": _display_name(phone),
        "priority": intake.get("priority"),
        "confidence": intake.get("confidence") or 0.0,
        "reasoning": intake.get("reasoning")
        or ("Persisted intake — no live triage session in Redis."),
        "escalated": False,
        "slots_complete": bool(intake.get("slots_complete")),
        "slots": slots,
        "routed_to": intake.get("routed_to"),
        "message_count": len(db_messages),
        "last_message": last_inbound,
        "pending_slot": intake.get("pending_slot"),
        "reply": last_outbound,
        "awaiting_human_review": False,
        "source": "database",
        "last_activity_at": _max_message_at(db_messages),
    }


def _merge_last_activity(case: dict[str, Any], db_messages: list[dict[str, Any]]) -> None:
    """Keep the newest timestamp from Redis session and Postgres messages."""
    candidates: list[datetime] = []
    for raw in (case.get("last_activity_at"), _max_message_at(db_messages)):
        parsed = _parse_activity_at(raw) if isinstance(raw, str) else None
        if parsed is not None:
            candidates.append(parsed)
    if candidates:
        case["last_activity_at"] = max(candidates).isoformat()


def _sort_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Newest patient activity first."""

    def sort_key(c: dict[str, Any]) -> str:
        return c.get("last_activity_at") or ""

    cases.sort(key=sort_key, reverse=True)
    return cases


async def _prune_orphan_sessions(
    db: Session,
    *,
    phones: list[str],
    web_sessions: list[str],
) -> None:
    """Drop Redis/web sessions with no matching patient row — keeps cache aligned with Postgres."""
    from app.models.patient import Patient

    db_phones = set(db.scalars(select(Patient.phone)).all())

    for phone in phones:
        if phone not in db_phones:
            await memory.delete(phone)

    for session_id in web_sessions:
        if session_id not in db_phones:
            await web_memory.delete(session_id)


async def clear_all_sessions() -> None:
    """Wipe WhatsApp + web triage sessions from Redis/in-memory (dev reset)."""
    await memory.clear_all()
    await web_memory.clear_all()


async def list_cases(*, db: Session | None = None) -> list[dict[str, Any]]:
    """Merge active Redis triage sessions with patients who only exist in Postgres."""
    phones = await memory.list_phones()
    web_sessions = await web_memory.list_sessions()

    if db is not None:
        await _prune_orphan_sessions(db, phones=phones, web_sessions=web_sessions)

    by_phone: dict[str, dict[str, Any]] = {}

    for phone in phones:
        state = await memory.load(phone)
        if state.get("messages"):
            by_phone[phone] = _state_to_case(phone, state, source="session")

    for session_id in web_sessions:
        state = await web_memory.load(session_id)
        if state.get("messages"):
            by_phone[session_id] = _state_to_case(session_id, state, source="web")

    if db is not None:
        from app.models.patient import Patient

        patients = db.scalars(select(Patient).order_by(desc(Patient.created_at))).all()
        for patient in patients:
            phone = patient.phone
            db_msgs = list_db_messages(db=db, phone=phone)
            if not db_msgs:
                continue
            if phone in by_phone:
                prev = by_phone[phone].get("source")
                by_phone[phone]["source"] = "both" if prev in ("session", "web") else prev
                db_count = len(db_msgs)
                if db_count > (by_phone[phone].get("message_count") or 0):
                    by_phone[phone]["message_count"] = db_count
                if not by_phone[phone].get("last_message"):
                    inbound = [m["body"] for m in db_msgs if m["direction"] == "inbound"]
                    if inbound:
                        by_phone[phone]["last_message"] = inbound[-1]
                _apply_patient_intake(by_phone[phone], patient)
                _merge_last_activity(by_phone[phone], db_msgs)
            else:
                by_phone[phone] = _case_from_db_messages(phone, db_msgs, patient=patient)

    return _sort_cases(list(by_phone.values()))


async def get_case(phone: str, *, db: Session | None = None) -> dict[str, Any] | None:
    patient_row = None
    if db is not None:
        from app.models.patient import Patient

        patient_row = db.scalar(select(Patient).where(Patient.phone == phone))

    if is_web_session_id(phone):
        state = await web_memory.load(phone)
        if state.get("messages"):
            case = _state_to_case(phone, state, source="web")
            case["messages"] = list(state.get("messages") or [])
            case["clarification_rounds"] = state.get("clarification_rounds") or 0
            if db is not None:
                case["db_messages"] = list_db_messages(db=db, phone=phone)
                if case["db_messages"]:
                    case["source"] = "both"
                    _merge_last_activity(case, case["db_messages"])
                _apply_patient_intake(case, patient_row)
            else:
                case["db_messages"] = []
            return case

    state = await memory.load(phone)
    if state.get("messages"):
        case = _state_to_case(phone, state, source="session")
        case["messages"] = list(state.get("messages") or [])
        case["clarification_rounds"] = state.get("clarification_rounds") or 0
        if db is not None:
            case["db_messages"] = list_db_messages(db=db, phone=phone)
            if case["db_messages"]:
                case["source"] = "both"
            _apply_patient_intake(case, patient_row)
        else:
            case["db_messages"] = []
        return case

    if db is not None:
        db_msgs = list_db_messages(db=db, phone=phone)
        if db_msgs:
            case = _case_from_db_messages(phone, db_msgs, patient=patient_row)
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
