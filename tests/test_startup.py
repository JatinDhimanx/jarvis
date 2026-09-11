"""Tests for Windows Startup Manager."""

import pytest
from jarvis.packaging.startup import WindowsStartupManager


def test_startup_virtual_mode():
    """Verify virtual startup manager enables, checks, and disables run entries."""
    manager = WindowsStartupManager(app_name="JarvisTestApp", virtual=True)
    assert not manager.is_enabled()

    success = manager.enable()
    assert success
    assert manager.is_enabled()

    disabled = manager.disable()
    assert disabled
    assert not manager.is_enabled()


def test_startup_command_builder():
    """Verify startup command formatting."""
    manager = WindowsStartupManager(app_name="JarvisAI", executable_path="C:\\Jarvis\\python.exe", virtual=True)
    assert "C:\\Jarvis\\python.exe" in manager.command
    assert "run.py" in manager.command
