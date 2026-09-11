"""Tests for HUDServer HTTP endpoints matching 01_SYSTEM_ARCHITECTURE.md."""

import json
import socket
import time
import urllib.request
import pytest

from jarvis.pipeline import ExecutionPipeline
from jarvis.ui.hud_server import HUDServer
from jarvis.ui.hud_state import HUDStateManager


def get_free_port() -> int:
    """Find a random available local port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def hud_server_instance():
    port = get_free_port()
    state_mgr = HUDStateManager()
    pipeline = ExecutionPipeline(hud_state=state_mgr)
    server = HUDServer(hud_state=state_mgr, pipeline=pipeline, host="127.0.0.1", port=port)
    server.start()
    time.sleep(0.1)  # allow thread to bind
    yield server, f"http://127.0.0.1:{port}", state_mgr, pipeline
    server.stop()


def test_hud_server_serves_html(hud_server_instance):
    _, base_url, _, _ = hud_server_instance
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "J.A.R.V.I.S." in content
        assert "reactor-core" in content


def test_hud_server_api_status(hud_server_instance):
    _, base_url, state_mgr, _ = hud_server_instance
    state_mgr.record_input_event("voice", "hello jarvis", 0.99, "GREETING")

    req = urllib.request.Request(f"{base_url}/api/status")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["state"] == "IDLE"
        assert data["last_event"]["payload"] == "hello jarvis"
        assert data["last_event"]["confidence"] == 0.99


def test_hud_server_api_emergency_stop(hud_server_instance):
    _, base_url, state_mgr, pipeline = hud_server_instance
    req = urllib.request.Request(f"{base_url}/api/stop", method="POST")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "stopped"

    assert state_mgr.to_dict()["state"] == "STOPPED"
    assert pipeline.state_machine.current_state.value == "STOPPED"


def test_hud_server_api_confirm_endpoint(hud_server_instance):
    _, base_url, state_mgr, pipeline = hud_server_instance
    post_data = json.dumps({"confirmed": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/confirm",
        data=post_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
