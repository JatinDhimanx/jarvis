"""Tests for Runtime State Machine matching 15_STATE_MACHINE.md."""

import pytest
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import State, StateMachine


def test_canonical_state_flow():
    """Verify normal flow: IDLE -> LISTENING -> THINKING -> EXECUTING -> VERIFYING -> IDLE."""
    sm = StateMachine()
    assert sm.current_state == State.IDLE

    sm.transition_to(State.LISTENING)
    assert sm.current_state == State.LISTENING

    sm.transition_to(State.THINKING)
    assert sm.current_state == State.THINKING

    sm.transition_to(State.EXECUTING, action_id="a-1")
    assert sm.current_state == State.EXECUTING
    assert sm.active_action_id == "a-1"

    sm.transition_to(State.VERIFYING)
    assert sm.current_state == State.VERIFYING

    sm.transition_to(State.IDLE)
    assert sm.current_state == State.IDLE


def test_confirmation_flow_and_cancellation():
    """Verify confirmation: THINKING -> WAITING_CONFIRMATION -> EXECUTING and cancellation -> IDLE."""
    sm = StateMachine()
    sm.transition_to(State.THINKING)
    sm.transition_to(State.WAITING_CONFIRMATION, action_id="a-confirm")
    assert sm.current_state == State.WAITING_CONFIRMATION

    # Cancellation flow: WAITING_CONFIRMATION -> IDLE
    sm.transition_to(State.IDLE)
    assert sm.current_state == State.IDLE

    # Re-test confirmation approval flow
    sm.transition_to(State.THINKING)
    sm.transition_to(State.WAITING_CONFIRMATION, action_id="a-confirm")
    sm.transition_to(State.EXECUTING, action_id="a-confirm")
    assert sm.current_state == State.EXECUTING


def test_emergency_stop_from_any_state():
    """Verify ANY -> STOPPED -> IDLE transition rule."""
    states_to_test = [
        State.IDLE,
        State.LISTENING,
        State.THINKING,
        State.WAITING_CONFIRMATION,
        State.EXECUTING,
        State.VERIFYING,
        State.ERROR,
    ]

    for start_state in states_to_test:
        sm = StateMachine(start_state)
        sm.emergency_stop()
        assert sm.current_state == State.STOPPED
        sm.reset_to_idle()
        assert sm.current_state == State.IDLE


def test_non_interruptible_action_lock():
    """Verify non-interruptible action in EXECUTING rejects conflicting commands with E510."""
    sm = StateMachine()
    sm.transition_to(State.THINKING)
    sm.transition_to(State.EXECUTING, action_id="a-critical", interruptible=False)
    assert sm.is_interruptible is False

    # Attempting another execution should be rejected
    with pytest.raises(JarvisError) as exc:
        sm.transition_to(State.EXECUTING, action_id="a-second")
    assert exc.value.code == ErrorCode.E510

    # But emergency stop MUST still be accepted
    sm.emergency_stop()
    assert sm.current_state == State.STOPPED


def test_illegal_state_transition():
    """Verify illegal transitions throw E510."""
    sm = StateMachine(State.IDLE)
    # Direct jump from IDLE to VERIFYING is illegal
    with pytest.raises(JarvisError) as exc:
        sm.transition_to(State.VERIFYING)
    assert exc.value.code == ErrorCode.E510
