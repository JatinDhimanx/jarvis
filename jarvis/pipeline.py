"""End-to-end pipeline connecting Input -> Router -> Policy -> Execution -> Verification -> Logging -> Response."""

from typing import Any, Dict, Optional
import uuid

from jarvis.core.config import JarvisConfig, load_config
from jarvis.core.errors import ErrorCode
from jarvis.core.logging import AuditLogger
from jarvis.core.state_machine import State, StateMachine
from jarvis.execution.action_engine import (
    ActionEngine,
    ActionRequest,
    ActionResult,
    ActionStatus,
)
from jarvis.brain_layer.context import ContextManager
from jarvis.brain_layer.hybrid_manager import HybridBrainManager
from jarvis.brain_layer.planner import MultiStepPlanner
from jarvis.execution.actions.application import register_application_tools, VirtualAppManager
from jarvis.execution.actions.api_client import register_api_tools, ExternalAPIClient
from jarvis.execution.actions.browser import register_browser_tools, VirtualBrowser
from jarvis.execution.actions.files import register_file_tools, VirtualFileManager
from jarvis.execution.actions.input import register_input_tools, VirtualInputBackend
from jarvis.execution.actions.media import register_media_tools, VirtualMediaManager
from jarvis.execution.actions.memory import register_memory_tools, MemoryActionManager
from jarvis.execution.actions.system import register_system_tools, VirtualSystemBackend
from jarvis.execution.actions.web_search import register_web_search_tools, WebSearchBackend
from jarvis.execution.actions.window import register_window_tools, VirtualWindowManager
from jarvis.memory.store import MemoryStore
from jarvis.memory.workflows import WorkflowManager
from jarvis.packaging.recovery import CrashRecoveryWatchdog, RecoveryCheckpoint
from jarvis.packaging.settings import SettingsManager, register_settings_tools
from jarvis.perception.gesture.models import GestureEvent
from jarvis.policy.safety import SafetyPolicy
from jarvis.registry.registry import ToolRegistry
from jarvis.response.formatter import ResponseFormatter
from jarvis.router.intents import Intent
from jarvis.router.router import CommandRouter, InputEvent
from jarvis.ui.hud_state import HUDStateManager


