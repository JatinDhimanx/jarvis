"""Tool discovery, schema registration, and lookup matching 09_TOOL_REGISTRY.md."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.policy.safety import RiskLevel


class Availability(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    HYBRID = "hybrid"


class ToolDeclaration(BaseModel):
    """Tool contract declaration matching 09_TOOL_REGISTRY.md (10 required fields)."""
    name: str
    version: int = 1
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    required_permissions: List[str] = Field(default_factory=list)
    availability: Availability = Availability.OFFLINE
    reversible: bool = False
    verification_method: str


class ToolRegistry:
    """Registry maintaining authorized tools and their executable handlers."""

    def __init__(self):
        self._tools: Dict[str, ToolDeclaration] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._verifiers: Dict[str, Callable[..., bool]] = {}

    def register_tool(
        self,
        declaration: ToolDeclaration,
        handler: Optional[Callable[..., Any]] = None,
        verifier: Optional[Callable[..., bool]] = None,
    ) -> None:
        """Register a new tool with its declaration, handler, and verifier."""
        self._tools[declaration.name] = declaration
        if handler:
            self._handlers[declaration.name] = handler
        if verifier:
            self._verifiers[declaration.name] = verifier

    # Alias for flexibility
    register = register_tool

    def get_declaration(self, tool_name: str) -> ToolDeclaration:
        """Retrieve tool declaration or raise E400 if unavailable."""
        if tool_name not in self._tools:
            raise JarvisError(
                ErrorCode.E400,
                f"Tool '{tool_name}' is not registered in Tool Registry",
            )
        return self._tools[tool_name]

    def get_handler(self, tool_name: str) -> Optional[Callable[..., Any]]:
        return self._handlers.get(tool_name)

    def get_verifier(self, tool_name: str) -> Optional[Callable[..., bool]]:
        return self._verifiers.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def list_tools(self) -> List[ToolDeclaration]:
        return list(self._tools.values())
