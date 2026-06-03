"""Dashboard merges Redis sessions with Postgres patient history."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.agent.triage import TriageResult
from app.models.patient import Patient
from app.services import dashboard, memory, pipeline, web_memory
from app.services.persist import persist_incoming_message, persist_outbound_message
from sqlalchemy import select

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_list_cases_includes_db_only_patients(db_session) -> None:
    await memory.clear_all()
    phone = "79009998877@c.us"
    persist_incoming_message(
        db=db_session, patient_phone=phone, body="fee kitni hai", raw_payload=None
    )
    persist_outbound_message(db=db_session, patient_phone=phone, body="Please call the front desk.")

    cases = await dashboard.list_cases(db=db_session)

    assert len(cases) == 1
    assert cases[0]["phone"] == phone
    assert cases[0]["source"] == "database"
    assert cases[0]["last_message"] == "fee kitni hai"
    assert cases[0]["message_count"] == 2


@patch("app.agent.nodes.classify_message_with_openai")
@pytest.mark.asyncio
async def test_list_cases_includes_web_chat_sessions(mock_classify, db_session) -> None:
    await memory.clear_all()
    await web_memory.clear_all()
    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.8,
        reasoning="Routine web intake.",
    )
    session_id = "ws_a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    await pipeline.process_web_inbound(session_id=session_id, body="web headache", db=db_session)

    cases = await dashboard.list_cases(db=db_session)
    match = [c for c in cases if c["phone"] == session_id]
    assert len(match) == 1
    assert match[0]["source"] in ("web", "both")
    assert match[0]["last_message"] == "web headache"
    assert match[0]["message_count"] >= 1

    detail = await dashboard.get_case(session_id, db=db_session)
    assert detail is not None
    assert detail["messages"] == ["web headache"]
    assert len(detail["db_messages"]) >= 2


@pytest.mark.asyncio
async def test_list_cases_prunes_redis_when_patient_not_in_db(db_session) -> None:
    await memory.clear_all()
    await web_memory.clear_all()
    phone = "79007770000@c.us"
    await memory.save(
        phone,
        {
            "patient_phone": phone,
            "messages": ["orphan redis only"],
            "priority": "P3",
        },
    )
    assert db_session.scalar(select(Patient).where(Patient.phone == phone)) is None

    cases = await dashboard.list_cases(db=db_session)

    assert not any(c["phone"] == phone for c in cases)
    assert not (await memory.load(phone)).get("messages")


@patch("app.agent.nodes.classify_message_with_openai")
async def test_get_case_includes_persisted_slots_when_redis_expired(
    mock_classify, db_session
) -> None:
    from app.agent.triage import TriageResult

    mock_classify.return_value = TriageResult(
        priority="P3",
        confidence=0.9,
        reasoning="Routine.",
    )
    phone = "79005556677@c.us"
    await pipeline.process_whatsapp_inbound(
        chat_id=phone,
        body="appointment for back pain",
        db=db_session,
    )
    await pipeline.process_whatsapp_inbound(
        chat_id=phone,
        body="lower back pain",
        db=db_session,
    )
    await memory.delete(phone)

    case = await dashboard.get_case(phone, db=db_session)
    assert case is not None
    assert case["slots"].get("chief_complaint") == "lower back pain"
    assert case["source"] == "database"


async def test_get_case_from_database_when_no_redis_session(db_session) -> None:
    await memory.clear_all()
    phone = "79001112233@c.us"
    persist_incoming_message(
        db=db_session, patient_phone=phone, body="seene mein dard", raw_payload=None
    )

    case = await dashboard.get_case(phone, db=db_session)

    assert case is not None
    assert case["source"] == "database"
    assert case["messages"] == ["seene mein dard"]
    assert len(case["db_messages"]) == 1
