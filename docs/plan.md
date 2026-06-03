# Sehat — Build Order

> **Rule for every day:** Build the ugliest version that works. Then make it work reliably. Then make it look good. In that order. Never the other way.

---

## Phase 1 — Make something move `Day 1`

**Goal:** A WhatsApp message reaches your terminal.

```
WhatsApp → Green API webhook → FastAPI endpoint → print to console
```

Just `print(message)`. No Gemini. No database. Prove the pipe works first.  
Everything else depends on this. If you wire WhatsApp last, you'll spend day 7 debugging webhook signatures instead of polishing your demo.

**Files:**
```
backend/app/main.py
backend/app/api/whatsapp.py
backend/app/services/whatsapp.py
.env                          # GREEN_API_INSTANCE + GREEN_API_TOKEN
```

---

## Phase 2 — Persist the message `Day 1–2`

**Goal:** Message gets saved to Postgres.

```
WhatsApp → FastAPI → save to DB → return 200
```

Use **Neon (Postgres)** as your database (set `DATABASE_URL` to your Neon connection string). Keep **Redis** for session memory (local via Docker is fine). Write your first Alembic migration for `patients` and `messages` tables. Every message now has a home.

**Files:**
```
backend/app/models/patient.py
backend/app/models/message.py
backend/app/database/session.py
backend/database/migrations/     # first alembic revision
```

**Commands:**
```bash
# bring up Redis locally (Postgres is Neon)
docker-compose up -d redis
make migrate
```

---

## Phase 3 — One Gemini call, no graph yet `Day 2`

**Goal:** Classify a hardcoded message and print structured JSON back.

Don't touch LangGraph yet. Call **Gemini** directly with your triage prompt and confirm you get back `priority`, `confidence`, `reasoning`. Paste `"seene mein dard"` as a test string. Watch it return P1.

This proves your prompt works **before** you wire it into a state machine.

**Files:**
```
backend/app/agent/prompts.py
backend/app/agent/tools.py        # JSON schema for tool-use
```

**Scratch test — not production code:**
```python
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

result = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="seene mein dard ho raha hai",
    # Wire structured output however you implement it in `tools.py`
    # (JSON schema, response_mime_type, or function/tool calling).
)

print(result)
# expect: {"priority": "P1", "confidence": 0.96, ...}
```

---

## Phase 4 — Build the state machine `Day 3`

**Goal:** LangGraph graph runs end to end on a hardcoded message.

Build the graph with three nodes first: `classify → slot_check → notify`. No WhatsApp yet — just invoke directly from a test script and watch it traverse all three nodes. Add remaining nodes one at a time. Add a conditional edge. Test after each addition.

**Files:**
```
backend/app/agent/state.py        # TriageState TypedDict
backend/app/agent/nodes.py        # all node functions
backend/app/agent/graph.py        # graph + conditional edges
```

**Scratch test:**
```python
from app.agent.graph import graph

result = graph.invoke({
    "messages": ["seene mein dard"],
    "patient_phone": "+923001234567",
    "priority": None,
    "confidence": 0.0,
    "clarification_rounds": 0,
    "slots_complete": False,
    "routed_to": None,
    "escalated": False,
})

print(result["priority"])    # P1
print(result["escalated"])   # True
```

**Node build order inside this phase:**
```
state.py          → define TriageState first, nothing works without it
classify_node     → most important, build and test alone
emergency_exit    → fast path for P1, add conditional edge
slot_check_node   → checks what info is missing
gather_slots_node → asks only missing fields, loops back
route_node        → assigns department
notify_human_node → fires Slack
confirm_user_node → sets reply_intent (structured instruction)
compose_reply_node → rewrites reply_intent → natural patient-facing reply via LLM
```

---

## Phase 5 — Wire the graph to WhatsApp `Day 3–4`

**Goal:** Real message from your phone → graph runs → reply sent back.

Your WhatsApp webhook now calls `graph.invoke()` instead of `print()`. The bot replies to you on WhatsApp. Test three scenarios manually from your own phone:

| Scenario | Expected behaviour |
|----------|-------------------|
| *"seene mein dard"* | P1 fires, Slack alert lands in < 4 seconds |
| *"appointment chahiye back pain"* | Slot questions asked one by one |
| *"fee kitni hai"* | OOS redirect, no slot-filling |

**Files:**
```
backend/app/api/whatsapp.py       # call graph.invoke here
backend/app/services/slack.py     # send the P1 Slack alert
```

**Webhook handler shape:**
```python
@router.post("/webhook")
async def whatsapp_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    message = payload.body
    phone   = payload.sender

    state   = await memory.load(phone)          # Redis → existing state or fresh
    state["messages"].append(message)

    result  = graph.invoke(state)               # run next node(s)

    await memory.save(phone, result)            # persist updated state
    await whatsapp.send(phone, result["reply"]) # reply to patient

    return {"status": "ok"}
```

