"""Tests for Web Search tools matching 08_ACTION_ENGINE.md, 09_TOOL_REGISTRY.md, and 20_DEVELOPER_CONTRACT.md."""

import pytest
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionRequest, ActionStatus
from jarvis.execution.actions.web_search import WebSearchBackend, register_web_search_tools
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolRegistry


def test_search_web_tool_declaration_compliance():
    registry = ToolRegistry()
    register_web_search_tools(registry)

    decl = registry.get_declaration("search_web")
    assert decl is not None
    assert decl.name == "search_web"
    assert decl.version == 1
    assert decl.risk_level == RiskLevel.LOW
    assert decl.required_permissions == ["network"]
    assert decl.reversible is True
    assert decl.verification_method == "verify_search"


def test_search_web_happy_path_and_verification():
    registry = ToolRegistry()
    backend = WebSearchBackend(is_online=True)
    register_web_search_tools(registry, backend)

    sm = StateMachine()
    engine = ActionEngine(registry=registry, state_machine=sm)

    req = ActionRequest(
        action_id="a-search-1",
        session_id="s-web",
        source_event_id="e-search",
        source="voice",
        action="search_web",
        parameters={"query": "python asyncio tutorials"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.SUCCESS
    assert result.verified is True
    assert result.result is not None
    assert "python asyncio tutorials" in result.result


def test_search_web_empty_query_raises_e100():
    backend = WebSearchBackend(is_online=True)
    with pytest.raises(JarvisError) as exc_info:
        backend.search("")
    assert exc_info.value.code == ErrorCode.E100


def test_search_web_network_offline_raises_e600():
    registry = ToolRegistry()
    backend = WebSearchBackend(is_online=False)
    register_web_search_tools(registry, backend)

    sm = StateMachine()
    engine = ActionEngine(registry=registry, state_machine=sm)

    req = ActionRequest(
        action_id="a-search-off",
        session_id="s-web",
        source_event_id="e-search",
        source="voice",
        action="search_web",
        parameters={"query": "world news"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.error_code == ErrorCode.E600
    assert result.verified is False


def test_search_web_verification_failure():
    registry = ToolRegistry()
    backend = WebSearchBackend(is_online=True)
    register_web_search_tools(registry, backend)

    sm = StateMachine()
    engine = ActionEngine(registry=registry, state_machine=sm)

    backend.fail_next_verification = True
    req = ActionRequest(
        action_id="a-search-fail",
        session_id="s-web",
        source_event_id="e-search",
        source="voice",
        action="search_web",
        parameters={"query": "test query"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.error_code == ErrorCode.E700
    assert result.verified is False
