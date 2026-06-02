"""Unit tests for session memory (in-memory fallback + Redis via fakeredis)."""

from __future__ import annotations

import pytest
from app.config import settings
from app.services import memory

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
async def _reset_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "redis_url", "")
    await memory.close_redis()
    memory.use_redis_client(None)
    await memory.clear_all()
    yield
    await memory.close_redis()
    memory.use_redis_client(None)
    await memory.clear_all()


async def test_load_returns_fresh_state_for_unknown_phone() -> None:
    state = await memory.load("+923001234567@c.us")
    assert state["patient_phone"] == "+923001234567@c.us"
    assert state["messages"] == []
    assert state["priority"] is None


async def test_save_and_load_round_trip_in_memory() -> None:
    phone = "79001234567@c.us"
    await memory.save(phone, {"patient_phone": phone, "priority": "P3", "messages": ["hi"]})
    loaded = await memory.load(phone)
    assert loaded["priority"] == "P3"
    assert loaded["messages"] == ["hi"]

    loaded["messages"].append("mutated")
    again = await memory.load(phone)
    assert again["messages"] == ["hi"]


async def test_redis_backend_uses_ttl_and_persists() -> None:
    fakeredis = pytest.importorskip("fakeredis.aioredis")
    fake = fakeredis.FakeRedis(decode_responses=True)
    memory.use_redis_client(fake)

    phone = "79001234567@c.us"
    await memory.save(phone, {"patient_phone": phone, "priority": "P2", "messages": ["fever"]})
    loaded = await memory.load(phone)
    assert loaded["priority"] == "P2"

    ttl = await fake.ttl(f"{memory.SESSION_KEY_PREFIX}{phone}")
    assert 0 < ttl <= memory.SESSION_TTL_SECONDS


async def test_clear_all_removes_redis_sessions() -> None:
    fakeredis = pytest.importorskip("fakeredis.aioredis")
    fake = fakeredis.FakeRedis(decode_responses=True)
    memory.use_redis_client(fake)

    phone = "79001234567@c.us"
    await memory.save(phone, {"patient_phone": phone, "priority": "P3", "messages": []})
    await memory.clear_all()
    loaded = await memory.load(phone)
    assert loaded["priority"] is None
