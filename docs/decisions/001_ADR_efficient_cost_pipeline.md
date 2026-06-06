# Decision record for WhatsApp-based physiotherapy clinic communication system

---

## 🧩 Example format

## Example

Event-driven WhatsApp pipeline with rule-first routing and three specialised agents chosen over a monolithic AI chat system due to strict per-message cost constraints, a single-doctor clinic scale, and the need for reliable appointment slot management.

---

# Decision record for physiotherapy clinic WhatsApp architecture

---

## Context

A single-doctor physiotherapy clinic (doctor + receptionist) requires:

- WhatsApp as the primary patient communication channel
- Support for text and voice messages (Urdu, English, Roman Urdu)
- Reliable appointment booking with correct slot duration logic
- FAQ and help desk for routine patient questions
- Message triage routing to doctor, receptionist, or both
- Receptionist web dashboard with manual override controls
- Slack alerts when AI confidence is critically low
- Extremely low per-message cost in PKR
- No dependency on Meta business verification (reseller WhatsApp provider)
- No separate vector database — Neon (PostgreSQL + pgvector) as single data store
- Minimal infrastructure footprint (Fly.io auto-sleep VM)

Core constraints:

- Target cost per message: **0.25 – 1.5 PKR**
- AI usage must be selective and cheap, not per-message by default
- Voice transcription must be lazy — triggered only, never automatic
- No automated patient-facing alerts (appointment reminders excluded from scope)
- Infrastructure budget: **$2–5/month** (Fly.io shared VM + Neon free tier)

---

## Decision

We adopt an **event-driven WhatsApp system with three specialised agents** (booking, help desk, triage), a **single Neon database**, a **receptionist web dashboard**, and **Slack-only alerting for low-confidence AI events**.

---

## Architecture overview

### 1. WhatsApp integration layer

- Provider: WhatsApp Business API via reseller BSP
- Recommended BSPs: **YCloud** or **360dialog** (zero Meta markup, PKR billing)
- Incoming messages received via webhook
- Every message becomes a typed system event

Reason:

- Fastest deployment, no NTN/business verification required
- Zero-markup BSPs pass Meta's base rate through directly
- Avoid Twilio, Wati, WeTarseel — they add 50–200% platform markup

---

### 2. Message event types

Each incoming message is classified into one of:


| Event                      | Trigger                                          |
| -------------------------- | ------------------------------------------------ |
| `AppointmentRequestEvent`  | Patient asks to book or reschedule               |
| `HelpDeskQueryEvent`       | Patient asks a clinic FAQ or general question    |
| `VoiceNoteReceived`        | Any voice message (stored, not auto-transcribed) |
| `UnclassifiedMessageEvent` | Falls through to triage classifier               |


---

### 3. Agent 1 — booking agent

Handles all appointment creation and rescheduling.

**Slot duration logic:**


| Appointment type          | Duration   |
| ------------------------- | ---------- |
| Exercise session          | 25 minutes |
| Discussion / consultation | 10 minutes |


**Booking flow:**

1. Detect appointment type from patient message
2. Query `appointments` table in Neon for today's booked slots
3. Calculate next available slot: `last_end_time + duration`, no overlap
4. Propose time to patient via WhatsApp reply
5. If patient requests a different time ("can you do 4 instead?"):
  - Re-query calendar for the requested window
  - Overlap check: `requested_start < existing_end AND requested_end > existing_start`
  - Confirm if free, offer next available if not
6. On confirmation: write to `appointments` table, notify receptionist dashboard

**Model:** Claude Haiku or GPT-4o mini (conversational slot confirmation layer only — slot logic is deterministic DB queries, LLM handles only the language layer)

**Cost per booking interaction:** ~PKR 0.028

---

### 4. Agent 2 — help desk (RAG)

Handles all routine patient questions: clinic hours, exercise instructions, pricing, preparation, post-session care.

**Knowledge base:** `clinic_knowledge` table in Neon with pgvector embeddings. Doctor or receptionist populates this via the dashboard. No external vector database required.

**Flow:**

1. Patient message classified as `HelpDeskQueryEvent`
2. pgvector similarity search against `clinic_knowledge`
3. Top-k results injected into prompt as context
4. Cheap model generates answer

**Model:** DeepSeek V3 or Gemini 2.0 Flash (~800 input + 300 output tokens per query)

**Cost per help desk query:** ~PKR 0.056

**Confidence threshold:** If the retrieval similarity score falls below a set threshold (e.g. cosine similarity < 0.72), the system does NOT attempt to answer. Instead it flags the message to the receptionist dashboard and fires a Slack alert (see section 7).

---

### 5. Agent 3 — triage classifier

Reads incoming messages (or a recent chunk of conversation) and routes them.

**Output:** one of `doctor`, `receptionist`, or `both`

**Triggers routing when:**

- Message is not cleanly handled by the booking or help desk agent
- Message contains clinical language outside standard FAQ scope
- Receptionist manually escalates via dashboard

