"""Context and reference resolution matching 03_CONTEXT_AND_MEMORY.md."""

from collections import deque
from typing import Any, Deque, Dict, List, Optional
from jarvis.brain_layer.models import Plan


class ContextManager:
    """Manages L0, L1, and L2 context layers and pronoun reference resolution."""

    def __init__(self, history_limit: int = 10):
        # L0: Latest input event
        self.l0_latest_input: Optional[Dict[str, Any]] = None

        # L1: Current task context
        self.l1_active_plan: Optional[Plan] = None
        self.l1_task_variables: Dict[str, Any] = {}

        # L2: Recent conversational history (turns)
        self.l2_turns: Deque[Dict[str, Any]] = deque(maxlen=history_limit)

        # Entity tracking for reference resolution
        self.last_referenced_app: Optional[str] = None
        self.last_referenced_file: Optional[str] = None
        self.last_reversible_action: Optional[Dict[str, Any]] = None

    def update_l0(self, input_event_dict: Dict[str, Any]) -> None:
        """Update L0 with newest input event."""
        self.l0_latest_input = input_event_dict

    def start_l1_task(self, plan: Plan) -> None:
        """Initialize L1 task context with active plan."""
        self.l1_active_plan = plan
        self.l1_task_variables.clear()

    def clear_l1_task(self) -> None:
        """Expire temporary task context when task ends per 03_CONTEXT_AND_MEMORY.md."""
        self.l1_active_plan = None
        self.l1_task_variables.clear()

    def record_turn(self, role: str, text: str, action: Optional[str] = None, entities: Optional[Dict[str, Any]] = None) -> None:
        """Record turn into L2 conversation context and update entity trackers."""
        entities = entities or {}
        if "app_name" in entities:
            self.last_referenced_app = entities["app_name"]
        if "path" in entities:
            self.last_referenced_file = entities["path"]

        self.l2_turns.append({
            "role": role,
            "text": text,
            "action": action,
            "entities": entities,
        })

    def record_action_executed(self, action_name: str, parameters: Dict[str, Any], reversible: bool = True) -> None:
        """Track last reversible action for 'do it again' commands."""
        if reversible:
            self.last_reversible_action = {"action": action_name, "parameters": parameters}

    def resolve_reference(self, pronoun_or_phrase: str) -> Optional[Dict[str, Any]]:
        """Resolve pronouns like 'it', 'that', 'this' to known active entities."""
        phrase = pronoun_or_phrase.lower().strip()

        if "close it" in phrase or phrase == "it":
            if self.last_referenced_app:
                return {"action": "close_app", "entities": {"app_name": self.last_referenced_app}}

        if "delete that" in phrase or "open that" in phrase or phrase == "that":
            if self.last_referenced_file:
                act = "delete_file" if "delete" in phrase else "open_file"
                return {"action": act, "entities": {"path": self.last_referenced_file}}

        if "do it again" in phrase:
            if self.last_reversible_action:
                return self.last_reversible_action

        return None
