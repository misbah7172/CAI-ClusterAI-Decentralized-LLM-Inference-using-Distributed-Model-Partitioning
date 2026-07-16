"""
Node Agent — core agent running on every CAI Sandbox node.

Handles cluster registration, heartbeating, chunk assignment,
and orchestrates local CAI services. This is the central nervous
system of each sandbox node.

Usage::

    from sandbox.agent.node_agent import NodeAgent
    from sandbox.config import SandboxConfig, ClusterMode, NodeRole

    config = SandboxConfig(mode=ClusterMode.MULTI_WORKER, role=NodeRole.WORKER)
    agent = NodeAgent(config)
    agent.start()
    agent.register("192.168.1.100:50100", "my-token")
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from sandbox.config import (
    SandboxConfig,
    ClusterMode,
    NodeRole,
    NodeState,
    HEARTBEAT_INTERVAL_S,
    HEARTBEAT_TIMEOUT_S,
)
from sandbox.agent.hardware_reporter import HardwareReport, HardwareReporter
from sandbox.agent.control_server import ControlServer

logger = logging.getLogger(__name__)


class NodeAgent:
    """Core agent running on every CAI Sandbox node.

    Responsibilities:
    - Register with a cluster's primary node
    - Send periodic heartbeats with hardware & energy metrics
    - Receive and execute chunk assignments
    - Manage local CAI services (chunk servers, gateway)

    Parameters
    ----------
    config : SandboxConfig
        Sandbox configuration for this node.
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self._config = config or SandboxConfig()
        self._node_id = self._config.node_id or f"node-{uuid.uuid4().hex[:8]}"
        self._state = NodeState.DISCONNECTED
        self._cluster_id: str = ""

        # Sub-components
        self._hw_reporter = HardwareReporter(
            node_id=self._node_id,
            interval_s=self._config.heartbeat_interval,
        )
        self._control_server = ControlServer(
            port=self._config.rest_port,
            auth_middleware=None,  # Set during start() if auth is available
        )
        self._grpc_server = None

        # Heartbeat
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._heartbeat_interval = self._config.heartbeat_interval

        # Cluster connectivity
        self._primary_address: str = ""
        self._primary_channel = None  # gRPC channel to primary
        self._primary_stub = None  # gRPC stub for primary

        # Chunk management
        self._active_chunks: Dict[int, Dict[str, Any]] = {}  # chunk_id -> info
        self._chunk_endpoints: Dict[int, str] = {}  # chunk_id -> endpoint

        # Event callbacks
        self._on_registered: Optional[Callable] = None
        self._on_deregistered: Optional[Callable] = None
        self._on_chunk_assigned: Optional[Callable] = None
        self._on_command_received: Optional[Callable] = None

        # Peer tracking (primary only)
        self._peers: Dict[str, Dict[str, Any]] = {}  # node_id -> peer info
        self._peers_lock = threading.Lock()

        # Start time
        self._start_time: float = 0.0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def state(self) -> NodeState:
        return self._state

    @property
    def cluster_id(self) -> str:
        return self._cluster_id

    @property
    def is_primary(self) -> bool:
        return self._config.role == NodeRole.PRIMARY

    @property
    def is_running(self) -> bool:
        return self._state in (NodeState.ACTIVE, NodeState.AUTHENTICATED)

    @property
    def active_chunks(self) -> List[int]:
        return list(self._active_chunks.keys())

    @property
    def peers(self) -> Dict[str, Dict[str, Any]]:
        with self._peers_lock:
            return dict(self._peers)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the node agent and all sub-components."""
        logger.info("Starting Node Agent (id=%s, role=%s)", self._node_id, self._config.role.value)
        self._start_time = time.time()

        # Start hardware reporter
        self._hw_reporter.start()

        # Register control server callbacks
        self._control_server.register_callback("get_status", self._handle_get_status)
        self._control_server.register_callback("get_hardware", self._handle_get_hardware)
        self._control_server.register_callback("get_metrics", self._handle_get_metrics)
        self._control_server.register_callback("handle_assign", self._handle_chunk_assignment)
        self._control_server.register_callback("handle_deploy", self._handle_deploy_request)

        # Start control server
        self._control_server.start()

        if self.is_primary:
            self._state = NodeState.ACTIVE
            self._cluster_id = self._cluster_id or uuid.uuid4().hex[:12]
            
            # Start control-plane gRPC server on primary
            from sandbox.agent.grpc_service import GrpcAgentServer
            self._grpc_server = GrpcAgentServer(self, port=self._config.grpc_port)
            self._grpc_server.start()
            
            logger.info("Primary node active (cluster=%s)", self._cluster_id)
        else:
            self._state = NodeState.DISCOVERED

        logger.info("Node Agent started")

    def stop(self) -> None:
        """Stop the node agent and deregister from cluster."""
        logger.info("Stopping Node Agent...")

        # Stop heartbeat
        self._stop_heartbeat()

        # Deregister from cluster
        if self._state == NodeState.ACTIVE and not self.is_primary:
            self.deregister()

        # Stop sub-components
        self._control_server.stop()
        self._hw_reporter.stop()

        # Stop primary gRPC server
        if self._grpc_server:
            self._grpc_server.stop()
            self._grpc_server = None

        # Stop local chunk servers
        if hasattr(self, "_chunk_servers"):
            for chunk_id, server in self._chunk_servers.items():
                logger.info("Stopping local chunk server for chunk %d...", chunk_id)
                try:
                    server.stop(grace=1.0)
                except Exception:
                    pass
            self._chunk_servers.clear()

        # Close gRPC channel
        if self._primary_channel:
            try:
                self._primary_channel.close()
            except Exception:
                pass
            self._primary_channel = None
            self._primary_stub = None

        self._state = NodeState.DISCONNECTED
        logger.info("Node Agent stopped")

    # ------------------------------------------------------------------
    # Registration (worker → primary)
    # ------------------------------------------------------------------

    def register(self, primary_address: str, access_token: str) -> bool:
        """Register this worker node with a cluster's primary node.

        Parameters
        ----------
        primary_address : str
            Address of the primary node (``ip:port``).
        access_token : str
            Access token generated by the primary node.

        Returns
        -------
        bool
            True if registration succeeded.
        """
        if self.is_primary:
            logger.warning("Primary nodes do not register with other nodes")
            return False

        self._state = NodeState.CONNECTING
        self._primary_address = primary_address
        logger.info("Registering with primary at %s...", primary_address)

        try:
            # Try gRPC registration
            success = self._grpc_register(primary_address, access_token)

            if success:
                self._state = NodeState.ACTIVE
                self._start_heartbeat()
                logger.info("Successfully registered with cluster '%s'", self._cluster_id)
                if self._on_registered:
                    self._on_registered(self._cluster_id)
                return True

            # Fallback to REST registration
            success = self._rest_register(primary_address, access_token)
            if success:
                self._state = NodeState.ACTIVE
                self._start_heartbeat()
                logger.info("Successfully registered with cluster '%s' (via REST)", self._cluster_id)
                if self._on_registered:
                    self._on_registered(self._cluster_id)
                return True

            self._state = NodeState.DISCONNECTED
            logger.error("Registration failed")
            return False

        except Exception as exc:
            self._state = NodeState.DISCONNECTED
            logger.error("Registration error: %s", exc)
            return False

    def deregister(self) -> None:
        """Gracefully leave the cluster."""
        if self._primary_address:
            try:
                self._grpc_deregister()
            except Exception as exc:
                logger.debug("Deregistration RPC failed: %s", exc)

        self._stop_heartbeat()
        self._state = NodeState.DISCONNECTED
        self._cluster_id = ""
        logger.info("Deregistered from cluster")

        if self._on_deregistered:
            self._on_deregistered()

    # ------------------------------------------------------------------
    # Registration handlers (primary receives from worker)
    # ------------------------------------------------------------------

    def handle_worker_registration(
        self,
        node_id: str,
        access_token: str,
        hardware: Dict[str, Any],
        address: str,
    ) -> Dict[str, Any]:
        """Handle a worker node's registration request (primary-side).

        Returns a response dict with ``accepted``, ``cluster_id``, etc.
        """
        if not self.is_primary:
            return {"accepted": False, "message": "This node is not a primary"}

        # Validate token
        try:
            from sandbox.auth.token_manager import TokenManager
            tm = TokenManager(token_dir=self._config.token_dir)
            valid, claims = tm.validate_token(access_token)
            if not valid:
                logger.warning("Worker %s registration rejected: invalid token", node_id)
                return {"accepted": False, "message": "Invalid or expired token"}
        except Exception as exc:
            logger.warning("Token validation error: %s", exc)
            return {"accepted": False, "message": f"Auth error: {exc}"}

        # Register the peer
        with self._peers_lock:
            self._peers[node_id] = {
                "node_id": node_id,
                "role": "worker",
                "address": address,
                "hardware": hardware,
                "state": NodeState.ACTIVE.value,
                "registered_at": time.time(),
                "last_heartbeat": time.time(),
            }

        logger.info("Worker '%s' registered from %s", node_id, address)

        # Build cluster info response
        nodes = []
        with self._peers_lock:
            for nid, info in self._peers.items():
                nodes.append({
                    "node_id": nid,
                    "role": info["role"],
                    "address": info["address"],
                    "status": info["state"],
                })

        return {
            "accepted": True,
            "cluster_id": self._cluster_id,
            "message": "Welcome to the cluster",
            "assigned_node_id": node_id,
            "cluster_info": {
                "primary_id": self._node_id,
                "primary_address": f"0.0.0.0:{self._config.grpc_port}",
                "nodes": nodes,
            },
        }

    def handle_worker_heartbeat(
        self,
        node_id: str,
        hardware: Dict[str, Any],
        energy: Dict[str, Any],
        load_pct: float,
        active_chunks: List[int],
    ) -> Dict[str, Any]:
        """Handle a worker's heartbeat (primary-side)."""
        with self._peers_lock:
            if node_id not in self._peers:
                return {"acknowledged": False, "commands": []}

            self._peers[node_id]["last_heartbeat"] = time.time()
            self._peers[node_id]["hardware"] = hardware
            self._peers[node_id]["energy"] = energy
            self._peers[node_id]["load_pct"] = load_pct
            self._peers[node_id]["active_chunks"] = active_chunks

        return {"acknowledged": True, "commands": []}

    def handle_worker_deregistration(self, node_id: str, reason: str) -> Dict[str, Any]:
        """Handle a worker's departure (primary-side)."""
        with self._peers_lock:
            if node_id in self._peers:
                del self._peers[node_id]
                logger.info("Worker '%s' deregistered (reason: %s)", node_id, reason)
                return {"acknowledged": True, "message": "Goodbye"}
        return {"acknowledged": False, "message": "Unknown node"}

    # ------------------------------------------------------------------
    # Heartbeat loop (worker)
    # ------------------------------------------------------------------

    def _start_heartbeat(self) -> None:
        """Start the heartbeat background loop."""
        if self._heartbeat_running:
            return
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name="agent-heartbeat",
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        """Stop the heartbeat loop."""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=3.0)
            self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        """Background heartbeat loop sending metrics to primary."""
        while self._heartbeat_running:
            try:
                self._send_heartbeat()
            except Exception as exc:
                logger.debug("Heartbeat error: %s", exc)
            time.sleep(self._heartbeat_interval)

    def _send_heartbeat(self) -> None:
        """Send a single heartbeat to the primary."""
        report = self._hw_reporter.get_report()

        heartbeat_data = {
            "node_id": self._node_id,
            "hardware": report.to_dict(),
            "energy": {
                "current_power_w": report.power_draw_w,
                "avg_power_w": report.power_draw_w,
                "total_energy_wh": report.energy_total_wh,
                "gpu_utilization_pct": report.gpu_utilization_pct,
                "cpu_utilization_pct": report.cpu_utilization_pct,
                "gpu_temperature_c": report.gpu_temperature_c,
                "threshold_level": "optimal",
            },
            "load_pct": report.load_pct,
            "active_chunks": self.active_chunks,
            "uptime_s": int(time.time() - self._start_time),
        }

        # Try gRPC heartbeat
        if self._primary_stub:
            try:
                self._grpc_heartbeat(heartbeat_data)
                return
            except Exception:
                pass

        # Fallback to REST heartbeat
        self._rest_heartbeat(heartbeat_data)

    # ------------------------------------------------------------------
    # gRPC communication
    # ------------------------------------------------------------------

    def _grpc_register(self, primary_address: str, access_token: str) -> bool:
        """Attempt gRPC-based registration."""
        try:
            import grpc

            self._primary_channel = grpc.insecure_channel(primary_address)
            # Use a simple unary call for registration since we
            # generate stubs in sandbox.agent.grpc_service
            from sandbox.agent.grpc_service import make_register_request
            return make_register_request(
                self._primary_channel,
                self._node_id,
                access_token,
                self._hw_reporter.get_report(),
                self._config.role.value,
                f"0.0.0.0:{self._config.grpc_port}",
                self,
            )
        except ImportError:
            logger.debug("gRPC not available for registration")
            return False
        except Exception as exc:
            logger.debug("gRPC registration failed: %s", exc)
            return False

    def _grpc_deregister(self) -> None:
        """Send deregister RPC to primary."""
        try:
            from sandbox.agent.grpc_service import make_deregister_request
            if self._primary_channel:
                make_deregister_request(self._primary_channel, self._node_id, "user_request")
        except Exception as exc:
            logger.debug("gRPC deregistration failed: %s", exc)

    def _grpc_heartbeat(self, data: Dict[str, Any]) -> None:
        """Send heartbeat via gRPC."""
        from sandbox.agent.grpc_service import make_heartbeat_request
        if self._primary_channel:
            make_heartbeat_request(self._primary_channel, data)

    # ------------------------------------------------------------------
    # REST fallback communication
    # ------------------------------------------------------------------

    def _rest_register(self, primary_address: str, access_token: str) -> bool:
        """Attempt REST-based registration as fallback."""
        try:
            import urllib.request
            import urllib.error

            report = self._hw_reporter.get_report()
            payload = json.dumps({
                "node_id": self._node_id,
                "access_token": access_token,
                "hardware": report.to_dict(),
                "role": self._config.role.value,
                "address": f"0.0.0.0:{self._config.rest_port}",
            }).encode("utf-8")

            # Parse host:port from primary_address
            host, port = primary_address.rsplit(":", 1)
            rest_port = int(port) + 100  # Convention: REST port = gRPC port + 100
            url = f"http://{host}:{rest_port}/api/v1/cluster/register"

            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if data.get("accepted"):
                    self._cluster_id = data.get("cluster_id", "")
                    return True
                logger.warning("REST registration rejected: %s", data.get("message"))
                return False
        except Exception as exc:
            logger.debug("REST registration failed: %s", exc)
            return False

    def _rest_heartbeat(self, data: Dict[str, Any]) -> None:
        """Send heartbeat via REST as fallback."""
        try:
            import urllib.request
            payload = json.dumps(data).encode("utf-8")
            host, port = self._primary_address.rsplit(":", 1)
            rest_port = int(port) + 100
            url = f"http://{host}:{rest_port}/api/v1/cluster/heartbeat"
            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Control server callbacks
    # ------------------------------------------------------------------

    def _handle_get_status(self) -> Dict[str, Any]:
        """Return node status for the control server."""
        report = self._hw_reporter.get_report()
        return {
            "node_id": self._node_id,
            "state": self._state.value,
            "role": self._config.role.value,
            "cluster_id": self._cluster_id,
            "uptime_s": int(time.time() - self._start_time) if self._start_time else 0,
            "active_chunks": self.active_chunks,
            "hardware_summary": {
                "gpu": report.gpu_type,
                "vram_mb": round(report.gpu_vram_mb, 1),
                "ram_mb": round(report.ram_mb, 1),
                "cpu_cores": report.cpu_cores,
            },
            "peers": len(self._peers) if self.is_primary else 0,
        }

    def _handle_get_hardware(self) -> Dict[str, Any]:
        """Return hardware report for the control server."""
        return self._hw_reporter.get_report().to_dict()

    def _handle_get_metrics(self) -> Dict[str, Any]:
        """Return energy/performance metrics for the control server."""
        report = self._hw_reporter.get_report()
        return {
            "power_draw_w": round(report.power_draw_w, 1),
            "gpu_utilization_pct": round(report.gpu_utilization_pct, 1),
            "cpu_utilization_pct": round(report.cpu_utilization_pct, 1),
            "gpu_temperature_c": round(report.gpu_temperature_c, 1),
            "energy_total_wh": round(report.energy_total_wh, 4),
            "load_pct": round(report.load_pct, 1),
        }

    def _handle_chunk_assignment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming chunk assignment from primary."""
        chunk_id = data.get("chunk_id")
        if chunk_id is None:
            return {"success": False, "message": "Missing chunk_id"}

        self._active_chunks[chunk_id] = {
            "chunk_id": chunk_id,
            "model_name": data.get("model_name", ""),
            "assigned_at": time.time(),
            "status": "loading",
        }

        logger.info("Received chunk assignment: chunk_id=%d", chunk_id)

        # Start the local chunk server
        self._start_local_chunk_server(
            chunk_id=chunk_id,
            model_name=data.get("model_name", ""),
            num_chunks=data.get("num_chunks", 1),
        )

        self._active_chunks[chunk_id]["status"] = "active"

        if self._on_chunk_assigned:
            self._on_chunk_assigned(data)

        return {
            "success": True,
            "message": f"Chunk {chunk_id} accepted",
            "chunk_endpoint": f"0.0.0.0:{50051 + chunk_id}",
        }

    def _start_local_chunk_server(self, chunk_id: int, model_name: str, num_chunks: int) -> None:
        """Start a local gRPC chunk server in the background."""
        try:
            from model.chunk_server import serve
            port = 50051 + chunk_id
            logger.info("Starting local chunk server for chunk %d on port %d...", chunk_id, port)
            
            # Start the server (runs in a background thread within gRPC framework)
            server = serve(
                chunk_id=chunk_id,
                num_chunks=num_chunks,
                model_type="transformer",
                weights_dir="",  # empty string enables on-the-fly partition splitting
                port=port,
                device="cpu",
            )
            
            if not hasattr(self, "_chunk_servers"):
                self._chunk_servers = {}
            self._chunk_servers[chunk_id] = server
            logger.info("Local chunk server for chunk %d started", chunk_id)
        except Exception as exc:
            logger.exception("Failed to start local chunk server for chunk %d: %s", chunk_id, exc)

    def _handle_deploy_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model deployment request."""
        model_name = data.get("model_name", "")
        chunks = data.get("chunks", [])

        logger.info("Received deploy request: model=%s, chunks=%s", model_name, chunks)

        results = []
        for chunk_info in chunks:
            result = self._handle_chunk_assignment(chunk_info)
            results.append(result)

        return {
            "success": all(r["success"] for r in results),
            "message": f"Deployed {len(chunks)} chunks",
            "results": results,
        }

    # ------------------------------------------------------------------
    # Event registration
    # ------------------------------------------------------------------

    def on_registered(self, callback: Callable) -> None:
        self._on_registered = callback

    def on_deregistered(self, callback: Callable) -> None:
        self._on_deregistered = callback

    def on_chunk_assigned(self, callback: Callable) -> None:
        self._on_chunk_assigned = callback

    def on_command_received(self, callback: Callable) -> None:
        self._on_command_received = callback

    # ------------------------------------------------------------------
    # Peer management (primary only)
    # ------------------------------------------------------------------

    def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """Return all nodes in the cluster (primary-side)."""
        nodes = [{
            "node_id": self._node_id,
            "role": "primary",
            "state": self._state.value,
            "hardware": self._hw_reporter.get_report().to_dict(),
        }]
        with self._peers_lock:
            for nid, info in self._peers.items():
                nodes.append({
                    "node_id": nid,
                    "role": info.get("role", "worker"),
                    "state": info.get("state", "unknown"),
                    "address": info.get("address", ""),
                    "hardware": info.get("hardware", {}),
                    "last_heartbeat": info.get("last_heartbeat", 0),
                })
        return nodes

    def remove_stale_peers(self, timeout_s: float = 30.0) -> List[str]:
        """Remove peers that haven't sent a heartbeat within timeout."""
        now = time.time()
        removed = []
        with self._peers_lock:
            stale = [
                nid for nid, info in self._peers.items()
                if now - info.get("last_heartbeat", 0) > timeout_s
            ]
            for nid in stale:
                del self._peers[nid]
                removed.append(nid)
        if removed:
            logger.warning("Removed stale peers: %s", removed)
        return removed
