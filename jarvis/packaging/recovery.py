"""Crash recovery watchdog, checkpointing, and retry policy matching 14_ERROR_RECOVERY.md."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.state_machine import State, StateMachine


class RecoveryCheckpoint(BaseModel):
    """Execution checkpoint saved prior to risky or multi-step executions."""
    session_id: str
    task_id: str
    intent_name: str
    step_index: int = 0
    total_steps: int = 1
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CrashRecoveryWatchdog:
    """Watchdog that manages execution checkpoints, crash recovery, and idempotent retries."""

    def __init__(self, checkpoint_path: Optional[str | Path] = None):
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else Path("logs/recovery_checkpoint.json")

    def save_checkpoint(self, checkpoint: RecoveryCheckpoint) -> None:
        """Write current execution checkpoint to disk."""
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.model_dump(), f, indent=2)

    def load_checkpoint(self) -> Optional[RecoveryCheckpoint]:
        """Load pending checkpoint if one exists from an interrupted session."""
        if not self.checkpoint_path.exists():
            return None
        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return RecoveryCheckpoint.model_validate(data)
        except Exception:
            return None

    def clear_checkpoint(self) -> None:
        """Clear checkpoint upon clean execution completion."""
        if self.checkpoint_path.exists():
            try:
                self.checkpoint_path.unlink()
            except OSError:
                pass

    def recover(self, state_machine: StateMachine) -> Dict[str, Any]:
        """Inspect state and checkpoint; safely restore state machine to IDLE and return status."""
        interrupted = self.load_checkpoint()
        was_stuck = state_machine.state in (State.EXECUTING, State.WAITING_CONFIRMATION, State.VERIFYING)
        prev_state = state_machine.state.value

        # Reset state machine to IDLE if stuck or interrupted
        if was_stuck or state_machine.state != State.IDLE:
            state_machine.reset_to_idle()

        recovery_summary = {
            "recovered": was_stuck or (interrupted is not None),
            "previous_state": state_machine.state.value if not was_stuck else "STUCK",
            "interrupted_checkpoint": interrupted.model_dump() if interrupted else None,
            "current_state": State.IDLE.value,
        }

        # Clear the interrupted checkpoint after recording recovery
        self.clear_checkpoint()
        return recovery_summary

    def execute_with_retry(
        self,
        action_fn: Callable[[], Any],
        is_safe_idempotent: bool,
        verify_fn: Optional[Callable[[], bool]] = None,
        max_retries: int = 1,
    ) -> Any:
        """
        Execute an action with safe retry policy matching 14_ERROR_RECOVERY.md.
        1. Detect failure.
        2. Stop dependent actions.
        3. Retry only if safe and idempotent (max 1 retry).
        4. Re-check state.
        5. Never loop indefinitely.
        """
        try:
            return action_fn()
        except Exception as first_err:
            # Check whether action actually succeeded despite exception
            if verify_fn:
                try:
                    if verify_fn():
                        return True
                except Exception:
                    pass

            # If not safe and idempotent, do not retry
            if not is_safe_idempotent or max_retries <= 0:
                raise first_err

            # Safe and idempotent: retry once
            try:
                result = action_fn()
                if verify_fn and not verify_fn():
                    raise JarvisError(ErrorCode.E700, "Verification failed after retry.")
                return result
            except Exception as second_err:
                raise second_err
