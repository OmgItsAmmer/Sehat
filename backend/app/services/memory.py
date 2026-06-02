"""Per-phone triage session state — Redis with TTL, in-memory fallback when unset."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.agent.state import TriageState, fresh_state
from app.config import settings

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 86400
SESSION_KEY_PREFIX = "session:"

# Used when REDIS_URL is empty (CI, local smoke tests without Docker).
_FALLBACK: dict[str, str] = {}

_redis_client: aioredis.Redis | None = None


def is_redis_configured() -> bool:
    return bool(settings.redis_url.strip())


def _session_key(phone: str) -> str:
    return f"{SESSION_KEY_PREFIX}{phone}"


def dumps(state: TriageState) -> str:
    return json.dumps(dict(state), ensure_ascii=False)


def loads(phone: str, raw: str) -> TriageState:
    data: dict[str, Any] = json.loads(raw)
    merged = fresh_state(phone)
    merged.update(data)
    merged["patient_phone"] = phone
    return merged


async def get_redis() -> aioredis.Redis | None:
    """Shared async Redis client (None when Redis is not configured)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not is_redis_configured():
        return None
    _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def use_redis_client(client: aioredis.Redis | None) -> None:
    """Test helper — inject a FakeRedis instance."""
    global _redis_client
    _redis_client = client


async def load(phone: str) -> TriageState:
    """Return existing state or a fresh one for this phone/chat id."""
    key = _session_key(phone)
    client = await get_redis()

    if client is not None:
        raw = await client.get(key)
        if raw:
            return loads(phone, raw)
        return fresh_state(phone)

    raw = _FALLBACK.get(key)
    if raw:
        return loads(phone, raw)
    return fresh_state(phone)


async def save(phone: str, state: TriageState) -> None:
    """Persist state after a graph pass (24h TTL when using Redis)."""
    key = _session_key(phone)
    payload = dumps(state)
    client = await get_redis()

    if client is not None:
        await client.set(key, payload, ex=SESSION_TTL_SECONDS)
        return

    _FALLBACK[key] = payload


async def delete(phone: str) -> None:
    """Remove one session (tests / admin)."""
    key = _session_key(phone)
    client = await get_redis()
    if client is not None:
        await client.delete(key)
    _FALLBACK.pop(key, None)


async def clear_all() -> None:
    """Test helper — wipe all sessions."""
    _FALLBACK.clear()
    client = await get_redis()
    if client is None:
        return
    async for key in client.scan_iter(match=f"{SESSION_KEY_PREFIX}*"):
        await client.delete(key)
