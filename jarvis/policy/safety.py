"""Safety and confirmation policy matching 11_SAFETY_AND_PERMISSIONS.md."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel
from jarvis.core.config import JarvisConfig


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


ACTION_DEFAULT_RISK: Dict[str, RiskLevel] = {
    # System
    "set_volume": RiskLevel.LOW,
    "mute": RiskLevel.LOW,
    "set_brightness": RiskLevel.LOW,
    "lock_screen": RiskLevel.LOW,
    "shutdown": RiskLevel.HIGH,
    "stop": RiskLevel.LOW,
    "cancel": RiskLevel.LOW,
    # Application
    "open_app": RiskLevel.LOW,
    "close_app": RiskLevel.LOW,
    "restart_app": RiskLevel.LOW,
    # Window
    "focus_window": RiskLevel.LOW,
    "minimize_window": RiskLevel.LOW,
    "maximize_window": RiskLevel.LOW,
    "switch_window": RiskLevel.LOW,
    # Input
    "move_mouse": RiskLevel.LOW,
    "click": RiskLevel.LOW,
    "double_click": RiskLevel.LOW,
    "scroll": RiskLevel.LOW,
    "type_text": RiskLevel.LOW,
    "press_key": RiskLevel.LOW,
    "hotkey": RiskLevel.LOW,
    # Media
    "play_pause": RiskLevel.LOW,
    "next_track": RiskLevel.LOW,
    "previous_track": RiskLevel.LOW,
    # Files
    "open_file": RiskLevel.LOW,
    "create_file": RiskLevel.LOW,
    "move_file": RiskLevel.LOW,
    "copy_file": RiskLevel.LOW,
    "delete_file": RiskLevel.HIGH,
    # Web & Browser
    "search_web": RiskLevel.LOW,
    "open_browser_url": RiskLevel.LOW,
    "browser_scroll": RiskLevel.LOW,
    "browser_click": RiskLevel.LOW,
    "browser_input": RiskLevel.LOW,
    "browser_submit_transaction": RiskLevel.HIGH,
    # External APIs
    "get_weather": RiskLevel.LOW,
    "fetch_api": RiskLevel.LOW,
    # Memory
    "write_memory": RiskLevel.LOW,
    "read_memory": RiskLevel.LOW,
    "update_memory": RiskLevel.LOW,
    "forget_memory": RiskLevel.LOW,
    # Status
    "get_status": RiskLevel.LOW,
    "confirm": RiskLevel.LOW,
    # Settings
    "read_setting": RiskLevel.LOW,
    "update_setting": RiskLevel.MEDIUM,
}


class PolicyDecision(BaseModel):
    action: str
    risk: RiskLevel
    requires_confirmation: bool
    confirmation_prompt: Optional[str] = None


class SafetyPolicy:
    """Evaluates risk and determines confirmation requirements strictly from config."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config = config or JarvisConfig()

    def evaluate(self, action_name: str, parameters: Optional[Dict[str, Any]] = None) -> PolicyDecision:
        """Evaluate action risk and whether confirmation is strictly required.
        
        Formula:
        requires_confirmation = (risk == HIGH and config.safety.require_confirmation_for_high) or
                                (risk == MEDIUM and config.safety.require_confirmation_for_medium)
        """
        parameters = parameters or {}
        risk = ACTION_DEFAULT_RISK.get(action_name, RiskLevel.MEDIUM)

        requires_confirmation = False
        if risk == RiskLevel.HIGH and self.config.safety.require_confirmation_for_high:
            requires_confirmation = True
        elif risk == RiskLevel.MEDIUM and self.config.safety.require_confirmation_for_medium:
            requires_confirmation = True

        prompt = None
        if requires_confirmation:
            prompt = self.generate_confirmation_prompt(action_name, parameters)

        return PolicyDecision(
            action=action_name,
            risk=risk,
            requires_confirmation=requires_confirmation,
            confirmation_prompt=prompt,
        )

    def generate_confirmation_prompt(self, action_name: str, parameters: Dict[str, Any]) -> str:
        """Generate specific confirmation prompt describing consequence.
        
        Per 11_SAFETY_AND_PERMISSIONS.md:
        Good: 'Delete project.zip permanently? Confirm or cancel.'
        Bad: 'Are you sure?'
        """
        if action_name == "delete_file":
            path = parameters.get("path", "the file")
            return f"Delete '{path}' permanently? Confirm or cancel."
        elif action_name == "shutdown":
            return "Shut down the computer now? Confirm or cancel."
        elif action_name == "close_app" and parameters.get("unsaved"):
            app = parameters.get("app_name", "the application")
            return f"Close '{app}' with unsaved changes? Confirm or cancel."
        elif action_name == "browser_submit_transaction":
            site = parameters.get("site", "external service")
            amount = parameters.get("amount", "specified amount")
            return f"Submit transaction on '{site}' for {amount}? Confirm or cancel."
        else:
            param_str = ", ".join(f"{k}={v}" for k, v in parameters.items())
            detail = f" with parameters ({param_str})" if param_str else ""
            return f"Execute '{action_name}'{detail}? Confirm or cancel."
