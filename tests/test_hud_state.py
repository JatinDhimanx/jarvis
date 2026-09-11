"""Tests for HUDStateManager matching 01_SYSTEM_ARCHITECTURE.md and 15_STATE_MACHINE.md."""

import pytest
from jarvis.core.state_machine import State
from jarvis.ui.hud_state import HUDStateManager


def test_hud_state_initial_values():
    mgr = HUDStateManager()
    data = mgr.to_dict()
    assert data["state"] == "IDLE"
    assert data["camera_active"] is False
    assert data["mic_active"] is False
    assert data["last_event"] is None
    assert data["active_plan"] is None
    assert data["pending_confirmation"] is None
    assert data["system_status"]["volume"] == 50


def test_hud_state_transitions_and_confirmation():
    mgr = HUDStateManager()

    mgr.set_state(State.LISTENING)
    assert mgr.to_dict()["state"] == "LISTENING"

    # Waiting confirmation with prompt
    mgr.set_state(State.WAITING_CONFIRMATION, pending_prompt="Delete 'file.zip' permanently? Confirm or cancel.")
    data = mgr.to_dict()
    assert data["state"] == "WAITING_CONFIRMATION"
    assert "Delete 'file.zip'" in data["pending_confirmation"]

    # Transitioning away clears prompt
    mgr.set_state(State.EXECUTING)
    assert mgr.to_dict()["pending_confirmation"] is None


def test_hud_privacy_indicators():
    mgr = HUDStateManager()

    mgr.set_privacy_indicators(camera=True)
    assert mgr.to_dict()["camera_active"] is True
    assert mgr.to_dict()["mic_active"] is False

    mgr.set_privacy_indicators(mic=True)
    assert mgr.to_dict()["mic_active"] is True

    mgr.set_privacy_indicators(camera=False, mic=False)
    assert mgr.to_dict()["camera_active"] is False
    assert mgr.to_dict()["mic_active"] is False


def test_hud_input_event_and_plan_progress():
    mgr = HUDStateManager()

    mgr.record_input_event(channel="voice", payload="open terminal", confidence=0.95, intent="APP_CONTROL")
    event = mgr.to_dict()["last_event"]
    assert event["channel"] == "voice"
    assert event["payload"] == "open terminal"
    assert event["confidence"] == 0.95
    assert event["intent"] == "APP_CONTROL"

    mgr.update_plan_progress(plan_id="p-1", current_step=0, total_steps=3, current_action="open_app")
    plan = mgr.to_dict()["active_plan"]
    assert plan["total_steps"] == 3
    assert plan["current_action"] == "open_app"

    mgr.clear_plan_progress()
    assert mgr.to_dict()["active_plan"] is None


def test_hud_recent_actions_buffer():
    mgr = HUDStateManager(max_recent_actions=3)

    mgr.record_action_executed("set_volume", "success", True, duration_ms=12.5)
    mgr.record_action_executed("open_app", "success", True, duration_ms=45.0)
    mgr.record_action_executed("delete_file", "failed", False, duration_ms=5.0)

    actions = mgr.to_dict()["recent_actions"]
    assert len(actions) == 3
    assert actions[0]["action"] == "delete_file"
    assert actions[0]["verified"] is False

    # Append 4th item, oldest drops
    mgr.record_action_executed("lock_screen", "success", True)
    actions2 = mgr.to_dict()["recent_actions"]
    assert len(actions2) == 3
    assert actions2[0]["action"] == "lock_screen"
    assert not any(a["action"] == "set_volume" for a in actions2)


def test_hud_listener_notification():
    mgr = HUDStateManager()
    received = []

    def on_update(data):
        received.append(data["state"])

    mgr.add_listener(on_update)
    mgr.set_state(State.THINKING)
    mgr.set_state(State.EXECUTING)

    assert len(received) == 2
    assert received == ["THINKING", "EXECUTING"]
