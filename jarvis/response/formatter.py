"""JARVIS response style formatter matching 13_RESPONSE_STYLE.md."""

from typing import Optional
from jarvis.core.errors import ErrorCode
from jarvis.execution.action_engine import ActionResult, ActionStatus


class ResponseFormatter:
    """Formats responses following the 1-2 sentence, concise, verified personality."""

    @staticmethod
    def format_acknowledgement(action_name: str, parameters: dict) -> str:
        """Brief acknowledgement before execution."""
        if action_name == "open_app":
            app = parameters.get("app_name", "the application")
            return f"Understood. Opening {app}."
        elif action_name == "close_app":
            app = parameters.get("app_name", "the application")
            return f"Closing {app}."
        elif action_name == "set_volume":
            val = parameters.get("value", "")
            return f"Setting volume to {val}%."
        elif action_name == "mute":
            state = parameters.get("state", True)
            return "Muting audio." if state else "Unmuting audio."
        elif action_name == "search_web":
            q = parameters.get("query", "")
            return f"Searching for '{q}'."
        return f"Executing {action_name}."

    @staticmethod
    def format_action_result(result: ActionResult) -> str:
        """Format final result after verification or failure."""
        if result.status == ActionStatus.SUCCESS and result.verified:
            if result.result:
                return result.result
            return f"{result.action} completed successfully."

        elif result.status == ActionStatus.NEEDS_CONFIRMATION:
            return result.result or "Confirmation is required to proceed. Please confirm or cancel."

        elif result.status == ActionStatus.BLOCKED:
            if result.error_code == ErrorCode.E400:
                return f"Cannot execute {result.action}: the requested tool is unavailable. Please verify your installed capabilities."
            elif result.error_code == ErrorCode.E410:
                return f"Cannot execute {result.action}: permission denied. Please grant the required system permission."
            elif result.error_code == ErrorCode.E420:
                return f"Action {result.action} was cancelled by user request."
            return f"Action {result.action} is blocked: {result.result}"

        elif result.status == ActionStatus.FAILED:
            if result.error_code == ErrorCode.E700:
                return f"{result.action} was triggered, but verification failed. The state could not be confirmed."
            elif result.error_code == ErrorCode.E600:
                return "Network connection failed. Unable to reach external service."
            return f"{result.action} failed: {result.result}"

        elif result.status == ActionStatus.CANCELLED:
            return f"{result.action} was cancelled."

        return f"Completed with status: {result.status.value}."

    @staticmethod
    def format_emergency_stop() -> str:
        return "Emergency stop activated. All running actions have been halted."
