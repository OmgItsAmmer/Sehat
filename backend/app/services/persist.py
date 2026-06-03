from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.state import TriageState
from app.models.message import Message
from app.models.patient import Patient


def persist_incoming_message(
    *,
    db: Session,
    patient_phone: str,
    body: str,
    raw_payload: dict | None,
) -> Message:
    patient = _get_or_create_patient(db=db, patient_phone=patient_phone)

    msg = Message(patient_id=patient.id, direction="inbound", body=body, raw_payload=raw_payload)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _get_or_create_patient(*, db: Session, patient_phone: str) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.phone == patient_phone))
    if patient is None:
        patient = Patient(phone=patient_phone)
        db.add(patient)
        db.flush()
    return patient


def persist_intake_state(*, db: Session, patient_phone: str, state: TriageState) -> None:
    """Snapshot agent-gathered intake slots onto the patient row for the clinic dashboard."""
    patient = _get_or_create_patient(db=db, patient_phone=patient_phone)
    patient.intake_slots = dict(state.get("slots") or {})
    patient.slots_complete = bool(state.get("slots_complete"))
    patient.pending_slot = state.get("pending_slot")
    patient.routed_to = state.get("routed_to")
    db.commit()


def persist_outbound_message(*, db: Session, patient_phone: str, body: str) -> Message:
    patient = _get_or_create_patient(db=db, patient_phone=patient_phone)

    msg = Message(patient_id=patient.id, direction="outbound", body=body, raw_payload=None)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
