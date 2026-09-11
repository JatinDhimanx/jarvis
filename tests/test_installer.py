"""Tests for Environment Validator and Pre-flight Installer Diagnostics."""

import pytest
from pathlib import Path
from jarvis.packaging.installer import EnvironmentValidator, DiagnosticReport


def test_environment_validator_diagnostics(tmp_path):
    """Verify validator executes checks and outputs structured diagnostic report."""
    validator = EnvironmentValidator(workspace_root=tmp_path)
    report = validator.run_diagnostics()

    assert isinstance(report, DiagnosticReport)
    assert report.python_version != ""
    assert "python_version" in report.checks
    assert "dependencies" in report.checks
    assert "directories" in report.checks
    assert "tools_registered" in report.checks
    assert "state_machine" in report.checks

    # Verify directory creation
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "models").exists()
    assert (tmp_path / "config").exists()


def test_environment_validator_ensure_directories(tmp_path):
    """Verify ensure_directories creates expected folders."""
    validator = EnvironmentValidator(workspace_root=tmp_path)
    created = validator.ensure_directories()

    assert "logs" in created
    assert "models" in created
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "models").is_dir()
