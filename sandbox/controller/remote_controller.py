"""
Remote Controller — central cluster management running on the primary node.

Coordinates node management, model deployment, inference orchestration,
and cluster-wide metrics aggregation.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sandbox.config import SandboxConfig, ClusterMode, NodeRole
from sandbox.agent.node_agent import NodeAgent
from sandbox.discovery.cluster_registry import ClusterRegistry, RegisteredNode
from sandbox.discovery.discovery_service import ClusterDiscoveryService
from sandbox.controller.model_deployer import ModelDeployer

logger = logging.getLogger(__name__)


class RemoteController:
    """Central management interface running on the primary node.

    Provides high-level operations for cluster management, model
    deployment, and inference orchestration.

    Parameters
    ----------
    agent : NodeAgent
        The primary node's agent instance.
    discovery : ClusterDiscoveryService
        Cluster discovery service.
    config : SandboxConfig
        Sandbox configuration.
    """

    def __init__(
        self,
        agent: NodeAgent,
        discovery: ClusterDiscoveryService,
        config: Optional[SandboxConfig] = None,
    ):
        self._agent = agent
        self._discovery = discovery
        self._config = config or SandboxConfig()
        self._registry = discovery.registry

        # Deployments tracking
        self._deployments: Dict[str, Dict[str, Any]] = {}  # deployment_id -> info
        self._inference_jobs: Dict[str, Dict[str, Any]] = {}  # job_id -> info
        self._model_deployer = ModelDeployer(self, self._config)

    def _sync_peers_to_registry(self) -> None:
        """Synchronize the agent's registered peers with the discovery registry."""
        peers = self._agent.peers
        for node_id, peer in peers.items():
            state = peer.get("state")
            if isinstance(state, str):
                from sandbox.config import NodeState
                try:
                    state = NodeState(state)
                except ValueError:
                    state = NodeState.ACTIVE
            
            self._registry.add_node(
                node_id=node_id,
                role=peer.get("role", "worker"),
                address=peer.get("address", ""),
                state=state,
                hardware=peer.get("hardware", {}),
                cluster_id=self._agent.cluster_id,
            )
            self._registry.update_heartbeat(
                node_id=node_id,
                hardware=peer.get("hardware", {}),
                load_pct=peer.get("load_pct", 0.0),
                power_draw_w=peer.get("energy", {}).get("current_power_w", 0.0),
                active_chunks=peer.get("active_chunks", []),
            )

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def list_nodes(self) -> List[Dict[str, Any]]:
        """List all connected nodes with status."""
        self._sync_peers_to_registry()
        nodes = self._registry.get_all_nodes()
        result = []
        for node in nodes:
            info = node.to_dict()
            info["is_self"] = node.node_id == self._agent.node_id
            result.append(info)
        return result

    def get_node_details(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a specific node."""
        self._sync_peers_to_registry()
        node = self._registry.get_node(node_id)
        if not node:
            return None

        details = node.to_dict()
        # Enrich with peer info from agent
        peers = self._agent.peers
        if node_id in peers:
            peer = peers[node_id]
            details["energy"] = peer.get("energy", {})
            details["last_heartbeat_ago_s"] = round(
                time.time() - peer.get("last_heartbeat", time.time()), 1
            )
        return details

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the cluster."""
        if node_id == self._agent.node_id:
            logger.warning("Cannot remove the primary node")
            return False
        removed = self._registry.remove_node(node_id)
        return removed is not None

    # ------------------------------------------------------------------
    # Model Deployment
    # ------------------------------------------------------------------

    def deploy_model(
        self,
        model_name: str,
        num_chunks: Optional[int] = None,
        strategy: str = "balanced",
        target_nodes: Optional[List[str]] = None,
        dtype: str = "float16",
    ) -> Dict[str, Any]:
        """Deploy a model across the cluster.

        Parameters
        ----------
        model_name : str
            HuggingFace model name or local path.
        num_chunks : int, optional
            Number of chunks (defaults to number of available nodes).
        strategy : str
            Scheduling strategy (``balanced``, ``energy``, ``latency``).
        target_nodes : list[str], optional
            Specific nodes to deploy to (empty = auto-select).
        dtype : str
            Data type for model weights.

        Returns
        -------
        dict
            Deployment result with placements and gateway endpoint.
        """
        res = self._model_deployer.deploy(
            model_name=model_name,
            num_chunks=num_chunks,
            strategy=strategy,
            target_nodes=target_nodes,
            dtype=dtype,
        )

        if res.get("success"):
            deployment_id = res["deployment_id"]
            self._deployments[deployment_id] = {
                "deployment_id": deployment_id,
                "model_name": model_name,
                "num_chunks": num_chunks or len(res.get("placements", [])),
                "strategy": strategy,
                "dtype": dtype,
                "placements": res["placements"],
                "success": True,
                "created_at": time.time(),
                "status": "active",
            }
        return res

    def list_deployments(self) -> List[Dict[str, Any]]:
        """List all model deployments."""
        return list(self._deployments.values())

    def get_deployment(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment details."""
        return self._deployments.get(deployment_id)

    def undeploy(self, deployment_id: str) -> bool:
        """Remove a deployment."""
        if deployment_id in self._deployments:
            self._model_deployer.undeploy(deployment_id)
            deployment = self._deployments.pop(deployment_id)
            deployment["status"] = "removed"
            logger.info("Undeployed: %s", deployment_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def trigger_inference(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Trigger an inference job on the cluster."""
        job_id = uuid.uuid4().hex[:12]

        # Find active deployment for this model
        deployment = None
        for d in self._deployments.values():
            if d["model_name"] == model_name and d["status"] == "active":
                deployment = d
                break

        if not deployment:
            return {
                "success": False,
                "job_id": job_id,
                "message": f"No active deployment found for model '{model_name}'",
            }

        self._inference_jobs[job_id] = {
            "job_id": job_id,
            "model_name": model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "deployment_id": deployment["deployment_id"],
            "status": "running",
            "created_at": time.time(),
        }

        logger.info("Inference job %s running for model '%s'", job_id, model_name)

        # Run text generation via model_deployer
        res = self._model_deployer.generate(
            deployment_id=deployment["deployment_id"],
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        if res.get("success"):
            self._inference_jobs[job_id]["status"] = "completed"
            self._inference_jobs[job_id]["result"] = res.get("text")
            self._inference_jobs[job_id]["completion"] = res.get("completion")
            self._inference_jobs[job_id]["stats"] = {
                "tokens_generated": res.get("tokens_generated"),
                "time_taken_s": res.get("time_taken_s"),
                "tokens_per_second": res.get("tokens_per_second"),
            }
            return {
                "success": True,
                "job_id": job_id,
                "message": "Inference job completed successfully",
                "text": res.get("text"),
                "completion": res.get("completion"),
            }
        else:
            self._inference_jobs[job_id]["status"] = "failed"
            self._inference_jobs[job_id]["error"] = res.get("message")
            return {
                "success": False,
                "job_id": job_id,
                "message": f"Inference job failed: {res.get('message')}",
            }

    def list_inference_jobs(self) -> List[Dict[str, Any]]:
        """List all inference jobs."""
        return list(self._inference_jobs.values())

    # ------------------------------------------------------------------
    # Cluster Metrics
    # ------------------------------------------------------------------

    def get_cluster_metrics(self) -> Dict[str, Any]:
        """Aggregate energy, latency, and throughput metrics."""
        self._sync_peers_to_registry()
        nodes = self._registry.get_all_nodes()
        active = [n for n in nodes if n.is_active]

        total_power = sum(n.power_draw_w for n in active)
        avg_load = sum(n.load_pct for n in active) / max(1, len(active))
        total_vram = sum(n.gpu_vram_mb for n in active if n.has_gpu)
        total_ram = sum(n.ram_mb for n in active)
        gpu_count = sum(1 for n in active if n.has_gpu)

        return {
            "total_nodes": len(nodes),
            "active_nodes": len(active),
            "gpu_nodes": gpu_count,
            "total_power_w": round(total_power, 1),
            "avg_load_pct": round(avg_load, 1),
            "total_gpu_vram_mb": round(total_vram, 1),
            "total_ram_mb": round(total_ram, 1),
            "active_deployments": sum(1 for d in self._deployments.values() if d.get("status") == "active"),
            "active_inference_jobs": sum(1 for j in self._inference_jobs.values() if j.get("status") in ("submitted", "running")),
            "cluster_eer": round(total_power / max(1, len(active)), 2) if active else 0,
        }

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster health summary."""
        metrics = self.get_cluster_metrics()
        discovery_summary = self._discovery.get_cluster_summary()

        return {
            "cluster_id": discovery_summary.get("cluster_id", ""),
            "status": "healthy" if metrics["active_nodes"] > 0 else "empty",
            "metrics": metrics,
            "discovery": discovery_summary,
        }

    # ------------------------------------------------------------------
    # Placement planning
    # ------------------------------------------------------------------

    def _plan_placement(
        self,
        num_chunks: int,
        available_nodes: List[RegisteredNode],
        strategy: str,
    ) -> List[Dict[str, Any]]:
        """Plan chunk-to-node placement based on strategy."""
        placements = []

        if strategy == "energy":
            # Sort by power efficiency (lowest power first)
            nodes = sorted(available_nodes, key=lambda n: n.power_draw_w)
        elif strategy == "latency":
            # Sort by load (lowest load first)
            nodes = sorted(available_nodes, key=lambda n: n.load_pct)
        else:
            # Balanced: round-robin with GPU preference
            gpu_nodes = [n for n in available_nodes if n.has_gpu]
            cpu_nodes = [n for n in available_nodes if not n.has_gpu]
            nodes = gpu_nodes + cpu_nodes

        for chunk_id in range(num_chunks):
            node_idx = chunk_id % len(nodes)
            node = nodes[node_idx]
            placements.append({
                "chunk_id": chunk_id,
                "node_id": node.node_id,
                "node_address": node.address,
                "has_gpu": node.has_gpu,
            })

        return placements

    def _get_available_nodes(
        self,
        target_nodes: Optional[List[str]] = None,
    ) -> List[RegisteredNode]:
        """Get list of available nodes for deployment."""
        self._sync_peers_to_registry()
        active = self._registry.get_active_nodes()

        if target_nodes:
            return [n for n in active if n.node_id in target_nodes]

        return active

    def _assign_chunk_to_node(
        self,
        node_id: str,
        chunk_id: int,
        model_name: str,
        num_chunks: int,
        dtype: str,
    ) -> Dict[str, Any]:
        """Send a chunk assignment to a specific node."""
        # If it's the local node, handle directly
        if node_id == self._agent.node_id:
            return self._agent._handle_chunk_assignment({
                "chunk_id": chunk_id,
                "model_name": model_name,
                "num_chunks": num_chunks,
                "dtype": dtype,
            })

        # For remote nodes, use REST API
        node = self._registry.get_node(node_id)
        if not node or not node.address:
            return {"success": False, "message": f"Node {node_id} not reachable"}

        try:
            import urllib.request
            import json

            host, port_str = node.address.rsplit(":", 1)
            rest_port = int(port_str) + 100  # Convention
            url = f"http://{host}:{rest_port}/agent/assign"

            payload = json.dumps({
                "chunk_id": chunk_id,
                "model_name": model_name,
                "num_chunks": num_chunks,
                "dtype": dtype,
            }).encode("utf-8")

            req = urllib.request.Request(
                url, data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.error("Failed to assign chunk %d to %s: %s", chunk_id, node_id, exc)
            return {"success": False, "message": str(exc)}
