"""Application action group (LOW risk) matching 08_ACTION_ENGINE.md and 09_TOOL_REGISTRY.md."""

import subprocess
import time
from typing import Optional, Set
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


# ── Known app aliases → Windows executable names ─────────────────────────────
APP_ALIASES: dict = {
    "notepad":        "notepad.exe",
    "calculator":     "calc.exe",
    "calc":           "calc.exe",
    "paint":          "mspaint.exe",
    "mspaint":        "mspaint.exe",
    "explorer":       "explorer.exe",
    "wordpad":        "wordpad.exe",
    "cmd":            "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell":     "powershell.exe",
    "taskmgr":        "taskmgr.exe",
    "task manager":   "taskmgr.exe",
    "chrome":         "chrome.exe",
    "firefox":        "firefox.exe",
    "edge":           "msedge.exe",
    "vlc":            "vlc.exe",
    "vscode":         "code.exe",
    "vs code":        "code.exe",
    "word":           "winword.exe",
    "excel":          "excel.exe",
    "spotify":        "spotify.exe",
    "discord":        "discord.exe",
    "snipping tool":  "SnippingTool.exe",
    "snip":           "SnippingTool.exe",
    "settings":       "ms-settings:",
    "control panel":  "control.exe",
}


def _resolve_exe(app_name: str) -> str:
    """Resolve human-readable app name to its Windows executable."""
    key = app_name.strip().lower()
    return APP_ALIASES.get(key, app_name.strip())


def _is_process_running(exe_name: str) -> bool:
    """Check if a process is running via tasklist."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
            stderr=subprocess.DEVNULL, text=True
        )
        return exe_name.lower() in out.lower()
    except Exception:
        return False


# ── Simulation backend (kept for unit tests) ─────────────────────────────────

class VirtualAppManager:
    """Simulation-only app manager — used in tests, never touches the OS."""

    def __init__(self):
        self.running_apps: Set[str] = set()
        self.fail_next_verification: bool = False

    def open_app(self, app_name: str) -> str:
        self.running_apps.add(app_name.strip().lower())
        return f"{app_name} is open."

    def verify_app_running(self, app_name: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return app_name.strip().lower() in self.running_apps

    def close_app(self, app_name: str, unsaved: bool = False) -> str:
        self.running_apps.discard(app_name.strip().lower())
        return f"{app_name} is closed."

    def verify_app_closed(self, app_name: str, unsaved: bool = False) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return app_name.strip().lower() not in self.running_apps

    def restart_app(self, app_name: str) -> str:
        self.running_apps.add(app_name.strip().lower())
        return f"{app_name} has been restarted."

    def verify_app_restarted(self, app_name: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return app_name.strip().lower() in self.running_apps


# ── Real Windows backend ──────────────────────────────────────────────────────

class RealAppManager:
    """Real Windows app manager — actually launches and kills processes."""

    def open_app(self, app_name: str) -> str:
        exe = _resolve_exe(app_name)
        try:
            if exe.startswith("ms-"):
                # URI-based apps (e.g. ms-settings:)
                subprocess.Popen(["start", exe], shell=True)
            else:
                subprocess.Popen(exe, shell=True)
            return f"{app_name} is open."
        except FileNotFoundError:
            raise RuntimeError(f"Cannot find '{exe}'. Is it installed and on PATH?")
        except Exception as e:
            raise RuntimeError(f"Failed to open {app_name}: {e}")

    def verify_app_running(self, app_name: str) -> bool:
        exe = _resolve_exe(app_name)
        if exe.startswith("ms-"):
            return True  # URI-based — best-effort
        # Poll up to 2 s for the process to appear
        for _ in range(4):
            if _is_process_running(exe):
                return True
            time.sleep(0.5)
        return False

    def close_app(self, app_name: str, unsaved: bool = False) -> str:
        exe = _resolve_exe(app_name)
        try:
            subprocess.run(
                ["taskkill", "/IM", exe, "/F"],
                check=True, capture_output=True
            )
            return f"{app_name} is closed."
        except subprocess.CalledProcessError:
            return f"{app_name} was not running."
        except Exception as e:
            raise RuntimeError(f"Failed to close {app_name}: {e}")

    def verify_app_closed(self, app_name: str, unsaved: bool = False) -> bool:
        exe = _resolve_exe(app_name)
        return not _is_process_running(exe)

    def restart_app(self, app_name: str) -> str:
        self.close_app(app_name)
        time.sleep(0.5)
        return self.open_app(app_name)

    def verify_app_restarted(self, app_name: str) -> bool:
        return self.verify_app_running(app_name)


# Production singleton — uses the real OS manager
_DEFAULT_APP_MANAGER = RealAppManager()


def get_default_app_manager() -> RealAppManager:
    return _DEFAULT_APP_MANAGER


def register_application_tools(registry: ToolRegistry, manager=None) -> None:
    """Register application management tools into ToolRegistry."""
    m = manager or _DEFAULT_APP_MANAGER

    # open_app tool
    open_app_decl = ToolDeclaration(
        name="open_app",
        version=1,
        description="Launch an application by name",
        input_schema={
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_process_running",
    )
    registry.register_tool(open_app_decl, handler=m.open_app, verifier=m.verify_app_running)

    # close_app tool
    close_app_decl = ToolDeclaration(
        name="close_app",
        version=1,
        description="Close a running application",
        input_schema={
            "type": "object",
            "properties": {
                "app_name": {"type": "string"},
                "unsaved": {"type": "boolean", "default": False},
            },
            "required": ["app_name"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_process_terminated",
    )
    registry.register_tool(close_app_decl, handler=m.close_app, verifier=m.verify_app_closed)

    # restart_app tool
    restart_app_decl = ToolDeclaration(
        name="restart_app",
        version=1,
        description="Restart a running application",
        input_schema={
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_process_restarted",
    )
    registry.register_tool(restart_app_decl, handler=m.restart_app, verifier=m.verify_app_restarted)
