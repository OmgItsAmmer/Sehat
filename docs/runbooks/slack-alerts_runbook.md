# Slack — triage alerts runbook

**Goal:** When the LangGraph triage graph classifies a case as urgent (P1/P2 or escalated), Sehat posts a staff alert to a Slack channel via an **Incoming Webhook**.

```
Patient message (WhatsApp or web chat)
    → triage graph
    → notify_human node
    → POST SLACK_WEBHOOK_URL
    → message in Slack channel
```

**Code:** `backend/app/services/slack.py` · `backend/app/agent/nodes.py` (`notify_human_node`) · `backend/app/config.py` (`slack_webhook_url`)

**Time:** ~10 minutes (Slack app + webhook + `.env` + smoke test)

---

## Prerequisites

| Item | Notes |
|------|--------|
| Slack workspace | Admin or permission to install apps / add webhooks |
| Sehat backend running | `make dev` from repo root (or deployed API on Fly.io) |
| LLM key for full triage | `OPENAI_API_KEY` in `.env` (or whatever your deployment uses for classification) |
| Optional: WhatsApp wired | For end-to-end tests — see [`Green-api-whatsapp-integration_runbook.md`](Green-api-whatsapp-integration_runbook.md) |

Slack alerts are **optional**. If `SLACK_WEBHOOK_URL` is empty, the graph still runs; `notify_human` logs a warning and continues.

---

## When alerts fire

The graph routes to `notify_human` (which calls Slack) in these cases:

| Trigger | Example |
|---------|---------|
| **P1 emergency** | Hardcoded keywords (`seene mein dard`, `chest pain`, …) or LLM classifies P1 → `emergency_exit` → Slack |
| **P2 urgent** | After slot-filling completes for a P2 case |
| **Escalated** | Max clarification rounds reached, or classifier flags escalation |

**P3 routine** and **OOS** cases do **not** send Slack alerts unless escalated.

The patient still gets a WhatsApp/web reply either way; Slack is for staff only.

---

## 1. Create a Slack Incoming Webhook

