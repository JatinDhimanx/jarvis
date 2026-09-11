"""Browser automation action group matching 08_ACTION_ENGINE.md, 09_TOOL_REGISTRY.md, and 11_SAFETY_AND_PERMISSIONS.md."""

from typing import Any, Dict, Optional
import urllib.parse
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class VirtualBrowser:
    """Authorized browser driver simulator with safe navigation and state verification."""

    def __init__(self, is_online: bool = True):
        self.is_online = is_online
        self.current_url: Optional[str] = None
        self.page_title: Optional[str] = None
        self.scroll_position: int = 0
        self.clicked_elements: list[str] = []
        self.input_values: Dict[str, str] = {}
        self.submitted_transactions: list[Dict[str, Any]] = []
        self.fail_next_verification: bool = False

    def open_url(self, url: str) -> str:
        """Navigate to URL with protocol validation."""
        if not self.is_online:
            raise JarvisError(ErrorCode.E600, "Browser navigation failed: network unavailable")

        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            raise JarvisError(
                ErrorCode.E400,
                f"Unauthorized or insecure URL scheme '{parsed.scheme}': only http and https are allowed",
            )

        self.current_url = url.strip()
        self.page_title = f"Page: {parsed.netloc}"
        self.scroll_position = 0
        return f"Navigated to {self.current_url}"

    def verify_url_opened(self, url: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.current_url == url.strip()

    def scroll(self, direction: str = "down", amount: int = 300) -> str:
        """Scroll webpage by specified amount."""
        if direction.lower() == "up":
            self.scroll_position = max(0, self.scroll_position - amount)
        else:
            self.scroll_position += amount
        return f"Scrolled {direction} to position {self.scroll_position}"

    def verify_scrolled(self, direction: str = "down", amount: int = 300) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return True

    def click(self, selector: str) -> str:
        """Click element by selector."""
        clean = selector.strip()
        self.clicked_elements.append(clean)
        return f"Clicked element '{clean}'"

    def verify_clicked(self, selector: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return selector.strip() in self.clicked_elements

    def input_text(self, selector: str, text: str) -> str:
        """Type text into element selector."""
        clean_sel = selector.strip()
        self.input_values[clean_sel] = text
        return f"Entered text into '{clean_sel}'"

    def verify_input(self, selector: str, text: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.input_values.get(selector.strip()) == text

    def submit_transaction(self, site: str, amount: str) -> str:
        """Execute web financial/order transaction (HIGH risk)."""
        tx = {"site": site, "amount": amount}
        self.submitted_transactions.append(tx)
        return f"Transaction on {site} for {amount} completed successfully."

    def verify_transaction(self, site: str, amount: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return any(t["site"] == site and t["amount"] == amount for t in self.submitted_transactions)


def register_browser_tools(registry: ToolRegistry, browser: Optional[VirtualBrowser] = None) -> VirtualBrowser:
    """Register browser automation tools declaring all 10 mandatory fields per 09_TOOL_REGISTRY.md."""
    b = browser or VirtualBrowser()

    # 1. open_browser_url
    registry.register_tool(
        ToolDeclaration(
            name="open_browser_url",
            version=1,
            description="Open specified URL in authorized web browser",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["network"],
            availability=Availability.ONLINE,
            reversible=True,
            verification_method="verify_url_opened",
        ),
        handler=lambda url="", **kw: {"result": b.open_url(url)},
        verifier=lambda url="", **kw: b.verify_url_opened(url),
    )

    # 2. browser_scroll
    registry.register_tool(
        ToolDeclaration(
            name="browser_scroll",
            version=1,
            description="Scroll the active web browser page",
            input_schema={"type": "object", "properties": {"direction": {"type": "string"}, "amount": {"type": "integer"}}},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["browser"],
            availability=Availability.ONLINE,
            reversible=True,
            verification_method="verify_scrolled",
        ),
        handler=lambda direction="down", amount=300, **kw: {"result": b.scroll(direction, amount)},
        verifier=lambda direction="down", amount=300, **kw: b.verify_scrolled(direction, amount),
    )

    # 3. browser_click
    registry.register_tool(
        ToolDeclaration(
            name="browser_click",
            version=1,
            description="Click an element on the current web page",
            input_schema={"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["browser"],
            availability=Availability.ONLINE,
            reversible=False,
            verification_method="verify_clicked",
        ),
        handler=lambda selector="", **kw: {"result": b.click(selector)},
        verifier=lambda selector="", **kw: b.verify_clicked(selector),
    )

    # 4. browser_input
    registry.register_tool(
        ToolDeclaration(
            name="browser_input",
            version=1,
            description="Enter text into input selector on web page",
            input_schema={"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}}, "required": ["selector", "text"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["browser"],
            availability=Availability.ONLINE,
            reversible=True,
            verification_method="verify_input",
        ),
        handler=lambda selector="", text="", **kw: {"result": b.input_text(selector, text)},
        verifier=lambda selector="", text="", **kw: b.verify_input(selector, text),
    )

    # 5. browser_submit_transaction (HIGH risk)
    registry.register_tool(
        ToolDeclaration(
            name="browser_submit_transaction",
            version=1,
            description="Execute authorized browser purchase or external transaction",
            input_schema={"type": "object", "properties": {"site": {"type": "string"}, "amount": {"type": "string"}}, "required": ["site", "amount"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.HIGH,
            required_permissions=["network", "payment"],
            availability=Availability.ONLINE,
            reversible=False,
            verification_method="verify_transaction",
        ),
        handler=lambda site="", amount="", **kw: {"result": b.submit_transaction(site, amount)},
        verifier=lambda site="", amount="", **kw: b.verify_transaction(site, amount),
    )

    return b
