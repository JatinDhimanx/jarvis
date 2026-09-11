"""Tests for MultiStepPlanner matching 10_PLANNER.md."""

import pytest
from jarvis.brain_layer.models import PlanState
from jarvis.brain_layer.planner import MultiStepPlanner
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionStatus
from jarvis.execution.actions.files import VirtualFileManager, register_file_tools
from jarvis.execution.actions.system import VirtualSystemBackend, register_system_tools
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolDeclaration, ToolRegistry


@pytest.fixture
def planner_env():
    registry = ToolRegistry()
    sys_backend = VirtualSystemBackend()
    register_system_tools(registry, sys_backend)

    file_backend = VirtualFileManager()
    register_file_tools(registry, file_backend)

    sm = StateMachine()
    engine = ActionEngine(registry=registry, state_machine=sm)
    planner = MultiStepPlanner(registry=registry, action_engine=engine)
    return planner, sys_backend, file_backend


def test_planner_create_and_validate(planner_env):
    planner, _, _ = planner_env
    plan = planner.create_plan(
        raw_goal="Adjust audio and create notes",
        steps_data=[
            {"action": "set_volume", "parameters": {"value": 50}},
            {"action": "create_file", "parameters": {"path": "notes.txt", "content": "hello"}},
        ],
    )
    assert plan.state == PlanState.DRAFT
    assert len(plan.steps) == 2

    validated_plan = planner.validate_plan(plan)
    assert validated_plan.state == PlanState.VALIDATED
    assert validated_plan.steps[0].requires_confirmation is False


def test_planner_validate_unregistered_tool_raises_e400(planner_env):
    planner, _, _ = planner_env
    plan = planner.create_plan(
        raw_goal="Run unknown action",
        steps_data=[{"action": "unknown_forbidden_action", "parameters": {}}],
    )
    with pytest.raises(JarvisError) as exc_info:
        planner.validate_plan(plan)
    assert exc_info.value.code == ErrorCode.E400
    assert plan.state == PlanState.ABORTED


def test_planner_validate_empty_plan_raises_e100(planner_env):
    planner, _, _ = planner_env
    plan = planner.create_plan(raw_goal="Empty", steps_data=[])
    with pytest.raises(JarvisError) as exc_info:
        planner.validate_plan(plan)
    assert exc_info.value.code == ErrorCode.E100


def test_planner_sequential_execution_to_completion(planner_env):
    planner, sys_backend, _ = planner_env
    plan = planner.create_plan(
        raw_goal="Change volume twice",
        steps_data=[
            {"action": "set_volume", "parameters": {"value": 40}},
            {"action": "set_volume", "parameters": {"value": 60}},
        ],
    )
    planner.validate_plan(plan)

    # Step 1
    step1 = planner.execute_next_step(plan)
    assert step1.status == ActionStatus.SUCCESS
    assert step1.verified is True
    assert sys_backend.volume == 40
    assert plan.current_step_index == 1
    assert plan.state == PlanState.VALIDATED

    # Step 2
    step2 = planner.execute_next_step(plan)
    assert step2.status == ActionStatus.SUCCESS
    assert step2.verified is True
    assert sys_backend.volume == 60
    assert plan.current_step_index == 2
    assert plan.state == PlanState.COMPLETE


def test_planner_halts_on_prerequisite_failure(planner_env):
    planner, sys_backend, _ = planner_env
    plan = planner.create_plan(
        raw_goal="Failing step stops plan",
        steps_data=[
            {"action": "set_volume", "parameters": {"value": 30}},
            {"action": "set_volume", "parameters": {"value": 90}},
        ],
    )
    planner.validate_plan(plan)

    # Induce verification failure on step 1
    sys_backend.fail_next_verification = True
    step1 = planner.execute_next_step(plan)
    assert step1.status == ActionStatus.FAILED
    assert step1.verified is False
    assert step1.error_code == ErrorCode.E700.value
    assert plan.state == PlanState.ABORTED

    # Subsequent execution attempt is rejected per 10_PLANNER.md
    with pytest.raises(JarvisError) as exc_info:
        planner.execute_next_step(plan)
    assert exc_info.value.code == ErrorCode.E510


def test_planner_confirmation_pause_and_resume(planner_env):
    planner, _, file_backend = planner_env
    # Create file first so delete has a target
    file_backend.create_file("delete_me.txt", "content")

    plan = planner.create_plan(
        raw_goal="Delete file requiring confirmation",
        steps_data=[
            {"action": "delete_file", "parameters": {"path": "delete_me.txt"}},
        ],
    )
    planner.validate_plan(plan)
    assert plan.steps[0].requires_confirmation is True

    # First attempt: without confirmation
    step_pause = planner.execute_next_step(plan, user_confirmed=False)
    assert step_pause.status == ActionStatus.NEEDS_CONFIRMATION
    assert plan.state == PlanState.WAITING_CONFIRMATION

    # Second attempt: with user confirmation
    step_confirmed = planner.execute_next_step(plan, user_confirmed=True)
    assert step_confirmed.status == ActionStatus.SUCCESS
    assert step_confirmed.verified is True
    assert plan.state == PlanState.COMPLETE
    assert "delete_me.txt" not in file_backend.files
