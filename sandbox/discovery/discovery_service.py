"""
Cluster Discovery Service — orchestrates LAN auto-discovery and
manual IP-based node connections.

Combines mDNS scanning with manual ``connect_manual()`` to build
a unified view of all known nodes in the cluster registry.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from sandbox.config import NodeState, HEARTBEAT_TIMEOUT_S
from sandbox.discovery.mdns_provider import MDNSProvider, DiscoveredNode
from sandbox.discovery.cluster_registry import ClusterRegistry, RegisteredNode

logger = logging.getLogger(__name__)


class ClusterDiscoveryService:
    """Unified discovery service combining mDNS and manual connections.

    Parameters
    ----------
    node_id : str
        This node's unique identifier.
    cluster_id : str
        Cluster identifier.
    role : str
        Node role (``"primary"`` or ``"worker"``).
    grpc_port : int
        Port the node agent listens on.
    enable_mdns : bool
        Whether to enable mDNS auto-discovery.
    """

    def __init__(
        self,
        node_id: Any,
        cluster_id: str = "",
        role: str = "primary",
        grpc_port: int = 50100,
        enable_mdns: bool = True,
    ):
        if hasattr(node_id, "node_id"):
            config = node_id
            self._node_id = config.node_id
            self._cluster_id = getattr(config, "cluster_id", cluster_id)
            role_val = getattr(config, "role", role)
            self._role = role_val.value if hasattr(role_val, "value") else role_val
            self._grpc_port = getattr(config, "grpc_port", grpc_port)
            self._enable_mdns = getattr(config, "enable_mdns", enable_mdns)
        else:
            self._node_id = node_id
            self._cluster_id = cluster_id
            self._role = role
            self._grpc_port = grpc_port
            self._enable_mdns = enable_mdns

        # Sub-components
        self._registry = ClusterRegistry()
        self._mdns: Optional[MDNSProvider] = None

        # Cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running = False
        self._cleanup_interval = 10.0

        # Event callbacks
        self._on_node_discovered: List[Callable[[RegisteredNode], None]] = []
        self._on_node_lost: List[Callable[[str], None]] = []

        # Wire registry events
        self._registry.on_node_added(self._handle_node_added)
        self._registry.on_node_removed(self._handle_node_removed)
        self._registry.on_state_change(self._handle_state_change)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry(self) -> ClusterRegistry:
        return self._registry

    @property
    def node_count(self) -> int:
        return self._registry.node_count

    @property
    def active_nodes(self) -> List[RegisteredNode]:
        return self._registry.get_active_nodes()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the discovery service."""
        logger.info("Starting ClusterDiscoveryService (mdns=%s)", self._enable_mdns)

        # Register self
        self._registry.add_node(
            node_id=self._node_id,
            role=self._role,
            address=f"localhost:{self._grpc_port}",
            state=NodeState.ACTIVE,
            cluster_id=self._cluster_id,
        )

        # Start mDNS
        if self._enable_mdns:
            self._mdns = MDNSProvider(
                node_id=self._node_id,
                port=self._grpc_port,
                cluster_id=self._cluster_id,
                role=self._role,
            )
            self._mdns.start_advertising()
            self._mdns.start_scanning(
                on_found=self._on_mdns_found,
                on_lost=self._on_mdns_lost,
            )

        # Start stale node cleanup
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="discovery-cleanup",
        )
        self._cleanup_thread.start()

        logger.info("ClusterDiscoveryService started")

    def stop(self) -> None:
        """Stop the discovery service."""
        self._cleanup_running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=3.0)
            self._cleanup_thread = None

        if self._mdns:
            self._mdns.close()
            self._mdns = None

        logger.info("ClusterDiscoveryService stopped")

    # ------------------------------------------------------------------
    # Manual connection
    # ------------------------------------------------------------------

    def connect_manual(
        self,
        address: str,
        token: str,
        node_id: str = "",
    ) -> bool:
        """Manually connect to a node at a specific IP:port.

        Parameters
        ----------
        address : str
            Target node address (``ip:port``).
        token : str
            Access token for authentication.
        node_id : str
            Optional node ID (auto-generated if empty).

        Returns
        -------
        bool
            True if the node was successfully added.
        """
        if not node_id:
            node_id = f"manual-{address.replace(':', '-').replace('.', '')}"

        logger.info("Manual connection to %s", address)

        # Add to registry as CONNECTING
        node = self._registry.add_node(
            node_id=node_id,
            role="worker",
            address=address,
            state=NodeState.CONNECTING,
            cluster_id=self._cluster_id,
        )

        # Verify connectivity
        if self._probe_node(address):
            self._registry.update_state(node_id, NodeState.AUTHENTICATED)
            logger.info("Manual node %s authenticated at %s", node_id, address)
            return True
        else:
            self._registry.update_state(node_id, NodeState.DISCONNECTED)
            logger.warning("Manual node %s unreachable at %s", node_id, address)
            return False

    # ------------------------------------------------------------------
    # Event subscriptions
    # ------------------------------------------------------------------

    def on_node_discovered(self, callback: Callable[[RegisteredNode], None]) -> None:
        """Subscribe to new node discoveries."""
        self._on_node_discovered.append(callback)

    def on_node_lost(self, callback: Callable[[str], None]) -> None:
        """Subscribe to node departures."""
        self._on_node_lost.append(callback)

    # ------------------------------------------------------------------
    # mDNS callbacks
    # ------------------------------------------------------------------

    def _on_mdns_found(self, discovered: DiscoveredNode) -> None:
        """Handle a node discovered via mDNS."""
        self._registry.add_node(
            node_id=discovered.node_id,
            role=discovered.role,
            address=discovered.address,
            state=NodeState.DISCOVERED,
            cluster_id=discovered.cluster_id,
        )

    def _on_mdns_lost(self, node_id: str) -> None:
        """Handle a node lost via mDNS."""
        self._registry.update_state(node_id, NodeState.DISCONNECTED)

    # ------------------------------------------------------------------
    # Registry event handlers
    # ------------------------------------------------------------------

    def _handle_node_added(self, node: RegisteredNode) -> None:
        for cb in self._on_node_discovered:
            try:
                cb(node)
            except Exception:
                pass

    def _handle_node_removed(self, node_id: str) -> None:
        for cb in self._on_node_lost:
            try:
                cb(node_id)
            except Exception:
                pass

    def _handle_state_change(self, node_id: str, old: NodeState, new: NodeState) -> None:
        if new == NodeState.DISCONNECTED:
            for cb in self._on_node_lost:
                try:
                    cb(node_id)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_loop(self) -> None:
        """Periodically clean up stale nodes."""
        while self._cleanup_running:
            try:
                self._registry.cleanup_stale()
            except Exception as exc:
                logger.debug("Cleanup error: %s", exc)
            time.sleep(self._cleanup_interval)

    # ------------------------------------------------------------------
    # Probing
    # ------------------------------------------------------------------

    @staticmethod
    def _probe_node(address: str) -> bool:
        """Probe a node to check if it's reachable."""
        import socket
        try:
            host, port_str = address.rsplit(":", 1)
            port = int(port_str)
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Cluster summary
    # ------------------------------------------------------------------

    def get_cluster_summary(self) -> Dict:
        """Return a summary of the current cluster state."""
        nodes = self._registry.get_all_nodes()
        return {
            "cluster_id": self._cluster_id,
            "total_nodes": len(nodes),
            "active_nodes": sum(1 for n in nodes if n.is_active),
            "total_gpu_vram_mb": sum(n.gpu_vram_mb for n in nodes),
            "total_ram_mb": sum(n.ram_mb for n in nodes),
            "total_cpu_cores": sum(n.cpu_cores for n in nodes),
            "nodes": [n.to_dict() for n in nodes],
        }
