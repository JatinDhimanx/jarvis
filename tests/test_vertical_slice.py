"""End-to-end vertical slice tests connecting Input -> Router -> Policy -> Action -> Verification -> Logging -> Response."""

import pytest
from jarvis.core.errors import ErrorCode
from jarvis.execution.action_engine import ActionStatus
from jarvis.registry.registry import Availability, ToolDeclaration
from jarvis.policy.safety import RiskLevel
from jarvis.router.router import InputEvent


def test_vertical_slice_volume_happy_path(pipeline, system_backend):
    """Voice input -> Router -> Policy -> set_volume -> Verify -> Log -> Response."""
    event = InputEvent(
        event_id="e-voice-001",
        channel="voice",
        raw_payload="Jarvis, set volume to 70",
    )

    result = pipeline.process_event(event)

    assert result["status"] == ActionStatus.SUCCESS.value
    assert result["verified"] is True
    assert result["error_code"] is None
    assert result["response_text"] == "Volume set to 70%"
    assert system_backend.volume == 70
    assert result["state"] == "IDLE"

    # Verify audit logs
    records = pipeline.logger.audit_records
    # Privacy check: speech is masked by default
    input_records = [r for r in records if r.get("type") == "input"]
    assert input_records[0]["raw_input"] == "[MASKED_BY_PRIVACY_POLICY]"

    intent_records = [r for r in records if r.get("type") == "intent"]
    assert intent_records[0]["intent"] == "SYSTEM_CONTROL"
    assert intent_records[0]["entities"] == {"value": 70}

    action_records = [r for r in records if r.get("type") == "action_result"]
    assert action_records[0]["status"] == "success"
    assert action_records[0]["verified"] is True


def test_vertical_slice_open_app_happy_path(pipeline, app_manager):
    """Voice input -> Router -> Policy -> open_app -> Verify -> Log -> Response."""
    event = InputEvent(
        event_id="e-voice-002",
        channel="voice",
        raw_payload="open Chrome",
    )

    result = pipeline.process_event(event)

    assert result["status"] == ActionStatus.SUCCESS.value
    assert result["verified"] is True
    assert result["error_code"] is None
    assert "Chrome is open" in result["response_text"]
    assert "chrome" in app_manager.running_apps
    assert result["state"] == "IDLE"


def test_vertical_slice_invalid_input(pipeline):
    """Ambiguous or unrecognized input routes to UNKNOWN with E300 without executing side effects."""
    event = InputEvent(
        event_id="e-voice-003",
        channel="voice",
        raw_payload="open that",
    )

    result = pipeline.process_event(event)

    assert result["status"] == ActionStatus.BLOCKED.value
    assert result["verified"] is False
    assert result["error_code"] == ErrorCode.E300.value
    assert "Which item did you mean" in result["response_text"]
    assert result["state"] == "IDLE"


def test_vertical_slice_verification_failure(pipeline, system_backend):
    """Action executed but post-check fails -> status failed, error_code E700, verified False."""
    system_backend.fail_next_verification = True

    event = InputEvent(
        event_id="e-voice-004",
        channel="voice",
        raw_payload="set volume to 80",
    )

    result = pipeline.process_event(event)

    assert result["status"] == ActionStatus.FAILED.value
    assert result["verified"] is False
    assert result["error_code"] == ErrorCode.E700.value
    assert "verification failed" in result["response_text"]
    assert result["state"] == "IDLE"


def test_vertical_slice_confirmation_flow(pipeline):
    """High-risk action requires confirmation; confirms then executes."""
    # Register shutdown in registry as HIGH risk
    pipeline.registry.register_tool(
        ToolDeclaration(
            name="shutdown",
            version=1,
            description="Shutdown",
            input_schema={},
            output_schema={},
            risk_level=RiskLevel.HIGH,
            verification_method="check_power_state",
        ),
        handler=lambda: "System shutting down.",
        verifier=lambda: True,
    )

    event = InputEvent(
        event_id="e-voice-005",
        channel="voice",
        raw_payload="turn off the computer",
    )

    # 1. First invocation requires confirmation
    result1 = pipeline.process_event(event)
    assert result1["status"] == ActionStatus.NEEDS_CONFIRMATION.value
    assert result1["verified"] is False
    assert "Confirm or cancel" in result1["response_text"]
    assert result1["state"] == "WAITING_CONFIRMATION"

    # 2. User confirms
    result2 = pipeline.confirm_pending(confirmed=True)
    assert result2["status"] == ActionStatus.SUCCESS.value
    assert result2["verified"] is True
    assert result2["response_text"] == "System shutting down."
    assert result2["state"] == "IDLE"


def test_vertical_slice_confirmation_rejection(pipeline):
    """High-risk action rejected by user -> cancelled with E420."""
    pipeline.registry.register_tool(
        ToolDeclaration(
            name="shutdown",
            version=1,
            description="Shutdown",
            input_schema={},
            output_schema={},
            risk_level=RiskLevel.HIGH,
            verification_method="check_power_state",
        ),
        handler=lambda: "System shutting down.",
        verifier=lambda: True,
    )

    event = InputEvent(
        event_id="e-voice-006",
        channel="voice",
        raw_payload="turn off the computer",
    )

    pipeline.process_event(event)
    # User cancels
    cancel_result = pipeline.confirm_pending(confirmed=False)
    assert cancel_result["status"] == ActionStatus.CANCELLED.value
    assert cancel_result["error_code"] == ErrorCode.E420.value
    assert "cancelled" in cancel_result["response_text"]
    assert cancel_result["state"] == "IDLE"


def test_vertical_slice_emergency_stop(pipeline):
    """Emergency stop event immediately resets state to IDLE and halts actions."""
    event = InputEvent(
        event_id="e-voice-007",
        channel="voice",
        raw_payload="Jarvis, emergency stop",
    )

    result = pipeline.process_event(event)
    assert result["status"] == ActionStatus.CANCELLED.value
    assert "Emergency stop activated" in result["response_text"]
    assert result["state"] == "IDLE"
