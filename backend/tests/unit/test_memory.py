"""Unit tests for in-memory session store."""

from __future__ import annotations

import pytest
from app.services import memory

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_sessions() -> None:
    memory.clear_all()
    yield
    memory.clear_all()


def test_load_returns_fresh_state_for_unknown_phone() -> None:
    state = memory.load("+923001234567@c.us")
    assert state["patient_phone"] == "+923001234567@c.us"
    assert state["messages"] == []
    assert state["priority"] is None


def test_save_and_load_round_trip() -> None:
    phone = "79001234567@c.us"
    memory.save(phone, {"patient_phone": phone, "priority": "P3", "messages": ["hi"]})
    loaded = memory.load(phone)
    assert loaded["priority"] == "P3"
    assert loaded["messages"] == ["hi"]

    loaded["messages"].append("mutated")
    again = memory.load(phone)
    assert again["messages"] == ["hi"]
