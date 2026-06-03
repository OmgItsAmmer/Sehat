"""Phase 2 unit tests: message persistence to Postgres (SQLite in CI)."""

from __future__ import annotations

import pytest
from app.models.message import Message
from app.models.patient import Patient
from app.services.persist import persist_incoming_message, persist_intake_state
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.unit


def test_persist_creates_patient_and_message(db_session: Session) -> None:
    payload = {"typeWebhook": "incomingMessageReceived", "idMessage": "ABC"}

    msg = persist_incoming_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="seene mein dard",
        raw_payload=payload,
    )

    assert msg.id is not None
    assert msg.direction == "inbound"
    assert msg.body == "seene mein dard"
    assert msg.raw_payload == payload

    patient = db_session.scalar(select(Patient).where(Patient.phone == "79001234567@c.us"))
    assert patient is not None
    assert msg.patient_id == patient.id


def test_persist_reuses_existing_patient(db_session: Session) -> None:
    first = persist_incoming_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="first message",
        raw_payload={"idMessage": "1"},
    )
    second = persist_incoming_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="second message",
        raw_payload={"idMessage": "2"},
    )

    patients = db_session.scalars(select(Patient)).all()
    messages = db_session.scalars(select(Message)).all()

    assert len(patients) == 1
    assert len(messages) == 2
    assert first.patient_id == second.patient_id


def test_persist_allows_null_raw_payload(db_session: Session) -> None:
    msg = persist_incoming_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="hello",
        raw_payload=None,
    )

    assert msg.raw_payload is None


def test_persist_intake_state_stores_slots(db_session: Session) -> None:
    phone = "79001234567@c.us"
    persist_incoming_message(
        db=db_session,
        patient_phone=phone,
        body="headache",
        raw_payload=None,
    )
    persist_intake_state(
        db=db_session,
        patient_phone=phone,
        state={
            "slots": {"chief_complaint": "headache", "symptom_duration": "2 days"},
            "slots_complete": False,
            "pending_slot": "preferred_day",
            "routed_to": "general",
        },
    )

    patient = db_session.scalar(select(Patient).where(Patient.phone == phone))
    assert patient is not None
    assert patient.intake_slots["chief_complaint"] == "headache"
    assert patient.intake_slots["symptom_duration"] == "2 days"
    assert patient.pending_slot == "preferred_day"
    assert patient.routed_to == "general"
    assert patient.slots_complete is False
