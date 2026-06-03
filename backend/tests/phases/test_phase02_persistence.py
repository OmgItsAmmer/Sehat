"""Phase 2 — inbound messages persist to Postgres (SQLite in CI)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.models.message import Message
from app.models.patient import Patient
from app.services.persist import persist_incoming_message, persist_outbound_message
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = [pytest.mark.unit, pytest.mark.phase2]


def test_persist_inbound_creates_patient_and_message(db_session: Session) -> None:
    msg = persist_incoming_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="seene mein dard",
        raw_payload={"idMessage": "1"},
    )

    assert msg.direction == "inbound"
    patient = db_session.scalar(select(Patient).where(Patient.phone == "79001234567@c.us"))
    assert patient is not None
    assert msg.patient_id == patient.id


def test_persist_outbound_message(db_session: Session) -> None:
    persist_incoming_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="hi",
        raw_payload=None,
    )
    out = persist_outbound_message(
        db=db_session,
        patient_phone="79001234567@c.us",
        body="Thanks for contacting us.",
    )
    assert out.direction == "outbound"
    assert len(db_session.scalars(select(Message)).all()) == 2


@pytest.mark.integration
@patch("app.services.pipeline.whatsapp.send_text", return_value=True)
@patch("app.agent.nodes.slack.send_triage_alert", return_value=True)
def test_webhook_persists_inbound_when_db_available(
    _mock_slack,
    _mock_send,
    client_with_db,
    db_session: Session,
    green_api_text_payload: dict,
) -> None:
    response = client_with_db.post("/api/whatsapp/webhook", json=green_api_text_payload)

    assert response.status_code == 200
    rows = db_session.scalars(select(Message).where(Message.direction == "inbound")).all()
    assert len(rows) == 1
    assert rows[0].body == "seene mein dard"
