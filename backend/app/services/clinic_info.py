"""Detect clinic FAQ / queue queries and build context for the composer."""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.database.session import rollback_db
from app.services import rag
from app.services.scheduling import lookup_queue_status, normalize_phone

logger = logging.getLogger(__name__)

_INFO_KEYWORDS = (
    "timing",
    "timings",
    "hours",
    "open",
    "close",
    "doctor",
    "dr ",
    "dr.",
    "saeed",
    "sarwar",
    "ammer",
    "muhid",
    "pediatric",
    "cardio",
    "reception",
    "fatima",
    "clinic",
    "address",
    "location",
)

_QUEUE_KEYWORDS = (
    "queue",
    "wait",
    "waiting",
    "appointment time",
    "mera appointment",
    "my appointment",
    "slot",
    "booked",
    "booking status",
    "number kitna",
    "turn",
)


def extract_phone_from_text(text: str) -> str | None:
    """Find Pakistani mobile in message."""
    patterns = [
        r"0?3\d{2}[\s-]?\d{7}",
        r"\+92[\s-]?3\d{2}[\s-]?\d{7}",
        r"92[\s-]?3\d{2}[\s-]?\d{7}",
    ]
    for pat in patterns:
        m = re.search(pat, text.replace(" ", ""))
        if m:
            return normalize_phone(m.group(0))
    return None


def is_bare_phone_message(text: str) -> bool:
    """True when the message is only a phone number (intake slot answer, not a FAQ)."""
    stripped = text.strip()
    if not stripped:
        return False
    if re.search(r"[a-zA-Z\u0600-\u06FF]", stripped):
        return False
    norm = normalize_phone(stripped)
    if not norm:
        return False
    digits = re.sub(r"\D", "", stripped)
    return len(digits) >= 10


def is_clinic_info_query(text: str) -> bool:
    if is_bare_phone_message(text):
        return False
    lowered = text.lower()
    if any(kw in lowered for kw in _INFO_KEYWORDS):
        return True
    if re.search(r"\b(dr|doctor)\b", lowered):
        return True
    return False


def is_queue_status_query(text: str) -> bool:
    if is_bare_phone_message(text):
        return False
    lowered = text.lower()
    if not any(kw in lowered for kw in _QUEUE_KEYWORDS):
        return False
    return extract_phone_from_text(text) is not None or "guest" in lowered


def _safe_lookup_queue(
    db: Session,
    *,
    contact_phone: str | None,
    guest_code: str | None,
) -> dict[str, str] | None:
    try:
        return lookup_queue_status(db, contact_phone=contact_phone, guest_code=guest_code)
    except Exception:
        logger.exception("appointment queue lookup failed")
        rollback_db(db)
        return None


def build_clinic_context(
    *,
    db: Session | None,
    message: str,
    contact_phone_from_slots: str | None = None,
    skip_db_lookup: bool = False,
) -> str:
    """RAG chunks + optional appointment lookup for composer."""
    if skip_db_lookup or is_bare_phone_message(message):
        return ""

    parts: list[str] = []

    wants_lookup = is_queue_status_query(message)
    if wants_lookup:
        phone = extract_phone_from_text(message) or (
            normalize_phone(contact_phone_from_slots)
            if contact_phone_from_slots
            else None
        )
        guest_m = re.search(r"guest[_\s-]?([a-z0-9]{4,8})", message, re.I)
        guest_code = guest_m.group(1).upper() if guest_m else None
        if db is not None and (phone or guest_code):
            status = _safe_lookup_queue(db, contact_phone=phone, guest_code=guest_code)
            if status:
                parts.append(
                    f"APPOINTMENT_LOOKUP: {status['doctor_label']} on "
                    f"{status['date']} at {status['time']}. "
                    f"(contact: {status.get('contact_phone') or 'guest code ' + status.get('guest_code', '')})"
                )
            else:
                parts.append(
                    "APPOINTMENT_LOOKUP: No appointment found for that phone or guest code."
                )

    if is_clinic_info_query(message) or is_queue_status_query(message):
        chunks = rag.retrieve(db, message)
        if chunks:
            parts.append("CLINIC_KNOWLEDGE:\n" + rag.format_context(chunks))

    return "\n\n".join(parts).strip()
