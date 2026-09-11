"""Action Engine contract and execution manager matching 08_ACTION_ENGINE.md."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field

from jarvis.core.config import JarvisConfig
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.core.logging import AuditLogger
from jarvis.core.state_machine import State, StateMachine
from jarvis.policy.safety import RiskLevel, SafetyPolicy
from jarvis.registry.registry import ToolRegistry


class ActionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    NEEDS_CONFIRMATION = "needs_confirmation"


class ActionRequest(BaseModel):
    """Structured action invocation request matching 08_ACTION_ENGINE.md."""
    action_id: str = Field(default_factory=lambda: f"a-{uuid.uuid4().hex[:6]}")
    session_id: str = "s-default"
    source_event_id: str
    source: str  # "voice" | "gesture" | "keyboard" | "ai_plan"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False


class ActionResult(BaseModel):
    """Structured action execution return matching 08_ACTION_ENGINE.md."""
    action_id: str
    status: ActionStatus
    action: str
    result: Optional[str] = None
    verified: bool = False
    error_code: Optional[ErrorCode] = None


class ActionEngine:
    """Action Engine responsible for safe, validated, and verifiable action execution."""

    def __init__(
        self,
        registry: ToolRegistry,
        state_machine: StateMachine,
        policy: Optional[SafetyPolicy] = None,
        logger: Optional[AuditLogger] = None,
        config: Optional[JarvisConfig] = None,
    ):
        self.registry = registry
        self.state_machine = state_machine
        self.config = config or JarvisConfig()
        self.policy = policy or SafetyPolicy(self.config)
        self.logger = logger

    def execute(self, request: ActionRequest, user_confirmed: bool = False) -> ActionResult:
        """Execute a structured action through validation, policy check, execution, and verification.
        
        Per 08_ACTION_ENGINE.md:
        - Recomputes and validates requires_confirmation deterministically.
        - Transitions state: EXECUTING -> VERIFYING -> IDLE (or WAITING_CONFIRMATION).
        - Returns ActionResult with status, verified, error_code.
        """
        # 1. Lookup tool in registry
        if not self.registry.has_tool(request.action):
            error_code = ErrorCode.E400
            err_msg = f"Tool '{request.action}' not registered"
            if self.logger:
                self.logger.log_action_result(
                    session_id=request.session_id,
                    action_id=request.action_id,
                    tool=request.action,
                    status=ActionStatus.BLOCKED.value,
                    verified=False,
                    result=err_msg,
                    error_code=error_code.value,
                )
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.BLOCKED,
                action=request.action,
                result=err_msg,
                verified=False,
                error_code=error_code,
            )

        tool_decl = self.registry.get_declaration(request.action)

        # 2. Recompute risk & requires_confirmation deterministically (never trust upstream claim)
        policy_decision = self.policy.evaluate(request.action, request.parameters)
        actual_risk = tool_decl.risk_level
        recomputed_requires_confirmation = policy_decision.requires_confirmation

        if self.logger:
            self.logger.log_policy_decision(
                session_id=request.session_id,
                action_id=request.action_id,
                risk=actual_risk.value,
                requires_confirmation=recomputed_requires_confirmation,
                confirmed=user_confirmed if recomputed_requires_confirmation else None,
            )

        # 3. Confirmation check
        if recomputed_requires_confirmation and not user_confirmed:
            # Transition state machine to WAITING_CONFIRMATION
            try:
                self.state_machine.transition_to(State.WAITING_CONFIRMATION, action_id=request.action_id)
            except JarvisError:
                pass

            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.NEEDS_CONFIRMATION,
                action=request.action,
                result=policy_decision.confirmation_prompt,
                verified=False,
                error_code=None,
            )

        # 4. State transition: EXECUTING
        try:
            if self.state_machine.current_state in {State.IDLE, State.LISTENING}:
                self.state_machine.transition_to(State.THINKING)

            self.state_machine.transition_to(
                State.EXECUTING,
                action_id=request.action_id,
                interruptible=(actual_risk != RiskLevel.HIGH),
            )
        except JarvisError as e:
            if self.logger:
                self.logger.log_action_result(
                    session_id=request.session_id,
                    action_id=request.action_id,
                    tool=request.action,
                    status=ActionStatus.BLOCKED.value,
                    verified=False,
                    result=str(e),
                    error_code=e.code.value,
                )
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.BLOCKED,
                action=request.action,
                result=str(e),
                verified=False,
                error_code=e.code,
            )

        # 5. Execution
        handler = self.registry.get_handler(request.action)
        verifier = self.registry.get_verifier(request.action)

        exec_output = None
        try:
            if handler:
                exec_output = handler(**request.parameters)
            else:
                exec_output = f"Executed {request.action}"
        except Exception as ex:
            self.state_machine.transition_to(State.ERROR, action_id=request.action_id)
            self.state_machine.reset_to_idle()
            err_code = ex.code if isinstance(ex, JarvisError) else ErrorCode.E510
            if self.logger:
                self.logger.log_action_result(
                    session_id=request.session_id,
                    action_id=request.action_id,
                    tool=request.action,
                    status=ActionStatus.FAILED.value,
                    verified=False,
                    result=str(ex),
                    error_code=err_code.value,
                )
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.FAILED,
                action=request.action,
                result=f"Execution error: {str(ex)}",
                verified=False,
                error_code=err_code,
            )

        # 6. Verification: State transition VERIFYING
        try:
            self.state_machine.transition_to(State.VERIFYING, action_id=request.action_id)
        except JarvisError:
            pass

        verified = False
        try:
            if verifier:
                verified = bool(verifier(**request.parameters))
            else:
                # If no verifier registered, default to verifying return value exists
                verified = exec_output is not None
        except Exception:
            verified = False

        # Transition back to IDLE
        self.state_machine.reset_to_idle()

        # Rule 5 of 20_DEVELOPER_CONTRACT.md: Never claim a tool executed successfully without a result or verification signal
        if not verified:
            err_code = ErrorCode.E700
            err_msg = f"Action '{request.action}' finished but post-check failed verification"
            if self.logger:
                self.logger.log_action_result(
                    session_id=request.session_id,
                    action_id=request.action_id,
                    tool=request.action,
                    status=ActionStatus.FAILED.value,
                    verified=False,
                    result=err_msg,
                    error_code=err_code.value,
                )
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.FAILED,
                action=request.action,
                result=err_msg,
                verified=False,
                error_code=err_code,
            )

        # Success
        result_msg = str(exec_output) if exec_output else f"{request.action} completed successfully"
        if self.logger:
            self.logger.log_action_result(
                session_id=request.session_id,
                action_id=request.action_id,
                tool=request.action,
                status=ActionStatus.SUCCESS.value,
                verified=True,
                result=result_msg,
                error_code=None,
            )

        return ActionResult(
            action_id=request.action_id,
            status=ActionStatus.SUCCESS,
            action=request.action,
            result=result_msg,
            verified=True,
            error_code=None,
        )
