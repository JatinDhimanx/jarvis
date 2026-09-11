"""Multi-step Task Planner matching 10_PLANNER.md."""

from typing import Any, Dict, List, Optional
import uuid

from jarvis.brain_layer.models import Plan, PlanState, PlanStep
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.logging import AuditLogger
from jarvis.core.state_machine import StateMachine
from jarvis.execution.action_engine import ActionEngine, ActionRequest, ActionStatus
from jarvis.policy.safety import SafetyPolicy
from jarvis.registry.registry import ToolRegistry


class MultiStepPlanner:
    """Orchestrates multi-step plans with prerequisite verification and safety confirmation."""

    def __init__(
        self,
        registry: ToolRegistry,
        action_engine: ActionEngine,
        policy: Optional[SafetyPolicy] = None,
        logger: Optional[AuditLogger] = None,
    ):
        self.registry = registry
        self.action_engine = action_engine
        self.policy = policy or SafetyPolicy()
        self.logger = logger

    def create_plan(self, raw_goal: str, steps_data: List[Dict[str, Any]]) -> Plan:
        """Create a new plan in DRAFT state."""
        steps = [
            PlanStep(
                action=s["action"],
                parameters=s.get("parameters", {}),
            )
            for s in steps_data
        ]
        return Plan(raw_goal=raw_goal, steps=steps, state=PlanState.DRAFT)

    def validate_plan(self, plan: Plan) -> Plan:
        """Validate plan against ToolRegistry and SafetyPolicy. Transitions DRAFT -> VALIDATED."""
        if not plan.steps:
            raise JarvisError(ErrorCode.E100, "Cannot validate empty plan")

        for step in plan.steps:
            if not self.registry.has_tool(step.action):
                plan.state = PlanState.ABORTED
                raise JarvisError(ErrorCode.E400, f"Plan step requires unregistered tool '{step.action}'")

            # Check policy requirements
            eval_result = self.policy.evaluate(step.action, step.parameters)
            step.requires_confirmation = eval_result.requires_confirmation

        plan.state = PlanState.VALIDATED
        return plan

    def execute_next_step(self, plan: Plan, session_id: str = "s-plan", user_confirmed: bool = False) -> PlanStep:
        """Execute current step in plan. Halts immediately if prerequisite step fails."""
        if plan.state not in {PlanState.VALIDATED, PlanState.EXECUTING, PlanState.WAITING_CONFIRMATION}:
            raise JarvisError(ErrorCode.E510, f"Cannot execute plan in state {plan.state.value}")

        step = plan.current_step
        if not step:
            plan.state = PlanState.COMPLETE
            raise JarvisError(ErrorCode.E510, "No remaining steps in plan")

        plan.state = PlanState.EXECUTING

        # Pre-check confirmation requirement
        if step.requires_confirmation and not user_confirmed:
            plan.state = PlanState.WAITING_CONFIRMATION
            step.status = ActionStatus.NEEDS_CONFIRMATION
            return step

        req = ActionRequest(
            action_id=f"a-{uuid.uuid4().hex[:6]}",
            session_id=session_id,
            source_event_id=f"plan-{plan.plan_id}",
            source="ai_plan",
            action=step.action,
            parameters=step.parameters,
        )

        plan.state = PlanState.VERIFYING
        result = self.action_engine.execute(req, user_confirmed=user_confirmed)

        step.status = result.status
        step.verified = result.verified
        step.result = result.result
        step.error_code = result.error_code.value if result.error_code else None

        # Check prerequisite rule per 10_PLANNER.md: Stop when a prerequisite fails
        if not result.verified or result.status != ActionStatus.SUCCESS:
            plan.state = PlanState.ABORTED
            return step

        # Advance step index
        plan.current_step_index += 1
        if plan.current_step_index >= len(plan.steps):
            plan.state = PlanState.COMPLETE
        else:
            plan.state = PlanState.VALIDATED

        return step
