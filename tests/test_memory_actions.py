"""Tests for memory action group execution matching 08_ACTION_ENGINE.md and 09_TOOL_REGISTRY.md."""

import pytest
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionRequest, ActionStatus
from jarvis.execution.actions.memory import MemoryActionManager, register_memory_tools
from jarvis.memory.store import MemoryStore
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolRegistry


@pytest.fixture
def memory_env():
    registry = ToolRegistry()
    store = MemoryStore()
    manager = MemoryActionManager(store=store)
    register_memory_tools(registry, manager)
    sm = StateMachine()
    policy = SafetyPolicy()
    engine = ActionEngine(registry=registry, state_machine=sm, policy=policy)
    return engine, store, manager


def test_memory_tools_declaration_compliance():
    registry = ToolRegistry()
    register_memory_tools(registry)

    for tool_name in ["write_memory", "read_memory", "update_memory", "forget_memory"]:
        decl = registry.get_declaration(tool_name)
        assert decl is not None
        assert decl.name == tool_name
        assert decl.version == 1
        assert decl.risk_level == RiskLevel.LOW
        assert decl.required_permissions == ["memory"]
        assert decl.verification_method is not None


def test_write_and_read_memory_action(memory_env):
    engine, store, _ = memory_env

    # 1. Write memory
    req_write = ActionRequest(
        action_id="a-mem-w",
        session_id="s-mem",
        source_event_id="e-mem",
        source="voice",
        action="write_memory",
        parameters={"key": "editor", "value": "neovim", "category": "preference"},
    )
    res_write = engine.execute(req_write)
    assert res_write.status == ActionStatus.SUCCESS
    assert res_write.verified is True
    assert store.read("editor").value == "neovim"

    # 2. Read memory
    req_read = ActionRequest(
        action_id="a-mem-r",
        session_id="s-mem",
        source_event_id="e-mem",
        source="voice",
        action="read_memory",
        parameters={"key": "editor"},
    )
    res_read = engine.execute(req_read)
    assert res_read.status == ActionStatus.SUCCESS
    assert res_read.verified is True
    assert "neovim" in res_read.result


def test_update_and_forget_memory_action(memory_env):
    engine, store, _ = memory_env
    store.write(key="volume_level", value=60)

    # 1. Update memory
    req_up = ActionRequest(
        action_id="a-mem-up",
        session_id="s-mem",
        source_event_id="e-mem",
        source="voice",
        action="update_memory",
        parameters={"key": "volume_level", "value": 75},
    )
    res_up = engine.execute(req_up)
    assert res_up.status == ActionStatus.SUCCESS
    assert res_up.verified is True
    assert store.read("volume_level").value == 75

    # 2. Forget memory
    req_f = ActionRequest(
        action_id="a-mem-f",
        session_id="s-mem",
        source_event_id="e-mem",
        source="voice",
        action="forget_memory",
        parameters={"key": "volume_level"},
    )
    res_f = engine.execute(req_f)
    assert res_f.status == ActionStatus.SUCCESS
    assert res_f.verified is True
    assert store.read("volume_level") is None
