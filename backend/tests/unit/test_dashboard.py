"""Dashboard merges Redis sessions with Postgres patient history."""

from __future__ import annotations

import pytest
from app.services import dashboard, memory
from app.services.persist import persist_incoming_message, persist_outbound_message

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
