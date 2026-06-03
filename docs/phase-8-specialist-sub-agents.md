# Phase 8 — Specialist sub-agents

**Goal:** Cardiology and pediatrics ask different slot questions during intake, without duplicating the LangGraph.

**Status:** Implemented.

**Prerequisites:** Phase 4–6 (graph, WhatsApp, Redis session memory). See [plan.md](./plan.md#phase-8--specialist-sub-agents-day-67) and [architecture/langgraph.md](./architecture/langgraph.md).

---

## Design

Specialists are **not separate graphs**. One `gather_slots_node` asks questions from whichever profile `route_node` selected:

```
classify (P2/P3)
    → route_node          # pick specialist → routed_to
    → slot_check_node     # missing_slots() uses that profile
    → gather_slots_node   # one question from profile.slot_questions
    → … notify / confirm
```

Each specialist module defines:

| Field | Purpose |
|-------|---------|
| `SYSTEM_PROMPT` | Intake persona (ready for LLM-driven slot fill later) |
| `REQUIRED_SLOTS` | Ordered slot names stored in `state["slots"]` |
| `SLOT_QUESTIONS` | Patient-facing copy, one field per turn |

---

## Specialists

### General (`general.py`)

Default for routine appointments without cardiac or pediatric keywords.

| Slot | Example question |
|------|------------------|
| `chief_complaint` | Main symptom |
| `symptom_duration` | How long |
| `preferred_day` | Appointment day |

### Cardiology (`cardiology.py`)

Triggered by P1-class keywords in history, or words like `seene`, `chest`, `dil`, `heart`.

| Slot | Example question |
|------|------------------|
| `pain_location` | Where exactly |
| `pain_radiation` | Arm / jaw spread |
| `onset` | Sudden vs gradual |
| `associated_symptoms` | Sweating, nausea, breathlessness |
| `medical_history` | Prior cardiac events |

### Pediatrics (`pediatrics.py`)

Triggered by `bach`, `bachay`, `child`, `infant`, `baby`, etc.

| Slot | Example question |
|------|------------------|
| `child_age` | Age in months/years |
| `child_weight` | Approximate weight |
| `fever_duration` | If fever, how long |
| `chief_symptoms` | Parent’s main concern |
| `preferred_day` | Appointment day |

**Routing precedence:** cardiology beats pediatrics when both keyword sets could match (e.g. chest pain in a child).

---

## Code map

| File | Role |
|------|------|
| `backend/app/agent/specialists/router.py` | `pick_specialist(state)` |
| `backend/app/agent/specialists/registry.py` | `SpecialistProfile`, `get_profile(key)` |
| `backend/app/agent/specialists/general.py` | General slots + questions |
| `backend/app/agent/specialists/cardiology.py` | Cardiac slots + questions |
| `backend/app/agent/specialists/pediatrics.py` | Pediatric slots + questions |
| `backend/app/agent/nodes.py` | `route_node`, `gather_slots_node` use profiles |
| `backend/app/agent/state.py` | `missing_slots()` reads `routed_to` |
| `backend/app/agent/graph.py` | P2/P3: `classify → route → slot_check` (route before slots) |

---

## Graph change vs Phase 4–7

Previously, `route` ran **after** all slots were filled. Phase 8 runs `route` **immediately after classify** for P2/P3 so the first `gather_slots` question is already specialist-specific.

Resume path (Phase 6) is unchanged: `ingress → slot_check` when `priority` is P2/P3 and slots are incomplete. `routed_to` stays in Redis from the first turn.

---

## Manual checks

With Gemini mocked or live, exercise three paths:

| Patient message | Expected `routed_to` | First `pending_slot` |
|-----------------|----------------------|----------------------|
| `appointment chahiye back pain` | `general` | `chief_complaint` |
| `bachay ko 3 din se tez bukhaar` | `pediatrics` | `child_age` |
| `dil ki dawa ke baad seene mein halka dard` (P3) | `cardiology` | `pain_location` |

Unit tests: `pytest tests/unit/test_specialists.py tests/unit/test_graph.py -q`

---

## What comes next

| Phase | Change |
|-------|--------|
| 9 | Done — `make eval` ([phase-9-eval-suite.md](./phase-9-eval-suite.md)) |
| 10 | Deploy + scripted demo scenarios |

See [plan.md](./plan.md#phase-9--eval-suite-day-7).
