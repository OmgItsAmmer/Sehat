# Sehat architecture

Sehat is an **agentic intake triage system**: a LangGraph state machine backed by FastAPI, Postgres (Neon), Redis (sessions, Phase 6+), and Gemini for classification.

## System context

```
Patient (WhatsApp)
       │
       ▼
Green API webhook ──► FastAPI (backend/app/api/whatsapp.py)
       │                      │
       │                      ├── persist message (Postgres)
       │                      ├── load/save TriageState (`services/memory.py`)
       │                      ├── graph.invoke(state)  ◄── LangGraph
       │                      ├── persist inbound (Postgres)
       │                      └── send reply (`services/whatsapp.py`)
       │                               │
       │                               ├── classify (Gemini)
       │                               ├── slot-fill / route
       │                               └── notify (`services/slack.py`)
       ▼
Reply via Green API          Dashboard / overrides (Phase 7)
```

## Backend layout

| Area | Path | Responsibility |
|------|------|----------------|
| API | `backend/app/api/` | Webhooks, health, dashboard (later) |
| Agent | `backend/app/agent/` | LangGraph state, nodes, graph, prompts, triage, reply composer |
| Models | `backend/app/models/` | SQLAlchemy `patients`, `messages` |
| Services | `backend/app/services/` | `intake`, `memory`, `whatsapp`, `slack`, `persist` |
| Migrations | `backend/database/migrations/` | Alembic |

## Agent / LangGraph

The core product logic lives in the **triage graph**, not in the webhook handler. The webhook delegates to `process_incoming_message()` in `services/intake.py`: load state → append message → apply slot answer → `graph.invoke` → save → WhatsApp reply.

**Deep dive:** [langgraph.md](./langgraph.md) — state fields, every node, conditional edges, scratch tests, and phase roadmap.

Quick reference:

```python
from app.agent.graph import graph
from app.agent.state import fresh_state

state = fresh_state("+923001234567")
state["messages"] = ["seene mein dard"]
result = graph.invoke(state)
# result["priority"] == "P1", result["escalated"] is True
```

## Data stores

| Store | Use |
|-------|-----|
| **Postgres** | Patients, messages, cases, overrides (dashboard phases) |
| **Redis sessions** | Per-phone `TriageState` via `memory.py` (`REDIS_URL`, 24h TTL; in-memory if unset) |
| **Gemini API** | Structured JSON classification in `classify_node` |

## Build phases

Implementation order is documented in [plan.md](../plan.md). Current status:

| Phase | Topic | Status |
|-------|--------|--------|
| 1 | WhatsApp → FastAPI | Done |
| 2 | Postgres persistence | Done |
| 3 | Standalone Gemini classify | Done (`triage.py`) |
| 4 | LangGraph graph | Done (`state.py`, `nodes.py`, `graph.py`) |
| 5 | WhatsApp + Slack wiring | Done |
| 6 | Redis session memory | Done (`services/memory.py`) |
| 7+ | Dashboard, specialists, evals | Planned |

## Related docs

- [Phase 5 — WhatsApp + triage wiring](../phase-5-whatsapp-triage.md)
- [Phase 6 — Redis session memory](../phase-6-session-memory.md)
- [LangGraph triage graph](./langgraph.md)
- [Build order / phases](../plan.md)
- [Green API WhatsApp runbook](../runbooks/Green-api-whatsapp-integration_runbook.md)
- [Alembic migrations](../runbooks/alembic_migration_rubooks.md)
