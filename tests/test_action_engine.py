"""Tests for Action Engine contract and execution matching 08_ACTION_ENGINE.md."""

import pytest
from jarvis.core.errors import ErrorCode
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionRequest, ActionStatus
from jarvis.execution.actions.system import VirtualSystemBackend, register_system_tools
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolRegistry


def test_action_engine_contract_compliance():
    """Verify ActionRequest carries action_id, session_id, source_event_id, source, timestamp, action, risk, requires_confirmation."""
    req = ActionRequest(
        action_id="a-123456",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="set_volume",
        parameters={"value": 50},
        risk=RiskLevel.LOW,
        requires_confirmation=False,
    )
    assert req.action_id == "a-123456"
    assert req.session_id == "s-test"
    assert req.source_event_id == "e-test"
    assert req.source == "voice"
    assert req.parameters == {"value": 50}


def test_action_engine_deterministic_confirmation_override():
    """Action Engine recomputes requires_confirmation and ignores upstream false claims."""
    registry = ToolRegistry()
    backend = VirtualSystemBackend()
    register_system_tools(registry, backend)

    sm = StateMachine()
    # Register shutdown as HIGH risk tool
    from jarvis.registry.registry import ToolDeclaration, Availability
    registry.register_tool(
        ToolDeclaration(
            name="shutdown",
            version=1,
            description="Shutdown",
            input_schema={},
            output_schema={},
            risk_level=RiskLevel.HIGH,
            verification_method="none",
        )
    )

    engine = ActionEngine(registry=registry, state_machine=sm)

    # Malicious or buggy upstream claims requires_confirmation is False for high risk
    req = ActionRequest(
        action_id="a-hack",
        session_id="s-test",
        source_event_id="e-hack",
        source="ai_plan",
        action="shutdown",
        risk=RiskLevel.HIGH,
        requires_confirmation=False,
    )

    result = engine.execute(req, user_confirmed=False)
    assert result.status == ActionStatus.NEEDS_CONFIRMATION
    assert result.verified is False
    assert result.result is not None
    assert "Confirm or cancel" in result.result


def test_action_engine_unregistered_tool_returns_e400():
    """Executing an unregistered tool returns BLOCKED with E400."""
    registry = ToolRegistry()
    sm = StateMachine()
    engine = ActionEngine(registry=registry, state_machine=sm)

    req = ActionRequest(
        action_id="a-unreg",
        session_id="s-test",
        source_event_id="e-test",
        source="keyboard",
        action="arbitrary_os_command",
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.BLOCKED
    assert result.error_code == ErrorCode.E400
    assert result.verified is False


def test_action_engine_verification_failure():
    """Per 20_DEVELOPER_CONTRACT.md Rule 5: Never claim success without verification."""
    registry = ToolRegistry()
    backend = VirtualSystemBackend()
    register_system_tools(registry, backend)
    sm = StateMachine()
    engine = ActionEngine(registry=registry, state_machine=sm)

    # Force verification failure in the backend
    backend.fail_next_verification = True

    req = ActionRequest(
        action_id="a-fail",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="set_volume",
        parameters={"value": 75},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.verified is False
    assert result.error_code == ErrorCode.E700
