"""Tests for Settings Manager and Configuration Tools."""

import pytest
from pathlib import Path
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.packaging.settings import SettingsManager
from jarvis.pipeline import ExecutionPipeline
from jarvis.router.router import InputEvent


def test_settings_manager_get_set(tmp_path):
    """Test getting and setting configuration parameters via dotted paths."""
    config_file = tmp_path / "test_config.yaml"
    manager = SettingsManager(config_path=config_file)

    # Defaults
    assert manager.get("vision.enabled") is False
    assert manager.get("jarvis.wake_word") == "jarvis"

    # Set boolean
    manager.set("vision.enabled", True)
    assert manager.get("vision.enabled") is True

    # Set string
    manager.set("jarvis.wake_word", "edith")
    assert manager.get("jarvis.wake_word") == "edith"

    # Set int
    manager.set("voice.silence_timeout_ms", 3000)
    assert manager.get("voice.silence_timeout_ms") == 3000

    # Test file was saved
    assert config_file.exists()

    # Reload from disk
    new_manager = SettingsManager(config_path=config_file)
    assert new_manager.get("vision.enabled") is True
    assert new_manager.get("jarvis.wake_word") == "edith"


def test_settings_manager_invalid_keys(tmp_path):
    """Verify appropriate error on invalid configuration key."""
    manager = SettingsManager(config_path=tmp_path / "cfg.yaml")

    with pytest.raises(JarvisError) as exc_info:
        manager.get("nonexistent.key")
    assert exc_info.value.code == ErrorCode.E400

    with pytest.raises(JarvisError) as exc_info:
        manager.set("vision.invalid_field", 123)
    assert exc_info.value.code == ErrorCode.E400


def test_settings_tools_via_pipeline(tmp_path):
    """Verify read_setting and update_setting through the safety policy in ExecutionPipeline."""
    config_file = tmp_path / "app_config.yaml"
    settings_mgr = SettingsManager(config_path=config_file)
    pipeline = ExecutionPipeline(settings_manager=settings_mgr)

    # Read setting (LOW risk -> immediate execution)
    event_read = InputEvent(
        event_id="e-read-set",
        channel="voice",
        raw_payload="read_setting",
        parsed_intent="read_setting",
        parameters={"key": "jarvis.wake_word"},
    )
    res_read = pipeline.process_event(event_read)
    assert res_read["status"] == "success"
    assert "jarvis" in str(res_read["response_text"])

    # Update setting (MEDIUM risk -> requires confirmation)
    event_update = InputEvent(
        event_id="e-update-set",
        channel="voice",
        raw_payload="update_setting",
        parsed_intent="update_setting",
        parameters={"key": "jarvis.wake_word", "value": "friday"},
    )
    res_prompt = pipeline.process_event(event_update)
    assert res_prompt["status"] == "needs_confirmation"

    # Confirm update
    res_confirmed = pipeline.confirm_action(confirmed=True)
    assert res_confirmed["status"] == "success"
    assert settings_mgr.get("jarvis.wake_word") == "friday"