**Model:** DeepSeek or Gemini Flash (~300 tokens, 3-way classification)

**Runs:** async after every message, result stored against `message_id` in Neon

**Cost per classification:** ~PKR 0.014

---

### 6. Voice message handling

Voice messages are treated as **lazy-processed assets**.

**Flow:**

1. Store audio file reference immediately on receipt
2. Do NOT transcribe by default
3. Transcribe only when:
  - Receptionist manually requests review from dashboard
  - Doctor flags the message for review
  - Message is part of a booking or help desk thread that needs resolution

**Transcription provider:** Groq Whisper Large v3 Turbo

- Cost: $0.04/hour → ~PKR 0.19 per 1-minute voice note
- Supports Urdu and English natively
- Roman Urdu caveat: Whisper may output Urdu script for Latin-script Urdu audio; the downstream AI layer must handle noisy or mixed-script transcriptions

**Cost per transcribed voice note (avg 1 min):** ~PKR 0.19

---

### 7. Alerting — Slack only (low-confidence events)

No automated patient-facing alerts are sent. All alerting is internal, directed at clinic staff.

**Slack alert fires when:**

- Help desk RAG confidence score falls below threshold (classifier not confident enough to answer)
- Triage classifier returns a low-confidence classification (e.g. softmax score < 0.65 across all three classes)
- A voice note has been in an unresolved thread for more than X hours without manual review (configurable)

**Slack is the only alert channel.** WhatsApp is not used for internal staff notifications.

**Alert payload includes:**

- Patient phone number (masked)
- Message snippet or event type
- Confidence score
- Suggested action (review / escalate / respond manually)

---

### 8. Receptionist dashboard

Web application (browser-based, Next.js).

**Features:**


| Action                         | Keyboard shortcut |
| ------------------------------ | ----------------- |
| Forward conversation to doctor | `D`               |
| Mark as resolved               | `R`               |
| Add manual appointment         | `A`               |
| Remove appointment             | `X`               |
| Trigger voice transcription    | `T`               |
| Add entry to knowledge base    | `K`               |


**Manual calendar controls:**

- Add appointment: select patient, date, time, type — writes directly to `appointments` table
- Remove appointment: soft-delete with reason field
- All manual changes logged with `source: manual` flag in DB for audit

---

### 9. Data model

`**appointments` table:**


| Field           | Type        | Notes                                   |
| --------------- | ----------- | --------------------------------------- |
| `id`            | uuid        | primary key                             |
| `patient_phone` | varchar     | indexed                                 |
| `type`          | enum        | `exercise` / `discussion`               |
| `start_time`    | timestamptz |                                         |
| `end_time`      | timestamptz | calculated from type                    |
| `status`        | enum        | `confirmed` / `cancelled` / `completed` |
| `source`        | enum        | `agent` / `manual`                      |
| `created_at`    | timestamptz |                                         |


`**messages` table:**


| Field               | Type        | Notes                                       |
| ------------------- | ----------- | ------------------------------------------- |
| `id`                | uuid        |                                             |
| `patient_phone`     | varchar     |                                             |
| `direction`         | enum        | `inbound` / `outbound`                      |
| `message_type`      | enum        | `text` / `voice`                            |
| `event_type`        | varchar     | classified event                            |
| `triage_result`     | enum        | `doctor` / `receptionist` / `both` / `null` |
| `ai_used`           | boolean     |                                             |
| `confidence_score`  | float       | nullable                                    |
| `cost_estimate_pkr` | float       |                                             |
| `timestamp`         | timestamptz |                                             |


`**clinic_knowledge` table:**


| Field        | Type         | Notes                               |
| ------------ | ------------ | ----------------------------------- |
| `id`         | uuid         |                                     |
| `content`    | text         | FAQ entry or clinic info            |
| `embedding`  | vector(1536) | pgvector, auto-generated on insert  |
| `category`   | varchar      | e.g. `pricing`, `exercise`, `hours` |
| `created_by` | varchar      | `doctor` / `receptionist`           |


---

### 10. Infrastructure


| Component       | Choice                                    | Cost                       |
| --------------- | ----------------------------------------- | -------------------------- |
| Runtime         | Fly.io shared-cpu-1x 256MB, auto-sleep    | ~$2–3/month                |
| Database        | Neon free tier (0.5GB, pgvector included) | $0/month                   |
| WhatsApp BSP    | YCloud or 360dialog                       | Zero markup over Meta rate |
| Transcription   | Groq Whisper Large v3 Turbo               | $0.04/hour                 |
| Help desk model | DeepSeek V3 / Gemini 2.0 Flash            | ~$0.0002/query             |
| Booking model   | Claude Haiku / GPT-4o mini                | ~$0.0001/turn              |
| Triage model    | DeepSeek / Gemini Flash                   | ~$0.00005/msg              |
| Alerts          | Slack incoming webhook                    | Free                       |


---

### 11. Cost model

**WhatsApp layer:**