---

## Phase 6 — Session memory `Day 4`

**Goal:** Bot remembers the conversation across multiple messages.

Right now every message is stateless — the bot forgets everything between turns. Add Redis to store `TriageState` keyed by patient phone number. On each new message: load state → append message → run next node → save state.

This is what makes it feel like a real conversation instead of isolated one-shot replies.

**Files:**
```
backend/app/services/memory.py
backend/app/api/whatsapp.py       # wrap graph.invoke with load/save
```

**Memory service shape:**
```python
async def load(phone: str) -> TriageState:
    raw = await redis.get(f"session:{phone}")
    if raw:
        return json.loads(raw)
    return fresh_state(phone)          # new patient, blank state

async def save(phone: str, state: TriageState):
    await redis.setex(
        f"session:{phone}",
        ex=86400,                      # 24hr TTL — stale sessions auto-expire
        value=json.dumps(state)
    )
```

---

## Phase 7 — Receptionist dashboard `Day 5–6`

**Goal:** Sana can see all cases with override buttons.

Case list on the left, full conversation detail on the right. The override buttons — `Agree / Upgrade / Downgrade` — hit your `human_override` FastAPI endpoint, which calls `graph.update_state()` and resumes the frozen graph. This is your most impressive demo moment: Sana clicks Upgrade and the patient immediately receives a different response.

**Files:**
```
backend/app/api/human_override.py
frontend/src/pages/Dashboard.tsx
frontend/src/pages/CaseDetail.tsx
frontend/src/components/dashboard/OverrideButtons.tsx
frontend/src/components/dashboard/AlertBanner.tsx     # P1 flash alert
```

**Override endpoint shape:**
```python
@router.post("/cases/{case_id}/override")
async def override(case_id: str, body: OverrideRequest):
    # log correction to DB for audit trail
    await db.save_override(case_id, body.original, body.correction, body.receptionist_id)

    # unfreeze the graph with corrected priority
    graph.update_state(
        config={"configurable": {"thread_id": case_id}},
        values={"priority": body.correction}
    )

    # resume from await_human_review node
    graph.invoke(None, config={"configurable": {"thread_id": case_id}})

    return {"status": "resumed"}
```

**Build frontend in this order:**
```
api/client.ts         → axios instance + base URL
api/cases.ts          → getCases(), getCaseById()
pages/Dashboard.tsx   → case list, polling every 5s
pages/CaseDetail.tsx  → conversation thread
OverrideButtons.tsx   → three buttons, calls api/override.ts
AlertBanner.tsx       → red flash when P1 arrives
```

---

## Phase 8 — Specialist sub-agents `Day 6–7`

**Goal:** Cardiology and pediatrics ask different slot questions.

`route_node` picks which specialist handles the slot-filling conversation. Each specialist is just a different system prompt passed to the same `gather_slots_node` — not a new graph. Cardiology asks about pain radiation, sweating, family history. Pediatrics asks about age, weight, fever duration.

**Files:**
```
backend/app/agent/specialists/router.py      # reads priority + keywords → picks specialist
backend/app/agent/specialists/cardiology.py  # system prompt + required slots
backend/app/agent/specialists/pediatrics.py
backend/app/agent/specialists/general.py
```

**Specialist shape:**
```python
# cardiology.py
SYSTEM_PROMPT = """
You are a cardiac intake assistant. Gather these fields in natural conversation.
Ask one question at a time. Be calm and reassuring.
"""

REQUIRED_SLOTS = [
    "pain_location",       # where exactly
    "pain_radiation",      # does it spread to arm/jaw
    "onset",               # sudden or gradual
    "associated_symptoms", # sweating, nausea, breathlessness
    "medical_history",     # prior cardiac events
]
```

---

## Phase 9 — Eval suite `Day 7`

**Goal:** `make eval` prints a classification accuracy report.

Write 20 labelled test messages — mix of Urdu and English, all four priority levels. Run them through `classify_node` and print accuracy per class. This takes half a day and signals more to an evaluator than any additional feature.

**Files:**
```
backend/evals/fixtures.py             # 20 messages with ground-truth labels
backend/evals/test_classification.py  # runner + accuracy report
```

**Fixtures shape:**
```python
TEST_CASES = [
    # P1 — emergency
    {"message": "seene mein dard ho raha hai",              "expected": "P1"},
    {"message": "chest pain since morning",                  "expected": "P1"},
    {"message": "mere bhai ko saans nahi aa rahi",           "expected": "P1"},
    {"message": "unconscious ho gaye hain",                  "expected": "P1"},

    # P2 — urgent
    {"message": "bachay ko 3 din se tez bukhaar hai",        "expected": "P2"},
    {"message": "suspected fracture in wrist",               "expected": "P2"},

    # P3 — routine
    {"message": "appointment chahiye back pain ke liye",     "expected": "P3"},
    {"message": "follow up visit for diabetes checkup",      "expected": "P3"},

    # OOS — out of scope
    {"message": "fee kitni hai consultation ki",             "expected": "OOS"},
    {"message": "visa medical certificate chahiye",          "expected": "OOS"},

    # ... 10 more
]
```

