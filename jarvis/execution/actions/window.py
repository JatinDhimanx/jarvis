"""Window action group matching 08_ACTION_ENGINE.md and 09_TOOL_REGISTRY.md."""

from typing import Dict, List, Optional
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class VirtualWindowManager:
    """Stateful virtual window manager with verification hooks."""

    def __init__(self):
        self.windows: List[str] = ["desktop", "chrome", "code", "terminal"]
        self.active_window: str = "chrome"
        self.minimized_windows: set[str] = set()
        self.maximized_windows: set[str] = set()
        self.fail_next_verification: bool = False

    def focus_window(self, window_title: str) -> str:
        clean = window_title.strip().lower()
        if clean not in self.windows:
            self.windows.append(clean)
        self.active_window = clean
        if clean in self.minimized_windows:
            self.minimized_windows.remove(clean)
        return f"Focused window '{window_title}'."

    def verify_window_focused(self, window_title: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.active_window == window_title.strip().lower()

    def minimize_window(self, window_title: Optional[str] = None) -> str:
        target = window_title.strip().lower() if window_title else self.active_window
        self.minimized_windows.add(target)
        return f"Minimized window '{target}'."

    def verify_window_minimized(self, window_title: Optional[str] = None) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        target = window_title.strip().lower() if window_title else self.active_window
        return target in self.minimized_windows

    def maximize_window(self, window_title: Optional[str] = None) -> str:
        target = window_title.strip().lower() if window_title else self.active_window
        self.maximized_windows.add(target)
        if target in self.minimized_windows:
            self.minimized_windows.remove(target)
        return f"Maximized window '{target}'."

    def verify_window_maximized(self, window_title: Optional[str] = None) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        target = window_title.strip().lower() if window_title else self.active_window
        return target in self.maximized_windows

    def switch_window(self, direction: str = "next") -> str:
        if not self.windows:
            return "No windows to switch."
        current_idx = self.windows.index(self.active_window) if self.active_window in self.windows else 0
        if direction.lower() == "next":
            new_idx = (current_idx + 1) % len(self.windows)
        else:
            new_idx = (current_idx - 1) % len(self.windows)
        self.active_window = self.windows[new_idx]
        return f"Switched to window '{self.active_window}'."

    def verify_switch_window(self, direction: str = "next") -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return bool(self.active_window)


_DEFAULT_WINDOW_MANAGER = VirtualWindowManager()


def get_default_window_manager() -> VirtualWindowManager:
    return _DEFAULT_WINDOW_MANAGER


def register_window_tools(registry: ToolRegistry, manager: Optional[VirtualWindowManager] = None) -> None:
    """Register window management tools into ToolRegistry."""
    m = manager or _DEFAULT_WINDOW_MANAGER

    # focus_window tool
    focus_decl = ToolDeclaration(
        name="focus_window",
        version=1,
        description="Bring a target window into foreground focus",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}, "required": ["window_title"]},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_window_focused",
    )
    registry.register_tool(focus_decl, handler=m.focus_window, verifier=m.verify_window_focused)

    # minimize_window tool
    min_decl = ToolDeclaration(
        name="minimize_window",
        version=1,
        description="Minimize target or currently active window",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_window_minimized",
    )
    registry.register_tool(min_decl, handler=m.minimize_window, verifier=m.verify_window_minimized)

    # maximize_window tool
    max_decl = ToolDeclaration(
        name="maximize_window",
        version=1,
        description="Maximize target or currently active window",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_window_maximized",
    )
    registry.register_tool(max_decl, handler=m.maximize_window, verifier=m.verify_window_maximized)

    # switch_window tool
    switch_decl = ToolDeclaration(
        name="switch_window",
        version=1,
        description="Switch active window to next or previous window",
        input_schema={"type": "object", "properties": {"direction": {"type": "string", "default": "next"}}},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_active_window",
    )
    registry.register_tool(switch_decl, handler=m.switch_window, verifier=m.verify_switch_window)
