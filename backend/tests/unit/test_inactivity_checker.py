"""Unit tests for background inactivity checker service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from app.agent.state import fresh_state
from app.agent.triage import TriageResult
from app.services.inactivity_checker import check_all_sessions

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@patch("app.services.inactivity_checker.memory.list_phones")
@patch("app.services.inactivity_checker.web_memory.list_sessions")
@patch("app.services.inactivity_checker.memory.load")
@patch("app.services.inactivity_checker.memory.save")
@patch("app.services.inactivity_checker.classify_message_with_openai")
@patch("app.services.inactivity_checker.slack.send_triage_alert")
@patch("app.services.inactivity_checker.persist_intake_state")
@patch("app.services.inactivity_checker.db_is_available", return_value=True)
@patch("app.services.inactivity_checker.get_sessionmaker")
async def test_inactivity_checker_finalizes_inactive_sessions(
    mock_get_sm,
    _mock_db_avail,
    mock_persist,
    mock_slack,
    mock_classify,
    mock_save,
    mock_load,
    mock_list_web,
    mock_list_phones,
) -> None:
    # 1. Setup mocks
    mock_list_phones.return_value = ["+923001234567"]
    mock_list_web.return_value = []

    # Active session last activity was 6 minutes ago (>= 300 seconds)
    six_mins_ago = (datetime.now(UTC) - timedelta(minutes=6)).isoformat()
    state = fresh_state("+923001234567")
    state["messages"] = ["first message", "second message"]
    state["last_activity_at"] = six_mins_ago
    state["routed_to"] = "pediatrics"
    state["escalated"] = True
    mock_load.return_value = state

    mock_classify.return_value = TriageResult(
        priority="P2",
        confidence=0.85,
        reasoning="Inactivity timeout triage.",
    )
    mock_slack.return_value = True

    db_ctx = MagicMock()
    mock_get_sm.return_value = MagicMock(return_value=db_ctx)

    # 2. Run inactivity check
    await check_all_sessions()

    # 3. Assertions
    # Triage was run on all messages joined by newline
    mock_classify.assert_called_once_with("first message\nsecond message")

    # Slack was notified for P2
    mock_slack.assert_called_once_with(
        patient_phone="+923001234567",
        priority="P2",
        routed_to="pediatrics",
        reasoning="Inactivity timeout triage.",
        message_preview="second message",
        escalated=True,
    )

    # Updated state was saved to memory with correct flags
    mock_save.assert_called_once()
    saved_state = mock_save.call_args[0][1]
    assert saved_state["intake_finalized"] is True
    assert saved_state["slots_complete"] is True
    assert saved_state["priority"] == "P2"
    assert saved_state["confidence"] == 0.85
    assert saved_state["slack_notified"] is True

    # Persisted to Postgres
    mock_persist.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.inactivity_checker.memory.list_phones")
@patch("app.services.inactivity_checker.web_memory.list_sessions")
@patch("app.services.inactivity_checker.memory.load")
@patch("app.services.inactivity_checker.memory.save")
@patch("app.services.inactivity_checker.classify_message_with_openai")
async def test_inactivity_checker_ignores_active_sessions(
    mock_classify,
    mock_save,
    mock_load,
    mock_list_web,
    mock_list_phones,
) -> None:
    # 1. Setup mocks
    mock_list_phones.return_value = ["+923001234567"]
    mock_list_web.return_value = []

    # Active session last activity was 2 minutes ago (< 300 seconds)
    two_mins_ago = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    state = fresh_state("+923001234567")
    state["messages"] = ["hello clinic"]
    state["last_activity_at"] = two_mins_ago
    mock_load.return_value = state

    # 2. Run inactivity check
    await check_all_sessions()

    # 3. Assertions
    mock_classify.assert_not_called()
    mock_save.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.inactivity_checker.memory.list_phones")
@patch("app.services.inactivity_checker.web_memory.list_sessions")
@patch("app.services.inactivity_checker.memory.load")
@patch("app.services.inactivity_checker.memory.save")
@patch("app.services.inactivity_checker.classify_message_with_openai")
async def test_inactivity_checker_ignores_finalized_sessions(
    mock_classify,
    mock_save,
    mock_load,
    mock_list_web,
    mock_list_phones,
) -> None:
    # 1. Setup mocks
    mock_list_phones.return_value = ["+923001234567"]
    mock_list_web.return_value = []

    # Finalized session last activity was 10 minutes ago but intake_finalized is True
    ten_mins_ago = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    state = fresh_state("+923001234567")
    state["messages"] = ["hello clinic"]
    state["last_activity_at"] = ten_mins_ago
    state["intake_finalized"] = True
    mock_load.return_value = state

    # 2. Run inactivity check
    await check_all_sessions()

    # 3. Assertions
    mock_classify.assert_not_called()
    mock_save.assert_not_called()
