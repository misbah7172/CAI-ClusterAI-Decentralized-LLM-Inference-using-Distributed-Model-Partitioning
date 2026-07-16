"""
Hybrid Scheduler — schedules model layers across hybrid (real + simulated) nodes.

Optimizes for energy, latency, and reliability based on node profiles.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from model.plugin_architecture import PluginRegistry, SchedulerPlugin

logger = logging.getLogger(__name__)


@PluginRegistry.register(
    "scheduler",
    "sandbox_hybrid",
    description="Hybrid scheduler balancing between real and simulated sandbox nodes"
)
class HybridScheduler(SchedulerPlugin):
    """Hybrid scheduler plugin.

    Distributes model layers across a mixture of physical (real) and virtual
    (simulated) nodes, taking into account their hardware capabilities, latency,
    and power metrics.

    Parameters
    ----------
    reliability_weight : float
        Preference for physical nodes (higher = more preferred).
    energy_weight : float
        Weight for energy-efficiency (DEAS style).
    latency_weight : float
        Weight for minimizing network latency.
    """

    def __init__(
        self,
        reliability_weight: float = 0.3,
        energy_weight: float = 0.4,
        latency_weight: float = 0.3,
    ):
        self.reliability_weight = reliability_weight
        self.energy_weight = energy_weight
        self.latency_weight = latency_weight

    def schedule(
        self,
        layers: List[Any],
        nodes: List[Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[int]]:
        """Schedule layers across physical and simulated nodes.

        Parameters
        ----------
        layers : list
            List of layers to assign (typically representations of layers).
        nodes : list
            List of available nodes. Each node should have `name`, `gpu_vram_mb`,
            `ram_mb`, `has_gpu`, and optional energy/load metrics.
        constraints : dict, optional
            Additional scheduling constraints.

        Returns
        -------
        dict
            Mapping of node_name -> list of layer indices.
        """
        if not nodes:
            logger.warning("No nodes available for scheduling")
            return {}
        if not layers:
            return {node.name: [] for node in nodes}

        num_layers = len(layers)
        logger.info(
            "Scheduling %d layers across %d hybrid nodes (real/simulated)",
            num_layers, len(nodes),
        )

        # 1. Score each node
        scores: Dict[str, float] = {}
        for node in nodes:
            name = getattr(node, "name", str(node))
            gpu_vram = getattr(node, "gpu_vram_mb", 0.0)
            ram = getattr(node, "ram_mb", 0.0)
            has_gpu = getattr(node, "has_gpu", False)
            
            # Distinguish real vs simulated
            # Convention: Simulated nodes have names starting with 'virtual-' or containing 'sim'
            is_simulated = "sim" in name.lower() or "virtual" in name.lower()
            
            # Hardware capacity score (VRAM is critical for LLMs)
            capacity_score = (gpu_vram * 2.0 + ram) / 1024.0
            if has_gpu:
                capacity_score += 10.0

            # Reliability score (physical nodes are generally more stable/trusted)
            reliability_score = 1.0 if not is_simulated else 0.5

            # Energy efficiency score
            # Physical nodes might report real power, simulated uses profile curves.
            # Lower power draw is better.
            power_draw = getattr(node, "power_draw_w", 50.0)
            energy_score = 100.0 / max(1.0, power_draw)

            # Combined node suitability score
            score = (
                capacity_score * (1.0 - self.reliability_weight - self.energy_weight) +
                reliability_score * self.reliability_weight * 10.0 +
                energy_score * self.energy_weight * 5.0
            )
            scores[name] = max(0.1, score)
            logger.debug(
                "Node %s suitability score: %.2f (simulated=%s)",
                name, score, is_simulated
            )

        # 2. Distribute layers proportionally based on scores
        total_score = sum(scores.values())
        layer_allocations: Dict[str, List[int]] = {getattr(n, "name", str(n)): [] for n in nodes}

        # Greedy layer assignment to keep assignments contiguous
        current_layer_idx = 0
        node_names = [getattr(n, "name", str(n)) for n in nodes]
        
        # Sort nodes by score descending to assign heavy layers first
        sorted_nodes = sorted(node_names, key=lambda n: scores[n], reverse=True)

        # Proportional count planning
        layer_counts = {}
        allocated_so_far = 0
        for name in sorted_nodes[:-1]:
            share = scores[name] / total_score
            count = int(round(share * num_layers))
            # Ensure at least 1 layer if possible and score is high
            if count == 0 and num_layers > len(nodes):
                count = 1
            layer_counts[name] = count
            allocated_so_far += count

        # Last node takes the remainder to ensure all layers are scheduled
        last_node = sorted_nodes[-1]
        layer_counts[last_node] = max(0, num_layers - allocated_so_far)

        # Assign contiguous layer indices
        layer_idx = 0
        for name in node_names:
            count = layer_counts.get(name, 0)
            layer_allocations[name] = list(range(layer_idx, min(num_layers, layer_idx + count)))
            layer_idx += count

        # Clean up any leftover layers due to rounding
        if layer_idx < num_layers:
            layer_allocations[sorted_nodes[0]].extend(range(layer_idx, num_layers))

        logger.info("Layer assignment completed: %s", layer_allocations)
        return layer_allocations
