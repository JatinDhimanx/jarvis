"""Workflow templates and macro routines matching 03_CONTEXT_AND_MEMORY.md and 10_PLANNER.md."""

from typing import Any, Dict, List, Optional

from jarvis.brain_layer.models import Plan
from jarvis.brain_layer.planner import MultiStepPlanner
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.memory.models import MemoryCategory
from jarvis.memory.store import MemoryStore


class WorkflowManager:
    """Manages reusable multi-step task workflows saved in persistent memory."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()

    def save_workflow(self, name: str, steps: List[Dict[str, Any]]) -> str:
        """Save a validated sequence of plan steps as a named reusable workflow."""
        clean_name = name.strip().lower()
        if not clean_name:
            raise JarvisError(ErrorCode.E100, "Workflow name cannot be empty")
        if not steps:
            raise JarvisError(ErrorCode.E100, "Workflow steps cannot be empty")

        key = f"workflow:{clean_name}"
        self.store.write(key=key, value=steps, category=MemoryCategory.WORKFLOW)
        return f"Workflow '{clean_name}' saved with {len(steps)} steps."

    def load_workflow(self, name: str) -> List[Dict[str, Any]]:
        """Retrieve steps of a saved workflow."""
        clean_name = name.strip().lower()
        key = f"workflow:{clean_name}"
        item = self.store.read(key)
        if not item:
            raise JarvisError(ErrorCode.E400, f"Workflow '{clean_name}' not found in memory")
        return item.value

    def create_plan_from_workflow(self, name: str, planner: MultiStepPlanner) -> Plan:
        """Synthesize a MultiStepPlanner Plan from a saved workflow template."""
        steps = self.load_workflow(name)
        plan = planner.create_plan(raw_goal=f"Execute workflow: {name}", steps_data=steps)
        return planner.validate_plan(plan)
