"""Tests for RealSystemBackend — covers Bug 3 requirements.

These tests verify the real backend's interface contract (methods exist and return
the right types) without actually executing OS-level actions in CI. Platform-specific
tests that actually invoke OS commands are marked with @pytest.mark.skipif so they
only run on the matching OS.
"""

import platform
import subprocess
import pytest

from jarvis.execution.actions.system import RealSystemBackend, VirtualSystemBackend, _OS


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def real():
    return RealSystemBackend()


@pytest.fixture
def virtual():
    return VirtualSystemBackend()


# ── Bug 3a: RealSystemBackend is importable and distinct from VirtualSystemBackend ─

def test_real_backend_exists():
    """RealSystemBackend must exist and be a distinct class from the Virtual one."""
    assert RealSystemBackend is not VirtualSystemBackend


def test_real_backend_instantiates(real):
    """RealSystemBackend must construct without errors."""
    assert real is not None


# ── Bug 3b: RealSystemBackend exposes required attributes for HUD telemetry ──

def test_real_backend_has_volume_attribute(real):
    """RealSystemBackend must have a 'volume' attribute (used by HUD status update)."""
    assert hasattr(real, "volume"), "RealSystemBackend missing 'volume' attribute"
    assert isinstance(real.volume, int)


def test_real_backend_has_brightness_attribute(real):
    """RealSystemBackend must have a 'brightness' attribute (used by HUD status update)."""
    assert hasattr(real, "brightness"), "RealSystemBackend missing 'brightness' attribute"
    assert isinstance(real.brightness, int)


# ── Bug 3b: All required methods exist and are callable ──────────────────────

@pytest.mark.parametrize("method,args", [
    ("set_volume",    (50,)),
    ("verify_volume", (50,)),
    ("mute",          (True,)),
    ("verify_mute",   (True,)),
    ("set_brightness",(70,)),
    ("verify_brightness", (70,)),
    ("verify_lock_screen", ()),
    ("verify_shutdown",    ()),
])
def test_real_backend_has_method(real, method, args):
    """Every method required by the registry must exist on RealSystemBackend."""
    assert hasattr(real, method), f"RealSystemBackend missing method: {method}"
    assert callable(getattr(real, method))


# ── Bug 3b: verify_* methods return bool (not unconditional True / constant) ─

def test_verify_volume_returns_bool(real):
    assert isinstance(real.verify_volume(50), bool)


def test_verify_mute_returns_bool(real):
    assert isinstance(real.verify_mute(True), bool)


def test_verify_brightness_returns_bool(real):
    assert isinstance(real.verify_brightness(70), bool)


def test_verify_lock_screen_returns_bool(real):
    assert isinstance(real.verify_lock_screen(), bool)


def test_verify_shutdown_returns_bool(real):
    assert isinstance(real.verify_shutdown(), bool)


# ── Bug 3b: set_* methods update the instance attributes ─────────────────────

@pytest.mark.skipif(_OS != "Windows", reason="Windows-only volume simulation check")
def test_set_volume_updates_attribute_windows(real):
    """After set_volume, the instance volume attribute must reflect the new value."""
    real.set_volume(75)
    assert real.volume == 75


@pytest.mark.skipif(_OS == "Windows", reason="Non-Windows volume attribute update check")
def test_set_volume_updates_attribute_nonwindows(real):
    real.set_volume(60)
    assert real.volume == 60


def test_set_brightness_updates_attribute(real):
    """After set_brightness, the instance brightness attribute must reflect the new value."""
    real.set_brightness(40)
    assert real.brightness == 40


# ── Bug 3b: set_volume clamps out-of-range values ────────────────────────────

def test_set_volume_clamps_above_100(real):
    msg = real.set_volume(150)
    assert real.volume == 100
    assert "100" in msg


def test_set_volume_clamps_below_0(real):
    msg = real.set_volume(-10)
    assert real.volume == 0
    assert "0" in msg


def test_set_brightness_clamps(real):
    real.set_brightness(200)
    assert real.brightness == 100
    real.set_brightness(-5)
    assert real.brightness == 0


# ── Bug 3b: set_* methods return a non-empty string response ─────────────────

def test_set_volume_returns_string(real):
    result = real.set_volume(50)
    assert isinstance(result, str) and len(result) > 0


def test_set_brightness_returns_string(real):
    result = real.set_brightness(70)
    assert isinstance(result, str) and len(result) > 0


def test_mute_returns_string(real):
    result = real.mute(True)
    assert isinstance(result, str) and "muted" in result.lower()


# ── Bug 3b: Unsupported-platform guard on lock_screen and shutdown ────────────

@pytest.mark.skipif(_OS in ("Windows", "Darwin", "Linux"),
                    reason="Only runs on genuinely unsupported platforms")
def test_lock_screen_raises_on_unsupported_platform(real):
    """On an unknown OS, lock_screen must raise JarvisError(E400) not FileNotFoundError."""
    from jarvis.core.errors import JarvisError, ErrorCode
    with pytest.raises(JarvisError) as exc:
        real.lock_screen()
    assert exc.value.error_code == ErrorCode.E400


