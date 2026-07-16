"""
Simulation Engine — runs multiple virtual CAI Sandbox nodes on one machine.

Spawns containerised or in-process sandbox nodes with configurable
hardware profiles for testing distributed inference scenarios
without requiring real hardware.

Usage::

    from sandbox.simulation.engine import SimulationEngine

    engine = SimulationEngine()
    engine.simulate(num_nodes=3, profile_type="mixed")
    print(engine.get_simulated_nodes())
    engine.stop_simulation()
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from sandbox.config import (
    SandboxConfig,
    ClusterMode,
    NodeRole,
    NodeState,
    MAX_SIMULATED_NODES,
    SIM_CONTAINER_PREFIX,
    GRPC_PORT,
    REST_PORT,
)
from sandbox.simulation.hardware_profiles import (
    HardwareProfile,
    PROFILES,
    get_mixed_profiles,
    get_gpu_profiles,
    get_cpu_profiles,
)
from sandbox.simulation.metrics_simulator import MetricsSimulator, NetworkLatencySimulator
from sandbox.discovery.cluster_registry import ClusterRegistry, RegisteredNode

logger = logging.getLogger(__name__)


class SimulatedNode:
    """An in-process virtual CAI Sandbox node.

    Instead of running in Docker containers, simulated nodes run
    as lightweight threads with simulated hardware and metrics.
    """

    def __init__(
        self,
        node_id: str,
        profile: HardwareProfile,
        grpc_port: int,
        rest_port: int,
    ):
        self.node_id = node_id
        self.profile = profile
        self.grpc_port = grpc_port
        self.rest_port = rest_port
        self.state = NodeState.ACTIVE
        self.active_chunks: List[int] = []
        self.started_at = time.time()

        self._metrics_sim = MetricsSimulator(node_id, profile)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the simulated node's background loop."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name=f"sim-{self.node_id}",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the simulated node."""
        self._running = False
        self.state = NodeState.DISCONNECTED
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def set_load(self, level: float) -> None:
        """Set the simulated load level."""
        self._metrics_sim.set_load(level)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current simulated metrics."""
        return self._metrics_sim.generate().to_dict()

    def get_info(self) -> Dict[str, Any]:
        """Get node info."""
        metrics = self.get_metrics()
        return {
            "node_id": self.node_id,
            "profile": self.profile.name,
            "state": self.state.value,
            "grpc_port": self.grpc_port,
            "rest_port": self.rest_port,
            "gpu_type": self.profile.gpu_type,
            "gpu_vram_mb": self.profile.gpu_vram_mb,
            "ram_mb": self.profile.ram_mb,
            "has_gpu": self.profile.has_gpu,
            "active_chunks": self.active_chunks,
            "uptime_s": round(time.time() - self.started_at, 1),
            "metrics": metrics,
        }

    def _run_loop(self) -> None:
        """Background loop simulating periodic activity."""
        while self._running:
            # Simulate varying load over time
            elapsed = time.time() - self.started_at
            # Sinusoidal load pattern
            base_load = 0.3 + 0.2 * (1 + self._sin_deterministic(elapsed / 60.0)) / 2
            # Increase load when chunks are assigned
            chunk_load = min(0.5, len(self.active_chunks) * 0.15)
            self._metrics_sim.set_load(min(1.0, base_load + chunk_load))
            time.sleep(2.0)

    @staticmethod
    def _sin_deterministic(x: float) -> float:
        """Deterministic sine function."""
        import math
        return math.sin(x * 2 * math.pi)


class SimulationEngine:
    """Manages multiple simulated sandbox nodes on a single machine.

    Parameters
    ----------
    registry : ClusterRegistry, optional
        Cluster registry to register simulated nodes in.
    max_nodes : int
        Maximum number of simulated nodes.
    """

    def __init__(
        self,
        registry: Optional[ClusterRegistry] = None,
        max_nodes: int = MAX_SIMULATED_NODES,
    ):
        self._registry = registry or ClusterRegistry()
        self._max_nodes = max_nodes
        self._nodes: Dict[str, SimulatedNode] = {}
        self._network_sim = NetworkLatencySimulator()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Simulation lifecycle
    # ------------------------------------------------------------------

    def simulate(
        self,
        num_nodes: int = 3,
        profile_type: str = "mixed",
        profiles: Optional[List[HardwareProfile]] = None,
        cluster_id: str = "",
    ) -> List[str]:
        """Spawn N simulated sandbox nodes.

        Parameters
        ----------
        num_nodes : int
            Number of virtual nodes to create.
        profile_type : str
            Profile selection strategy: ``mixed``, ``gpu``, ``cpu``.
        profiles : list[HardwareProfile], optional
            Explicit profiles (overrides profile_type).
        cluster_id : str
            Cluster ID for the simulated cluster.

        Returns
        -------
        list[str]
            Node IDs of created simulated nodes.
        """
        num_nodes = min(num_nodes, self._max_nodes)
        if not cluster_id:
            cluster_id = f"sim-{uuid.uuid4().hex[:8]}"

        # Select profiles
        if profiles:
            selected = profiles[:num_nodes]
            # Pad with repeating if not enough
            while len(selected) < num_nodes:
                selected.append(selected[len(selected) % len(profiles)])
        elif profile_type == "gpu":
            selected = get_gpu_profiles(num_nodes)
        elif profile_type == "cpu":
            selected = get_cpu_profiles(num_nodes)
        else:
            selected = get_mixed_profiles(num_nodes)

        logger.info(
            "Starting simulation: %d nodes (type=%s, cluster=%s)",
            num_nodes, profile_type, cluster_id,
        )

        created_ids = []
        base_grpc_port = GRPC_PORT + 10  # Offset from real ports
        base_rest_port = REST_PORT + 10

        with self._lock:
            for i in range(num_nodes):
                profile = selected[i]
                node_id = f"{SIM_CONTAINER_PREFIX}-{i}-{uuid.uuid4().hex[:6]}"
                grpc_port = base_grpc_port + i
                rest_port = base_rest_port + i

                node = SimulatedNode(
                    node_id=node_id,
                    profile=profile,
                    grpc_port=grpc_port,
                    rest_port=rest_port,
                )
                node.start()
                self._nodes[node_id] = node

                # Register in cluster registry
                self._registry.add_node(
                    node_id=node_id,
                    role="worker",
                    address=f"localhost:{grpc_port}",
                    state=NodeState.ACTIVE,
                    hardware={
                        "gpu_type": profile.gpu_type,
                        "gpu_vram_mb": profile.gpu_vram_mb,
                        "ram_mb": profile.ram_mb,
                        "cpu_cores": profile.cpu_cores,
                        "has_gpu": profile.has_gpu,
                    },
                    cluster_id=cluster_id,
                )

                created_ids.append(node_id)
                logger.info(
                    "  Simulated node: %s (profile=%s, GPU=%s)",
                    node_id, profile.name, profile.gpu_type,
                )

        logger.info("Simulation started: %d nodes active", len(created_ids))
        return created_ids

    def stop_simulation(self) -> int:
        """Stop all simulated nodes.

        Returns the number of nodes stopped.
        """
        with self._lock:
            count = len(self._nodes)
            for node_id, node in self._nodes.items():
                node.stop()
                self._registry.remove_node(node_id)
            self._nodes.clear()

        logger.info("Simulation stopped: %d nodes removed", count)
        return count

    def stop_node(self, node_id: str) -> bool:
        """Stop a specific simulated node."""
        with self._lock:
            node = self._nodes.pop(node_id, None)
            if node:
                node.stop()
                self._registry.remove_node(node_id)
                return True
        return False

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_simulated_nodes(self) -> List[Dict[str, Any]]:
        """Get info for all simulated nodes."""
        with self._lock:
            return [node.get_info() for node in self._nodes.values()]

    def get_node(self, node_id: str) -> Optional[SimulatedNode]:
        """Get a specific simulated node."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_node_metrics(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific simulated node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                return node.get_metrics()
        return None

    @property
    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    @property
    def is_running(self) -> bool:
        return self.node_count > 0

    # ------------------------------------------------------------------
    # Load control
    # ------------------------------------------------------------------

    def set_all_load(self, level: float) -> None:
        """Set load level for all simulated nodes."""
        with self._lock:
            for node in self._nodes.values():
                node.set_load(level)

    def set_node_load(self, node_id: str, level: float) -> bool:
        """Set load level for a specific node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.set_load(level)
                return True
        return False

    # ------------------------------------------------------------------
    # Network simulation
    # ------------------------------------------------------------------

    def get_network_latency(self, src: str, dst: str) -> float:
        """Get simulated network latency between two nodes."""
        return self._network_sim.get_latency(src, dst)

    def get_network_bandwidth(self, src: str, dst: str) -> float:
        """Get simulated bandwidth between two nodes in Gbps."""
        return self._network_sim.get_bandwidth_gbps(src, dst)

    def get_network_topology(self) -> Dict[str, Any]:
        """Get the full simulated network topology."""
        with self._lock:
            node_ids = list(self._nodes.keys())

        links = []
        for i, src in enumerate(node_ids):
            for j, dst in enumerate(node_ids):
                if i >= j:
                    continue
                links.append({
                    "source": src,
                    "target": dst,
                    "latency_ms": self._network_sim.get_latency(src, dst),
                    "bandwidth_gbps": self._network_sim.get_bandwidth_gbps(src, dst),
                })

        return {
            "nodes": node_ids,
            "links": links,
        }

    # ------------------------------------------------------------------
    # Chunk assignment
    # ------------------------------------------------------------------

    def assign_chunk(self, node_id: str, chunk_id: int) -> bool:
        """Assign a chunk to a simulated node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.active_chunks.append(chunk_id)
                self._registry.update_heartbeat(
                    node_id, active_chunks=node.active_chunks,
                )
                return True
        return False

    def release_chunk(self, node_id: str, chunk_id: int) -> bool:
        """Release a chunk from a simulated node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node and chunk_id in node.active_chunks:
                node.active_chunks.remove(chunk_id)
                return True
        return False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """Get simulation summary."""
        with self._lock:
            nodes = [n.get_info() for n in self._nodes.values()]

        total_vram = sum(n.get("gpu_vram_mb", 0) for n in nodes)
        total_ram = sum(n.get("ram_mb", 0) for n in nodes)
        gpu_count = sum(1 for n in nodes if n.get("has_gpu"))

        return {
            "total_nodes": len(nodes),
            "gpu_nodes": gpu_count,
            "cpu_only_nodes": len(nodes) - gpu_count,
            "total_gpu_vram_mb": total_vram,
            "total_ram_mb": total_ram,
            "nodes": nodes,
            "network": self.get_network_topology(),
        }
