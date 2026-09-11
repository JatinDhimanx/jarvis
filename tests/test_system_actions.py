"""Tests for System actions (brightness, lock screen, shutdown) matching 08_ACTION_ENGINE.md."""

import pytest
from jarvis.execution.action_engine import ActionRequest, ActionStatus
from jarvis.execution.actions.system import VirtualSystemBackend
from jarvis.pipeline import ExecutionPipeline


def test_brightness_control_clamping_and_verification():
    """Test brightness set and clamping."""
    sb = VirtualSystemBackend()

    # Normal set
    msg1 = sb.set_brightness(85)
    assert "85%" in msg1
    assert sb.brightness == 85
    assert sb.verify_brightness(85) is True

    # Clamping > 100
    msg2 = sb.set_brightness(150)
    assert "100%" in msg2
    assert sb.brightness == 100

    # Clamping < 0
    msg3 = sb.set_brightness(-20)
    assert "0%" in msg3
    assert sb.brightness == 0


def test_lock_screen_execution():
    """Test lock screen action."""
    sb = VirtualSystemBackend()
    pipeline = ExecutionPipeline(system_backend=sb)

    req = ActionRequest(
        action_id="a-sys1",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="lock_screen",
    )
    result = pipeline.action_engine.execute(req)
    assert result.status == ActionStatus.SUCCESS
    assert result.verified is True
    assert sb.is_locked is True


def test_shutdown_high_risk_confirmation_flow():
    """Per 11_SAFETY_AND_PERMISSIONS.md: shutdown is HIGH risk requiring confirmation."""
    sb = VirtualSystemBackend()
    pipeline = ExecutionPipeline(system_backend=sb)

    req = ActionRequest(
        action_id="a-sys2",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="shutdown",
    )

    # 1. First execution requires confirmation
    res1 = pipeline.action_engine.execute(req, user_confirmed=False)
    assert res1.status == ActionStatus.NEEDS_CONFIRMATION
    assert "Confirm or cancel" in res1.result
    assert sb.is_shutdown is False

    # 2. Confirmed execution succeeds
    res2 = pipeline.action_engine.execute(req, user_confirmed=True)
    assert res2.status == ActionStatus.SUCCESS
    assert res2.verified is True
    assert sb.is_shutdown is True
