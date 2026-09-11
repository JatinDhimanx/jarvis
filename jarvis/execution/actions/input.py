"""Input action group (mouse/scroll/keyboard) matching 08_ACTION_ENGINE.md and 09_TOOL_REGISTRY.md."""

from typing import List, Optional, Tuple
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class VirtualInputBackend:
    """Stateful virtual input backend for mouse and scroll actions with verification hooks."""

    def __init__(self):
        self.cursor_pos: Tuple[int, int] = (0, 0)
        self.click_count: int = 0
        self.double_click_count: int = 0
        self.scroll_delta: int = 0
        self.last_action: Optional[str] = None
        self.fail_next_verification: bool = False

    def move_mouse(self, x: int, y: int) -> str:
        self.cursor_pos = (int(x), int(y))
        self.last_action = "move_mouse"
        return f"Mouse moved to ({x}, {y})"

    def verify_mouse_position(self, x: int, y: int) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.cursor_pos == (int(x), int(y))

    def click(self, button: str = "left") -> str:
        self.click_count += 1
        self.last_action = "click"
        return f"Mouse {button} clicked"

    def verify_click(self, button: str = "left") -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_action == "click"

    def double_click(self, button: str = "left") -> str:
        self.double_click_count += 1
        self.last_action = "double_click"
        return f"Mouse {button} double-clicked"

    def verify_double_click(self, button: str = "left") -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_action == "double_click"

    def scroll(self, amount: int = 1) -> str:
        self.scroll_delta += int(amount)
        self.last_action = "scroll"
        return f"Scrolled {amount} units"

    def verify_scroll(self, amount: int = 1) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_action == "scroll"

    def type_text(self, text: str) -> str:
        self.last_action = "type_text"
        return f"Typed: '{text}'"

    def verify_type_text(self, text: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_action == "type_text"

    def press_key(self, key: str) -> str:
        self.last_action = "press_key"
        return f"Pressed key: '{key}'"

    def verify_press_key(self, key: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_action == "press_key"

    def hotkey(self, keys: List[str]) -> str:
        self.last_action = "hotkey"
        combo = "+".join(keys)
        return f"Triggered hotkey: '{combo}'"

    def verify_hotkey(self, keys: List[str]) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_action == "hotkey"


_DEFAULT_INPUT_BACKEND = VirtualInputBackend()


def get_default_input_backend() -> VirtualInputBackend:
    return _DEFAULT_INPUT_BACKEND


def register_input_tools(registry: ToolRegistry, backend: Optional[VirtualInputBackend] = None) -> None:
    """Register mouse/scroll tools into the ToolRegistry."""
    b = backend or _DEFAULT_INPUT_BACKEND

    # click tool
    click_decl = ToolDeclaration(
        name="click",
        version=1,
        description="Click mouse button at current cursor location",
        input_schema={"type": "object", "properties": {"button": {"type": "string", "default": "left"}}},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_mouse_event",
    )
    registry.register_tool(click_decl, handler=b.click, verifier=b.verify_click)

    # double_click tool
    double_click_decl = ToolDeclaration(
        name="double_click",
        version=1,
        description="Double click mouse button at current cursor location",
        input_schema={"type": "object", "properties": {"button": {"type": "string", "default": "left"}}},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_mouse_event",
    )
    registry.register_tool(double_click_decl, handler=b.double_click, verifier=b.verify_double_click)

    # scroll tool
    scroll_decl = ToolDeclaration(
        name="scroll",
        version=1,
        description="Scroll active viewport by specified amount",
        input_schema={"type": "object", "properties": {"amount": {"type": "integer", "default": 1}}},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_scroll_event",
    )
    registry.register_tool(scroll_decl, handler=b.scroll, verifier=b.verify_scroll)

    # move_mouse tool
    move_mouse_decl = ToolDeclaration(
        name="move_mouse",
        version=1,
        description="Move mouse cursor to target coordinates",
        input_schema={
            "type": "object",
            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "required": ["x", "y"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="read_cursor_position",
    )
    registry.register_tool(move_mouse_decl, handler=b.move_mouse, verifier=b.verify_mouse_position)

    # type_text tool
    type_text_decl = ToolDeclaration(
        name="type_text",
        version=1,
        description="Type simulated keyboard text string",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_text_input",
    )
    registry.register_tool(type_text_decl, handler=b.type_text, verifier=b.verify_type_text)

    # press_key tool
    press_key_decl = ToolDeclaration(
        name="press_key",
        version=1,
        description="Press a specific keyboard key",
        input_schema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_key_event",
    )
    registry.register_tool(press_key_decl, handler=b.press_key, verifier=b.verify_press_key)

    # hotkey tool
    hotkey_decl = ToolDeclaration(
        name="hotkey",
        version=1,
        description="Trigger keyboard shortcut combination",
        input_schema={"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}}}, "required": ["keys"]},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_hotkey_event",
    )
    registry.register_tool(hotkey_decl, handler=b.hotkey, verifier=b.verify_hotkey)
