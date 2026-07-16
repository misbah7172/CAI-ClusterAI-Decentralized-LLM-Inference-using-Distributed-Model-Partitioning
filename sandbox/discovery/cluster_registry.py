"""
Cluster Registry — in-memory state management of known nodes.

Thread-safe registry that tracks discovered, authenticated, and
active nodes. Emits events on state transitions.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sandbox.config import NodeState, NODE_EXPIRY_S

logger = logging.getLogger(__name__)


@dataclass
class RegisteredNode:
    """Full state of a node known to the cluster."""
    node_id: str
    role: str = "worker"
    address: str = ""
    state: NodeState = NodeState.DISCOVERED
    cluster_id: str = ""

    # Hardware
    gpu_type: str = "none"
    gpu_vram_mb: float = 0.0
    ram_mb: float = 0.0
    cpu_cores: int = 1
    has_gpu: bool = False

    # Dynamic
    load_pct: float = 0.0
    power_draw_w: float = 0.0
    active_chunks: List[int] = field(default_factory=list)

    # Timestamps
    discovered_at: float = 0.0
    registered_at: float = 0.0
    last_heartbeat: float = 0.0

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = time.time()

    @property
    def is_active(self) -> bool:
        return self.state == NodeState.ACTIVE

    @property
    def is_stale(self) -> bool:
        return self.is_stale_with(NODE_EXPIRY_S)

    def is_stale_with(self, expiry_s: float) -> bool:
        if self.last_heartbeat <= 0:
            return False
        return (time.time() - self.last_heartbeat) > expiry_s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "address": self.address,
            "state": self.state.value,
            "cluster_id": self.cluster_id,
            "gpu_type": self.gpu_type,
            "gpu_vram_mb": round(self.gpu_vram_mb, 1),
            "ram_mb": round(self.ram_mb, 1),
            "cpu_cores": self.cpu_cores,
            "has_gpu": self.has_gpu,
            "load_pct": round(self.load_pct, 1),
            "power_draw_w": round(self.power_draw_w, 1),
            "active_chunks": self.active_chunks,
            "last_heartbeat": self.last_heartbeat,
        }


class ClusterRegistry:
    """Thread-safe registry of cluster nodes.

    Supports add/remove/query, state transitions, and event callbacks.

    Parameters
    ----------
    expiry_s : float
        Seconds after which a node with no heartbeat is marked stale.
    """

    def __init__(self, expiry_s: float = NODE_EXPIRY_S):
        self._nodes: Dict[str, RegisteredNode] = {}
        self._lock = threading.RLock()
        self._expiry_s = expiry_s

        # Event callbacks
        self._on_state_change: List[Callable[[str, NodeState, NodeState], None]] = []
        self._on_node_added: List[Callable[[RegisteredNode], None]] = []
        self._on_node_removed: List[Callable[[str], None]] = []

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(
        self,
        node_id: str,
        role: str = "worker",
        address: str = "",
        state: NodeState = NodeState.DISCOVERED,
        hardware: Optional[Dict[str, Any]] = None,
        cluster_id: str = "",
    ) -> RegisteredNode:
        """Add a node to the registry or update if already exists."""
        hw = hardware or {}
        with self._lock:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                old_state = node.state
                node.address = address or node.address
                node.role = role or node.role
                self._update_hardware(node, hw)
                if state != old_state:
                    node.state = state
                    self._emit_state_change(node_id, old_state, state)
                return node

            node = RegisteredNode(
                node_id=node_id,
                role=role,
                address=address,
                state=state,
                cluster_id=cluster_id,
                gpu_type=hw.get("gpu_type", "none"),
                gpu_vram_mb=float(hw.get("gpu_vram_mb", 0)),
                ram_mb=float(hw.get("ram_mb", 0)),
                cpu_cores=int(hw.get("cpu_cores", 1)),
                has_gpu=bool(hw.get("has_gpu", False)),
            )
            self._nodes[node_id] = node
            logger.info("Node added: %s (role=%s, state=%s)", node_id, role, state.value)

            for cb in self._on_node_added:
                try:
                    cb(node)
                except Exception:
                    pass

            return node

    def remove_node(self, node_id: str) -> Optional[RegisteredNode]:
        """Remove a node from the registry."""
        with self._lock:
            node = self._nodes.pop(node_id, None)
            if node:
                old_state = node.state
                node.state = NodeState.REMOVED
                self._emit_state_change(node_id, old_state, NodeState.REMOVED)
                logger.info("Node removed: %s", node_id)
                for cb in self._on_node_removed:
                    try:
                        cb(node_id)
                    except Exception:
                        pass
            return node

    def update_state(self, node_id: str, new_state: NodeState) -> bool:
        """Transition a node to a new state."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            old_state = node.state
            if old_state == new_state:
                return True
            node.state = new_state
            self._emit_state_change(node_id, old_state, new_state)
            return True

    def update_heartbeat(
        self,
        node_id: str,
        hardware: Optional[Dict[str, Any]] = None,
        load_pct: float = 0.0,
        power_draw_w: float = 0.0,
        active_chunks: Optional[List[int]] = None,
    ) -> bool:
        """Update a node's heartbeat data."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            node.last_heartbeat = time.time()
            node.load_pct = load_pct
            node.power_draw_w = power_draw_w
            if active_chunks is not None:
                node.active_chunks = list(active_chunks)
            if hardware:
                self._update_hardware(node, hardware)
            # Auto-transition from AUTHENTICATED → ACTIVE on first heartbeat
            if node.state == NodeState.AUTHENTICATED:
                node.state = NodeState.ACTIVE
                self._emit_state_change(node_id, NodeState.AUTHENTICATED, NodeState.ACTIVE)
            return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[RegisteredNode]:
        """Get a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[RegisteredNode]:
        """Return all registered nodes."""
        with self._lock:
            return list(self._nodes.values())

    def get_active_nodes(self) -> List[RegisteredNode]:
        """Return only active nodes."""
        with self._lock:
            return [n for n in self._nodes.values() if n.is_active]

    def get_nodes_by_role(self, role: str) -> List[RegisteredNode]:
        """Return nodes with a specific role."""
        with self._lock:
            return [n for n in self._nodes.values() if n.role == role]

    @property
    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    @property
    def active_count(self) -> int:
        with self._lock:
            return sum(1 for n in self._nodes.values() if n.is_active)

    # ------------------------------------------------------------------
    # Stale node cleanup
    # ------------------------------------------------------------------

    def cleanup_stale(self) -> List[str]:
        """Mark stale nodes as DISCONNECTED and return their IDs."""
        removed = []
        with self._lock:
            for node_id, node in list(self._nodes.items()):
                if node.is_stale_with(self._expiry_s) and node.state == NodeState.ACTIVE:
                    old_state = node.state
                    node.state = NodeState.DISCONNECTED
                    self._emit_state_change(node_id, old_state, NodeState.DISCONNECTED)
                    removed.append(node_id)
        if removed:
            logger.warning("Stale nodes disconnected: %s", removed)
        return removed

    # ------------------------------------------------------------------
    # Event subscriptions
    # ------------------------------------------------------------------

    def on_state_change(self, callback: Callable[[str, NodeState, NodeState], None]) -> None:
        """Subscribe to node state transitions."""
        self._on_state_change.append(callback)

    def on_node_added(self, callback: Callable[[RegisteredNode], None]) -> None:
        """Subscribe to node additions."""
        self._on_node_added.append(callback)

    def on_node_removed(self, callback: Callable[[str], None]) -> None:
        """Subscribe to node removals."""
        self._on_node_removed.append(callback)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _emit_state_change(self, node_id: str, old: NodeState, new: NodeState) -> None:
        logger.debug("Node %s: %s → %s", node_id, old.value, new.value)
        for cb in self._on_state_change:
            try:
                cb(node_id, old, new)
            except Exception:
                pass

    @staticmethod
    def _update_hardware(node: RegisteredNode, hw: Dict[str, Any]) -> None:
        if "gpu_type" in hw:
            node.gpu_type = hw["gpu_type"]
        if "gpu_vram_mb" in hw:
            node.gpu_vram_mb = float(hw["gpu_vram_mb"])
        if "ram_mb" in hw:
            node.ram_mb = float(hw["ram_mb"])
        if "cpu_cores" in hw:
            node.cpu_cores = int(hw["cpu_cores"])
        if "has_gpu" in hw:
            node.has_gpu = bool(hw["has_gpu"])
