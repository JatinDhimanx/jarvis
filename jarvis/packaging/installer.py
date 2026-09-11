"""Installer and pre-flight self-test validator matching 18_FEATURE_ROADMAP.md."""

import importlib
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from jarvis.core.state_machine import State, StateMachine
from jarvis.policy.safety import SafetyPolicy
from jarvis.registry.registry import ToolRegistry


class DiagnosticReport(BaseModel):
    all_passed: bool
    python_version: str
    checks: Dict[str, bool]
    notes: List[str]


class EnvironmentValidator:
    """Pre-flight diagnostic validator and installer helper for JARVIS."""

    def __init__(self, workspace_root: Optional[str | Path] = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()

    def check_python_version(self) -> bool:
        """Validate Python runtime is 3.11 or greater."""
        return sys.version_info >= (3, 11)

    def check_dependencies(self) -> Dict[str, bool]:
        """Check required core packages are importable."""
        packages = ["pydantic", "yaml", "pytest"]
        results = {}
        for pkg in packages:
            try:
                importlib.import_module(pkg)
                results[pkg] = True
            except ImportError:
                results[pkg] = False
        return results

    def ensure_directories(self) -> List[str]:
        """Ensure necessary runtime directories exist."""
        dirs = ["config", "logs", "models"]
        created = []
        for d in dirs:
            target = self.workspace_root / d
            target.mkdir(parents=True, exist_ok=True)
            created.append(d)
        return created

    def verify_workspace_layout(self) -> bool:
        """Ensure necessary runtime directories exist or can be created."""
        try:
            self.ensure_directories()
            return True
        except Exception:
            return False

    def run_diagnostics(self) -> DiagnosticReport:
        """Run full pre-flight self-test diagnostics."""
        notes = []
        checks = {}

        # 1. Python version check
        checks["python_version"] = self.check_python_version()
        if not checks["python_version"]:
            notes.append(f"Python 3.11+ required, current is {sys.version}")

        # 2. Dependencies check
        dep_results = self.check_dependencies()
        checks["dependencies"] = all(dep_results.values())
        if not checks["dependencies"]:
            missing = [k for k, v in dep_results.items() if not v]
            notes.append(f"Missing dependencies: {', '.join(missing)}")

        # 3. Workspace directories
        checks["directories"] = self.verify_workspace_layout()
        checks["workspace_dirs"] = checks["directories"]

        # 4. State machine sanity check
        try:
            sm = StateMachine(State.IDLE)
            sm.transition_to(State.LISTENING)
            sm.transition_to(State.THINKING)
            sm.reset_to_idle()
            checks["state_machine"] = True
        except Exception as ex:
            checks["state_machine"] = False
            notes.append(f"State machine check failed: {ex}")

        # 5. Safety policy check
        try:
            policy = SafetyPolicy()
            dec_high = policy.evaluate("shutdown")
            dec_low = policy.evaluate("open_app")
            checks["safety_policy"] = (dec_high.requires_confirmation is True and dec_low.requires_confirmation is False)
        except Exception as ex:
            checks["safety_policy"] = False
            notes.append(f"Safety policy check failed: {ex}")

        # 6. Tool registry check
        try:
            reg = ToolRegistry()
            from jarvis.execution.actions.system import register_system_tools
            register_system_tools(reg)
            checks["tools_registered"] = reg.has_tool("set_volume")
            checks["tool_registry"] = checks["tools_registered"]
        except Exception as ex:
            checks["tools_registered"] = False
            checks["tool_registry"] = False
            notes.append(f"Tool registry check failed: {ex}")

        all_passed = all(checks.values())
        return DiagnosticReport(
            all_passed=all_passed,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            checks=checks,
            notes=notes,
        )

    def run_self_test(self) -> DiagnosticReport:
        """Alias for run_diagnostics."""
        return self.run_diagnostics()
