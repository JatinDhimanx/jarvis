"""Configuration schema and loading matching 17_CONFIG_SCHEMA.md."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SECURITY = "SECURITY"


class JarvisSection(BaseModel):
    name: str = "JARVIS"
    wake_word: str = "jarvis"
    language: str = "en-IN"


class ModeSection(BaseModel):
    offline_enabled: bool = True
    online_enabled: bool = True
    prefer_offline: bool = True


class VisionSection(BaseModel):
    enabled: bool = Field(default=False, description="Opt-in; camera stays off until explicitly enabled")
    camera_index: int = 0
    gesture_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    cooldown_ms: int = Field(default=500, ge=0)
    show_camera_active_indicator: bool = True


class VoiceSection(BaseModel):
    enabled: bool = True
    always_listen: bool = Field(default=False, description="If false, mic is idle until wake word detection window opens")
    wake_word_enabled: bool = True
    silence_timeout_ms: int = Field(default=2500, ge=0)


class SafetySection(BaseModel):
    require_confirmation_for_medium: bool = True
    require_confirmation_for_high: bool = True


class UISection(BaseModel):
    hud_enabled: bool = True
    show_gesture_feedback: bool = True


class MemorySection(BaseModel):
    persistent_enabled: bool = True


class LoggingSection(BaseModel):
    level: LogLevel = LogLevel.INFO
    log_raw_speech: bool = Field(default=False, description="Never log recognized text content unless true and user-acknowledged")
    session_id_prefix: str = "s-"

    @field_validator("level", mode="before")
    @classmethod
    def parse_log_level(cls, v: Any) -> LogLevel:
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v


class JarvisConfig(BaseModel):
    """Root configuration matching 17_CONFIG_SCHEMA.md."""
    jarvis: JarvisSection = Field(default_factory=JarvisSection)
    mode: ModeSection = Field(default_factory=ModeSection)
    vision: VisionSection = Field(default_factory=VisionSection)
    voice: VoiceSection = Field(default_factory=VoiceSection)
    safety: SafetySection = Field(default_factory=SafetySection)
    ui: UISection = Field(default_factory=UISection)
    memory: MemorySection = Field(default_factory=MemorySection)
    logging: LoggingSection = Field(default_factory=LoggingSection)


def load_config(config_path: Optional[str | Path] = None) -> JarvisConfig:
    """Load and validate configuration from YAML file or return defaults."""
    if config_path is None:
        # Default config path
        default_path = Path(__file__).resolve().parent.parent.parent / "config" / "default_config.yaml"
        if default_path.exists():
            config_path = default_path
        else:
            return JarvisConfig()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return JarvisConfig.model_validate(data)
