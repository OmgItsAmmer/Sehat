# Sehat (صحت) — AI Clinic Intake Triage

**Practical assignment submission · June 2026**

| | |
|---|---|
| **Case study** | [AI Intern Case Study (PDF)](https://drive.google.com/file/d/15jw-jFdx_2puXqi-Lwbdf7iT9uZczNTC/view?usp=sharing) |
| **Scenario** | Pakistani clinic — receptionist **Sana** faces 34+ WhatsApp messages before 9am; urgency is not FIFO |
| **Solution** | Agentic triage: classify → gather context → route → book — with human override when uncertain |
| **Stack** | LangGraph · FastAPI · PostgreSQL · Redis · React · Green API (WhatsApp) · OpenAI |

---

## 1. Problem (case study)

Patients message the clinic on WhatsApp in **Urdu, English, and Roman Urdu** — appointments, fees, mild symptoms, and emergencies mixed in one inbox. Sana reads messages **in arrival order**. A chest-pain message (`seene mein dard`) can sit behind routine chats for **40+ minutes**.

**Core insight:** A human inbox is FIFO; **medical urgency is not FIFO.** Sehat turns the inbox into a **priority-ranked, pre-documented queue** before Sana picks up the phone.

---

## 2. Approach (how I solved it)

| Step | Decision | Why |
|------|----------|-----|
| 1 | **Prove the pipe first** (WhatsApp → API → DB) | No point tuning prompts if messages never arrive |
| 2 | **LangGraph state machine**, not a free-form chatbot | Explicit branches: emergency exit, slot-fill, human pause, booking |
| 3 | **Structured LLM output** (JSON schema) on classify & reply | Avoid parsing fragile natural language in code |
| 4 | **Hardcoded P1 keyword override** before the model | Safety: chest pain / unconscious / breathing — alert even if the model hesitates |
| 5 | **Freeze graph when confidence < 0.75** | Receptionist **Agree / Upgrade / Downgrade** — correction resumes the same session |
| 6 | **Specialist sub-flows** (general · pediatrics · cardiology) | Different slot questions per route |
| 7 | **RAG clinic desk + appointment slots** | Hours/doctors from KB; 15-min per-doctor booking after intake |

Build order and phase notes: [`docs/plan.md`](docs/plan.md)

---

## 3. Case study requirements → what I delivered

| Case need | Implementation |
|-----------|----------------|
| Triage by urgency | **P1** emergency · **P2** urgent · **P3** routine · **OOS** (billing, visa, labs) |
| WhatsApp channel | Green API webhook → `process_incoming_message` → LangGraph → reply |
| Web channel (demo without WhatsApp) | React web chat + same graph / session store |
| Natural conversation | Reply composer: greetings, Urdu/Roman Urdu, one question at a time |
| P1 immediate escalation | Slack alert; graph skips slot-fill; advises emergency care |
| Receptionist visibility | Dashboard: case list, conversation, priority, filled slots |
| Human correction | Override API → updates state → graph resumes; audit in DB |
| Returning patients | Redis session TTL + Postgres messages & intake state |
| Clinic information | RAG over seeded [`backend/data/clinic_kb.md`](backend/data/clinic_kb.md) (hours, doctors, phone) |
| Appointment booking | Per-doctor 15-minute slots (9:00–23:00); guest code if no phone |
| Queue lookup | Patient asks by phone or guest code → appointment status in context |

---

## 4. System (one diagram)

```
WhatsApp / Web  →  FastAPI  →  load TriageState (Redis)
                    │
                    ▼
              LangGraph triage
         ┌────────┼────────┐
         ▼        ▼        ▼
    P1 alert   slot-fill   OOS redirect
    (Slack)   + specialist + RAG desk
         │        │        │
         └────────┴────────┘
                    ▼
         book slot · persist · reply
                    ▼
         Dashboard (override · audit)
```

Graph detail: [`docs/architecture/langgraph.md`](docs/architecture/langgraph.md)

---

## 5. Evidence (for reviewers)

| Check | Command / result |
|-------|------------------|
| Automated tests | `make test` — **119 tests** (unit + integration + system) |
| Classification eval | `make eval` — **20 labelled** Urdu/English messages ([`backend/evals/fixtures.py`](backend/evals/fixtures.py)) |
| Lint / types | `make lint` — ruff + mypy |
| P1 path | Keyword `seene mein dard` → P1 without relying on model luck (`test_graph.py`) |
| Human pause | Low confidence → hold message until override (`test_pipeline.py`) |

**Demo messages to try**

| Message | Expected behaviour |
|---------|-------------------|
| `seene mein dard` | P1 · Slack alert · no booking loop |
| `appointment chahiye back pain ke liye` | P3 · slot questions · booking offer |
| `fee kitni hai` | OOS · polite redirect |
| `clinic timing kya hai` | RAG hours from clinic KB |
| `haan` (after booking offer) | Next free 15-min slot for routed doctor |

---

## 6. Tech stack

| Layer | Choice |
|-------|--------|
| Agent orchestration | LangGraph 0.2 (`backend/app/agent/`) |
| LLM | OpenAI `gpt-4o-mini` — classify + compose (`OPENAI_API_KEY`) |
| Embeddings (RAG) | `text-embedding-3-small` + pgvector |
| API | FastAPI · Python 3.11+ |
| Data | PostgreSQL 16 · Redis (sessions) · Alembic migrations |
| Channels | Green API (WhatsApp) · React dashboard + web chat |
| Alerts | Slack incoming webhook |

---

## 7. Run locally (5 minutes)

**Prerequisites:** Python 3.11+, Node 20+, Docker (Postgres + Redis).

```bash
git clone <repo-url> && cd sehat
cp .env.example .env    # set OPENAI_API_KEY, DATABASE_URL, REDIS_URL (optional: GREEN_API_*, SLACK_*)

docker compose up -d
make migrate
make seed-kb            # needs OPENAI_API_KEY + Postgres with pgvector

make dev                # API :8000
make frontend-dev       # UI :5173
```

WhatsApp setup: [`docs/runbooks/Green-api-whatsapp-integration_runbook.md`](docs/runbooks/Green-api-whatsapp-integration_runbook.md)  
Production deploy: [`docs/runbooks/flyio-deploy_runbook.md`](docs/runbooks/flyio-deploy_runbook.md)

**Makefile:** `make test` · `make lint` · `make eval` · `make migrate` · `make seed-kb`

---

## 8. Repository map (high level)

```
sehat/
├── backend/app/agent/     # LangGraph: graph, nodes, state, specialists
├── backend/app/services/  # pipeline, RAG, scheduling, WhatsApp, memory
├── backend/evals/         # 20-message classification suite
├── frontend/src/          # ClinicDashboard, web chat, override UI
└── docs/                  # architecture, phases, runbooks
```

---

## 9. Deeper documentation

| Topic | Link |
|-------|------|
| Architecture | [`docs/architecture/architecture.md`](docs/architecture/architecture.md) |
| Triage graph nodes & edges | [`docs/architecture/langgraph.md`](docs/architecture/langgraph.md) |
| Human-in-the-loop (Phase 7) | [`docs/phase-7-human-override.md`](docs/phase-7-human-override.md) |
| Eval suite (Phase 9) | [`docs/phase-9-eval-suite.md`](docs/phase-9-eval-suite.md) |
| Build phases | [`docs/plan.md`](docs/plan.md) |

---

## 10. Scope & trade-offs (honest limits)

- **Demo clinic data** in markdown seed — not a live EMR integration  
- **Green API** used to avoid Meta Business verification for the assignment timeline  
- **Voice** supported via Whisper when `OPENAI_API_KEY` is set; primary demo path is text  
- **Multi-clinic / calendar UI** — out of scope for this submission; listed in product backlog in repo history  

---

<div align="center">

**Submission:** AI Intern practical assignment · deadline **3 June 2026**  
Case study: [Google Drive PDF](https://drive.google.com/file/d/15jw-jFdx_2puXqi-Lwbdf7iT9uZczNTC/view?usp=sharing)

*The hardest design choice was the human-interrupt pattern: override must update graph state and audit trail without losing the patient mid-conversation.*

</div>
