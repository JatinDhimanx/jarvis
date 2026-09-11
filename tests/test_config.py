"""Tests for configuration loading, privacy defaults, and validation matching 17_CONFIG_SCHEMA.md."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from jarvis.core.config import JarvisConfig, LogLevel, load_config


def test_default_privacy_values():
    """Verify privacy-first defaults: vision off, always_listen off."""
    cfg = JarvisConfig()
    assert cfg.vision.enabled is False, "Camera must default to disabled (opt-in)"
    assert cfg.voice.always_listen is False, "Microphone must default to idle/not always listen"
    assert cfg.vision.show_camera_active_indicator is True
    assert cfg.logging.log_raw_speech is False, "Raw speech must not be logged by default"
    assert cfg.logging.level == LogLevel.INFO


def test_config_load_from_yaml(tmp_path):
    """Verify loading from YAML matches 17_CONFIG_SCHEMA.md."""
    yaml_content = """
jarvis:
  name: "MyJarvis"
  wake_word: "jarvis"
  language: "en-IN"
vision:
  enabled: true
  camera_index: 1
  gesture_confidence: 0.90
  cooldown_ms: 600
voice:
  enabled: true
  always_listen: true
safety:
  require_confirmation_for_medium: false
  require_confirmation_for_high: true
logging:
  level: "DEBUG"
  log_raw_speech: true
  session_id_prefix: "s-custom-"
"""
    cfg_file = tmp_path / "test_config.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.jarvis.name == "MyJarvis"
    assert cfg.vision.enabled is True
    assert cfg.vision.camera_index == 1
    assert cfg.vision.gesture_confidence == 0.90
    assert cfg.voice.always_listen is True
    assert cfg.safety.require_confirmation_for_medium is False
    assert cfg.safety.require_confirmation_for_high is True
    assert cfg.logging.level == LogLevel.DEBUG
    assert cfg.logging.log_raw_speech is True
    assert cfg.logging.session_id_prefix == "s-custom-"


def test_config_validation_errors():
    """Verify invalid values are rejected at startup."""
    # Invalid confidence (> 1.0)
    with pytest.raises(ValidationError):
        JarvisConfig(vision={"gesture_confidence": 1.5})

    # Invalid confidence (< 0.0)
    with pytest.raises(ValidationError):
        JarvisConfig(vision={"gesture_confidence": -0.1})

    # Negative cooldown
    with pytest.raises(ValidationError):
        JarvisConfig(vision={"cooldown_ms": -100})

    # Invalid log level
    with pytest.raises(ValidationError):
        JarvisConfig(logging={"level": "SUPER_VERBOSE"})
