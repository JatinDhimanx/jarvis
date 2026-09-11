"""Memory models matching 12_MEMORY_SCHEMA.md."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class MemoryCategory(str, Enum):
    """Allowed memory categories from 12_MEMORY_SCHEMA.md."""
    PREFERENCE = "preference"
    WORKFLOW = "workflow"
    DEVICE = "device"
    PROJECT = "project"
    TOOL_CONFIGURATION = "tool_configuration"


class MemoryLifecycle(str, Enum):
    """Lifecycle states from 12_MEMORY_SCHEMA.md."""
    CANDIDATE = "candidate"
    AUTHORIZED = "authorized"
    ACTIVE = "active"
    OUTDATED = "outdated"


class MemoryItem(BaseModel):
    """Structured persistent memory record matching 12_MEMORY_SCHEMA.md."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str
    value: Any
    category: MemoryCategory = MemoryCategory.PREFERENCE
    source: str = "user"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    lifecycle: MemoryLifecycle = MemoryLifecycle.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
