"""
REST API server for the CAI Sandbox Remote Controller.

Runs on the primary node and exposes cluster management endpoints
with CORS support for desktop app integration.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from sandbox.config import CONTROLLER_API_PORT

logger = logging.getLogger(__name__)


class ControllerAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for the controller REST API.

    Endpoints
    ---------
    GET   /api/v1/cluster/nodes          — List all nodes
    GET   /api/v1/cluster/nodes/{id}     — Node details
    GET   /api/v1/cluster/status         — Cluster health
    GET   /api/v1/cluster/metrics        — Aggregated metrics
    POST  /api/v1/cluster/register       — Register a new worker
    POST  /api/v1/cluster/heartbeat      — Worker heartbeat
    POST  /api/v1/models/deploy          — Deploy model
    GET   /api/v1/models/deployments     — List deployments
    POST  /api/v1/inference/run          — Trigger inference
    GET   /api/v1/inference/jobs         — List inference jobs
    POST  /api/v1/cluster/tokens         — Generate access token
    GET   /health                        — Health check
    """

    _controller = None  # RemoteController
    _agent = None       # NodeAgent
    _auth_middleware = None

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "/health":
            self._json_response(200, {"status": "healthy", "timestamp": time.time()})
            return

        if not self._controller:
            self._json_response(503, {"error": "Controller not initialized"})
            return

        # Cluster endpoints
        if path == "/api/v1/cluster/nodes":
            nodes = self._controller.list_nodes()
            self._json_response(200, {"nodes": nodes, "count": len(nodes)})

        elif path.startswith("/api/v1/cluster/nodes/"):
            node_id = path.split("/")[-1]
            details = self._controller.get_node_details(node_id)
            if details:
                self._json_response(200, details)
            else:
                self._json_response(404, {"error": f"Node '{node_id}' not found"})

        elif path == "/api/v1/cluster/status":
            status = self._controller.get_cluster_status()
            self._json_response(200, status)

        elif path == "/api/v1/cluster/metrics":
            metrics = self._controller.get_cluster_metrics()
            self._json_response(200, metrics)

        elif path == "/api/v1/models/deployments":
            deployments = self._controller.list_deployments()
            self._json_response(200, {"deployments": deployments})

        elif path == "/api/v1/inference/jobs":
            jobs = self._controller.list_inference_jobs()
            self._json_response(200, {"jobs": jobs})

        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        path = urlparse(self.path).path.rstrip("/")

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._json_response(400, {"error": "Invalid JSON"})
            return

        if not self._controller:
            self._json_response(503, {"error": "Controller not initialized"})
            return

        # Worker registration
        if path == "/api/v1/cluster/register":
            if self._agent:
                result = self._agent.handle_worker_registration(
                    node_id=data.get("node_id", ""),
                    access_token=data.get("access_token", ""),
                    hardware=data.get("hardware", {}),
                    address=data.get("address", ""),
                )
                self._json_response(200 if result.get("accepted") else 401, result)
            else:
                self._json_response(503, {"error": "Agent not available"})

        # Worker heartbeat
        elif path == "/api/v1/cluster/heartbeat":
            if self._agent:
                result = self._agent.handle_worker_heartbeat(
                    node_id=data.get("node_id", ""),
                    hardware=data.get("hardware", {}),
                    energy=data.get("energy", {}),
                    load_pct=float(data.get("load_pct", 0)),
                    active_chunks=data.get("active_chunks", []),
                )
                self._json_response(200, result)
            else:
                self._json_response(503, {"error": "Agent not available"})

        # Model deployment
        elif path == "/api/v1/models/deploy":
            result = self._controller.deploy_model(
                model_name=data.get("model_name", ""),
                num_chunks=data.get("num_chunks"),
                strategy=data.get("strategy", "balanced"),
                target_nodes=data.get("target_nodes"),
                dtype=data.get("dtype", "float16"),
            )
            self._json_response(200 if result.get("success") else 400, result)

        # Inference
        elif path == "/api/v1/inference/run":
            result = self._controller.trigger_inference(
                model_name=data.get("model_name", ""),
                prompt=data.get("prompt", ""),
                max_tokens=int(data.get("max_tokens", 100)),
                temperature=float(data.get("temperature", 0.7)),
            )
            self._json_response(200 if result.get("success") else 400, result)

        # Token generation
        elif path == "/api/v1/cluster/tokens":
            try:
                from sandbox.auth.token_manager import TokenManager
                tm = TokenManager()
                token = tm.generate_cluster_token(
                    cluster_id=data.get("cluster_id", ""),
                    node_role=data.get("role", "worker"),
                    expiry_hours=int(data.get("expires_hours", 720)),
                )
                self._json_response(200, {"token": token, "message": "Token generated"})
            except Exception as exc:
                self._json_response(500, {"error": str(exc)})

        # Node removal
        elif path == "/api/v1/cluster/remove-node":
            node_id = data.get("node_id", "")
            if self._controller.remove_node(node_id):
                self._json_response(200, {"message": f"Node '{node_id}' removed"})
            else:
                self._json_response(400, {"error": f"Cannot remove node '{node_id}'"})

        else:
            self._json_response(404, {"error": "Not found"})

    def _json_response(self, status: int, data: dict) -> None:
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _add_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def log_message(self, format, *args) -> None:
        logger.debug(format, *args)


class ControllerAPIServer:
    """REST API server for the Remote Controller.

    Parameters
    ----------
    controller : RemoteController
        The cluster controller.
    agent : NodeAgent
        The primary node agent.
    port : int
        Port to listen on.
    auth_middleware : AuthMiddleware, optional
        Auth middleware for token validation.
    """

    def __init__(
        self,
        controller,
        agent,
        port: int = CONTROLLER_API_PORT,
        auth_middleware=None,
    ):
        self._controller = controller
        self._agent = agent
        self._port = port
        self._auth_middleware = auth_middleware
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the API server."""
        ControllerAPIHandler._controller = self._controller
        ControllerAPIHandler._agent = self._agent
        ControllerAPIHandler._auth_middleware = self._auth_middleware

        self._server = HTTPServer(("0.0.0.0", self._port), ControllerAPIHandler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="controller-api",
        )
        self._thread.start()
        logger.info("Controller API server started on port %d", self._port)

    def stop(self) -> None:
        """Stop the API server."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Controller API server stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
