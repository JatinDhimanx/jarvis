"""HUD state and visual feedback manager matching 01_SYSTEM_ARCHITECTURE.md and 15_STATE_MACHINE.md."""

from collections import deque
from datetime import datetime, timezone
import threading
from typing import Any, Callable, Dict, List, Optional

from jarvis.core.state_machine import State


class HUDStateManager:
    """Thread-safe telemetry and visual feedback manager for JARVIS HUD."""

    def __init__(self, max_recent_actions: int = 10):
        self._lock = threading.Lock()
        self.max_recent_actions = max_recent_actions

        self.current_state: State = State.IDLE
        self.camera_active: bool = False
        self.mic_active: bool = False
        self.last_event: Optional[Dict[str, Any]] = None
        self.active_plan: Optional[Dict[str, Any]] = None
        self.pending_confirmation: Optional[str] = None
        self.system_status: Dict[str, Any] = {
            "volume": 50,
            "brightness": 100,
            "network_online": True,
            "memory_items": 0,
        }
        self.recent_actions: deque[Dict[str, Any]] = deque(maxlen=max_recent_actions)
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def set_state(self, state: State, pending_prompt: Optional[str] = None) -> None:
        """Update active state machine state."""
        with self._lock:
            self.current_state = state
            if state == State.WAITING_CONFIRMATION:
                self.pending_confirmation = pending_prompt
            elif state != State.WAITING_CONFIRMATION:
                self.pending_confirmation = None
        self._notify_listeners()

    def set_privacy_indicators(self, camera: Optional[bool] = None, mic: Optional[bool] = None) -> None:
        """Update camera and microphone hardware active indicators per privacy rule."""
        with self._lock:
            if camera is not None:
                self.camera_active = camera
            if mic is not None:
                self.mic_active = mic
        self._notify_listeners()

    def record_input_event(self, channel: str, payload: str, confidence: float, intent: Optional[str] = None) -> None:
        """Record newest perception event."""
        with self._lock:
            self.last_event = {
                "channel": channel,
                "payload": payload,
                "confidence": round(confidence, 2),
                "intent": intent or "DETECTING",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        self._notify_listeners()

    def update_plan_progress(self, plan_id: str, current_step: int, total_steps: int, current_action: str) -> None:
        """Update multi-step plan progress."""
        with self._lock:
            self.active_plan = {
                "plan_id": plan_id,
                "current_step": current_step,
                "total_steps": total_steps,
                "current_action": current_action,
            }
        self._notify_listeners()

    def clear_plan_progress(self) -> None:
        with self._lock:
            self.active_plan = None
        self._notify_listeners()

    def update_system_status(self, **kwargs: Any) -> None:
        """Update system dashboard indicators."""
        with self._lock:
            self.system_status.update(kwargs)
        self._notify_listeners()

    def record_action_executed(self, action: str, status: str, verified: bool, duration_ms: float = 0.0) -> None:
        """Append executed action with verification badge."""
        with self._lock:
            self.recent_actions.appendleft({
                "action": action,
                "status": status,
                "verified": verified,
                "duration_ms": round(duration_ms, 1),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })
        self._notify_listeners()

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to telemetry updates."""
        self._listeners.append(callback)

    def _notify_listeners(self) -> None:
        state_dict = self.to_dict()
        for cb in self._listeners:
            try:
                cb(state_dict)
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        """Serialize current HUD state to dictionary."""
        with self._lock:
            return {
                "state": self.current_state.value,
                "camera_active": self.camera_active,
                "mic_active": self.mic_active,
                "last_event": self.last_event,
                "active_plan": self.active_plan,
                "pending_confirmation": self.pending_confirmation,
                "system_status": dict(self.system_status),
                "recent_actions": list(self.recent_actions),
            }
