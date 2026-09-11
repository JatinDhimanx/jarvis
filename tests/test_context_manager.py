"""Tests for ContextManager matching 03_CONTEXT_AND_MEMORY.md."""

import pytest
from jarvis.brain_layer.context import ContextManager
from jarvis.brain_layer.models import Plan, PlanState, PlanStep


def test_l0_context_update():
    cm = ContextManager()
    assert cm.l0_latest_input is None

    event = {"source": "voice", "text": "open notepad", "timestamp": 123456.0}
    cm.update_l0(event)
    assert cm.l0_latest_input == event


def test_l1_task_lifecycle():
    cm = ContextManager()
    plan = Plan(raw_goal="test goal", steps=[PlanStep(action="set_volume", parameters={"level": 50})])
    
    cm.start_l1_task(plan)
    assert cm.l1_active_plan == plan
    cm.l1_task_variables["target"] = "speaker"
    assert cm.l1_task_variables["target"] == "speaker"

    cm.clear_l1_task()
    assert cm.l1_active_plan is None
    assert len(cm.l1_task_variables) == 0


def test_l2_turn_recording_and_history_limit():
    cm = ContextManager(history_limit=3)
    
    cm.record_turn("user", "turn 1")
    cm.record_turn("assistant", "reply 1")
    cm.record_turn("user", "turn 2")
    assert len(cm.l2_turns) == 3

    # Add 4th turn, should drop turn 1
    cm.record_turn("assistant", "reply 2")
    assert len(cm.l2_turns) == 3
    assert cm.l2_turns[0]["text"] == "reply 1"
    assert cm.l2_turns[-1]["text"] == "reply 2"


def test_pronoun_resolution_app():
    cm = ContextManager()
    cm.record_turn("user", "open chrome", action="open_app", entities={"app_name": "chrome"})
    assert cm.last_referenced_app == "chrome"

    resolved = cm.resolve_reference("close it")
    assert resolved is not None
    assert resolved["action"] == "close_app"
    assert resolved["entities"]["app_name"] == "chrome"

    # Single word "it"
    resolved_single = cm.resolve_reference("it")
    assert resolved_single is not None
    assert resolved_single["entities"]["app_name"] == "chrome"


def test_pronoun_resolution_file():
    cm = ContextManager()
    cm.record_turn("user", "create test.txt", action="create_file", entities={"path": "test.txt"})
    assert cm.last_referenced_file == "test.txt"

    resolved_delete = cm.resolve_reference("delete that")
    assert resolved_delete is not None
    assert resolved_delete["action"] == "delete_file"
    assert resolved_delete["entities"]["path"] == "test.txt"

    resolved_open = cm.resolve_reference("open that")
    assert resolved_open is not None
    assert resolved_open["action"] == "open_file"
    assert resolved_open["entities"]["path"] == "test.txt"


def test_pronoun_resolution_repeat_action():
    cm = ContextManager()
    cm.record_action_executed("set_volume", {"level": 70}, reversible=True)
    
    resolved = cm.resolve_reference("do it again")
    assert resolved is not None
    assert resolved["action"] == "set_volume"
    assert resolved["parameters"]["level"] == 70

    # Irreversible action should not overwrite
    cm.record_action_executed("delete_file", {"path": "important.txt"}, reversible=False)
    resolved2 = cm.resolve_reference("do it again")
    assert resolved2["action"] == "set_volume"


def test_unresolved_pronoun():
    cm = ContextManager()
    assert cm.resolve_reference("what is the weather") is None
    assert cm.resolve_reference("close it") is None
