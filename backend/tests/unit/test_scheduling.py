"""Appointment scheduling service."""

from __future__ import annotations

from datetime import date

import pytest
from app.database.base import Base
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.services.scheduling import (
    book_next_slot,
    format_slot_time,
    lookup_queue_status,
    normalize_phone,
    parse_appointment_consent,
    parse_preferred_day,
    slots_taken_count,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.unit


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Patient.__table__, Appointment.__table__],
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_normalize_phone_pk() -> None:
    assert normalize_phone("0323 650 8184") == "03236508184"
    assert normalize_phone("+923236508184") == "03236508184"


def test_slot_times() -> None:
    assert format_slot_time(0) == "09:00"
    assert format_slot_time(1) == "09:15"


def test_parse_preferred_day_weekday() -> None:
    ref = date(2026, 6, 3)  # Wednesday
    d = parse_preferred_day("Thursday", today=ref)
    assert d == date(2026, 6, 4)


def test_parse_appointment_consent() -> None:
    assert parse_appointment_consent("haan ji") is True
    assert parse_appointment_consent("nahi") is False
    assert parse_appointment_consent("maybe later") is None


def test_book_next_slot_sequential(db_session) -> None:
    r1 = book_next_slot(
        db_session,
        doctor_key="general",
        preferred_day_text="Thursday",
        session_phone="+923001234567",
        contact_phone="03001234567",
    )
    assert r1["appointment_time"] == "09:00"

    r2 = book_next_slot(
        db_session,
        doctor_key="general",
        preferred_day_text="Thursday",
        session_phone="+923009999999",
        contact_phone="03009999999",
    )
    assert r2["appointment_time"] == "09:15"


def test_per_doctor_isolation(db_session) -> None:
    appt_date = parse_preferred_day("Friday", today=date(2026, 6, 3))
    assert appt_date is not None
    book_next_slot(
        db_session,
        doctor_key="general",
        preferred_day_text=appt_date.isoformat(),
        session_phone="s1",
        contact_phone="03001111111",
    )
    book_next_slot(
        db_session,
        doctor_key="pediatrics",
        preferred_day_text=appt_date.isoformat(),
        session_phone="s2",
        contact_phone="03002222222",
    )
    assert slots_taken_count(db_session, doctor_key="general", appointment_date=appt_date) == 1
    assert slots_taken_count(db_session, doctor_key="pediatrics", appointment_date=appt_date) == 1


def test_guest_booking(db_session) -> None:
    r = book_next_slot(
        db_session,
        doctor_key="cardiology",
        preferred_day_text="Monday",
        session_phone="ws_test",
        contact_phone=None,
    )
    assert r["guest_code"]
    assert len(r["guest_code"]) == 6


def test_lookup_by_phone(db_session) -> None:
    book_next_slot(
        db_session,
        doctor_key="general",
        preferred_day_text="Monday",
        session_phone="s1",
        contact_phone="03001234567",
    )
    status = lookup_queue_status(db_session, contact_phone="03001234567")
    assert status is not None
    assert status["time"] == "09:00"
    assert "Saeed" in status["doctor_label"]
