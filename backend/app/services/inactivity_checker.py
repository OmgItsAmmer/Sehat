"""Background service to monitor active session inactivity and finalize/triage inactive chats."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.agent.state import TriageState
from app.agent.triage import classify_message_with_openai
from app.database.session import db_is_available, get_sessionmaker
from app.services import memory, slack, web_memory
from app.services.persist import persist_intake_state

logger = logging.getLogger(__name__)

_daemon_task: asyncio.Task | None = None


async def check_all_sessions() -> None:
    """Scan both WhatsApp and web chat sessions, finalizing those inactive for >= 5 minutes."""
    phones = await memory.list_phones()
    web_sessions = await web_memory.list_sessions()

    db_sessionmaker = get_sessionmaker() if db_is_available() else None

    # WhatsApp sessions
    for phone in phones:
        try:
            state = await memory.load(phone)
            await _check_and_finalize_session(
                session_id=phone,
                state=state,
                save_fn=memory.save,
                db_sessionmaker=db_sessionmaker,
            )
        except Exception:
            logger.exception("Error checking inactivity for WhatsApp session %s", phone)

    # Web sessions
    for session_id in web_sessions:
        try:
            state = await web_memory.load(session_id)
            await _check_and_finalize_session(
                session_id=session_id,
                state=state,
                save_fn=web_memory.save,
                db_sessionmaker=db_sessionmaker,
            )
        except Exception:
            logger.exception("Error checking inactivity for Web session %s", session_id)


async def _check_and_finalize_session(
    session_id: str,
    state: TriageState,
    save_fn: Callable[[str, TriageState], Any],
    db_sessionmaker: sessionmaker | None,
) -> None:
    """Evaluate one session for inactivity, run final classification, notify Slack, and persist."""
    if state.get("intake_finalized"):
        return

    last_activity = state.get("last_activity_at")
    if not last_activity:
        return

    try:
        last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
    except ValueError:
        return

    elapsed = (datetime.now(UTC) - last_dt).total_seconds()
    if elapsed < 300:  # 5 minutes
        return

    logger.info("Finalizing session %s due to 5 minutes of inactivity", session_id)

    messages = state.get("messages") or []
    history = "\n".join(messages)

    state["slots_complete"] = True
    state["intake_finalized"] = True

    if history:
        try:
            classification = classify_message_with_openai(history)
            state["priority"] = classification.priority
            state["confidence"] = classification.confidence
            state["reasoning"] = classification.reasoning

            # Notify Slack if P1 or P2, and not already notified
            if classification.priority in ("P1", "P2") and not state.get("slack_notified"):
                preview = messages[-1] if messages else ""
                sent = slack.send_triage_alert(
                    patient_phone=session_id,
                    priority=classification.priority,
                    routed_to=state.get("routed_to") or "general",
                    reasoning=classification.reasoning,
                    message_preview=preview,
                    escalated=bool(state.get("escalated")),
                )
                state["slack_notified"] = sent
        except Exception:
            logger.exception(
                "Final classification failed during inactivity check for %s", session_id
            )

    # Save finalized state back to session store (Redis / fallback)
    await save_fn(session_id, state)

    # Persist snapshot to database
    if db_sessionmaker is not None:
        try:
            with db_sessionmaker() as db:
                persist_intake_state(db=db, patient_phone=session_id, state=state)
        except Exception:
            logger.exception("Failed to persist finalized intake state for %s", session_id)


async def inactivity_checker_daemon() -> None:
    """Daemon loop that calls check_all_sessions every 10 seconds."""
    logger.info("Inactivity checker daemon started")
    while True:
        try:
            await check_all_sessions()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Unexpected error in inactivity checker daemon loop")
        await asyncio.sleep(10)
    logger.info("Inactivity checker daemon stopped")


def start_inactivity_checker() -> None:
    """Register and start the inactivity checker background task."""
    global _daemon_task
    if _daemon_task is None:
        _daemon_task = asyncio.create_task(inactivity_checker_daemon())
        logger.info("Registered background inactivity checker task")


async def stop_inactivity_checker() -> None:
    """Cancel and stop the inactivity checker background task."""
    global _daemon_task
    if _daemon_task is not None:
        _daemon_task.cancel()
        try:
            await _daemon_task
        except asyncio.CancelledError:
            pass
        _daemon_task = None
        logger.info("Stopped background inactivity checker task")
