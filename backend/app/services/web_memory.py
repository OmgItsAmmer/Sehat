"""Web patient chat sessions — separate Redis/in-memory store from WhatsApp triage."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

from app.agent.state import TriageState, fresh_state
from app.services.memory import SESSION_TTL_SECONDS, dumps, get_redis, loads

logger = logging.getLogger(__name__)

WEB_SESSION_KEY_PREFIX = "web-session:"

_FALLBACK: dict[str, str] = {}


def _session_key(session_id: str) -> str:
    return f"{WEB_SESSION_KEY_PREFIX}{session_id}"


async def load(session_id: str) -> TriageState:
    key = _session_key(session_id)
    client = await get_redis()

    if client is not None:
        try:
            raw = await client.get(key)
            if isinstance(raw, str):
                return loads(session_id, raw)
            return fresh_state(session_id)
        except Exception:
            logger.warning(
                "Redis load failed for web session %s — using in-memory fallback",
                session_id,
            )
            from app.services.memory import _invalidate_redis

            await _invalidate_redis()

    raw = _FALLBACK.get(key)
    if raw:
        return loads(session_id, raw)
    return fresh_state(session_id)


async def save(session_id: str, state: TriageState) -> None:
    stored = cast(TriageState, dict(state))
    stored["last_activity_at"] = datetime.now(UTC).isoformat()
    key = _session_key(session_id)
    payload = dumps(stored)
    client = await get_redis()

    if client is not None:
        try:
            await client.set(key, payload, ex=SESSION_TTL_SECONDS)
            return
        except Exception:
            logger.warning(
                "Redis save failed for web session %s — using in-memory fallback",
                session_id,
            )
            from app.services.memory import _invalidate_redis

            await _invalidate_redis()

    _FALLBACK[key] = payload


async def delete(session_id: str) -> None:
    key = _session_key(session_id)
    client = await get_redis()
    if client is not None:
        await client.delete(key)
    _FALLBACK.pop(key, None)


async def clear_all() -> None:
    _FALLBACK.clear()
    client = await get_redis()
    if client is None:
        return
    try:
        async for key in client.scan_iter(match=f"{WEB_SESSION_KEY_PREFIX}*"):
            await client.delete(key)
    except Exception:
        logger.warning("Redis unavailable during web clear_all")


async def list_sessions() -> list[str]:
    client = await get_redis()
    sessions: list[str] = []
    prefix_len = len(WEB_SESSION_KEY_PREFIX)

    if client is not None:
        try:
            async for key in client.scan_iter(match=f"{WEB_SESSION_KEY_PREFIX}*"):
                sessions.append(key[prefix_len:])
            return sorted(sessions)
        except Exception:
            logger.warning("Redis list_sessions failed — using in-memory fallback")
            from app.services.memory import _invalidate_redis

            await _invalidate_redis()

    for key in _FALLBACK:
        if key.startswith(WEB_SESSION_KEY_PREFIX):
            sessions.append(key[prefix_len:])
    return sorted(sessions)