**Expected output:**
```
Classification accuracy report
────────────────────────────────
P1  (emergency)    8/8    100%
P2  (urgent)       5/6     83%
P3  (routine)      5/5    100%
OOS                1/1    100%
────────────────────────────────
Overall           19/20    95%
Avg confidence     0.91
```

---

## Phase 10 — Polish and deploy `Day 8–9`

**Goal:** A public URL that works, with three scripted demo scenarios ready.

**Deploy on Fly.io (cheapest path):**

Keep Postgres on **Neon** (free tier) and Redis on **Upstash** (free tier). Fly only runs the API container — one shared-cpu machine that auto-stops when idle so you pay almost nothing outside demo hours.

```bash
# one-time
fly auth login
cd backend && fly launch --no-deploy    # pick nearest region (e.g. sin, bom)
fly secrets set DATABASE_URL=... REDIS_URL=... GEMINI_API_KEY=...   # see runbook
make migrate                            # Neon — run from laptop, not on Fly
fly deploy
# update GREEN_API webhook URL to https://<your-app>.fly.dev/api/whatsapp/webhook
```

Full steps, `fly.toml` cost settings, Vercel dashboard deploy, and webhook checklist: [`docs/runbooks/flyio-deploy_runbook.md`](runbooks/flyio-deploy_runbook.md).

**Cost target (~$0/mo for a hackathon demo):**

| Service | Provider | Tier |
|---------|----------|------|
| API | Fly.io | 1× `shared-cpu-1x` 256MB, `min_machines_running = 0`, auto-stop |
| Postgres | Neon | Free — already wired in Phase 2 |
| Redis | Upstash | Free — `REDIS_URL` from console |
| Frontend (dashboard) | Vercel | Hobby tier — `VITE_API_URL` → Fly API |

**Seed three demo scenarios** so any evaluator can test end to end without knowing what to type:

```
Scenario A — Emergency
  Patient types: "mere shohar ko seene mein dard aur saans lene mein takleef"
  Expected:      Slack alert fires, bot advises 1122, case marked P1 on dashboard

Scenario B — Routine appointment
  Patient types: "appointment chahiye, peet mein dard hai ek hafte se"
  Expected:      Bot asks 3 slot questions, books Wednesday slot, no human alert

Scenario C — Out of scope
  Patient types: "mujhe visa medical certificate chahiye"
  Expected:      Polite redirect to City Medical Center, case logged OOS
```

**Pre-demo checklist:**
```
[ ] WhatsApp webhook URL updated to live Fly.io API (https://<api>.fly.dev/...)
[ ] Vercel dashboard live; VITE_API_URL points at Fly API
[ ] Slack workspace connected and test alert received
[ ] Postgres migrations run against Neon (make migrate)
[ ] Upstash Redis provisioned; REDIS_URL set as Fly secret
[ ] fly secrets set for all keys in .env.example (nothing committed to git)
[ ] First webhook after idle wakes the machine (~5–15s cold start — send a ping before demo)
[ ] Three demo scenarios tested end to end (WhatsApp + Vercel dashboard)
[ ] Screen recording taken as backup
```

---

## Cut list — if you run out of time

Cut in this order. Least painful first.

| Feature | Cut it? | Why |
|---------|---------|-----|
| Voice / Whisper | Yes | Demo works fine without it |
| RAG on clinic PDF | Yes | Impressive but not core to the brief |
| Analytics page | Yes | Case list is enough for the demo |
| Specialist sub-agents | Maybe | One general agent still shows the architecture |
| Eval suite | **Never** | Half a day, huge signal to evaluator |
| Human override | **Never** | The brief explicitly asks for escalation logic |
| Slack P1 alert | **Never** | The most visceral demo moment |
| Session memory | **Never** | Without it, it's just a chatbot |

---

## Dependency map

```
Phase 1 (pipe works)
    └── Phase 2 (DB)
            └── Phase 3 (Gemini call)
                    └── Phase 4 (graph)
                            └── Phase 5 (WhatsApp + graph)
                                    └── Phase 6 (memory)
                                            ├── Phase 7 (dashboard)
                                            ├── Phase 8 (specialists)
                                            └── Phase 9 (evals)
                                                        └── Phase 10 (deploy)
```

Each phase is a working, testable system. If you stop at any phase, you have something that runs.