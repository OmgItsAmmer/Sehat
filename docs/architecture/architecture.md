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
       │                      ├── load TriageState (Redis, Phase 6)
       │                      └── graph.invoke(state)  ◄── LangGraph
       │                               │
       │                               ├── classify (Gemini)
       │                               ├── slot-fill / route
       │                               └── notify (Slack, Phase 5)
       ▼
Reply via Green API          Dashboard / overrides (Phase 7)
```

## Backend layout

| Area | Path | Responsibility |
|------|------|----------------|
| API | `backend/app/api/` | Webhooks, health, dashboard (later) |
| Agent | `backend/app/agent/` | LangGraph state, nodes, graph, prompts, triage |
| Models | `backend/app/models/` | SQLAlchemy `patients`, `messages` |
| Services | `backend/app/services/` | WhatsApp client, persistence, Slack (later) |
| Migrations | `backend/database/migrations/` | Alembic |

## Agent / LangGraph

The core product logic lives in the **triage graph**, not in the webhook handler. The webhook should stay thin: normalize payload → load state → append message → invoke graph → save state → send `reply`.

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
| **Redis** | Per-phone `TriageState` with TTL (Phase 6) |
| **Gemini API** | Structured JSON classification in `classify_node` |

## Build phases

Implementation order is documented in [plan.md](../plan.md). Current status:

| Phase | Topic | Status |
|-------|--------|--------|
| 1 | WhatsApp → FastAPI | Done |
| 2 | Postgres persistence | Done |
| 3 | Standalone Gemini classify | Done (`triage.py`) |
| 4 | LangGraph graph | Done (`state.py`, `nodes.py`, `graph.py`) |
| 5+ | WhatsApp wiring, memory, dashboard, specialists, evals | Planned |

## Related docs

- [LangGraph triage graph](./langgraph.md)
- [Build order / phases](../plan.md)
- [Green API WhatsApp runbook](../runbooks/Green-api-whatsapp-integration_runbook.md)
- [Alembic migrations](../runbooks/alembic_migration_rubooks.md)