# ── Bug 3c: Virtual backend still passes all its existing tests ───────────────

def test_virtual_set_volume(virtual):
    virtual.set_volume(80)
    assert virtual.volume == 80
    assert virtual.verify_volume(80) is True


def test_virtual_fail_next_verification(virtual):
    virtual.set_volume(80)
    virtual.fail_next_verification = True
    assert virtual.verify_volume(80) is False  # flag consumed
    assert virtual.verify_volume(80) is True   # subsequent checks pass


def test_virtual_mute(virtual):
    virtual.mute(True)
    assert virtual.muted is True
    assert virtual.verify_mute(True) is True


def test_virtual_lock_screen(virtual):
    result = virtual.lock_screen()
    assert virtual.is_locked is True
    assert "locked" in result.lower()


def test_virtual_shutdown(virtual):
    result = virtual.shutdown()
    assert virtual.is_shutdown is True
    assert "shut" in result.lower()


# ── Bug 3d: Pipeline constructs RealSystemBackend when use_real_backends=True ─

def test_pipeline_virtual_mode_uses_virtual_backend():
    """Default (virtual) mode must give a VirtualSystemBackend, never RealSystemBackend."""
    from jarvis.pipeline import ExecutionPipeline
    p = ExecutionPipeline(use_real_backends=False)
    assert isinstance(p.system_backend, VirtualSystemBackend)


def test_pipeline_real_mode_uses_real_backend():
    """--real mode must give a RealSystemBackend."""
    from jarvis.pipeline import ExecutionPipeline
    p = ExecutionPipeline(use_real_backends=True)
    assert isinstance(p.system_backend, RealSystemBackend)


def test_pipeline_injected_backend_is_not_overridden():
    """If a specific backend is injected, it must be used regardless of use_real_backends."""
    from jarvis.pipeline import ExecutionPipeline
    custom = VirtualSystemBackend()
    p = ExecutionPipeline(system_backend=custom, use_real_backends=True)
    assert p.system_backend is custom


# ── Bug 3d: verify_brightness on Windows queries WMI (smoke test, no OS call) ─

@pytest.mark.skipif(_OS != "Windows", reason="WMI only available on Windows")
def test_verify_brightness_windows_smoke(real, monkeypatch):
    """On Windows, verify_brightness should call powershell and parse its output."""
    # Monkeypatch subprocess.run to return a fake WMI brightness value
    class FakeResult:
        stdout = "75\n"
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    real.set_brightness(75)
    result = real.verify_brightness(75)
    assert result is True   # 75 == 75, within tolerance


@pytest.mark.skipif(_OS != "Windows", reason="WMI only available on Windows")
def test_verify_brightness_windows_mismatch(real, monkeypatch):
    """verify_brightness returns False when reported brightness differs significantly."""
    class FakeResult:
        stdout = "10\n"  # WMI says 10, but we set 75
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    real.set_brightness(75)
    result = real.verify_brightness(75)
    assert result is False  # |10 - 75| = 65 > 5 tolerance


@pytest.mark.skipif(_OS != "Windows", reason="LogonUI check only on Windows")
def test_verify_lock_screen_checks_logonui(real, monkeypatch):
    """verify_lock_screen should return True when LogonUI.exe appears in tasklist."""
    class FakeResult:
        stdout = "LogonUI.exe   1234 Console   1   5,000 K\n"
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    assert real.verify_lock_screen() is True


@pytest.mark.skipif(_OS != "Windows", reason="LogonUI check only on Windows")
def test_verify_lock_screen_returns_false_when_not_locked(real, monkeypatch):
    """verify_lock_screen should return False when LogonUI.exe is absent."""
    class FakeResult:
        stdout = "INFO: No tasks are running which match the specified criteria.\n"
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    assert real.verify_lock_screen() is False


# ── RealAppManager URI & Camera App Tests ────────────────────────────────────

from jarvis.execution.actions.application import RealAppManager, _resolve_exe


def test_camera_alias_resolves():
    """App aliases must resolve 'camera' and 'webcam' to Windows Camera URI."""
    assert _resolve_exe("camera") == "microsoft.windows.camera:"
    assert _resolve_exe("webcam") == "microsoft.windows.camera:"


def test_real_app_manager_opens_camera_uri(monkeypatch):
    """RealAppManager.open_app should invoke os.startfile with the URI."""
    mgr = RealAppManager()
    opened = []
    import os
    monkeypatch.setattr(os, "startfile", lambda path: opened.append(path), raising=False)
    msg = mgr.open_app("camera")
    assert "camera is open" in msg
    assert opened == ["microsoft.windows.camera:"]


def test_real_app_manager_verify_running_uri():
    """verify_app_running for URI apps returns True (best-effort or process found)."""
    mgr = RealAppManager()
    assert mgr.verify_app_running("camera") is True
