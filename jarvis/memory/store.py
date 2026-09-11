"""Persistent Memory Store matching 03_CONTEXT_AND_MEMORY.md and 12_MEMORY_SCHEMA.md."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.memory.models import MemoryCategory, MemoryItem, MemoryLifecycle


FORBIDDEN_SECRET_PATTERNS = [
    r"pass(?:word)?",
    r"api[_-]?key",
    r"secret",
    r"token",
    r"auth[_-]?token",
    r"bearer\s+[a-zA-Z0-9_\-\.]+",
    r"private[_-]?key",
    r"id_rsa",
]


class MemoryStore:
    """Structured, minimal, user-controlled persistent memory store."""

    def __init__(self, persistence_file: Optional[str] = None):
        self.persistence_file = Path(persistence_file) if persistence_file else None
        self._items: Dict[str, MemoryItem] = {}
        self.fail_next_verification: bool = False
        self._load()

    def _load(self) -> None:
        """Load persistent memories from JSON file if configured and exists."""
        if self.persistence_file and self.persistence_file.exists():
            try:
                data = json.loads(self.persistence_file.read_text(encoding="utf-8"))
                for raw_item in data:
                    item = MemoryItem(**raw_item)
                    if item.lifecycle != MemoryLifecycle.OUTDATED:
                        self._items[item.key] = item
            except Exception:
                pass

    def _persist(self) -> None:
        """Save memories to file if persistence is configured."""
        if self.persistence_file:
            try:
                self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
                serialized = [item.model_dump() for item in self._items.values()]
                self.persistence_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
            except Exception:
                pass

    def _check_no_secrets(self, key: str, value: Any) -> None:
        """Enforce 12_MEMORY_SCHEMA.md: Do not store credentials or secrets."""
        search_targets = [str(key)]
        if isinstance(value, str):
            search_targets.append(value)
        elif isinstance(value, dict):
            search_targets.extend([str(k) for k in value.keys()])
            search_targets.extend([str(v) for v in value.values() if isinstance(v, str)])

        for target in search_targets:
            for pattern in FORBIDDEN_SECRET_PATTERNS:
                if re.search(pattern, target, re.IGNORECASE):
                    raise JarvisError(
                        ErrorCode.E400,
                        f"Refusing to save sensitive secret or credential in memory: pattern '{pattern}' matched",
                    )

    def write(
        self,
        key: str,
        value: Any,
        category: MemoryCategory = MemoryCategory.PREFERENCE,
        source: str = "user",
        confidence: float = 1.0,
    ) -> MemoryItem:
        """Save or create user-authorized persistent memory record."""
        clean_key = key.strip()
        if not clean_key:
            raise JarvisError(ErrorCode.E100, "Memory key cannot be empty")

        self._check_no_secrets(clean_key, value)

        now = datetime.now(timezone.utc).isoformat()
        item = MemoryItem(
            key=clean_key,
            value=value,
            category=category,
            source=source,
            confidence=confidence,
            lifecycle=MemoryLifecycle.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._items[clean_key] = item
        self._persist()
        return item

    def read(self, key: str) -> Optional[MemoryItem]:
        """Retrieve active memory record by key."""
        clean_key = key.strip()
        item = self._items.get(clean_key)
        if item and item.lifecycle == MemoryLifecycle.ACTIVE:
            return item
        return None

    def update(self, key: str, value: Any) -> MemoryItem:
        """Update existing memory value and refresh timestamp."""
        clean_key = key.strip()
        if clean_key not in self._items:
            raise JarvisError(ErrorCode.E400, f"Cannot update non-existent memory key '{clean_key}'")

        self._check_no_secrets(clean_key, value)

        item = self._items[clean_key]
        item.value = value
        item.updated_at = datetime.now(timezone.utc).isoformat()
        item.lifecycle = MemoryLifecycle.ACTIVE
        self._persist()
        return item

    def forget(self, key: str) -> bool:
        """Mark memory as OUTDATED or remove it per user instruction."""
        clean_key = key.strip()
        if clean_key in self._items:
            self._items[clean_key].lifecycle = MemoryLifecycle.OUTDATED
            del self._items[clean_key]
            self._persist()
            return True
        return False

    def list_by_category(self, category: MemoryCategory) -> List[MemoryItem]:
        """List all active memories for given category."""
        return [
            item for item in self._items.values()
            if item.category == category and item.lifecycle == MemoryLifecycle.ACTIVE
        ]

    def clear(self) -> None:
        """Clear all memories."""
        self._items.clear()
        self._persist()
