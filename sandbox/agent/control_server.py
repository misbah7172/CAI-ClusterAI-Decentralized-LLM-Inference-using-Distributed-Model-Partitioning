"""
REST + WebSocket control server for the CAI Sandbox Node Agent.

Exposes node status, hardware info, metrics, and chunk assignment
endpoints with token-based authentication.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class AgentHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for the node agent control API.

    Endpoints
    ---------
    GET  /agent/status    — Node status and health
    GET  /agent/hardware  — Hardware capabilities
    GET  /agent/metrics   — Energy and performance metrics
    POST /agent/assign    — Receive chunk assignment
    POST /agent/deploy    — Deploy model chunks
    GET  /health          — Simple health check
    """

    # Class-level references set by ControlServer.start()
    _get_status: Optional[Callable] = None
    _get_hardware: Optional[Callable] = None
    _get_metrics: Optional[Callable] = None
    _handle_assign: Optional[Callable] = None
    _handle_deploy: Optional[Callable] = None
    _auth_middleware = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._json_response(200, {"status": "healthy", "timestamp": time.time()})
            return

        # Auth required for all other endpoints
        if self._auth_middleware:
            ok, claims = self._auth_middleware.authenticate_request(self)
            if not ok:
                return

        if path == "/agent/status":
            if self._get_status:
                data = self._get_status()
                self._json_response(200, data)
            else:
                self._json_response(503, {"error": "Status not available"})

        elif path == "/agent/hardware":
            if self._get_hardware:
                data = self._get_hardware()
                self._json_response(200, data)
            else:
                self._json_response(503, {"error": "Hardware info not available"})

        elif path == "/agent/metrics":
            if self._get_metrics:
                data = self._get_metrics()
                self._json_response(200, data)
            else:
                self._json_response(503, {"error": "Metrics not available"})

        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self) -> None:
        # Auth required for all POST endpoints
        if self._auth_middleware:
            ok, claims = self._auth_middleware.authenticate_request(self)
            if not ok:
                return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        if self.path == "/agent/assign":
            if self._handle_assign:
                try:
                    data = json.loads(body.decode("utf-8"))
                    result = self._handle_assign(data)
                    self._json_response(200, result)
                except json.JSONDecodeError:
                    self._json_response(400, {"error": "Invalid JSON"})
                except Exception as exc:
                    self._json_response(500, {"error": str(exc)})
            else:
                self._json_response(503, {"error": "Assignment handler not available"})

        elif self.path == "/agent/deploy":
            if self._handle_deploy:
                try:
                    data = json.loads(body.decode("utf-8"))
                    result = self._handle_deploy(data)
                    self._json_response(200, result)
                except json.JSONDecodeError:
                    self._json_response(400, {"error": "Invalid JSON"})
                except Exception as exc:
                    self._json_response(500, {"error": str(exc)})
            else:
                self._json_response(503, {"error": "Deploy handler not available"})

        else:
            self._json_response(404, {"error": "not found"})

    def _json_response(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:
        logger.debug(format, *args)


class ControlServer:
    """REST control server for the node agent.

    Parameters
    ----------
    port : int
        HTTP port to listen on.
    auth_middleware : AuthMiddleware, optional
        Auth middleware for token validation.
    """

    def __init__(
        self,
        port: int = 8100,
        auth_middleware=None,
    ):
        self._port = port
        self._auth_middleware = auth_middleware
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

        # Callback registrations
        self._callbacks: Dict[str, Optional[Callable]] = {
            "get_status": None,
            "get_hardware": None,
            "get_metrics": None,
            "handle_assign": None,
            "handle_deploy": None,
        }

    def register_callback(self, name: str, callback: Callable) -> None:
        """Register a callback for a specific endpoint."""
        if name in self._callbacks:
            self._callbacks[name] = callback

    def start(self) -> None:
        """Start the control server in a background thread."""
        # Wire up callbacks to handler class
        AgentHTTPHandler._get_status = self._callbacks.get("get_status")
        AgentHTTPHandler._get_hardware = self._callbacks.get("get_hardware")
        AgentHTTPHandler._get_metrics = self._callbacks.get("get_metrics")
        AgentHTTPHandler._handle_assign = self._callbacks.get("handle_assign")
        AgentHTTPHandler._handle_deploy = self._callbacks.get("handle_deploy")
        AgentHTTPHandler._auth_middleware = self._auth_middleware

        self._server = HTTPServer(("0.0.0.0", self._port), AgentHTTPHandler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="agent-control-server",
        )
        self._thread.start()
        logger.info("Agent control server started on port %d", self._port)

    def stop(self) -> None:
        """Stop the control server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Agent control server stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
