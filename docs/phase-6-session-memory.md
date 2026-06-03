# Phase 6 — Session memory (Redis)

**Goal:** The bot remembers each patient's conversation across multiple WhatsApp messages instead of treating every webhook as a new case.

**Status:** Implemented.

**Prerequisites:** Phase 5 (webhook → `process_incoming_message` → graph → reply). See [phase-5-whatsapp-triage.md](./phase-5-whatsapp-triage.md).

---

## Problem Phase 6 solves

Before Redis, session state lived in a **process-local dictionary**. That meant:

- Restarting uvicorn wiped all conversations
- Multiple workers (or Fly.io replicas) each had their own memory — a patient could get inconsistent replies
- Slot-filling only worked while the same process stayed up

Phase 6 stores `TriageState` in **Redis** keyed by Green API `chatId`, with a **24-hour TTL** so stale threads expire automatically.

---

## How it works

On every inbound message, `intake.process_incoming_message()` does:

```
1. state = await memory.load(chat_id)
2. append new message to state["messages"]
3. apply_pending_slot_answer(state)   # if bot asked a slot question last turn
4. result = graph.invoke(state)
5. await memory.save(chat_id, result)
6. persist to Postgres (optional) + WhatsApp reply
```

Redis key format:

```text
session:79001234567@c.us
```

Value: JSON serialization of the full `TriageState` dict (`priority`, `slots`, `messages`, `pending_slot`, etc.).

TTL: **86400 seconds (24 hours)** — refreshed on every `save`.

---

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | *(empty)* | e.g. `redis://localhost:6379` from [docker-compose.yml](../docker-compose.yml) |

| `REDIS_URL` set | Behaviour |
|-----------------|-----------|
| Yes | All `load` / `save` use Redis |
| No | **In-memory fallback** (same as Phase 5) — fine for CI and quick local tests |

Start Redis locally:

```bash
docker compose up -d redis
```

Ensure `.env` contains:

```env
REDIS_URL=redis://localhost:6379
```

On startup, uvicorn logs either `Session memory: redis` or `Session memory: in-memory`.

---

## Code map

| File | Role |
|------|------|
| `backend/app/services/memory.py` | `async def load` / `save`, Redis client, fallback dict, `SESSION_TTL_SECONDS` |
| `backend/app/services/intake.py` | `await memory.load` / `save` (async orchestration) |
| `backend/app/api/whatsapp.py` | `await process_incoming_message(...)` |
| `backend/app/main.py` | Logs backend choice; `close_redis()` on shutdown |

No change to the LangGraph definition — only **where state lives** between invocations.

---

## Multi-turn example

| Turn | Patient sends | Stored after `save` |
|------|---------------|---------------------|
| 1 | `appointment chahiye back pain` | `priority=P3`, `pending_slot=chief_complaint`, bot asked first slot question |
| 2 | `lower back, one week` | `slots.chief_complaint` filled, next slot question or routing |
| 3 | `Wednesday` | More slots filled → route → confirmation |

Turn 2+ uses graph **ingress** → `slot_check` (skips re-classify) because `priority` is already set. That logic is unchanged from Phase 5; Phase 6 only ensures turn 1's state is still there when turn 2 arrives.

---

## API reference (`memory.py`)

```python
await memory.load(phone: str) -> TriageState
await memory.save(phone: str, state: TriageState) -> None
await memory.delete(phone: str) -> None      # single session
await memory.clear_all() -> None             # tests
await memory.close_redis() -> None           # app shutdown
memory.is_redis_configured() -> bool
```

Serialization helpers: `dumps(state)`, `loads(phone, raw)` — merge stored JSON over `fresh_state()` so new fields get defaults.

---

## Testing

| Test file | What it verifies |
|-----------|------------------|
| `tests/unit/test_memory.py` | In-memory round-trip; fakeredis TTL and `clear_all` |
| `tests/unit/test_intake.py` | Two-message P3 flow with persisted state (async) |
| `tests/integration/test_whatsapp_triage.py` | Webhook leaves `priority` in memory after P1 |

CI runs **without** Redis (`REDIS_URL` unset) — tests use the in-memory fallback automatically.

To exercise Redis locally:

```bash
docker compose up -d redis
cd backend && REDIS_URL=redis://localhost:6379 pytest tests/unit/test_memory.py -v
```

---

## Operations notes

- **Horizontal scaling:** Point every app instance at the same `REDIS_URL` so all workers share session keys.
- **Privacy:** Session JSON contains message text; treat Redis like PHI-adjacent storage (network ACLs, no public exposure).
- **Eviction:** TTL handles cleanup; no manual delete required for normal flows.
- **Deploy:** Provision Redis on Upstash and set `REDIS_URL` as a Fly secret (see [`flyio-deploy_runbook.md`](runbooks/flyio-deploy_runbook.md)).

---

## Related documentation

- [Build order — Phase 6](./plan.md#phase-6--session-memory-day-4)
- [Phase 5 — WhatsApp wiring](./phase-5-whatsapp-triage.md)
- [LangGraph state fields](./architecture/langgraph.md)
- [Architecture overview](./architecture/architecture.md)
