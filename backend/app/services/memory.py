"""Per-phone triage session state — Redis with TTL, in-memory fallback when unset."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, cast

import redis.asyncio as aioredis

from app.agent.state import TriageState, fresh_state, merge_state
from app.config import settings

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 86400
SESSION_KEY_PREFIX = "session:"
REDIS_SOCKET_CONNECT_TIMEOUT = 1.0
REDIS_SOCKET_TIMEOUT = 1.0
REDIS_UNAVAILABLE_COOLDOWN_SECONDS = 30.0

# Used when REDIS_URL is empty (CI, local smoke tests without Docker).
_FALLBACK: dict[str, str] = {}

_redis_client: aioredis.Redis | None = None
_redis_disabled_until: float = 0.0
_redis_lock = asyncio.Lock()


def is_redis_configured() -> bool:
    return bool(settings.redis_url.strip())


def _session_key(phone: str) -> str:
    return f"{SESSION_KEY_PREFIX}{phone}"


def dumps(state: TriageState) -> str:
    return json.dumps(dict(state), ensure_ascii=False)


def loads(phone: str, raw: str) -> TriageState:
    data: dict[str, Any] = json.loads(raw)
    merged = merge_state(fresh_state(phone), data)
    merged["patient_phone"] = phone
    return merged


async def get_redis() -> aioredis.Redis | None:
    """Shared async Redis client (None when Redis is not configured or unavailable)."""
    global _redis_client
    if time.monotonic() < _redis_disabled_until:
        return None
    if _redis_client is not None:
        return _redis_client
    if not is_redis_configured():
        return None

    async with _redis_lock:
        # Re-check under lock in case another task resolved it
        if time.monotonic() < _redis_disabled_until:
            return None
        if _redis_client is not None:
            return _redis_client

        try:
            client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                retry_on_timeout=False,
            )
            await asyncio.wait_for(client.ping(), timeout=REDIS_SOCKET_CONNECT_TIMEOUT)
            _redis_client = client
            return _redis_client
        except Exception:
            logger.warning(
                "Redis unavailable — using in-memory fallback for %.0fs",
                REDIS_UNAVAILABLE_COOLDOWN_SECONDS,
            )
            _mark_redis_unavailable()
            await _invalidate_redis()
            return None


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except (RuntimeError, Exception):
            pass
        _redis_client = None


async def _invalidate_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
    _redis_client = None


def _mark_redis_unavailable() -> None:
    global _redis_disabled_until
    _redis_disabled_until = time.monotonic() + REDIS_UNAVAILABLE_COOLDOWN_SECONDS


def reset_redis_circuit_breaker() -> None:
    """Test helper — allow Redis retries immediately."""
    global _redis_disabled_until
    _redis_disabled_until = 0.0


def use_redis_client(client: aioredis.Redis | None) -> None:
    """Test helper — inject a FakeRedis instance."""
    global _redis_client
    _redis_client = client


async def load(phone: str) -> TriageState:
    """Return existing state or a fresh one for this phone/chat id."""
    key = _session_key(phone)
    client = await get_redis()

    if client is not None:
        try:
            raw = await client.get(key)
            if isinstance(raw, str):
                try:
                    return loads(phone, raw)
                except json.JSONDecodeError:
                    logger.error("Corrupted JSON in Redis for key %s", key)
                    return fresh_state(phone)
            return fresh_state(phone)
        except Exception:
            logger.exception("Redis load failed for %s — using in-memory fallback", phone)
            _mark_redis_unavailable()
            await _invalidate_redis()

    raw = _FALLBACK.get(key)
    if raw:
        return loads(phone, raw)
    return fresh_state(phone)


async def save(phone: str, state: TriageState) -> None:
    """Persist state after a graph pass (24h TTL when using Redis)."""
    stored = cast(TriageState, dict(state))
    stored["last_activity_at"] = datetime.now(UTC).isoformat()
    key = _session_key(phone)
    payload = dumps(stored)
    client = await get_redis()

    if client is not None:
        try:
            await client.set(key, payload, ex=SESSION_TTL_SECONDS)
            return
        except Exception:
            logger.exception("Redis save failed for %s — using in-memory fallback", phone)
            _mark_redis_unavailable()
            await _invalidate_redis()

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
    global _redis_client
    _FALLBACK.clear()
    client = await get_redis()
    if client is None:
        return
    try:
        async for key in client.scan_iter(match=f"{SESSION_KEY_PREFIX}*"):
            await client.delete(key)
    except Exception:
        logger.exception("Redis unavailable during clear_all — resetting client")
        if _redis_client is not None:
            try:
                await _redis_client.aclose()
            except Exception:
                pass
        _redis_client = None


async def list_phones() -> list[str]:
    """All chat ids with stored session state (Redis scan or in-memory keys)."""
    client = await get_redis()
    phones: list[str] = []
    prefix_len = len(SESSION_KEY_PREFIX)

    if client is not None:
        try:
            async for key in client.scan_iter(match=f"{SESSION_KEY_PREFIX}*"):
                phones.append(key[prefix_len:])
            return sorted(phones)
        except Exception:
            logger.exception("Redis list_phones failed — using in-memory fallback")
            _mark_redis_unavailable()
            await _invalidate_redis()

    for key in _FALLBACK:
        if key.startswith(SESSION_KEY_PREFIX):
            phones.append(key[prefix_len:])
    return sorted(phones)