class ExecutionPipeline:
    """Coordinates the full vertical slice of JARVIS execution."""

    def __init__(
        self,
        config: Optional[JarvisConfig] = None,
        system_backend: Optional[VirtualSystemBackend] = None,
        app_manager: Optional[VirtualAppManager] = None,
        input_backend: Optional[VirtualInputBackend] = None,
        window_manager: Optional[VirtualWindowManager] = None,
        media_manager: Optional[VirtualMediaManager] = None,
        file_manager: Optional[VirtualFileManager] = None,
        web_search_backend: Optional[WebSearchBackend] = None,
        browser: Optional[VirtualBrowser] = None,
        api_client: Optional[ExternalAPIClient] = None,
        memory_store: Optional[MemoryStore] = None,
        memory_manager: Optional[MemoryActionManager] = None,
        hud_state: Optional[HUDStateManager] = None,
        tts: Optional[Any] = None,
        settings_manager: Optional[SettingsManager] = None,
        recovery_watchdog: Optional[CrashRecoveryWatchdog] = None,
    ):
        self.config = config or load_config()
        self.session_id = f"{self.config.logging.session_id_prefix}{uuid.uuid4().hex[:6]}"
        self.state_machine = StateMachine(State.IDLE)
        self.logger = AuditLogger(self.config)
        self.router = CommandRouter(logger=self.logger, debounce_window_ms=self.config.vision.cooldown_ms)
        self.policy = SafetyPolicy(self.config)
        self.registry = ToolRegistry()
        self.context = ContextManager()
        self.hud_state = hud_state or HUDStateManager()

        # Packaging & settings & recovery
        self.settings_manager = settings_manager or SettingsManager()
        self.recovery_watchdog = recovery_watchdog or CrashRecoveryWatchdog()
        self.recovery_watchdog.recover(self.state_machine)

        # Register tools & storage
        self.system_backend = system_backend or VirtualSystemBackend()
        self.app_manager = app_manager or VirtualAppManager()
        self.input_backend = input_backend or VirtualInputBackend()
        self.window_manager = window_manager or VirtualWindowManager()
        self.media_manager = media_manager or VirtualMediaManager()
        self.file_manager = file_manager or VirtualFileManager()
        self.web_search_backend = web_search_backend or WebSearchBackend()
        self.browser = browser or VirtualBrowser()
        self.api_client = api_client or ExternalAPIClient()
        self.memory_store = memory_store or MemoryStore()
        self.memory_manager = memory_manager or MemoryActionManager(self.memory_store)
        self.workflow_manager = WorkflowManager(self.memory_store)
        self.tts = tts

        # Initial HUD telemetry
        self.hud_state.update_system_status(
            volume=self.system_backend.volume,
            brightness=self.system_backend.brightness,
            network_online=True,
            memory_items=len(self.memory_store._items),
        )

        register_system_tools(self.registry, self.system_backend)
        register_application_tools(self.registry, self.app_manager)
        register_input_tools(self.registry, self.input_backend)
        register_window_tools(self.registry, self.window_manager)
        register_media_tools(self.registry, self.media_manager)
        register_file_tools(self.registry, self.file_manager)
        register_web_search_tools(self.registry, self.web_search_backend)
        register_browser_tools(self.registry, self.browser)
        register_api_tools(self.registry, self.api_client)
        register_memory_tools(self.registry, self.memory_manager)
        register_settings_tools(self.registry, self.settings_manager)

        self.action_engine = ActionEngine(
            registry=self.registry,
            state_machine=self.state_machine,
            policy=self.policy,
            logger=self.logger,
            config=self.config,
        )

        self.planner = MultiStepPlanner(
            registry=self.registry,
            action_engine=self.action_engine,
            policy=self.policy,
            logger=self.logger,
        )

        self.hybrid_brain = HybridBrainManager(
            config=self.config,
            logger=self.logger,
        )

        self._pending_request: Optional[ActionRequest] = None

    def trigger_emergency_stop(self) -> None:
        """Immediately abort any active execution and force STOPPED state."""
        self.state_machine.emergency_stop()
        self.hud_state.set_state(State.STOPPED)
        self._pending_request = None

    def process_gesture(self, gesture_event: GestureEvent, user_confirmed: bool = False) -> Dict[str, Any]:
        """Convenience method to route a GestureEvent through the execution pipeline."""
        input_event = InputEvent(
            event_id=f"g-{hex(gesture_event.timestamp)[-4:]}",
            channel="gesture",
            raw_payload=gesture_event.name,
            confidence=gesture_event.confidence,
            timestamp_ms=gesture_event.timestamp,
        )
        return self.process_event(input_event, user_confirmed=user_confirmed)

    def process_voice(self, voice_event: Any, user_confirmed: bool = False) -> Dict[str, Any]:
        """Convenience method to route a VoiceEvent and speak the response."""
        input_event = InputEvent(
            event_id=f"v-{uuid.uuid4().hex[:6]}",
            channel="voice",
            raw_payload=voice_event.transcript,
            confidence=voice_event.confidence,
            timestamp_ms=voice_event.timestamp_ms,
        )
        result = self.process_event(input_event, user_confirmed=user_confirmed)
        if self.tts and result.get("response_text"):
            self.tts.speak(result["response_text"])
        return result

    def process_event(self, event: InputEvent, user_confirmed: bool = False) -> Dict[str, Any]:
        """Process an input event through the entire pipeline.
        
        Returns:
            Dict with action_id, status, response_text, state, verified, error_code.
        """
        # 1. State transition: IDLE -> LISTENING -> THINKING
        # Auto-recover from terminal states (STOPPED / ERROR) so web commands
        # never crash with an illegal transition.
        if self.state_machine.current_state in {State.STOPPED, State.ERROR}:
            self.state_machine.reset_to_idle()
            self.hud_state.set_state(State.IDLE)

        if self.state_machine.current_state == State.IDLE:
            self.state_machine.transition_to(State.LISTENING)
            self.hud_state.set_state(State.LISTENING)

        # Log input respecting privacy
        self.logger.log_input(
            session_id=self.session_id,
            source=event.channel,
            source_event_id=event.event_id,
            raw_text=event.raw_payload,
            confidence=event.confidence,
        )

        self.state_machine.transition_to(State.THINKING)
        self.hud_state.set_state(State.THINKING)

        # 2. Routing
        decision = self.router.route(event)
        self.hud_state.record_input_event(
            channel=event.channel,
            payload=event.raw_payload,
            confidence=event.confidence,
            intent=decision.intent.value,
        )

        # Handle emergency stop immediately from router
        if decision.is_emergency:
            self.state_machine.emergency_stop()
            self._pending_request = None
            stop_response = ResponseFormatter.format_emergency_stop()
            self.state_machine.reset_to_idle()
            return {
                "action_id": None,
                "status": ActionStatus.CANCELLED.value,
                "response_text": stop_response,
                "state": self.state_machine.current_state.value,
                "verified": True,
                "error_code": None,
            }

        # Update L0 context
        self.context.update_l0(event.model_dump())

        # Check for ambiguous / unknown - attempt reference resolution via context
        if decision.requires_clarification:
            resolved = self.context.resolve_reference(event.raw_payload)
            if resolved:
                decision.action = resolved.get("action")
                decision.entities = resolved.get("entities", resolved.get("parameters", {}))
                decision.requires_clarification = False
            else:
                self.state_machine.reset_to_idle()
                return {
                    "action_id": None,
                    "status": ActionStatus.BLOCKED.value,
                    "response_text": decision.clarification_prompt,
                    "state": self.state_machine.current_state.value,
                    "verified": False,
                    "error_code": ErrorCode.E300.value,
                }

        # Handle AI_QUERY / Multi-step / Reasoning
        if decision.intent == Intent.AI_QUERY or not decision.action:
            llm_resp = self.hybrid_brain.process(event.raw_payload)
            if llm_resp.suggested_steps:
                plan = self.planner.create_plan(event.raw_payload, llm_resp.suggested_steps)
                self.planner.validate_plan(plan)
                self.context.start_l1_task(plan)
                step = self.planner.execute_next_step(plan, session_id=self.session_id, user_confirmed=user_confirmed)

                if plan.is_complete:
                    self.context.clear_l1_task()

                self.state_machine.reset_to_idle()
                return {
                    "action_id": step.step_id,
                    "status": step.status.value,
                    "response_text": step.result or f"Executed step: {step.action}",
                    "state": self.state_machine.current_state.value,
                    "verified": step.verified,
                    "error_code": step.error_code,
                }

            self.state_machine.reset_to_idle()
            return {
                "action_id": None,
                "status": ActionStatus.SUCCESS.value,
                "response_text": llm_resp.reply_text or "Understood.",
                "state": self.state_machine.current_state.value,
                "verified": True,
                "error_code": None,
            }

        # 3. Create ActionRequest
        action_id = f"a-{uuid.uuid4().hex[:6]}"
        self.logger.log_intent(
            session_id=self.session_id,
            action_id=action_id,
            source=event.channel,
            intent=decision.intent.value,
            entities=decision.entities,
        )

        # Pre-evaluation of policy for request packaging
        policy_eval = self.policy.evaluate(decision.action, decision.entities)

        request = ActionRequest(
            action_id=action_id,
            session_id=self.session_id,
            source_event_id=event.event_id,
            source=event.channel,
            action=decision.action,
            parameters=decision.entities,
            risk=policy_eval.risk,
            requires_confirmation=policy_eval.requires_confirmation,
        )

        # 4. Action Engine Execution & Verification
        result = self.action_engine.execute(request, user_confirmed=user_confirmed)

        if result.status == ActionStatus.NEEDS_CONFIRMATION:
            self._pending_request = request
            response_text = result.result or "Confirmation required."
            self.hud_state.set_state(State.WAITING_CONFIRMATION, pending_prompt=result.result)
        else:
            self._pending_request = None
            response_text = ResponseFormatter.format_action_result(result)
            self.hud_state.set_state(self.state_machine.current_state)
            self.hud_state.record_action_executed(
                action=decision.action,
                status=result.status.value,
                verified=result.verified,
            )
            self.hud_state.update_system_status(
                volume=self.system_backend.volume,
                brightness=self.system_backend.brightness,
                memory_items=len(self.memory_store._items),
            )
            # Record context
            self.context.record_turn(
                role="user",
                text=event.raw_payload,
                action=decision.action,
                entities=decision.entities,
            )
            self.context.record_action_executed(
                action_name=decision.action,
                parameters=decision.entities,
                reversible=True,
            )

        return {
            "action_id": result.action_id,
            "status": result.status.value,
            "response_text": response_text,
            "state": self.state_machine.current_state.value,
            "verified": result.verified,
            "error_code": result.error_code.value if result.error_code else None,
        }

    def confirm_pending(self, confirmed: bool = True) -> Dict[str, Any]:
        """Confirm or reject a pending action awaiting confirmation."""
        if not self._pending_request:
            return {
                "action_id": None,
                "status": ActionStatus.BLOCKED.value,
                "response_text": "No action is currently awaiting confirmation.",
                "state": self.state_machine.current_state.value,
                "verified": False,
                "error_code": ErrorCode.E510.value,
            }

        req = self._pending_request
        self._pending_request = None

        if not confirmed:
            self.state_machine.reset_to_idle()
            self.logger.log_policy_decision(
                session_id=req.session_id,
                action_id=req.action_id,
                risk=req.risk.value,
                requires_confirmation=True,
                confirmed=False,
            )
            return {
                "action_id": req.action_id,
                "status": ActionStatus.CANCELLED.value,
                "response_text": f"Action '{req.action}' was cancelled.",
                "state": self.state_machine.current_state.value,
                "verified": True,
                "error_code": ErrorCode.E420.value,
            }

        # Re-execute with user_confirmed=True
        result = self.action_engine.execute(req, user_confirmed=True)
        response_text = ResponseFormatter.format_action_result(result)

        return {
            "action_id": result.action_id,
            "status": result.status.value,
            "response_text": response_text,
            "state": self.state_machine.current_state.value,
            "verified": result.verified,
            "error_code": result.error_code.value if result.error_code else None,
        }

    # Alias for flexibility
    confirm_action = confirm_pending
