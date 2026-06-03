<div align="center">

<br />

```
███████╗███████╗██╗  ██╗ █████╗ ████████╗
██╔════╝██╔════╝██║  ██║██╔══██╗╚══██╔══╝
███████╗█████╗  ███████║███████║   ██║   
╚════██║██╔══╝  ██╔══██║██╔══██║   ██║   
███████║███████╗██║  ██║██║  ██║   ██║   
╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═╝   
```

### **صحت** — AI-Powered Emergency Intake Triage

*Turning an unordered flood of patient messages into a ranked, routed,<br/>and already-documented work queue — before Sana even picks up the phone.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-CC785C?style=flat-square)](https://anthropic.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

<br/>

[**Live Demo**](#) · [**Architecture**](docs/architecture.md) · [**Deploy runbook**](docs/runbooks/flyio-deploy_runbook.md) · [**Report a Bug**](#)

<br/>

</div>

---

## The Problem

A Pakistani clinic receptionist receives **34+ WhatsApp messages every morning** before 9am. She reads them sequentially — appointments, fee questions, medicine queries — while somewhere in that unordered list, a chest pain message sits unanswered.

> *A human inbox is a FIFO queue. Medical urgency is not FIFO.*

By the time she reaches the emergency message, **40 minutes have passed.**

**Sehat fixes this.**

---

## What Sehat Does

Sehat is an **agentic intake triage system** — not a chatbot. It operates as a LangGraph state machine that:

- Receives patient messages from **WhatsApp, web, or voice**
- **Classifies urgency** (P1 Emergency → P2 Urgent → P3 Routine → Out of Scope) with a confidence score
- **Conducts a focused, natural conversation** — replies warmly in the patient's language (English / Urdu / Roman Urdu), answers greetings before asking clinical questions, and gently redirects off-topic messages
- **Escalates P1 cases immediately** with a Slack alert, bypassing all conversation steps
- **Packages a complete handoff** — patient name, symptoms, history, priority — before a human ever reads it
- **Remembers returning patients** across sessions
- Lets the receptionist **override any classification** in one click, with the correction flowing back into the agent graph

Sehat handles **~80% of intake autonomously.** The remaining 20% — ambiguous, complex, or emergency cases — reach a human faster and better-documented than before.

---

## Demo

<div align="center">

| Patient side (WhatsApp) | Receptionist dashboard |
|:---:|:---:|
| Patient sends *"seene mein dard"* | P1 alert fires in **< 4 seconds** |
| Bot asks one clarifying question | Case appears with full context |
| Bot confirms next steps to patient | Sana sees override buttons |

</div>

> **Try it:** Send a WhatsApp message to `+92-XXX-XXXXXXX` or open the [web chat](#).
> Try these scenarios: a chest pain report, a routine appointment request, and an out-of-scope billing question.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTAKE LAYER                            │
│   WhatsApp (Green API)  ·  Web Chat (React)  ·  Voice (Whisper) │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Input Normalizer    │
                    │  Urdu/English · clean │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Urgency Classifier  │  ← Claude (tool-use)
                    │  P1 · P2 · P3 · OOS  │
                    └──┬──────────┬─────────┘
                       │          │
              P1 ──────┘    P2/P3 │
              │                   │
   ┌──────────▼──────┐  ┌────────▼────────────┐
   │ Emergency Exit  │  │  Slot-Filling Agent │  ← LangGraph loop
   │ Skip everything │  │  Asks missing info  │
   └──────────┬──────┘  └────────┬────────────┘
              │                   │
              │         ┌─────────▼──────────┐
              │         │  Specialist Router  │
              │         │  Cardio·Paeds·Gen  │
              │         └─────────┬──────────┘
              │                   │
              └──────┬────────────┘
                     │
          ┌──────────▼──────────┐
          │  Summary + Routing  │  ← structured handoff packet
          └──────────┬──────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
┌───────▼────────┐        ┌────────▼────────┐
│  Slack Alert   │        │  Case DB + Dash │
│  Human notified│        │  Postgres · PG  │
└────────────────┘        └─────────────────┘
```

**Key design decisions:**

- Every node calls Claude with a strict JSON schema via tool-use — no free-text parsing anywhere
- `TriageState` persists across all turns; nodes read and write shared state
- Confidence < 0.75 triggers `await_human_review` — the graph **freezes** until Sana acts
- P1 keyword list is a hardcoded override — LLM output is ignored, alert fires regardless
- Two unresolved clarification rounds → forced escalation; the bot never loops forever

Full architecture notes: [`docs/architecture.md`](docs/architecture.md)

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent framework | **LangGraph 0.2** | State machine with real branching, interrupts, and human-in-loop |
| LLM | **Claude Sonnet 4.6** | Tool-use / structured output on every decision node |
| Backend | **FastAPI + Python 3.11** | Async, fast to deploy, production standard |
| Database | **PostgreSQL 16 + pgvector** | Cases, patient memory, embeddings |
| Session state | **Redis** | Conversation state with TTL — stale sessions auto-expire |
| WhatsApp | **Green API** | No Meta business verification — scan QR, get webhook in 20 min |
| Frontend | **React 18 + Vite + Tailwind** | Receptionist dashboard + web chat widget |
| Notifications | **Slack Webhooks** | P1 alert reaches Sana in < 2 seconds |
| Voice | **OpenAI Whisper** | Voice messages → text before entering the graph |
| Auth | **Clerk** | Dashboard login, one-line setup |
| Migrations | **Alembic** | Never touch schema manually |
| Deployment | **Fly.io (API) + Vercel (frontend)** | Cheapest demo stack; Neon + Upstash for data |

---

## Project Structure

```
sehat/
│
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py              # LangGraph graph + conditional edges
│   │   │   ├── state.py              # TriageState TypedDict
│   │   │   ├── nodes.py              # all node functions
│   │   │   ├── prompts.py            # system prompts per node
│   │   │   ├── tools.py              # Claude tool-use schemas
│   │   │   └── specialists/
│   │   │       ├── cardiology.py     # cardiac-specific slot questions
│   │   │       ├── pediatrics.py     # child-specific flow
│   │   │       ├── general.py
│   │   │       └── router.py         # picks which specialist
│   │   │
│   │   ├── api/
│   │   │   ├── whatsapp.py           # Green API webhook receiver
│   │   │   ├── dashboard.py          # REST endpoints for React
│   │   │   ├── human_override.py     # Sana's one-click override
│   │   │   └── health.py
│   │   │
│   │   ├── services/
│   │   │   ├── whatsapp.py           # Green API client
│   │   │   ├── slack.py              # alert sender
│   │   │   ├── whisper.py            # voice → text
│   │   │   ├── memory.py             # patient memory (Redis + PG)
│   │   │   └── rag.py                # pgvector clinic knowledge base
│   │   │
│   │   ├── models/                   # SQLAlchemy tables
│   │   └── schemas/                  # Pydantic request/response shapes
│   │
│   ├── database/
│   │   └── migrations/               # Alembic versioned migrations
│   │
│   └── evals/
│       ├── test_classification.py    # 20 labelled Urdu/English messages
│       ├── test_slots.py
│       ├── test_routing.py
│       └── fixtures.py               # ground-truth test cases
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx         # Sana's case queue
│       │   ├── CaseDetail.tsx        # full convo + override buttons
│       │   ├── WebChat.tsx           # patient-facing web widget
│       │   └── Analytics.tsx         # P1 response time, volume
│       └── components/
│           └── dashboard/
│               └── OverrideButtons.tsx  # human-in-loop widget
│
├── docs/
│   ├── architecture.md
│   ├── triage_logic.md
│   ├── plan.md
│   ├── ci-cd.md
│   └── runbooks/
│       ├── flyio-deploy_runbook.md      # Fly API + Vercel dashboard
│       ├── Green-api-whatsapp-integration_runbook.md
│       └── alembic_migration_rubooks.md
│
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop
- A WhatsApp number (personal is fine — Green API, no business verification)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/sehat.git
cd sehat
cp .env.example .env
```

Open `.env` and fill in:

```env
# Core
ANTHROPIC_API_KEY=        # console.anthropic.com
DATABASE_URL=postgresql://sehat:sehat@localhost:5432/sehat
REDIS_URL=redis://localhost:6379

# WhatsApp — green-api.com (free, scan QR, done in 20 min)
GREEN_API_INSTANCE=
GREEN_API_TOKEN=

# Notifications
SLACK_WEBHOOK_URL=        # api.slack.com/apps → Incoming Webhooks

# Optional
OPENAI_API_KEY=           # only needed for voice message support
CLERK_SECRET_KEY=         # only needed for dashboard auth
```

### 2. Start infrastructure

```bash
docker-compose up -d      # starts PostgreSQL + Redis
make migrate              # runs Alembic migrations
make seed                 # optional: loads dev fixtures
```

### 3. Run backend

```bash
cd backend
pip install -r requirements.txt
make dev                  # uvicorn with hot reload on :8000
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev               # Vite on :5173
```

### 5. Connect WhatsApp

See [`docs/runbooks/Green-api-whatsapp-integration_runbook.md`](docs/runbooks/Green-api-whatsapp-integration_runbook.md) — takes about 20 minutes. You scan a QR code in the Green API console, paste your instance ID and token into `.env`, and set your webhook URL to `https://<api>.fly.dev/api/whatsapp/webhook` when deployed.

---

## Makefile Commands

```bash
make dev          # start backend dev server
make migrate      # run pending Alembic migrations
make seed         # load dev fixtures
make eval         # run classification accuracy suite
make test         # run full test suite
make lint         # ruff + mypy
make build        # docker build all services
make up           # docker-compose up
make down         # docker-compose down
make logs         # tail all service logs
```

---

## Evaluation

Sehat ships with a labelled test suite of 20 real-world messages in Urdu and English across all four priority levels. Run it before every deploy:

```bash
make eval
```

```
Classification accuracy report
────────────────────────────────
P1  (emergency)   8/8   100%
P2  (urgent)      5/6    83%
P3  (routine)     5/5   100%
OOS               1/1   100%
────────────────────────────────
Overall          19/20   95%
Avg confidence    0.91
```

---

## Human-in-the-Loop

When confidence falls below 0.75, the LangGraph graph **pauses** at `await_human_review`. Sana sees the case on her dashboard with three buttons:

- **Agree** — classification is correct, resume graph
- **Upgrade** — raise priority, resume with correction logged
- **Downgrade** — lower priority, resume with correction logged

Every override is stored in the `overrides` table with timestamp, original classification, correction, and the receptionist's ID. This audit trail is what separates a clinical tool from a toy.

---

## Triage Logic

| Priority | Criteria | Bot action |
|----------|---------|-----------|
| **P1 Emergency** | Cardiac symptoms, stroke, unconsciousness, heavy bleeding, seizures, suicidal ideation | Bypass all conversation → immediate Slack alert → advise 1122 |
| **P2 Urgent** | High fever (esp. children), moderate acute pain, suspected fracture, diabetic concern | Gather slots quickly → route to specialist → same-day booking |
| **P3 Routine** | Mild ongoing symptoms, follow-ups, prescription refills, checkups | Full slot-filling flow → standard appointment booking |
| **OOS** | Billing, visa medicals, lab results, pharmacy | Polite redirect with alternative resource → log and close |

P1 keywords (`seene mein dard`, `chest pain`, `unconscious`, `nahi saans`, ...) are **hardcoded overrides** — the LLM result is ignored and the alert fires regardless of confidence score.

Full logic: [`docs/triage_logic.md`](docs/triage_logic.md)

---

## Deployment

Production uses **Fly.io** for the FastAPI backend and **Vercel** for the React dashboard. Postgres stays on **Neon**; Redis on **Upstash** (both free tier).

```bash
# Backend (Fly.io)
fly auth login
cd backend && fly launch --no-deploy
fly secrets set DATABASE_URL=... REDIS_URL=...   # see runbook
make migrate                                     # Neon, from laptop
fly deploy

# Frontend (Vercel) — import repo, root directory frontend/, set:
#   VITE_API_URL=https://<your-api>.fly.dev
# Or: cd frontend && vercel --prod
```

Full step-by-step (Fly `fly.toml`, Vercel env vars, Green API webhook, pre-demo checklist): [`docs/runbooks/flyio-deploy_runbook.md`](docs/runbooks/flyio-deploy_runbook.md).

---

## Roadmap

- [ ] Voice call intake via Twilio
- [ ] Urdu TTS responses for low-literacy patients  
- [ ] RAG on clinic PDF — services, timings, doctor profiles
- [ ] Multi-clinic support with tenant isolation
- [ ] Analytics dashboard — P1 response time SLA tracking
- [ ] Appointment calendar integration

---

## Contributing

Pull requests are welcome. For significant changes, open an issue first.

```bash
git checkout -b feature/your-feature
# make changes
make test && make lint
git commit -m "feat: your feature"
git push origin feature/your-feature
```

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

Built for the Anthropic AI Internship Case Study · June 2026

*"The hardest part wasn't the AI — it was designing the interrupt pattern<br/>so a human correction flows back into graph state without breaking the audit trail."*

</div>