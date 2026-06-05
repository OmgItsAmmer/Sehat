"""Clinic info desk detection and context building."""

from __future__ import annotations

import pytest
from app.services.clinic_info import (
    build_clinic_context,
    is_bare_phone_message,
    is_clinic_info_query,
    is_queue_status_query,
)

pytestmark = pytest.mark.unit


def test_bare_phone_not_clinic_info() -> None:
    assert is_bare_phone_message("03001234567")
    assert not is_clinic_info_query("03001234567")
    assert build_clinic_context(db=None, message="03001234567") == ""


def test_is_clinic_info_query_hours() -> None:
    assert is_clinic_info_query("clinic timing kya hai")


def test_is_queue_status_query() -> None:
    assert is_queue_status_query("mera appointment 03001234567 queue")
    assert is_queue_status_query("what is my queue number?")
    assert is_queue_status_query("what is my appointment date?")
    assert not is_queue_status_query("appointment chahiye")


def test_build_clinic_context_has_knowledge() -> None:
    ctx = build_clinic_context(db=None, message="doctor list and timings")
    assert "CLINIC_KNOWLEDGE" in ctx or "Fatima" in ctx or "Saeed" in ctx


def test_build_clinic_context_asks_for_phone() -> None:
    ctx = build_clinic_context(db=None, message="what is my queue number?")
    assert "Please ask the patient to share the mobile number" in ctx


def test_build_clinic_context_with_previous_messages() -> None:
    ctx = build_clinic_context(
        db=None,
        message="03001234567",
        session_messages=["what is my queue number?", "03001234567"]
    )
    assert "APPOINTMENT_LOOKUP" in ctx
