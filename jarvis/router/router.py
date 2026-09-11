"""Command Router pipeline and multi-modal conflict resolution matching 02_COMMAND_ROUTER.md."""

import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.logging import AuditLogger
from jarvis.router.intents import (
    ActionGroup,
    Intent,
    INTENT_TO_ACTION_GROUP,
    INTENT_TO_ALLOWED_ACTIONS,
)


class InputEvent(BaseModel):
    """Normalized input event from perception layer."""
    event_id: str
    channel: str  # "voice" | "gesture" | "keyboard" | "ai_plan"
    raw_payload: str  # text or gesture name
    confidence: float = 1.0
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    entities: Dict[str, Any] = Field(default_factory=dict)
    parsed_intent: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class RouteDecision(BaseModel):
    """Structured routing outcome."""
    intent: Intent
    action_group: ActionGroup
    action: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    is_emergency: bool = False
    source_event_id: str
    source_channel: str
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None


EMERGENCY_WORDS = {"stop", "cancel", "emergency stop", "halt", "abort"}
EMERGENCY_GESTURES = {"STOP", "STOP_OR_PAUSE", "FIST"}


class CommandRouter:
    """Deterministic command router and multi-modal conflict arbiter."""

    def __init__(self, logger: Optional[AuditLogger] = None, debounce_window_ms: int = 500):
        self.logger = logger
        self.debounce_window_ms = debounce_window_ms

    def normalize_text(self, text: str) -> str:
        """Normalize raw input text."""
        cleaned = text.strip().lower()
        # Remove wake word prefixes like "jarvis, " or "jarvis "
        cleaned = re.sub(r"^(hey\s+)?jarvis[,:\s]*", "", cleaned).strip()
        # Remove trailing punctuation
        cleaned = re.sub(r"[.?!]+$", "", cleaned).strip()
        return cleaned

    def detect_intent(self, event: InputEvent) -> Tuple[Intent, Optional[str], Dict[str, Any], bool]:
        """Detect intent, action, and entities deterministically from input event.
        
        Returns: (intent, action_name, entities, is_emergency)
        """
        raw = event.raw_payload.strip()

        # 1. Gesture channel detection
        if event.channel == "gesture":
            gesture_name = raw.upper()
            if gesture_name in EMERGENCY_GESTURES:
                return Intent.SYSTEM_CONTROL, "stop", {}, True
            elif gesture_name in {"SELECT_OR_CLICK", "PINCH"}:
                return Intent.MOUSE_CONTROL, "click", {}, False
            elif gesture_name in {"SCROLL_MODE", "TWO_FINGERS"}:
                return Intent.MOUSE_CONTROL, "scroll", {}, False
            elif gesture_name in {"NEXT", "SWIPE_RIGHT"}:
                return Intent.MEDIA_CONTROL, "next_track", {}, False
            elif gesture_name in {"PREVIOUS", "SWIPE_LEFT"}:
                return Intent.MEDIA_CONTROL, "previous_track", {}, False
            elif gesture_name == "CONFIRM":
                return Intent.STATUS, "confirm", {}, False
            elif gesture_name == "CANCEL":
                return Intent.SYSTEM_CONTROL, "cancel", {}, True
            return Intent.UNKNOWN, None, {}, False

        # Check explicit parsed_intent if provided
        if event.parsed_intent:
            params = dict(event.parameters) if event.parameters else dict(event.entities)
            for it, actions in INTENT_TO_ALLOWED_ACTIONS.items():
                if event.parsed_intent in actions:
                    return it, event.parsed_intent, params, False

        # 2. Text / Voice channel detection
        normalized = self.normalize_text(raw)

        # Check emergency words
        if normalized in EMERGENCY_WORDS or any(normalized == w for w in EMERGENCY_WORDS):
            return Intent.SYSTEM_CONTROL, "stop", {}, True

        # Ambiguous pronoun references (per 02_COMMAND_ROUTER.md rule 2 & 19_COMMAND_EXAMPLES.md)
        if normalized in {"open that", "close it", "search this", "do it again"}:
            return Intent.UNKNOWN, None, {"ambiguous_pronoun": normalized}, False

        # Volume controls
        vol_match = re.search(r"^(?:set|change)\s+volume\s+(?:to\s+)?(\d+)(?:%)?$", normalized)
        if vol_match:
            val = int(vol_match.group(1))
            return Intent.SYSTEM_CONTROL, "set_volume", {"value": val}, False

        if normalized in {"mute", "mute audio", "mute sound"}:
            return Intent.SYSTEM_CONTROL, "mute", {"state": True}, False
        if normalized in {"unmute", "unmute audio", "unmute sound"}:
            return Intent.SYSTEM_CONTROL, "mute", {"state": False}, False

        # Brightness controls
        bright_match = re.search(r"^(?:set|change)\s+brightness\s+(?:to\s+)?(\d+)(?:%)?$", normalized)
        if bright_match:
            val = int(bright_match.group(1))
            return Intent.SYSTEM_CONTROL, "set_brightness", {"value": val}, False

        # System lock/shutdown
        if normalized in {"lock screen", "lock the screen", "lock computer"}:
            return Intent.SYSTEM_CONTROL, "lock_screen", {}, False
        if normalized in {"turn off the computer", "shut down", "shutdown", "power off"}:
            return Intent.SYSTEM_CONTROL, "shutdown", {}, False

        # App controls
        open_app_match = re.search(r"^open\s+(.+)$", raw, re.IGNORECASE)
        if open_app_match:
            app_name = open_app_match.group(1).strip()
            # If it's "open Chrome and search for ...", that's a composite/multi-step intent handled by planner/web search
            if " and search " in app_name.lower():
                parts = re.split(r"\s+and\s+search\s+(?:for\s+)?", app_name, flags=re.IGNORECASE)
                if len(parts) == 2:
                    return Intent.WEB_SEARCH, "search_web", {"application": parts[0].strip(), "query": parts[1].strip()}, False
            return Intent.APP_CONTROL, "open_app", {"app_name": app_name}, False

        close_app_match = re.search(r"^close\s+(.+)$", raw, re.IGNORECASE)
        if close_app_match:
            app_name = close_app_match.group(1).strip()
            return Intent.APP_CONTROL, "close_app", {"app_name": app_name}, False

        restart_app_match = re.search(r"^restart\s+(.+)$", raw, re.IGNORECASE)
        if restart_app_match:
            app_name = restart_app_match.group(1).strip()
            return Intent.APP_CONTROL, "restart_app", {"app_name": app_name}, False

        # Media controls
        if normalized in {"play", "pause", "play/pause", "play pause"}:
            return Intent.MEDIA_CONTROL, "play_pause", {}, False
        if normalized in {"next track", "next song", "skip track", "skip song"}:
            return Intent.MEDIA_CONTROL, "next_track", {}, False
        if normalized in {"previous track", "previous song"}:
            return Intent.MEDIA_CONTROL, "previous_track", {}, False

        # Web search & external APIs
        weather_match = re.search(r"^(?:(?:what is the\s+)?weather\s+(?:in|for)?\s*)(.+)$", normalized)
        if weather_match:
            loc = weather_match.group(1).strip()
            return Intent.WEB_SEARCH, "get_weather", {"location": loc}, False

        search_match = re.search(r"^(?:search\s+(?:the\s+web\s+for|for)?\s*)(.+)$", normalized)
        if search_match:
            query = search_match.group(1).strip()
            return Intent.WEB_SEARCH, "search_web", {"query": query}, False

        # Web browser automation
        browser_url_match = re.search(r"^(?:open\s+url|navigate\s+to|go\s+to)\s+(https?://\S+)$", raw, re.IGNORECASE)
        if browser_url_match:
            target_url = browser_url_match.group(1).strip()
            return Intent.WEB_AUTOMATION, "open_browser_url", {"url": target_url}, False

        # File operations
        delete_file_match = re.search(r"^delete\s+(?:file\s+)?(.+)$", normalized)
        if delete_file_match:
            filename = delete_file_match.group(1).strip()
            return Intent.FILE_OPERATION, "delete_file", {"path": filename}, False

        # Memory operations (03_CONTEXT_AND_MEMORY.md)
        remember_match = re.search(r"^remember\s+(?:that\s+)?(?:my\s+)?(.+?)\s+(?:is|=|as)\s+(.+)$", raw, re.IGNORECASE)
        if remember_match:
            k = remember_match.group(1).strip()
            v = remember_match.group(2).strip()
            return Intent.MEMORY, "write_memory", {"key": k, "value": v, "category": "preference"}, False

        forget_match = re.search(r"^forget\s+(?:that\s+)?(?:my\s+)?(.+)$", raw, re.IGNORECASE)
        if forget_match:
            k = forget_match.group(1).strip()
            return Intent.MEMORY, "forget_memory", {"key": k}, False

        recall_match = re.search(r"^(?:what\s+is\s+my|recall|get\s+memory)\s+(.+)$", raw, re.IGNORECASE)
        if recall_match:
            k = recall_match.group(1).strip()
            return Intent.MEMORY, "read_memory", {"key": k}, False

        # Status / health query
        if normalized in {"status", "system status", "health check", "ping"}:
            return Intent.STATUS, "get_status", {}, False

        # Ambiguous pronoun references
        if normalized in {"open that", "close it", "search this"}:
            return Intent.UNKNOWN, None, {"ambiguous_pronoun": normalized}, False

        # Fallback to AI_QUERY if natural language query, or UNKNOWN
        if any(normalized.startswith(q) for q in ["what is", "who is", "how to", "why is", "tell me"]):
            return Intent.AI_QUERY, None, {"query": normalized}, False

        return Intent.UNKNOWN, None, {"raw": raw}, False

    def resolve_multimodal(self, events: List[InputEvent], session_id: str = "s-default") -> InputEvent:
        """Resolve multi-modal conflict when multiple events arrive in debounce window.
        
        Rules from 02_COMMAND_ROUTER.md:
        1. Emergency signal always wins (regardless of source).
        2. Within debounce window: higher-confidence / more recent input wins; discard the other.
        3. Same intent: execute once, not twice.
        4. Log which channel won.
        """
        if not events:
            raise JarvisError(ErrorCode.E100, "No events provided to resolve")
        if len(events) == 1:
            return events[0]

        # Filter events within debounce window of the latest event
        latest_ts = max(e.timestamp_ms for e in events)
        window_events = [e for e in events if (latest_ts - e.timestamp_ms) <= self.debounce_window_ms]
        if not window_events:
            window_events = events

        # Rule 1: Emergency check
        for e in window_events:
            _, _, _, is_emergency = self.detect_intent(e)
            if is_emergency:
                if self.logger:
                    other_channels = [o.channel for o in window_events if o.event_id != e.event_id]
                    self.logger.log_channel_arbitration(
                        session_id=session_id,
                        winning_channel=e.channel,
                        discarded_channel=",".join(other_channels),
                        reason="Emergency stop priority",
                    )
                return e

        # Rule 3: Check if both inputs resolve to same intent and action
        intents_and_actions = [self.detect_intent(e) for e in window_events]
        first_intent = (intents_and_actions[0][0], intents_and_actions[0][1])
        if all((ia[0], ia[1]) == first_intent for ia in intents_and_actions):
            # Same intent deduplicated: pick the higher confidence
            winner = max(window_events, key=lambda x: (x.confidence, x.timestamp_ms))
            if self.logger:
                discarded = [o.channel for o in window_events if o.event_id != winner.event_id]
                self.logger.log_channel_arbitration(
                    session_id=session_id,
                    winning_channel=winner.channel,
                    discarded_channel=",".join(discarded),
                    reason="Deduplicated identical intents; selected highest confidence",
                )
            return winner

        # Rule 2: Non-emergency different intents -> highest confidence then most recent
        winner = max(window_events, key=lambda x: (x.confidence, x.timestamp_ms))
        if self.logger:
            discarded = [o.channel for o in window_events if o.event_id != winner.event_id]
            self.logger.log_channel_arbitration(
                session_id=session_id,
                winning_channel=winner.channel,
                discarded_channel=",".join(discarded),
                reason=f"Debounce arbitration: confidence={winner.confidence}, recency={winner.timestamp_ms}",
            )
        return winner

    def route(self, event: InputEvent) -> RouteDecision:
        """Route normalized input event to structured decision."""
        intent, action_name, entities, is_emergency = self.detect_intent(event)
        action_group = INTENT_TO_ACTION_GROUP.get(intent, ActionGroup.NONE)

        # Validate action against allowed table
        if action_name:
            allowed = INTENT_TO_ALLOWED_ACTIONS.get(intent, set())
            if action_name not in allowed:
                # Per 02_COMMAND_ROUTER.md: Never fabricate an action not listed
                intent = Intent.UNKNOWN
                action_group = ActionGroup.NONE
                action_name = None

        requires_clarification = False
        clarification_prompt = None

        if intent == Intent.UNKNOWN:
            requires_clarification = True
            if entities.get("ambiguous_pronoun"):
                clarification_prompt = f"Which item did you mean by '{entities['ambiguous_pronoun']}'?"
            else:
                clarification_prompt = "I didn't quite understand that command. Could you clarify?"

        return RouteDecision(
            intent=intent,
            action_group=action_group,
            action=action_name,
            entities=entities,
            is_emergency=is_emergency,
            source_event_id=event.event_id,
            source_channel=event.channel,
            requires_clarification=requires_clarification,
            clarification_prompt=clarification_prompt,
        )
