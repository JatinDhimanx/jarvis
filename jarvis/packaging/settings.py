"""Settings manager and tools matching 17_CONFIG_SCHEMA.md and 18_FEATURE_ROADMAP.md."""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from jarvis.core.config import JarvisConfig, load_config
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class SettingsManager:
    """Manages reading, updating, and persisting system configurations."""

    def __init__(self, config_path: Optional[str | Path] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config = self._load()

    def _load(self) -> JarvisConfig:
        if self.config_path and self.config_path.exists():
            return load_config(self.config_path)
        return JarvisConfig()

    def save(self) -> None:
        """Persist current configuration to YAML file."""
        if not self.config_path:
            return
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.config.model_dump(mode="json")
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def get(self, key: str) -> Any:
        """Retrieve setting value by dotted path, e.g. 'vision.enabled'."""
        parts = key.strip().split(".")
        current: Any = self.config.model_dump()
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise JarvisError(ErrorCode.E400, f"Setting key '{key}' not found.")
        return current

    def set(self, key: str, value: Any) -> bool:
        """Update setting value by dotted path and persist."""
        data = self.config.model_dump()
        parts = key.strip().split(".")
        target = data
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                raise JarvisError(ErrorCode.E400, f"Invalid setting path '{key}'.")
            target = target[part]

        final_key = parts[-1]
        if final_key not in target:
            raise JarvisError(ErrorCode.E400, f"Setting key '{key}' not found.")

        # Type conversion if needed (e.g. string to bool/int/float)
        original = target[final_key]
        if isinstance(original, bool) and not isinstance(value, bool):
            if str(value).lower() in ("true", "1", "yes", "on"):
                value = True
            elif str(value).lower() in ("false", "0", "no", "off"):
                value = False
        elif isinstance(original, int) and not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise JarvisError(ErrorCode.E100, f"Value '{value}' cannot be converted to int.")
        elif isinstance(original, float) and not isinstance(value, float):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise JarvisError(ErrorCode.E100, f"Value '{value}' cannot be converted to float.")

        target[final_key] = value

        # Validate through Pydantic
        try:
            new_config = JarvisConfig.model_validate(data)
        except Exception as ex:
            raise JarvisError(ErrorCode.E100, f"Configuration validation failed: {str(ex)}")

        self.config = new_config
        self.save()
        return True

    def reset_defaults(self) -> JarvisConfig:
        """Reset all configuration values to defaults."""
        self.config = JarvisConfig()
        self.save()
        return self.config


def register_settings_tools(registry: ToolRegistry, settings_manager: SettingsManager) -> None:
    """Register read_setting and update_setting tools into the ToolRegistry."""

    def read_setting_handler(key: str, **kwargs: Any) -> Dict[str, Any]:
        val = settings_manager.get(key)
        return {"key": key, "value": val}

    def read_setting_verifier(key: str, **kwargs: Any) -> bool:
        try:
            settings_manager.get(key)
            return True
        except Exception:
            return False

    registry.register_tool(
        ToolDeclaration(
            name="read_setting",
            version=1,
            description="Read a configuration setting value by dotted key",
            input_schema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            output_schema={"type": "object"},
            risk_level=RiskLevel.LOW,
            required_permissions=["settings:read"],
            availability=Availability.OFFLINE,
            reversible=True,
            verification_method="verify_setting_exists",
        ),
        handler=read_setting_handler,
        verifier=read_setting_verifier,
    )

    def update_setting_handler(key: str, value: Any, **kwargs: Any) -> Dict[str, Any]:
        settings_manager.set(key, value)
        return {"key": key, "value": settings_manager.get(key)}

    def update_setting_verifier(key: str, value: Any, **kwargs: Any) -> bool:
        try:
            current = settings_manager.get(key)
            # Compare equality (handling stringified bools)
            if isinstance(current, bool) and isinstance(value, str):
                return current == (value.lower() in ("true", "1", "yes", "on"))
            return current == value
        except Exception:
            return False

    registry.register_tool(
        ToolDeclaration(
            name="update_setting",
            version=1,
            description="Update a configuration setting value by dotted key",
            input_schema={"type": "object", "properties": {"key": {"type": "string"}, "value": {}}, "required": ["key", "value"]},
            output_schema={"type": "object"},
            risk_level=RiskLevel.MEDIUM,
            required_permissions=["settings:write"],
            availability=Availability.OFFLINE,
            reversible=True,
            verification_method="verify_setting_updated",
        ),
        handler=update_setting_handler,
        verifier=update_setting_verifier,
    )
