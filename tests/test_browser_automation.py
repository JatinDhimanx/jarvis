"""Tests for Browser Automation actions matching 08_ACTION_ENGINE.md, 09_TOOL_REGISTRY.md, and 11_SAFETY_AND_PERMISSIONS.md."""

import pytest
from jarvis.core.errors import ErrorCode
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionRequest, ActionStatus
from jarvis.execution.actions.browser import VirtualBrowser, register_browser_tools
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolRegistry


@pytest.fixture
def browser_env():
    registry = ToolRegistry()
    browser = VirtualBrowser(is_online=True)
    register_browser_tools(registry, browser)
    sm = StateMachine()
    policy = SafetyPolicy()
    engine = ActionEngine(registry=registry, state_machine=sm, policy=policy)
    return engine, browser


def test_browser_open_url_happy_path(browser_env):
    engine, browser = browser_env
    req = ActionRequest(
        action_id="a-b-1",
        session_id="s-b",
        source_event_id="e-b",
        source="voice",
        action="open_browser_url",
        parameters={"url": "https://github.com/trending"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.SUCCESS
    assert result.verified is True
    assert browser.current_url == "https://github.com/trending"


def test_browser_insecure_scheme_rejected(browser_env):
    engine, browser = browser_env
    req = ActionRequest(
        action_id="a-b-bad",
        session_id="s-b",
        source_event_id="e-b",
        source="voice",
        action="open_browser_url",
        parameters={"url": "javascript:alert('pwned')"},
    )
    result = engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.error_code == ErrorCode.E400
    assert result.verified is False


def test_browser_interactions(browser_env):
    engine, browser = browser_env
    # 1. Scroll
    req_scroll = ActionRequest(
        action_id="a-b-scroll",
        session_id="s-b",
        source_event_id="e-b",
        source="gesture",
        action="browser_scroll",
        parameters={"direction": "down", "amount": 500},
    )
    res_scroll = engine.execute(req_scroll)
    assert res_scroll.status == ActionStatus.SUCCESS
    assert res_scroll.verified is True
    assert browser.scroll_position == 500

    # 2. Input
    req_input = ActionRequest(
        action_id="a-b-input",
        session_id="s-b",
        source_event_id="e-b",
        source="keyboard",
        action="browser_input",
        parameters={"selector": "#search-input", "text": "agentic AI"},
    )
    res_input = engine.execute(req_input)
    assert res_input.status == ActionStatus.SUCCESS
    assert res_input.verified is True
    assert browser.input_values["#search-input"] == "agentic AI"

    # 3. Click
    req_click = ActionRequest(
        action_id="a-b-click",
        session_id="s-b",
        source_event_id="e-b",
        source="gesture",
        action="browser_click",
        parameters={"selector": "button.submit"},
    )
    res_click = engine.execute(req_click)
    assert res_click.status == ActionStatus.SUCCESS
    assert res_click.verified is True
    assert "button.submit" in browser.clicked_elements


def test_browser_transaction_high_risk_confirmation_flow(browser_env):
    engine, browser = browser_env
    req = ActionRequest(
        action_id="a-b-tx",
        session_id="s-b",
        source_event_id="e-b",
        source="voice",
        action="browser_submit_transaction",
        parameters={"site": "store.com", "amount": "$49.99"},
    )

    # 1. Initial attempt without confirmation pauses
    res_pause = engine.execute(req, user_confirmed=False)
    assert res_pause.status == ActionStatus.NEEDS_CONFIRMATION
    assert res_pause.verified is False
    assert "Submit transaction on 'store.com' for $49.99? Confirm or cancel." in res_pause.result

    # 2. Execution with explicit confirmation succeeds
    res_confirmed = engine.execute(req, user_confirmed=True)
    assert res_confirmed.status == ActionStatus.SUCCESS
    assert res_confirmed.verified is True
    assert len(browser.submitted_transactions) == 1
    assert browser.submitted_transactions[0]["site"] == "store.com"