1. Open [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**.
2. Name it (e.g. `Sehat Triage Alerts`) and pick your workspace.
3. In the app sidebar: **Features** → **Incoming Webhooks** → toggle **Activate Incoming Webhooks** **On**.
4. Click **Add New Webhook to Workspace**.
5. Choose the channel where alerts should appear (e.g. `#triage-alerts` or `#reception`).
6. Copy the webhook URL. It looks like:

```text

```

Treat this URL like a password — anyone with it can post to that channel.

### Optional: dedicated alert channel

Create `#sehat-alerts` (or similar) before step 5 so only triage staff see notifications. Pin a short note in the channel explaining P1 vs P2 and who should respond.

---

## 2. Configure Sehat

From the repo root:

```bash
cp .env.example .env   # skip if you already have .env
```

Add the webhook URL:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../...
```

Restart the API so settings reload:

```bash
make dev
```

> **Production (Fly.io):** set the secret on the deployed app instead of committing `.env`:
>
> ```bash
> fly secrets set SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
> ```
>
> See [`flyio-deploy_runbook.md`](flyio-deploy_runbook.md) for the full deploy checklist.

---

## 3. Smoke test — Slack webhook only

Verify Slack accepts posts **before** testing the full triage graph:

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\":white_check_mark: Sehat Slack webhook smoke test\"}"
```

**Expected:** HTTP `200` with body `ok`, and the message appears in your chosen channel.

On Windows PowerShell (replace the URL):

```powershell
Invoke-RestMethod -Method Post -Uri "https://hooks.slack.com/services/..." `
  -ContentType "application/json" `
  -Body '{"text":":white_check_mark: Sehat Slack webhook smoke test"}'
```

If this fails, fix Slack setup before continuing.

---

## 4. Smoke test — through Sehat (no WhatsApp)

Run the LangGraph scratch script with a P1 keyword message. With `SLACK_WEBHOOK_URL` set, this sends a real alert:

```bash
make graph-scratch
```

**Expected terminal output:**

```text
priority: P1
escalated: True
slack_notified: True
reply: ...
```

**Expected in Slack:** a message like:

```text
:rotating_light: Sehat triage alert
Priority: P1
Phone: +923001234567
Routed to: n/a
Escalated: True
Reasoning: ...
Latest message: seene mein dard
```

**Expected in Uvicorn logs:**

```text
Slack triage alert sent phone=+923001234567 priority=P1
```

If `slack_notified: False`, see [Troubleshooting](#7-troubleshooting).

---

## 5. End-to-end test (WhatsApp)

With Green API and ngrok (or Fly.io) already configured:

1. Ensure `SLACK_WEBHOOK_URL` is set and the API is running.
2. From another phone, send a P1-style message to your linked WhatsApp number, e.g. `seene mein dard` or `chest pain`.
3. Confirm:
   - Slack alert in the channel
   - Patient receives an emergency reply (mentions **1122** for P1)
   - Uvicorn log: `Slack triage alert sent ...`

Web chat (`/chat` in the frontend) uses the same pipeline — a P1 message there also triggers Slack if the webhook is configured.

---

## 6. What gets posted

Implementation in `backend/app/services/slack.py`:

| Field | Source |
|-------|--------|
| Priority | `P1`, `P2`, etc. |
| Phone | WhatsApp `chatId` or web session id |
| Routed to | Specialist queue (`cardiology`, `general`, …) or `n/a` |
| Escalated | `True` / `False` |
| Reasoning | Classifier reasoning (may be empty for keyword P1) |
| Latest message | Last patient message, truncated to 500 characters |

Payload format: plain Slack `text` with mrkdwn (`*bold*`, emoji). No Block Kit / buttons yet — staff act from the dashboard or by calling the patient back.

---

## 7. Troubleshooting

| Symptom | What to check |
|---------|----------------|
| `slack_notified: False` in scratch script | `SLACK_WEBHOOK_URL` empty or API not restarted after editing `.env` |
| Log: `SLACK_WEBHOOK_URL not set — skipping alert` | Add URL to repo-root `.env`; confirm `backend/app/config.py` loads that file |
| Log: `Slack triage alert failed` | Webhook revoked, wrong URL, Slack outage, or network blocked outbound HTTPS |
| curl smoke test returns `404` / `410` | Webhook deleted — create a new one in Slack app settings |
| curl returns `200` but no graph alert | Case may be P3/OOS (no alert). Retry with `make graph-scratch` or a P1 keyword |
| Alert on scratch but not WhatsApp | Triage path differed (LLM classified non-P1). Try explicit P1 keywords |
| Duplicate alerts | Patient sent multiple messages that each completed an urgent path; expected for now |
| Wrong channel | Incoming Webhooks are bound to one channel at creation — add a new webhook for another channel |

### Confirm env is loaded

```bash
cd backend && python -c "from app.config import settings; print('set' if settings.slack_webhook_url else 'missing')"
```

Should print `set`.

### Run unit tests (mocked Slack)

```bash
cd backend && pytest tests/unit/test_slack.py tests/unit/test_graph.py -q
```

---

## 8. Security and operations

- **Rotate** the webhook if the URL leaks (regenerate in Slack app → Incoming Webhooks → remove old, add new → update `.env` / Fly secrets).
- **Do not commit** `SLACK_WEBHOOK_URL` to git.
- Alerts contain **patient phone numbers and message snippets** — restrict channel membership to clinical staff.
- Outbound HTTP timeout is **4 seconds**; a slow Slack response is logged and does not block the patient reply.
- For on-call paging (PagerDuty, SMS), you would add a separate integration later; today Sehat only supports Slack Incoming Webhooks.

---

## Quick reference

| | |
|--|--|
| Env var | `SLACK_WEBHOOK_URL` |
| Slack setup | [api.slack.com/apps](https://api.slack.com/apps) → Incoming Webhooks |
| Local graph test | `make graph-scratch` |
| Direct webhook test | `curl -X POST "$SLACK_WEBHOOK_URL" -H "Content-Type: application/json" -d '{"text":"test"}'` |
| Production secret | `fly secrets set SLACK_WEBHOOK_URL=...` |
| Related runbooks | [WhatsApp](Green-api-whatsapp-integration_runbook.md) · [Fly deploy](flyio-deploy_runbook.md) |
