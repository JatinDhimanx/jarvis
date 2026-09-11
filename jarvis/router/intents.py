"""Canonical intent definitions and Intent -> Action group mapping table matching 02_COMMAND_ROUTER.md."""

from enum import Enum
from typing import Dict, List, Set


class Intent(str, Enum):
    """Canonical intent categories from 02_COMMAND_ROUTER.md."""
    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    APP_CONTROL = "APP_CONTROL"
    WINDOW_CONTROL = "WINDOW_CONTROL"
    MOUSE_CONTROL = "MOUSE_CONTROL"
    KEYBOARD_CONTROL = "KEYBOARD_CONTROL"
    MEDIA_CONTROL = "MEDIA_CONTROL"
    FILE_OPERATION = "FILE_OPERATION"
    WEB_SEARCH = "WEB_SEARCH"
    WEB_AUTOMATION = "WEB_AUTOMATION"
    AI_QUERY = "AI_QUERY"
    MEMORY = "MEMORY"
    SETTINGS = "SETTINGS"
    STATUS = "STATUS"
    CONVERSATION = "CONVERSATION"
    UNKNOWN = "UNKNOWN"


class ActionGroup(str, Enum):
    """Action groups from 02_COMMAND_ROUTER.md and 08_ACTION_ENGINE.md."""
    SYSTEM = "System"
    APPLICATION = "Application"
    WINDOW = "Window"
    INPUT = "Input"
    MEDIA = "Media"
    FILES = "Files"
    ONLINE_TOOL = "Online tool"
    BRAIN_LAYER = "Brain layer"
    MEMORY = "Memory"
    CONFIG = "Config"
    READ_ONLY = "Read-only"
    RESPONSE_ONLY = "Response only"
    NONE = "None"


# Single source of truth table matching 02_COMMAND_ROUTER.md
INTENT_TO_ACTION_GROUP: Dict[Intent, ActionGroup] = {
    Intent.SYSTEM_CONTROL: ActionGroup.SYSTEM,
    Intent.APP_CONTROL: ActionGroup.APPLICATION,
    Intent.WINDOW_CONTROL: ActionGroup.WINDOW,
    Intent.MOUSE_CONTROL: ActionGroup.INPUT,
    Intent.KEYBOARD_CONTROL: ActionGroup.INPUT,
    Intent.MEDIA_CONTROL: ActionGroup.MEDIA,
    Intent.FILE_OPERATION: ActionGroup.FILES,
    Intent.WEB_SEARCH: ActionGroup.ONLINE_TOOL,
    Intent.WEB_AUTOMATION: ActionGroup.ONLINE_TOOL,
    Intent.AI_QUERY: ActionGroup.BRAIN_LAYER,
    Intent.MEMORY: ActionGroup.MEMORY,
    Intent.SETTINGS: ActionGroup.CONFIG,
    Intent.STATUS: ActionGroup.READ_ONLY,
    Intent.CONVERSATION: ActionGroup.RESPONSE_ONLY,
    Intent.UNKNOWN: ActionGroup.NONE,
}

INTENT_TO_ALLOWED_ACTIONS: Dict[Intent, Set[str]] = {
    Intent.SYSTEM_CONTROL: {"set_volume", "mute", "set_brightness", "lock_screen", "shutdown"},
    Intent.APP_CONTROL: {"open_app", "close_app", "restart_app"},
    Intent.WINDOW_CONTROL: {"focus_window", "minimize_window", "maximize_window", "switch_window"},
    Intent.MOUSE_CONTROL: {"move_mouse", "click", "double_click", "scroll"},
    Intent.KEYBOARD_CONTROL: {"type_text", "press_key", "hotkey"},
    Intent.MEDIA_CONTROL: {"play_pause", "next_track", "previous_track"},
    Intent.FILE_OPERATION: {"open_file", "create_file", "move_file", "copy_file", "delete_file"},
    Intent.WEB_SEARCH: {"search_web", "get_weather", "fetch_api"},
    Intent.WEB_AUTOMATION: {"browser_automation", "open_browser_url", "browser_click", "browser_scroll", "browser_input", "browser_submit_transaction"},
    Intent.AI_QUERY: set(),
    Intent.MEMORY: {"READ", "WRITE", "UPDATE", "FORGET", "read_memory", "write_memory", "update_memory", "forget_memory"},
    Intent.SETTINGS: {"read_setting", "update_setting"},
    Intent.STATUS: {"get_status"},
    Intent.CONVERSATION: set(),
    Intent.UNKNOWN: set(),
}
