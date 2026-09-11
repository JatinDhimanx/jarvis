"""Lightweight local HTTP server for JARVIS Tactical HUD matching 01_SYSTEM_ARCHITECTURE.md."""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import threading
from typing import Any, Dict, Optional
import uuid

from jarvis.core.state_machine import State, StateMachine
from jarvis.router.router import InputEvent
from jarvis.ui.hud_state import HUDStateManager

STATIC_DIR = Path(__file__).parent / "static"


class HUDRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler serving static HUD UI and JSON API endpoints."""

    def __init__(self, *args: Any, hud_state: HUDStateManager, pipeline: Optional[Any] = None, **kwargs: Any):
        self.hud_state = hud_state
        self.pipeline = pipeline
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps(self.hud_state.to_dict()).encode("utf-8")
            self.wfile.write(data)
            return

        if self.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        if self.path == "/api/stop":
            # Emergency Stop override
            if self.pipeline and hasattr(self.pipeline, "trigger_emergency_stop"):
                self.pipeline.trigger_emergency_stop()
            else:
                self.hud_state.set_state(State.STOPPED)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "stopped"}).encode("utf-8"))
            return

        if self.path == "/api/confirm":
            confirmed = bool(payload.get("confirmed", False))
            result = None
            if self.pipeline and hasattr(self.pipeline, "confirm_pending"):
                result = self.pipeline.confirm_pending(confirmed=confirmed)
            else:
                self.hud_state.set_state(State.IDLE if confirmed else State.IDLE)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "result": result}).encode("utf-8"))
            return

        if self.path == "/api/command":
            text = payload.get("text", "").strip()
            channel = payload.get("channel", "voice")
            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Empty command text"}).encode("utf-8"))
                return

            event = InputEvent(
                event_id=f"web-{uuid.uuid4().hex[:6]}",
                channel=channel,
                raw_payload=text,
            )
            result = self.pipeline.process_event(event) if self.pipeline else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Safely serialise result — enum values and other non-JSON types
            # are converted to their string representation.
            def _safe(obj):
                if hasattr(obj, "value"):   # Enum
                    return obj.value
                return str(obj)
            self.wfile.write(
                json.dumps({"status": "ok", "result": result}, default=_safe).encode("utf-8")
            )
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stdout logging to avoid cluttering test outputs."""
        pass


class HUDServer:
    """Manager for running local HUD HTTP server in background thread."""

    def __init__(
        self,
        hud_state: HUDStateManager,
        pipeline: Optional[Any] = None,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self.hud_state = hud_state
        self.pipeline = pipeline
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start server in daemon background thread."""
        def handler_factory(*args: Any, **kwargs: Any) -> HUDRequestHandler:
            return HUDRequestHandler(*args, hud_state=self.hud_state, pipeline=self.pipeline, **kwargs)

        self._server = HTTPServer((self.host, self.port), handler_factory)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shutdown server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
