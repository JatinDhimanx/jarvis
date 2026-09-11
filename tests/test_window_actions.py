"""Tests for Window actions matching 08_ACTION_ENGINE.md."""

import pytest
from jarvis.execution.action_engine import ActionRequest, ActionStatus
from jarvis.execution.actions.window import VirtualWindowManager, register_window_tools
from jarvis.registry.registry import ToolRegistry
from jarvis.pipeline import ExecutionPipeline
from jarvis.router.router import InputEvent


def test_window_manager_actions_and_verification():
    """Direct window manager unit tests."""
    wm = VirtualWindowManager()

    # focus_window
    msg1 = wm.focus_window("terminal")
    assert "terminal" in msg1
    assert wm.verify_window_focused("terminal") is True

    # minimize_window
    msg2 = wm.minimize_window("terminal")
    assert "terminal" in msg2
    assert wm.verify_window_minimized("terminal") is True

    # maximize_window
    msg3 = wm.maximize_window("terminal")
    assert "terminal" in msg3
    assert wm.verify_window_maximized("terminal") is True
    assert "terminal" not in wm.minimized_windows

    # switch_window
    msg4 = wm.switch_window("next")
    assert "Switched to window" in msg4
    assert wm.verify_switch_window("next") is True


def test_window_pipeline_execution():
    """Pipeline execution for window actions."""
    wm = VirtualWindowManager()
    pipeline = ExecutionPipeline(window_manager=wm)

    req = ActionRequest(
        action_id="a-win1",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="focus_window",
        parameters={"window_title": "code"},
    )
    res = pipeline.action_engine.execute(req)
    assert res.status == ActionStatus.SUCCESS
    assert res.verified is True
    assert wm.active_window == "code"


def test_window_verification_failure():
    """Verify window action verification failure reports E700."""
    wm = VirtualWindowManager()
    wm.fail_next_verification = True
    pipeline = ExecutionPipeline(window_manager=wm)

    req = ActionRequest(
        action_id="a-win2",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="minimize_window",
        parameters={"window_title": "code"},
    )
    res = pipeline.action_engine.execute(req)
    assert res.status == ActionStatus.FAILED
    assert res.verified is False
    assert res.error_code == "E700"
