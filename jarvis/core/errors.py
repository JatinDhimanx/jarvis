"""Standard error classes and codes matching 14_ERROR_RECOVERY.md."""

from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    """Stable error codes per 14_ERROR_RECOVERY.md."""
    E100 = "E100"  # input error: malformed or unrecognized raw input
    E200 = "E200"  # perception error: STT/gesture confidence below threshold or sensor failure
    E300 = "E300"  # routing error: intent could not be resolved to a known action group
    E400 = "E400"  # tool unavailable: requested tool not registered or disabled for current mode
    E410 = "E410"  # permission denied: required OS/user permission missing
    E420 = "E420"  # confirmation denied: user rejected a required confirmation
    E500 = "E500"  # timeout: action or tool call exceeded its time budget
    E510 = "E510"  # unexpected UI state: target app/window not in the expected state to proceed
    E600 = "E600"  # network failure: online capability required but unreachable
    E700 = "E700"  # verification failure: action executed but post-check did not confirm success


ERROR_DEFINITIONS = {
    ErrorCode.E100: ("input error", "malformed or unrecognized raw input"),
    ErrorCode.E200: ("perception error", "STT/gesture confidence below threshold or sensor failure"),
    ErrorCode.E300: ("routing error", "intent could not be resolved to a known action group"),
    ErrorCode.E400: ("tool unavailable", "requested tool not registered or disabled for current mode"),
    ErrorCode.E410: ("permission denied", "required OS/user permission missing"),
    ErrorCode.E420: ("confirmation denied", "user rejected a required confirmation"),
    ErrorCode.E500: ("timeout", "action or tool call exceeded its time budget"),
    ErrorCode.E510: ("unexpected UI state", "target app/window not in the expected state to proceed"),
    ErrorCode.E600: ("network failure", "online capability required but unreachable"),
    ErrorCode.E700: ("verification failure", "action executed but post-check did not confirm success"),
}


class JarvisError(Exception):
    """Base exception for all JARVIS errors with standardized code."""

    def __init__(self, code: ErrorCode, message: Optional[str] = None):
        self.code = code
        self.error_class, default_msg = ERROR_DEFINITIONS.get(code, ("unknown", "An error occurred"))
        self.message = message or default_msg
        super().__init__(f"[{self.code.value}] {self.error_class}: {self.message}")
