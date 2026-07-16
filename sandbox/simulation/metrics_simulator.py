"""
Metrics Simulator for virtual CAI Sandbox nodes.

Generates realistic, deterministic energy and utilization metrics
based on hardware profiles and load patterns. Compatible with the
existing MetricsCollector interface.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sandbox.simulation.hardware_profiles import HardwareProfile


@dataclass
class SimulatedMetrics:
    """Snapshot of simulated node metrics."""
    node_id: str
    timestamp: float

    # Power & energy
    power_draw_w: float = 0.0
    total_energy_wh: float = 0.0

    # GPU
    gpu_utilization_pct: float = 0.0
    gpu_temperature_c: float = 0.0
    gpu_vram_used_mb: float = 0.0

    # CPU
    cpu_utilization_pct: float = 0.0
    ram_used_mb: float = 0.0

    # Derived
    threshold_level: str = "optimal"
    eer: float = 0.0  # energy efficiency ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "power_draw_w": round(self.power_draw_w, 1),
            "total_energy_wh": round(self.total_energy_wh, 4),
            "gpu_utilization_pct": round(self.gpu_utilization_pct, 1),
            "gpu_temperature_c": round(self.gpu_temperature_c, 1),
            "gpu_vram_used_mb": round(self.gpu_vram_used_mb, 1),
            "cpu_utilization_pct": round(self.cpu_utilization_pct, 1),
            "ram_used_mb": round(self.ram_used_mb, 1),
            "threshold_level": self.threshold_level,
            "eer": round(self.eer, 4),
        }


class MetricsSimulator:
    """Generates realistic simulated metrics for a virtual node.

    Produces deterministic metrics based on the hardware profile, a
    load level, and elapsed time. Uses hash-based determinism so the
    same inputs always produce the same outputs.

    Parameters
    ----------
    node_id : str
        Unique node identifier.
    profile : HardwareProfile
        Hardware profile for this virtual node.
    """

    def __init__(self, node_id: str, profile: HardwareProfile):
        self._node_id = node_id
        self._profile = profile
        self._start_time = time.time()
        self._energy_accumulator_wh = 0.0
        self._last_sample_time = self._start_time
        self._load_level = 0.3  # 0.0-1.0

    # ------------------------------------------------------------------
    # Load control
    # ------------------------------------------------------------------

    def set_load(self, level: float) -> None:
        """Set the simulated load level (0.0 = idle, 1.0 = max)."""
        self._load_level = max(0.0, min(1.0, level))

    @property
    def load_level(self) -> float:
        return self._load_level

    # ------------------------------------------------------------------
    # Metric generation
    # ------------------------------------------------------------------

    def generate(self) -> SimulatedMetrics:
        """Generate a new metrics snapshot based on current state."""
        now = time.time()
        elapsed = now - self._start_time
        load = self._load_level

        # Deterministic micro-variation based on node + time
        variation = self._deterministic_variation(elapsed)

        # Power consumption
        power = self._simulate_power(load, variation)

        # Energy accumulation
        dt_hours = (now - self._last_sample_time) / 3600.0
        self._energy_accumulator_wh += power * dt_hours
        self._last_sample_time = now

        # GPU metrics
        gpu_util = self._simulate_gpu_utilization(load, variation)
        gpu_temp = self._simulate_gpu_temperature(load, gpu_util, elapsed)
        gpu_vram_used = self._simulate_vram_usage(load)

        # CPU metrics
        cpu_util = self._simulate_cpu_utilization(load, variation)
        ram_used = self._simulate_ram_usage(load)

        # Threshold level
        threshold = self._compute_threshold(power, gpu_temp)

        # EER
        throughput_estimate = load * self._profile.compute_tflops * 0.8
        eer = throughput_estimate / max(power, 1.0)

        return SimulatedMetrics(
            node_id=self._node_id,
            timestamp=now,
            power_draw_w=power,
            total_energy_wh=self._energy_accumulator_wh,
            gpu_utilization_pct=gpu_util,
            gpu_temperature_c=gpu_temp,
            gpu_vram_used_mb=gpu_vram_used,
            cpu_utilization_pct=cpu_util,
            ram_used_mb=ram_used,
            threshold_level=threshold,
            eer=eer,
        )

    # ------------------------------------------------------------------
    # Simulation helpers
    # ------------------------------------------------------------------

    def _simulate_power(self, load: float, variation: float) -> float:
        """Simulate power consumption based on load."""
        p = self._profile
        # Power follows a non-linear curve with load
        base = p.idle_power_w + (p.peak_power_w - p.idle_power_w) * (load ** 1.3)
        # Add deterministic micro-variation (±3%)
        jitter = base * 0.03 * variation
        return max(p.idle_power_w * 0.8, base + jitter)

    def _simulate_gpu_utilization(self, load: float, variation: float) -> float:
        """Simulate GPU utilization percentage."""
        if not self._profile.has_gpu:
            return 0.0
        base = load * 95.0  # Max ~95%
        jitter = 5.0 * variation
        return max(0.0, min(100.0, base + jitter))

    def _simulate_gpu_temperature(
        self, load: float, gpu_util: float, elapsed: float
    ) -> float:
        """Simulate GPU temperature with thermal ramp-up."""
        if not self._profile.has_gpu:
            return 0.0
        ambient = 35.0
        max_temp = 85.0
        # Temperature ramps up over time under load
        thermal_constant = min(1.0, elapsed / 120.0)  # ~2 min to steady state
        target_temp = ambient + (max_temp - ambient) * (load ** 0.8) * thermal_constant
        return max(ambient, min(max_temp, target_temp))

    def _simulate_vram_usage(self, load: float) -> float:
        """Simulate GPU VRAM usage."""
        if not self._profile.has_gpu:
            return 0.0
        # Base OS usage + model proportional to load
        base = self._profile.gpu_vram_mb * 0.05  # 5% baseline
        model = self._profile.gpu_vram_mb * 0.7 * load  # Up to 70%
        return min(self._profile.gpu_vram_mb * 0.95, base + model)

    def _simulate_cpu_utilization(self, load: float, variation: float) -> float:
        """Simulate CPU utilization."""
        if self._profile.has_gpu:
            # GPU node: CPU mostly idle during inference
            base = 10.0 + load * 30.0
        else:
            # CPU-only: CPU is the primary compute
            base = 5.0 + load * 90.0
        jitter = 5.0 * variation
        return max(0.0, min(100.0, base + jitter))

    def _simulate_ram_usage(self, load: float) -> float:
        """Simulate system RAM usage."""
        base = self._profile.ram_mb * 0.15  # OS baseline
        model = self._profile.ram_mb * 0.5 * load
        return min(self._profile.ram_mb * 0.9, base + model)

    def _compute_threshold(self, power_w: float, temperature_c: float) -> str:
        """Determine the threshold level based on power and temperature."""
        tdp = self._profile.tdp_w
        if power_w > tdp * 0.9 or temperature_c > 80:
            return "critical"
        if power_w > tdp * 0.7 or temperature_c > 70:
            return "warning"
        return "optimal"

    def _deterministic_variation(self, elapsed: float) -> float:
        """Generate a deterministic variation value in [-1, 1].

        Uses a hash of node_id and quantised time so the same inputs
        always produce the same variation.
        """
        # Quantise time to 1-second bins
        time_bin = int(elapsed)
        seed_str = f"{self._node_id}:{time_bin}"
        digest = hashlib.sha256(seed_str.encode()).hexdigest()
        # Map first 8 hex chars to [-1, 1]
        val = int(digest[:8], 16) / 0xFFFFFFFF
        return val * 2.0 - 1.0


class NetworkLatencySimulator:
    """Simulates network latency between virtual nodes.

    Provides deterministic latency values based on node pair
    identity and configurable base parameters.
    """

    def __init__(
        self,
        base_latency_ms: float = 0.5,
        max_latency_ms: float = 5.0,
        jitter_pct: float = 0.1,
    ):
        self._base = base_latency_ms
        self._max = max_latency_ms
        self._jitter_pct = jitter_pct

    def get_latency(self, src_node: str, dst_node: str) -> float:
        """Get simulated latency between two nodes."""
        if src_node == dst_node:
            return 0.01  # Loopback

        # Deterministic latency from node pair hash
        pair = f"{min(src_node, dst_node)}|{max(src_node, dst_node)}"
        digest = hashlib.sha256(pair.encode()).hexdigest()
        val = int(digest[:8], 16) / 0xFFFFFFFF

        latency = self._base + (self._max - self._base) * val
        return round(latency, 3)

    def get_bandwidth_gbps(self, src_node: str, dst_node: str) -> float:
        """Get simulated bandwidth between two nodes."""
        if src_node == dst_node:
            return 100.0  # Loopback

        pair = f"{min(src_node, dst_node)}|{max(src_node, dst_node)}"
        digest = hashlib.sha256(pair.encode()).hexdigest()
        val = int(digest[8:16], 16) / 0xFFFFFFFF

        return round(1.0 + 9.0 * val, 2)  # 1-10 Gbps
