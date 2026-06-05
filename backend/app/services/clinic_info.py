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
    
    # Matches: "queue", "wait", "turn", "number kitna", "status", etc.
    if any(kw in lowered for kw in (
        "queue", "wait", "waiting", "turn", "number kitna", "status", "lookup", "check"
    )):
        return True
        
    # Matches: "my appointment", "appointment date", "appointment time", "when is my appointment"
    if "appointment" in lowered and any(kw in lowered for kw in ("my", "mera", "meri", "date", "time", "when", "kab", "status", "scheduled")):
        return True
        
    if "booking" in lowered and any(kw in lowered for kw in ("my", "mera", "meri", "status", "check")):
        return True
        
    return False


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
    session_messages: list[str] | None = None,
) -> str:
    """RAG chunks + optional appointment lookup for composer."""
    is_bare_phone = is_bare_phone_message(message)
    has_prev_queue_query = session_messages and any(is_queue_status_query(m) for m in session_messages)
    
    if skip_db_lookup or (is_bare_phone and not has_prev_queue_query):
        return ""

    parts: list[str] = []

    wants_lookup = is_queue_status_query(message)
    if not wants_lookup and is_bare_phone and has_prev_queue_query:
        wants_lookup = True

    if wants_lookup:
        phone = extract_phone_from_text(message) or (
            normalize_phone(contact_phone_from_slots) if contact_phone_from_slots else None
        )
        guest_m = re.search(r"guest[_\s-]?([a-z0-9]{4,8})", message, re.I)
        guest_code = guest_m.group(1).upper() if guest_m else None
        if db is not None and (phone or guest_code):
            status = _safe_lookup_queue(db, contact_phone=phone, guest_code=guest_code)
            if status:
                contact = status.get("contact_phone") or (
                    "guest code " + status.get("guest_code", "")
                )
                parts.append(
                    f"APPOINTMENT_LOOKUP: {status['doctor_label']} on "
                    f"{status['date']} at {status['time']}. "
                    f"(contact: {contact})"
                )
            else:
                parts.append(
                    "APPOINTMENT_LOOKUP: No appointment found for that phone or guest code."
                )
        else:
            parts.append(
                "APPOINTMENT_LOOKUP: Please ask the patient to share the mobile number "
                "they used when booking, or their guest code, so we can look up their appointment."
            )

    if is_clinic_info_query(message) or wants_lookup:
        chunks = rag.retrieve(db, message)
        if chunks:
            parts.append("CLINIC_KNOWLEDGE:\n" + rag.format_context(chunks))

    return "\n\n".join(parts).strip()
