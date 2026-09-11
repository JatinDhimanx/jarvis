"""Data structures and schemas for AI reasoning and planning matching 10_PLANNER.md."""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from jarvis.execution.action_engine import ActionStatus


class PlanState(str, Enum):
    """Plan states matching 10_PLANNER.md."""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"


class PlanStep(BaseModel):
    """Single step in a multi-step execution plan."""
    step_id: str = Field(default_factory=lambda: f"step-{uuid.uuid4().hex[:4]}")
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: ActionStatus = ActionStatus.SUCCESS
    verified: bool = False
    result: Optional[str] = None
    error_code: Optional[str] = None
    requires_confirmation: bool = False


class Plan(BaseModel):
    """Multi-step plan container matching 10_PLANNER.md."""
    plan_id: str = Field(default_factory=lambda: f"p-{uuid.uuid4().hex[:6]}")
    raw_goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    state: PlanState = PlanState.DRAFT
    current_step_index: int = 0

    @property
    def is_complete(self) -> bool:
        return self.state == PlanState.COMPLETE

    @property
    def current_step(self) -> Optional[PlanStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None


class LLMResponse(BaseModel):
    """Structured AI output - models never emit raw OS commands."""
    intent: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    suggested_steps: List[Dict[str, Any]] = Field(default_factory=list)
    reply_text: Optional[str] = None
    is_online: bool = False
