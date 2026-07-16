"""
Hardware profiles for simulated CAI Sandbox nodes.

Predefined and custom profiles representing different hardware
configurations for testing distributed inference scenarios.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class HardwareProfile:
    """Describes the hardware configuration of a simulated node."""

    name: str = "custom"
    gpu_type: str = "none"
    gpu_vram_mb: float = 0.0
    ram_mb: float = 8192.0
    cpu_cores: int = 4
    has_gpu: bool = False

    # Power characteristics
    idle_power_w: float = 30.0
    peak_power_w: float = 250.0
    tdp_w: float = 250.0

    # Performance characteristics
    compute_tflops: float = 1.0  # FP16 TFLOPS
    memory_bandwidth_gbps: float = 50.0

    # Docker resource limits
    docker_cpus: float = 2.0
    docker_memory: str = "4g"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "gpu_type": self.gpu_type,
            "gpu_vram_mb": self.gpu_vram_mb,
            "ram_mb": self.ram_mb,
            "cpu_cores": self.cpu_cores,
            "has_gpu": self.has_gpu,
            "idle_power_w": self.idle_power_w,
            "peak_power_w": self.peak_power_w,
            "tdp_w": self.tdp_w,
            "compute_tflops": self.compute_tflops,
            "memory_bandwidth_gbps": self.memory_bandwidth_gbps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardwareProfile":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def from_json(cls, path: Path) -> "HardwareProfile":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Predefined profiles
# ---------------------------------------------------------------------------

PROFILES: Dict[str, HardwareProfile] = {
    "high_gpu": HardwareProfile(
        name="high_gpu",
        gpu_type="NVIDIA RTX 4090",
        gpu_vram_mb=24576,
        ram_mb=65536,
        cpu_cores=16,
        has_gpu=True,
        idle_power_w=40,
        peak_power_w=450,
        tdp_w=450,
        compute_tflops=82.6,
        memory_bandwidth_gbps=1008,
        docker_cpus=8.0,
        docker_memory="16g",
    ),
    "mid_gpu": HardwareProfile(
        name="mid_gpu",
        gpu_type="NVIDIA RTX 3060",
        gpu_vram_mb=12288,
        ram_mb=32768,
        cpu_cores=8,
        has_gpu=True,
        idle_power_w=25,
        peak_power_w=170,
        tdp_w=170,
        compute_tflops=12.7,
        memory_bandwidth_gbps=360,
        docker_cpus=4.0,
        docker_memory="8g",
    ),
    "low_gpu": HardwareProfile(
        name="low_gpu",
        gpu_type="NVIDIA GTX 1650",
        gpu_vram_mb=4096,
        ram_mb=16384,
        cpu_cores=4,
        has_gpu=True,
        idle_power_w=15,
        peak_power_w=75,
        tdp_w=75,
        compute_tflops=2.9,
        memory_bandwidth_gbps=128,
        docker_cpus=2.0,
        docker_memory="4g",
    ),
    "cpu_only": HardwareProfile(
        name="cpu_only",
        gpu_type="none",
        gpu_vram_mb=0,
        ram_mb=16384,
        cpu_cores=8,
        has_gpu=False,
        idle_power_w=20,
        peak_power_w=65,
        tdp_w=65,
        compute_tflops=0.2,
        memory_bandwidth_gbps=40,
        docker_cpus=4.0,
        docker_memory="8g",
    ),
    "edge": HardwareProfile(
        name="edge",
        gpu_type="none",
        gpu_vram_mb=0,
        ram_mb=4096,
        cpu_cores=2,
        has_gpu=False,
        idle_power_w=5,
        peak_power_w=15,
        tdp_w=15,
        compute_tflops=0.05,
        memory_bandwidth_gbps=15,
        docker_cpus=1.0,
        docker_memory="2g",
    ),
    "jetson_nano": HardwareProfile(
        name="jetson_nano",
        gpu_type="NVIDIA Tegra (128 CUDA)",
        gpu_vram_mb=4096,
        ram_mb=4096,
        cpu_cores=4,
        has_gpu=True,
        idle_power_w=3,
        peak_power_w=10,
        tdp_w=10,
        compute_tflops=0.47,
        memory_bandwidth_gbps=25.6,
        docker_cpus=2.0,
        docker_memory="2g",
    ),
}


def get_profile(name: str) -> HardwareProfile:
    """Get a predefined hardware profile by name."""
    if name in PROFILES:
        return PROFILES[name]
    raise ValueError(f"Unknown profile: '{name}'. Available: {list(PROFILES.keys())}")


def list_profiles() -> List[str]:
    """List all available profile names."""
    return list(PROFILES.keys())


def get_mixed_profiles(count: int) -> List[HardwareProfile]:
    """Get a diverse mix of profiles for simulation."""
    profile_order = ["high_gpu", "mid_gpu", "low_gpu", "cpu_only", "edge"]
    profiles = []
    for i in range(count):
        idx = i % len(profile_order)
        profiles.append(PROFILES[profile_order[idx]])
    return profiles


def get_gpu_profiles(count: int) -> List[HardwareProfile]:
    """Get GPU-only profiles for simulation."""
    gpu_order = ["high_gpu", "mid_gpu", "low_gpu", "jetson_nano"]
    profiles = []
    for i in range(count):
        idx = i % len(gpu_order)
        profiles.append(PROFILES[gpu_order[idx]])
    return profiles


def get_cpu_profiles(count: int) -> List[HardwareProfile]:
    """Get CPU-only profiles for simulation."""
    cpu_order = ["cpu_only", "edge"]
    profiles = []
    for i in range(count):
        idx = i % len(cpu_order)
        profiles.append(PROFILES[cpu_order[idx]])
    return profiles
