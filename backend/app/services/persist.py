from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.patient import Patient


def persist_incoming_message(
    *,
    db: Session,
    patient_phone: str,
    body: str,
    raw_payload: dict | None,
) -> Message:
    patient = db.scalar(select(Patient).where(Patient.phone == patient_phone))
    if patient is None:
        patient = Patient(phone=patient_phone)
        db.add(patient)
        db.flush()

    msg = Message(patient_id=patient.id, direction="inbound", body=body, raw_payload=raw_payload)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

