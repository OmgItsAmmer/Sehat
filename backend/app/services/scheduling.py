"""Per-doctor 15-minute appointment booking and queue lookup."""

from __future__ import annotations

import re
import secrets
import string
import uuid
from datetime import date, datetime, time, timedelta

from dateutil import parser as date_parser
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.patient import Patient

CLINIC_OPEN = time(9, 0)
CLINIC_CLOSE = time(23, 0)
SLOT_MINUTES = 15
MAX_SLOTS_PER_DAY = int(
    ((CLINIC_CLOSE.hour * 60 + CLINIC_CLOSE.minute) - (CLINIC_OPEN.hour * 60 + CLINIC_OPEN.minute))
    / SLOT_MINUTES
)

DOCTOR_LABELS: dict[str, str] = {
    "general": "Dr Saeed Sarwar (General)",
    "pediatrics": "Dr Ammer Saeed (Pediatrics)",
    "cardiology": "Dr Muhid Saeed (Cardiology)",
}

PATIENT_TYPE_LABELS: dict[str, str] = {
    "general": "general medicine",
    "pediatrics": "pediatrics",
    "cardiology": "cardiology",
}

_WEEKDAY_MAP = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "jumerat": 3,
    "jumeraat": 3,
    "friday": 4,
    "fri": 4,
    "juma": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
    "peer": 0,
    "mangal": 1,
    "budh": 2,
    "itwar": 6,
    "hafta": 6,
}


def normalize_phone(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    digits = re.sub(r"\D", "", str(raw).strip())
    if digits.startswith("92") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if digits.startswith("3") and len(digits) == 10:
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("03"):
        return digits
    return None


def generate_guest_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def slot_index_to_time(slot_index: int) -> time:
    base = datetime.combine(date.today(), CLINIC_OPEN)
    t = base + timedelta(minutes=slot_index * SLOT_MINUTES)
    return t.time()


def format_slot_time(slot_index: int) -> str:
    t = slot_index_to_time(slot_index)
    return t.strftime("%H:%M")


def parse_preferred_day(text: str, *, today: date | None = None) -> date | None:
    """Resolve natural language day to a calendar date."""
    if not text or not text.strip():
        return None
    ref = today or date.today()
    lowered = text.strip().lower()

    if lowered in ("kal", "tomorrow", "agla din"):
        return ref + timedelta(days=1)
    if lowered in ("parson", "day after tomorrow", "parso"):
        return ref + timedelta(days=2)
    if lowered in ("aaj", "today", "aj"):
        return ref

    for name, wd in _WEEKDAY_MAP.items():
        if name in lowered.split():
            days_ahead = (wd - ref.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return ref + timedelta(days=days_ahead)

    try:
        parsed = date_parser.parse(text, fuzzy=True, default=datetime.combine(ref, time(12, 0)))
        if isinstance(parsed, datetime):
            return parsed.date()
        if isinstance(parsed, date):
            return parsed
        return None
    except (ValueError, TypeError, OverflowError):
        return None


def slots_taken_count(db: Session, *, doctor_key: str, appointment_date: date) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.doctor_key == doctor_key,
                Appointment.appointment_date == appointment_date,
            )
        )
        or 0
    )


def _get_or_create_patient_for_booking(
    db: Session,
    *,
    session_phone: str,
    contact_phone: str | None,
    guest_code: str | None,
) -> Patient:
    if contact_phone:
        patient = db.scalar(select(Patient).where(Patient.phone == contact_phone))
        if patient is None:
            patient = Patient(phone=contact_phone)
            db.add(patient)
            db.flush()
        return patient

    guest_phone = f"guest_{guest_code}"
    patient = db.scalar(select(Patient).where(Patient.phone == guest_phone))
    if patient is None:
        patient = Patient(phone=guest_phone)
        db.add(patient)
        db.flush()
    return patient


def book_next_slot(
    db: Session,
    *,
    doctor_key: str,
    preferred_day_text: str,
    session_phone: str,
    contact_phone: str | None,
) -> dict[str, str]:
    """
    Book the next free 15-minute slot for a doctor on the resolved day.
    Returns dict with date, time, doctor_label, guest_code (if any), contact_phone.
    """
    appt_date = parse_preferred_day(preferred_day_text)
    if appt_date is None:
        appt_date = date.today() + timedelta(days=1)

    taken = slots_taken_count(db, doctor_key=doctor_key, appointment_date=appt_date)
    if taken >= MAX_SLOTS_PER_DAY:
        raise ValueError("No slots available on that day for this doctor.")

    slot_index = taken
    normalized = normalize_phone(contact_phone)
    guest_code: str | None = None
    if not normalized:
        guest_code = generate_guest_code()

    patient = _get_or_create_patient_for_booking(
        db,
        session_phone=session_phone,
        contact_phone=normalized,
        guest_code=guest_code,
    )

    row = Appointment(
        id=uuid.uuid4(),
        doctor_key=doctor_key,
        appointment_date=appt_date,
        slot_index=slot_index,
        contact_phone=normalized,
        guest_code=guest_code,
        session_phone=session_phone,
        patient_id=patient.id,
    )
    db.add(row)
    db.commit()

    time_str = format_slot_time(slot_index)
    return {
        "appointment_date": appt_date.isoformat(),
        "appointment_time": time_str,
        "doctor_key": doctor_key,
        "doctor_label": DOCTOR_LABELS.get(doctor_key, doctor_key),
        "patient_type": PATIENT_TYPE_LABELS.get(doctor_key, doctor_key),
        "contact_phone": normalized or "",
        "guest_code": guest_code or "",
        "slot_index": str(slot_index),
    }


def lookup_queue_status(
    db: Session,
    *,
    contact_phone: str | None = None,
    guest_code: str | None = None,
) -> dict[str, str] | None:
    """Latest appointment for phone or guest code."""
    stmt = select(Appointment).order_by(Appointment.created_at.desc())
    if guest_code:
        stmt = stmt.where(Appointment.guest_code == guest_code.upper())
    elif contact_phone:
        norm = normalize_phone(contact_phone)
        if not norm:
            return None
        stmt = stmt.where(Appointment.contact_phone == norm)
    else:
        return None

    row = db.scalars(stmt.limit(1)).first()
    if row is None:
        return None

    return {
        "doctor_key": row.doctor_key,
        "doctor_label": DOCTOR_LABELS.get(row.doctor_key, row.doctor_key),
        "date": row.appointment_date.isoformat(),
        "time": format_slot_time(row.slot_index),
        "contact_phone": row.contact_phone or "",
        "guest_code": row.guest_code or "",
    }


def parse_appointment_consent(text: str) -> bool | None:
    """True=yes, False=no, None=unclear."""
    t = text.strip().lower()
    yes_tokens = (
        "yes",
        "yeah",
        "yep",
        "haan",
        "han",
        "ji",
        "jee",
        "bilkul",
        "ok",
        "okay",
        "theek",
        "book",
        "confirm",
        "kar do",
        "kardein",
    )
    no_tokens = ("no", "nahi", "nah", "na", "cancel", "mat", "nope", "don't", "dont")
    if any(tok in t for tok in no_tokens) and not any(tok in t for tok in yes_tokens):
        return False
    if any(tok in t for tok in yes_tokens):
        return True
    return None
