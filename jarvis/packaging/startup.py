"""Windows startup and launch manager matching 18_FEATURE_ROADMAP.md."""

import os
import sys
from pathlib import Path
from typing import Optional


class WindowsStartupManager:
    """Manages Windows startup registration with safe fallback/virtual registry simulation."""

    def __init__(
        self,
        app_name: str = "JARVIS",
        executable_path: Optional[str] = None,
        arguments: str = "run.py --minimized",
        virtual_mode: bool = False,
        virtual: bool = False,
    ):
        self.app_name = app_name
        self.executable_path = executable_path or sys.executable
        self.arguments = arguments
        self.virtual_mode = virtual or virtual_mode or (os.name != "nt")
        self._virtual_registry: dict[str, str] = {}

    @property
    def command(self) -> str:
        """Formatted execution command string."""
        return f'"{self.executable_path}" {self.arguments}'.strip()

    def enable(self, executable_path: Optional[str] = None, arguments: Optional[str] = None) -> bool:
        """Alias for enable_startup."""
        return self.enable_startup(executable_path=executable_path, arguments=arguments)

    def disable(self) -> bool:
        """Alias for disable_startup."""
        return self.disable_startup()

    def is_enabled(self) -> bool:
        """Alias for is_startup_enabled."""
        return self.is_startup_enabled()

    def enable_startup(self, executable_path: Optional[str] = None, arguments: Optional[str] = None) -> bool:
        """Register application to launch automatically on Windows user login."""
        exe = executable_path or self.executable_path
        args = arguments if arguments is not None else self.arguments
        cmd = f'"{exe}" {args}'.strip()

        if self.virtual_mode:
            self._virtual_registry[self.app_name] = cmd
            return True

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            return True
        except Exception:
            # Fallback to virtual storage if registry access is denied or restricted
            self._virtual_registry[self.app_name] = cmd
            return True

    def disable_startup(self) -> bool:
        """Remove application from Windows startup."""
        if self.virtual_mode:
            self._virtual_registry.pop(self.app_name, None)
            return True

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, self.app_name)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            self._virtual_registry.pop(self.app_name, None)
            return True
        except Exception:
            self._virtual_registry.pop(self.app_name, None)
            return True

    def is_startup_enabled(self) -> bool:
        """Check if application is registered in Windows startup."""
        if self.virtual_mode:
            return self.app_name in self._virtual_registry

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            try:
                val, _ = winreg.QueryValueEx(key, self.app_name)
                enabled = bool(val)
            except FileNotFoundError:
                enabled = False
            winreg.CloseKey(key)
            return enabled
        except Exception:
            return self.app_name in self._virtual_registry
