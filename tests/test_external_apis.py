"""Tests for External API client and tools matching 08_ACTION_ENGINE.md, 09_TOOL_REGISTRY.md, and 20_DEVELOPER_CONTRACT.md."""

import pytest
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionRequest, ActionStatus
from jarvis.execution.actions.api_client import ExternalAPIClient, register_api_tools
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolRegistry


@pytest.fixture
def api_env():
    registry = ToolRegistry()
    client = ExternalAPIClient(is_online=True, allowed_domains=["api.weather.com", "api.github.com"])
    register_api_tools(registry, client)
    sm = StateMachine()
    policy = SafetyPolicy()
    engine = ActionEngine(registry=registry, state_machine=sm, policy=policy)
    return engine, client


def test_get_weather_happy_path(api_env):
    engine, client = api_env
    req = ActionRequest(
        action_id="a-api-w",
        session_id="s-api",
        source_event_id="e-api",
        source="voice",
        action="get_weather",
        parameters={"location": "London"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.SUCCESS
    assert result.verified is True
    assert "London" in result.result
    assert "22" in result.result


def test_get_weather_empty_location_raises_e100(api_env):
    _, client = api_env
    with pytest.raises(JarvisError) as exc_info:
        client.get_weather("")
    assert exc_info.value.code == ErrorCode.E100


def test_get_weather_network_offline_raises_e600(api_env):
    engine, client = api_env
    client.is_online = False
    req = ActionRequest(
        action_id="a-api-off",
        session_id="s-api",
        source_event_id="e-api",
        source="voice",
        action="get_weather",
        parameters={"location": "Tokyo"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.error_code == ErrorCode.E600
    assert result.verified is False


def test_fetch_api_allowed_domain_success(api_env):
    engine, client = api_env
    req = ActionRequest(
        action_id="a-api-fetch",
        session_id="s-api",
        source_event_id="e-api",
        source="voice",
        action="fetch_api",
        parameters={"endpoint_url": "https://api.github.com/user/repos"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.SUCCESS
    assert result.verified is True
    assert "200" in result.result
    assert "Success" in result.result


def test_fetch_api_disallowed_domain_rejected(api_env):
    engine, client = api_env
    req = ActionRequest(
        action_id="a-api-bad",
        session_id="s-api",
        source_event_id="e-api",
        source="voice",
        action="fetch_api",
        parameters={"endpoint_url": "https://malicious-site.net/exfiltrate"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.error_code == ErrorCode.E400
    assert result.verified is False
