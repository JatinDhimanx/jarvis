"""Memory action group matching 03_CONTEXT_AND_MEMORY.md, 08_ACTION_ENGINE.md, and 09_TOOL_REGISTRY.md."""

from typing import Any, Dict, Optional
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.memory.models import MemoryCategory
from jarvis.memory.store import MemoryStore
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class MemoryActionManager:
    """Action manager for executing structured memory operations."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        self.fail_next_verification: bool = False

    def write(self, key: str, value: Any, category: str = "preference") -> str:
        cat = MemoryCategory(category.lower()) if category.lower() in [c.value for c in MemoryCategory] else MemoryCategory.PREFERENCE
        item = self.store.write(key=key, value=value, category=cat)
        return f"Stored memory '{item.key}' = '{item.value}' in category '{item.category.value}'."

    def verify_written(self, key: str, value: Any, **kwargs: Any) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        item = self.store.read(key)
        return item is not None and item.value == value

    def read(self, key: str) -> str:
        item = self.store.read(key)
        if not item:
            return f"No memory found for '{key}'."
        return f"Memory '{key}': {item.value}"

    def verify_read(self, key: str, **kwargs: Any) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return True

    def update(self, key: str, value: Any) -> str:
        item = self.store.update(key=key, value=value)
        return f"Updated memory '{item.key}' = '{item.value}'."

    def verify_updated(self, key: str, value: Any, **kwargs: Any) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        item = self.store.read(key)
        return item is not None and item.value == value

    def forget(self, key: str) -> str:
        forgotten = self.store.forget(key)
        if forgotten:
            return f"Memory '{key}' forgotten."
        return f"No active memory found for '{key}'."

    def verify_forgotten(self, key: str, **kwargs: Any) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.store.read(key) is None


def register_memory_tools(registry: ToolRegistry, manager: Optional[MemoryActionManager] = None) -> MemoryActionManager:
    """Register persistent memory tools into ToolRegistry declaring all 10 mandatory fields."""
    mgr = manager or MemoryActionManager()

    # 1. write_memory
    registry.register_tool(
        ToolDeclaration(
            name="write_memory",
            version=1,
            description="Persist user preference or configuration to memory",
            input_schema={"type": "object", "properties": {"key": {"type": "string"}, "value": {}, "category": {"type": "string"}}, "required": ["key", "value"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["memory"],
            availability=Availability.OFFLINE,
            reversible=True,
            verification_method="verify_written",
        ),
        handler=lambda key="", value="", category="preference", **kw: mgr.write(key, value, category),
        verifier=lambda key="", value="", **kw: mgr.verify_written(key, value),
    )

    # 2. read_memory
    registry.register_tool(
        ToolDeclaration(
            name="read_memory",
            version=1,
            description="Retrieve stored preference or item from memory",
            input_schema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["memory"],
            availability=Availability.OFFLINE,
            reversible=True,
            verification_method="verify_read",
        ),
        handler=lambda key="", **kw: mgr.read(key),
        verifier=lambda key="", **kw: mgr.verify_read(key),
    )

    # 3. update_memory
    registry.register_tool(
        ToolDeclaration(
            name="update_memory",
            version=1,
            description="Update an existing stored memory value",
            input_schema={"type": "object", "properties": {"key": {"type": "string"}, "value": {}}, "required": ["key", "value"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["memory"],
            availability=Availability.OFFLINE,
            reversible=True,
            verification_method="verify_updated",
        ),
        handler=lambda key="", value="", **kw: mgr.update(key, value),
        verifier=lambda key="", value="", **kw: mgr.verify_updated(key, value),
    )

    # 4. forget_memory
    registry.register_tool(
        ToolDeclaration(
            name="forget_memory",
            version=1,
            description="Remove or mark memory as outdated",
            input_schema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["memory"],
            availability=Availability.OFFLINE,
            reversible=False,
            verification_method="verify_forgotten",
        ),
        handler=lambda key="", **kw: mgr.forget(key),
        verifier=lambda key="", **kw: mgr.verify_forgotten(key),
    )

    return mgr
