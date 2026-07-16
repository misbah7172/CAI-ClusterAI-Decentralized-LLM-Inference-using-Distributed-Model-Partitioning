"""
Hardware Reporter for the CAI Sandbox Node Agent.

Extends the existing ResourceDetector with continuous monitoring and
energy metrics reporting for the sandbox cluster.
"""

from __future__ import annotations

import concurrent.futures
import logging
import platform
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HardwareReport:
    """Snapshot of node hardware and resource utilization.

    Compatible with the existing ``NodeInfo`` dataclass from
    ``model.resource_detector`` but includes additional fields
    for energy and utilization metrics.
    """

    node_id: str = ""
    hostname: str = ""
    os_platform: str = ""

    # Static hardware
    gpu_type: str = "none"
    gpu_vram_mb: float = 0.0
    ram_mb: float = 0.0
    cpu_cores: int = 1
    has_gpu: bool = False

    # Dynamic utilization
    gpu_utilization_pct: float = 0.0
    cpu_utilization_pct: float = 0.0
    ram_used_mb: float = 0.0
    gpu_vram_used_mb: float = 0.0

    # Energy
    power_draw_w: float = 0.0
    gpu_temperature_c: float = 0.0
    energy_total_wh: float = 0.0

    # Network
    network_bandwidth_mbps: float = 0.0

    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    @property
    def load_pct(self) -> float:
        """Overall load percentage (max of CPU and GPU utilization)."""
        return max(self.cpu_utilization_pct, self.gpu_utilization_pct)

    @property
    def usable_memory_mb(self) -> float:
        """Available memory for model layers."""
        if self.has_gpu and self.gpu_vram_mb > 0:
            return max(0, self.gpu_vram_mb - 500)  # Reserve 500MB for CUDA
        return self.ram_mb * 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "os_platform": self.os_platform,
            "gpu_type": self.gpu_type,
            "gpu_vram_mb": round(self.gpu_vram_mb, 1),
            "ram_mb": round(self.ram_mb, 1),
            "cpu_cores": self.cpu_cores,
            "has_gpu": self.has_gpu,
            "gpu_utilization_pct": round(self.gpu_utilization_pct, 1),
            "cpu_utilization_pct": round(self.cpu_utilization_pct, 1),
            "ram_used_mb": round(self.ram_used_mb, 1),
            "power_draw_w": round(self.power_draw_w, 1),
            "gpu_temperature_c": round(self.gpu_temperature_c, 1),
            "load_pct": round(self.load_pct, 1),
            "usable_memory_mb": round(self.usable_memory_mb, 1),
            "timestamp": self.timestamp,
        }

    def to_node_info(self):
        """Convert to the existing NodeInfo format."""
        from model.resource_detector import NodeInfo
        return NodeInfo(
            name=self.node_id or self.hostname,
            gpu_vram_mb=self.gpu_vram_mb,
            gpu_type=self.gpu_type,
            ram_mb=self.ram_mb,
            cpu_cores=self.cpu_cores,
            has_gpu=self.has_gpu,
        )


class HardwareReporter:
    """Continuously monitors local hardware and produces reports.

    Wraps ``ResourceDetector._scan_local()`` with periodic refresh and
    adds CPU/GPU utilization and energy metrics.

    Parameters
    ----------
    node_id : str
        Unique node identifier.
    interval_s : float
        Seconds between hardware scans.
    """

    def __init__(self, node_id: str = "", interval_s: float = 5.0):
        self._node_id = node_id
        self._interval = interval_s
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._latest: Optional[HardwareReport] = None
        self._energy_accumulator_wh: float = 0.0
        self._last_sample_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background reporter thread."""
        if self._running:
            return
        self._running = True
        # Do initial scan synchronously
        self._scan()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="hw-reporter")
        self._thread.start()
        logger.info("HardwareReporter started (interval=%.1fs)", self._interval)

    def stop(self) -> None:
        """Stop the background reporter."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_report(self) -> HardwareReport:
        """Return the latest hardware report."""
        with self._lock:
            if self._latest is None:
                self._scan()
            return self._latest or HardwareReport(node_id=self._node_id)

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Background scanning loop."""
        while self._running:
            try:
                self._scan()
            except Exception as exc:
                logger.debug("Hardware scan error: %s", exc)
            time.sleep(self._interval)

    def _scan(self) -> None:
        """Perform a full hardware scan."""
        report = HardwareReport(
            node_id=self._node_id,
            hostname=platform.node(),
            os_platform=platform.system(),
        )

        # Static hardware info
        self._scan_cpu_ram(report)
        self._scan_gpu(report)

        # Dynamic utilization
        self._scan_utilization(report)

        # Energy tracking
        self._update_energy(report)

        report.timestamp = time.time()

        with self._lock:
            self._latest = report

    @staticmethod
    def _scan_cpu_ram(report: HardwareReport) -> None:
        """Scan CPU and RAM info."""
        try:
            import psutil
            report.ram_mb = psutil.virtual_memory().total / (1024 ** 2)
            report.cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 1
        except ImportError:
            report.ram_mb = 0
            report.cpu_cores = 1

    @staticmethod
    def _scan_gpu(report: HardwareReport) -> None:
        """Scan GPU info using pynvml (with a hard timeout to avoid driver hangs).

        ``pynvml.nvmlInit()`` can block indefinitely on machines without
        proper NVIDIA drivers.  We submit the scan to a background thread,
        call ``executor.shutdown(wait=False)`` immediately so the thread is
        treated as a daemon, then wait at most 5 seconds for the result
        before giving up and treating the node as GPU-less.
        """
        def _do_gpu_scan() -> None:
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)

                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                report.gpu_type = name

                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                report.gpu_vram_mb = mem_info.total / (1024 ** 2)
                report.gpu_vram_used_mb = mem_info.used / (1024 ** 2)

                try:
                    power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
                    report.power_draw_w = power_mw / 1000.0
                except Exception:
                    pass

                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    report.gpu_temperature_c = float(temp)
                except Exception:
                    pass

                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    report.gpu_utilization_pct = float(util.gpu)
                except Exception:
                    pass

                report.has_gpu = True
                pynvml.nvmlShutdown()
            except Exception:
                report.has_gpu = False
                report.gpu_type = "none"

        # IMPORTANT: call shutdown(wait=False) BEFORE future.result() so the
        # executor does NOT hold a join barrier.  The worker thread is a daemon
        # and will be reaped when the process exits if it outlives the timeout.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_do_gpu_scan)
        executor.shutdown(wait=False)   # non-blocking — thread continues as daemon
        try:
            future.result(timeout=5.0)
        except Exception:
            report.has_gpu = False
            report.gpu_type = "none"
            logger.debug("GPU scan timed out or failed — assuming no GPU")

    @staticmethod
    def _scan_utilization(report: HardwareReport) -> None:
        """Scan current CPU and RAM utilization (non-blocking)."""
        try:
            import psutil
            # Use interval=None (non-blocking). First call returns 0.0, which
            # is acceptable — the background loop calls this periodically so
            # subsequent reads will have real values.
            report.cpu_utilization_pct = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            report.ram_used_mb = mem.used / (1024 ** 2)
        except ImportError:
            pass

    def _update_energy(self, report: HardwareReport) -> None:
        """Accumulate energy consumption using trapezoidal integration."""
        now = time.time()
        if self._last_sample_time > 0 and report.power_draw_w > 0:
            dt_hours = (now - self._last_sample_time) / 3600.0
            self._energy_accumulator_wh += report.power_draw_w * dt_hours
        self._last_sample_time = now
        report.energy_total_wh = self._energy_accumulator_wh
