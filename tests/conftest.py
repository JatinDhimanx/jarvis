"""Shared test fixtures for JARVIS test suite."""

import pytest
from jarvis.core.config import JarvisConfig, LoggingSection, SafetySection, VisionSection, VoiceSection
from jarvis.execution.actions.application import VirtualAppManager
from jarvis.execution.actions.system import VirtualSystemBackend
from jarvis.pipeline import ExecutionPipeline


@pytest.fixture
def test_config():
    """Default test config matching 17_CONFIG_SCHEMA.md."""
    return JarvisConfig(
        vision=VisionSection(enabled=False, cooldown_ms=500),
        voice=VoiceSection(enabled=True, always_listen=False),
        safety=SafetySection(require_confirmation_for_medium=True, require_confirmation_for_high=True),
        logging=LoggingSection(level="DEBUG", log_raw_speech=False, session_id_prefix="s-test-"),
    )


@pytest.fixture
def system_backend():
    return VirtualSystemBackend()


@pytest.fixture
def app_manager():
    return VirtualAppManager()


@pytest.fixture
def pipeline(test_config, system_backend, app_manager):
    return ExecutionPipeline(
        config=test_config,
        system_backend=system_backend,
        app_manager=app_manager,
    )