Since patients initiate conversations, replies within the 24-hour service window are free at the Meta layer. Only proactive outbound utility templates (e.g. appointment confirmations sent first) are billed at ~PKR 0.28 each. These represent approximately 15% of total messages.

**Blended per-message cost (PKR):**


| Daily volume | Best case  | Realistic | Worst case |
| ------------ | ---------- | --------- | ---------- |
| 200 msg/day  | 0.25 – 0.5 | 0.7 – 1.0 | 1.2 – 1.5  |
| 100 msg/day  | 0.5 – 0.8  | 0.8 – 1.2 | 1.5 – 1.8  |
| 50 msg/day   | 0.6 – 1.0  | 1.0 – 1.5 | 1.8 – 2.2  |


**Monthly totals (PKR):**


| Daily messages | AI + WA cost | Infra (fixed) | Total/month    |
| -------------- | ------------ | ------------- | -------------- |
| 50/day         | ~PKR 350     | ~PKR 560      | **~PKR 910**   |
| 100/day        | ~PKR 900     | ~PKR 700      | **~PKR 1,600** |
| 200/day        | ~PKR 2,100   | ~PKR 840      | **~PKR 2,940** |


Cost target of 0.25 – 1.5 PKR/message is met at 100–200 messages/day. At 50 messages/day the fixed infra cost raises the blended rate to ~1.0–2.0 PKR but remains within acceptable range given MVP scale.

---

## Alternatives considered

### 1. Full AI conversational system (rejected)

AI handles every message end-to-end with persistent memory and real-time responses.

Reason: Cost increases to 5–15+ PKR per message. Not justified for a single-doctor clinic doing primarily appointment booking and FAQ.

---

### 2. Direct Meta WhatsApp API (rejected for MVP)

Direct API access without a BSP.

Reason: Requires NTN/business verification and longer setup cycle. BSP resellers deploy faster with no meaningful cost difference at this volume.

---

### 3. Always-on voice transcription (rejected)

All voice notes transcribed on receipt.

Reason: Most voice notes are routine updates that never need text extraction. Lazy transcription reduces cost and avoids processing audio that the clinic never reviews.

---

### 4. Google Calendar or Calendly for scheduling (rejected)

External calendar service for appointment management.

Reason: Adds an external API dependency and per-seat or per-booking cost. A simple `appointments` table in Neon gives full programmatic control at zero additional cost and handles the clinic's slot logic natively.

---

### 5. Separate vector database (Pinecone, Weaviate) for RAG (rejected)

Dedicated vector store for clinic knowledge base.

Reason: Neon's pgvector extension handles vector similarity search natively. At clinic scale (hundreds to low thousands of knowledge entries) pgvector performs identically to a dedicated vector DB with no added cost or infrastructure.

---

### 6. Automated patient appointment reminders via WhatsApp (deferred, not in scope)

System-initiated reminders sent to patients when appointment time approaches.

Reason: Explicitly out of scope for this version. When added in future, reminders must use Meta utility templates (billed at ~PKR 0.28 each) and require patient opt-in under Meta's messaging policy to avoid being flagged as spam.

---

## Consequences

### Positive

- Per-message cost of 0.25–1.5 PKR achievable at 100–200 messages/day
- Infrastructure cost of $2–5/month met with Fly.io auto-sleep + Neon free tier
- Appointment slot logic is deterministic — no AI guessing on availability
- RAG help desk handles 70% of patient queries without doctor involvement
- Lazy voice processing keeps costs predictable regardless of voice message volume
- Single Neon database eliminates operational complexity of managing separate stores
- Receptionist dashboard with keyboard shortcuts enables fast manual overrides
- Slack alerting gives staff visibility into low-confidence AI events without noise

### Negative

- Not a fully conversational AI system — some patient queries require manual receptionist response
- Rule-based triage requires ongoing maintenance as query patterns evolve
- Fly.io auto-sleep introduces cold start latency (~300ms) on first message after idle period
- Roman Urdu voice transcription produces inconsistent output (Urdu script vs Latin); AI layer must tolerate noisy input
- RAG knowledge base quality depends entirely on how well the doctor and receptionist populate it

---

## Practically questionable decisions (with reasons)


| Decision                                     | Why it is questionable in this scenario                                                                                                                                                                       |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Keyboard shortcuts on receptionist dashboard | A solo receptionist at a small clinic will rarely remember more than 2–3 shortcuts; discoverability via buttons is more reliable at this scale.                                                               |
| Confidence score threshold for Slack alerts  | Threshold calibration requires real message data to tune; a poorly set threshold will either spam Slack or miss genuinely uncertain responses in early production.                                            |
| Roman Urdu voice via Whisper                 | Whisper outputs Urdu script for phonetic Roman Urdu audio — the transcription is technically correct but may confuse downstream text-matching in the booking or help desk agents if they expect Latin script. |
| pgvector cosine similarity cutoff for RAG    | A fixed similarity threshold ignores query length and phrasing variation in Urdu/English mixed queries; edge cases will either hallucinate answers or over-escalate to Slack.                                 |


