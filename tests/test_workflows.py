"""Tests for WorkflowManager, macro templates, and plan execution matching 03_CONTEXT_AND_MEMORY.md and 10_PLANNER.md."""

import pytest
from jarvis.brain_layer.models import PlanState
from jarvis.brain_layer.planner import MultiStepPlanner
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionStatus
from jarvis.execution.actions.application import VirtualAppManager, register_application_tools
from jarvis.execution.actions.system import VirtualSystemBackend, register_system_tools
from jarvis.memory.store import MemoryStore
from jarvis.memory.workflows import WorkflowManager
from jarvis.policy.safety import SafetyPolicy
from jarvis.registry.registry import ToolRegistry


@pytest.fixture
def workflow_env():
    registry = ToolRegistry()
    sys_b = VirtualSystemBackend()
    register_system_tools(registry, sys_b)
    app_b = VirtualAppManager()
    register_application_tools(registry, app_b)

    sm = StateMachine()
    policy = SafetyPolicy()
    engine = ActionEngine(registry=registry, state_machine=sm, policy=policy)
    planner = MultiStepPlanner(registry=registry, action_engine=engine, policy=policy)

    store = MemoryStore()
    wf_mgr = WorkflowManager(store=store)
    return wf_mgr, planner, sys_b, app_b


def test_workflow_save_and_load(workflow_env):
    wf_mgr, _, _, _ = workflow_env
    steps = [
        {"action": "set_volume", "parameters": {"value": 50}},
        {"action": "open_app", "parameters": {"app_name": "terminal"}},
    ]
    msg = wf_mgr.save_workflow("morning_routine", steps)
    assert "morning_routine" in msg
    assert "2 steps" in msg

    loaded = wf_mgr.load_workflow("morning_routine")
    assert len(loaded) == 2
    assert loaded[0]["action"] == "set_volume"


def test_workflow_empty_validation_errors(workflow_env):
    wf_mgr, _, _, _ = workflow_env
    with pytest.raises(JarvisError) as exc_info:
        wf_mgr.save_workflow("", [{"action": "set_volume"}])
    assert exc_info.value.code == ErrorCode.E100

    with pytest.raises(JarvisError) as exc_info:
        wf_mgr.save_workflow("empty", [])
    assert exc_info.value.code == ErrorCode.E100

    with pytest.raises(JarvisError) as exc_info:
        wf_mgr.load_workflow("does_not_exist")
    assert exc_info.value.code == ErrorCode.E400


def test_workflow_execution_via_planner(workflow_env):
    wf_mgr, planner, sys_b, app_b = workflow_env

    # 1. Save workflow
    steps = [
        {"action": "set_volume", "parameters": {"value": 35}},
        {"action": "open_app", "parameters": {"app_name": "vscode"}},
    ]
    wf_mgr.save_workflow("dev_start", steps)

    # 2. Synthesize plan
    plan = wf_mgr.create_plan_from_workflow("dev_start", planner)
    assert plan.state == PlanState.VALIDATED
    assert len(plan.steps) == 2

    # 3. Step 1 execution
    s1 = planner.execute_next_step(plan)
    assert s1.status == ActionStatus.SUCCESS
    assert s1.verified is True
    assert sys_b.volume == 35

    # 4. Step 2 execution
    s2 = planner.execute_next_step(plan)
    assert s2.status == ActionStatus.SUCCESS
    assert s2.verified is True
    assert app_b.verify_app_running("vscode")
    assert plan.state == PlanState.COMPLETE
