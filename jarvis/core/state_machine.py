"""Runtime State Machine matching 15_STATE_MACHINE.md."""

from enum import Enum
from typing import Callable, List, Optional
import threading
from jarvis.core.errors import ErrorCode, JarvisError


class State(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


# Allowed state transitions per 15_STATE_MACHINE.md
ALLOWED_TRANSITIONS = {
    State.IDLE: {State.LISTENING, State.THINKING, State.STOPPED, State.ERROR},
    State.LISTENING: {State.THINKING, State.IDLE, State.STOPPED, State.ERROR},
    State.THINKING: {State.EXECUTING, State.WAITING_CONFIRMATION, State.IDLE, State.STOPPED, State.ERROR},
    State.WAITING_CONFIRMATION: {State.EXECUTING, State.IDLE, State.STOPPED, State.ERROR},
    State.EXECUTING: {State.VERIFYING, State.ERROR, State.STOPPED},
    State.VERIFYING: {State.IDLE, State.ERROR, State.STOPPED},
    State.ERROR: {State.IDLE, State.STOPPED},
    State.STOPPED: {State.IDLE},
}


class StateMachine:
    """Thread-safe runtime state machine managing JARVIS execution states."""

    def __init__(self, initial_state: State = State.IDLE):
        self._state = initial_state
        self._lock = threading.RLock()
        self._is_interruptible = True
        self._active_action_id: Optional[str] = None
        self._listeners: List[Callable[[State, State], None]] = []

    @property
    def current_state(self) -> State:
        with self._lock:
            return self._state

    @property
    def state(self) -> State:
        """Alias for current_state."""
        return self.current_state

    @property
    def is_interruptible(self) -> bool:
        with self._lock:
            return self._is_interruptible

    @property
    def active_action_id(self) -> Optional[str]:
        with self._lock:
            return self._active_action_id

    def add_listener(self, listener: Callable[[State, State], None]) -> None:
        """Register a callback for state transitions (old_state, new_state)."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[State, State], None]) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def transition_to(self, new_state: State, *, action_id: Optional[str] = None, interruptible: bool = True) -> State:
        """Transition to a new state if allowed.
        
        Raises JarvisError with E510 if transition is illegal or if non-interruptible action is executing.
        """
        with self._lock:
            # Check emergency stop condition
            if new_state == State.STOPPED:
                return self._force_transition(State.STOPPED, action_id=None, interruptible=True)

            # Check if current action is non-interruptible and another execution is requested
            if not self._is_interruptible and self._state == State.EXECUTING and new_state in {State.EXECUTING, State.THINKING}:
                raise JarvisError(
                    ErrorCode.E510,
                    f"Cannot transition to {new_state.value}: active non-interruptible action {self._active_action_id} is running"
                )

            allowed = ALLOWED_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                raise JarvisError(
                    ErrorCode.E510,
                    f"Illegal state transition from {self._state.value} to {new_state.value}"
                )

            return self._force_transition(new_state, action_id=action_id, interruptible=interruptible)

    def emergency_stop(self) -> State:
        """Emergency stop transition: ANY -> STOPPED."""
        with self._lock:
            return self._force_transition(State.STOPPED, action_id=None, interruptible=True)

    def reset_to_idle(self) -> State:
        """Helper to transition back to IDLE from terminal states."""
        with self._lock:
            if self._state in {State.STOPPED, State.ERROR, State.VERIFYING, State.WAITING_CONFIRMATION}:
                return self.transition_to(State.IDLE)
            elif self._state == State.IDLE:
                return State.IDLE
            else:
                # Force emergency then idle if in dangerous middle state
                self._force_transition(State.STOPPED)
                return self._force_transition(State.IDLE)

    def _force_transition(self, new_state: State, *, action_id: Optional[str] = None, interruptible: bool = True) -> State:
        old_state = self._state
        self._state = new_state
        self._active_action_id = action_id
        self._is_interruptible = interruptible

        for listener in list(self._listeners):
            try:
                listener(old_state, new_state)
            except Exception:
                pass

        return self._state
