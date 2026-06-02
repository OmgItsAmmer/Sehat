"""Per-phone triage session state (in-memory now; Redis in Phase 6)."""

from __future__ import annotations

import copy
import json
from typing import Any

from app.agent.state import TriageState, fresh_state

_SESSIONS: dict[str, TriageState] = {}


def _session_key(phone: str) -> str:
    return f"session:{phone}"


def load(phone: str) -> TriageState:
    """Return existing state or a fresh one for this phone/chat id."""
    key = _session_key(phone)
    stored = _SESSIONS.get(key)
    if stored is not None:
        return copy.deepcopy(stored)
    return fresh_state(phone)


def save(phone: str, state: TriageState) -> None:
    """Persist state after a graph pass (deep copy to avoid mutation leaks)."""
    _SESSIONS[_session_key(phone)] = copy.deepcopy(state)


def clear_all() -> None:
    """Test helper — reset all in-memory sessions."""
    _SESSIONS.clear()


def dumps(state: TriageState) -> str:
    """JSON snapshot for future Redis storage."""
    return json.dumps(dict(state), ensure_ascii=False)


def loads(phone: str, raw: str) -> TriageState:
    data: dict[str, Any] = json.loads(raw)
    data.setdefault("patient_phone", phone)
    return data  # type: ignore[return-value]
