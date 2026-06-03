# Phase 9 — Classification eval suite

**Goal:** `make eval` runs 20 labelled patient messages through `classify_node` and prints per-priority accuracy.

**Status:** Implemented.

**Prerequisites:** Phase 3 (`classify_message_with_gemini`) and Phase 4 (`classify_node` with P1 keyword override). See [plan.md](./plan.md#phase-9--eval-suite-day-7).

---

## What it measures

The eval exercises the **same classify path as production**:

1. P1 **keyword override** (no API call) when the message matches `P1_KEYWORDS` in `state.py`
2. Otherwise **Gemini** structured JSON (`priority`, `confidence`, `reasoning`)

It does **not** run the full LangGraph (no routing, slots, or Slack).

---

## Files

| File | Role |
|------|------|
| `backend/evals/fixtures.py` | `TEST_CASES` — 20 Urdu/English messages with `expected` priority |
| `backend/evals/test_classification.py` | Runner, report formatter, CLI |
| `backend/tests/unit/test_eval_report.py` | Report layout tests (no API) |

**Fixture mix (20 total):** 5× P1, 5× P2, 6× P3, 4× OOS.

---

## Run

```bash
# Requires GEMINI_API_KEY in .env (backend loads settings on import)
make eval
```

Equivalent:

```bash
cd backend && python -m evals.test_classification --show-errors
```

**Flags:**

| Flag | Effect |
|------|--------|
| `--show-errors` | Print each misclassified message (default via `make eval`) |
| `--strict` | Exit code 1 if any case is wrong (useful for CI gates) |

Example output shape:

```text
Classification accuracy report
────────────────────────────────
P1  (emergency)          5/5     100%
P2  (urgent)            4/5      80%
...
Overall                18/20     90%
Avg confidence          0.87
```

Exact numbers depend on the live Gemini model and API behaviour.

---

## Adding cases

Edit `TEST_CASES` in `fixtures.py`:

```python
{"message": "your phrase here", "expected": "P2"},
```

Keep `expected` one of `P1`, `P2`, `P3`, `OOS`.

---

## What comes next

| Phase | Change |
|-------|--------|
| 10 | Deploy API to Fly.io, dashboard to Vercel, seed demo scenarios, pre-demo checklist |

See [plan.md](./plan.md#phase-10--polish-and-deploy-day-89).
