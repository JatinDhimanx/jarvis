"""Tests for Crash Recovery Watchdog and Retry Policies matching 14_ERROR_RECOVERY.md."""

import pytest
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import State, StateMachine
from jarvis.packaging.recovery import CrashRecoveryWatchdog, RecoveryCheckpoint


def test_watchdog_checkpoint_lifecycle(tmp_path):
    """Test saving, loading, and clearing execution checkpoints."""
    checkpoint_file = tmp_path / "test_checkpoint.json"
    watchdog = CrashRecoveryWatchdog(checkpoint_path=checkpoint_file)

    assert watchdog.load_checkpoint() is None

    cp = RecoveryCheckpoint(
        session_id="s-test1",
        task_id="t-101",
        intent_name="bulk_action",
        step_index=2,
        total_steps=5,
        parameters={"dry_run": False},
    )
    watchdog.save_checkpoint(cp)

    loaded = watchdog.load_checkpoint()
    assert loaded is not None
    assert loaded.session_id == "s-test1"
    assert loaded.task_id == "t-101"
    assert loaded.step_index == 2

    watchdog.clear_checkpoint()
    assert watchdog.load_checkpoint() is None


def test_watchdog_recover_stuck_state(tmp_path):
    """Verify watchdog resets stuck non-IDLE state machine safely to IDLE."""
    checkpoint_file = tmp_path / "test_checkpoint.json"
    watchdog = CrashRecoveryWatchdog(checkpoint_path=checkpoint_file)

    sm = StateMachine(State.IDLE)
    sm.transition_to(State.THINKING)
    sm.transition_to(State.EXECUTING)
    assert sm.state == State.EXECUTING

    # Save checkpoint to simulate interrupted run
    cp = RecoveryCheckpoint(session_id="s-crash", task_id="t-crash", intent_name="crash_intent")
    watchdog.save_checkpoint(cp)

    recovery_report = watchdog.recover(sm)
    assert recovery_report["recovered"] is True
    assert recovery_report["current_state"] == State.IDLE.value
    assert sm.state == State.IDLE
    assert watchdog.load_checkpoint() is None


def test_watchdog_retry_policy():
    """Verify safe idempotent retry behavior matching 14_ERROR_RECOVERY.md."""
    watchdog = CrashRecoveryWatchdog()

    call_count = 0

    def flaky_action():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Temporary glitch")
        return "Success"

    # Idempotent action retries once and succeeds
    result = watchdog.execute_with_retry(flaky_action, is_safe_idempotent=True)
    assert result == "Success"
    assert call_count == 2

    # Non-idempotent action does not retry
    call_count = 0
    with pytest.raises(RuntimeError):
        watchdog.execute_with_retry(flaky_action, is_safe_idempotent=False)
    assert call_count == 1

    # Action that fails repeatedly does not loop indefinitely (stops after 1 retry)
    call_count = 0

    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent failure")

    with pytest.raises(ValueError):
        watchdog.execute_with_retry(always_fails, is_safe_idempotent=True, max_retries=1)
    assert call_count == 2


def test_watchdog_retry_verify_shortcut():
    """Verify that if post-check succeeds despite transient exception, action is considered successful."""
    watchdog = CrashRecoveryWatchdog()

    def noisy_app_launch():
        raise TimeoutError("UI took 100ms longer than timeout")

    # verify_fn checks if app is actually running
    app_running = True
    result = watchdog.execute_with_retry(
        noisy_app_launch,
        is_safe_idempotent=True,
        verify_fn=lambda: app_running,
    )
    assert result is True
