"""
Pre-flight dependency checker for the CAI Sandbox.

Verifies that Docker, Python packages, GPU drivers, network, and disk
resources are available before starting the sandbox runtime.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    """Result of a single dependency check."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Outcome of one pre-flight check."""
    name: str
    status: CheckStatus
    message: str
    fix_hint: str = ""

    def __str__(self) -> str:
        icon = {"ok": "✓", "warning": "⚠", "error": "✗", "skipped": "–"}
        line = f"  [{icon[self.status.value]}] {self.name}: {self.message}"
        if self.fix_hint and self.status in (CheckStatus.ERROR, CheckStatus.WARNING):
            line += f"\n      Fix: {self.fix_hint}"
        return line


@dataclass
class PreflightReport:
    """Aggregate of all pre-flight checks."""
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status != CheckStatus.ERROR for c in self.checks)

    @property
    def errors(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status == CheckStatus.ERROR]

    @property
    def warnings(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status == CheckStatus.WARNING]

    def summary(self) -> str:
        lines = ["[CAI Sandbox] Pre-flight Check Results", "=" * 44]
        for c in self.checks:
            lines.append(str(c))
        lines.append("")
        if self.passed:
            if self.warnings:
                lines.append(f"Result: PASS with {len(self.warnings)} warning(s)")
            else:
                lines.append("Result: ALL CHECKS PASSED")
        else:
            lines.append(f"Result: FAILED — {len(self.errors)} error(s)")
        return "\n".join(lines)


class DependencyChecker:
    """Run all pre-flight dependency checks.

    Usage::

        checker = DependencyChecker()
        report = checker.run_all()
        if not report.passed:
            print(report.summary())
            sys.exit(1)
    """

    def __init__(self, require_gpu: bool = False, min_disk_gb: float = 5.0):
        self._require_gpu = require_gpu
        self._min_disk_gb = min_disk_gb

    def run_all(self) -> PreflightReport:
        """Execute every check and return a consolidated report."""
        report = PreflightReport()
        report.checks.append(self.check_python())
        report.checks.append(self.check_docker())
        report.checks.append(self.check_docker_running())
        report.checks.append(self.check_gpu_drivers())
        report.checks.append(self.check_python_packages())
        report.checks.append(self.check_network())
        report.checks.append(self.check_disk_space())
        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def check_python() -> CheckResult:
        """Verify Python version ≥ 3.9."""
        import sys
        v = sys.version_info
        if v >= (3, 9):
            return CheckResult("Python", CheckStatus.OK, f"{v.major}.{v.minor}.{v.micro}")
        return CheckResult(
            "Python", CheckStatus.ERROR,
            f"{v.major}.{v.minor}.{v.micro} (need ≥ 3.9)",
            fix_hint="Install Python 3.9+ from https://python.org",
        )

    @staticmethod
    def check_docker() -> CheckResult:
        """Verify Docker CLI is on PATH."""
        docker_bin = shutil.which("docker")
        if docker_bin:
            try:
                result = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                version = result.stdout.strip()
                return CheckResult("Docker CLI", CheckStatus.OK, version)
            except Exception as exc:
                return CheckResult(
                    "Docker CLI", CheckStatus.ERROR, str(exc),
                    fix_hint="Ensure Docker is properly installed",
                )
        return CheckResult(
            "Docker CLI", CheckStatus.ERROR, "Not found on PATH",
            fix_hint="Install Docker Desktop from https://docker.com/products/docker-desktop",
        )

    @staticmethod
    def check_docker_running() -> CheckResult:
        """Verify the Docker daemon is responsive."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return CheckResult("Docker Daemon", CheckStatus.OK, "Running")
            return CheckResult(
                "Docker Daemon", CheckStatus.ERROR,
                "Docker daemon not responding",
                fix_hint="Start Docker Desktop or run 'sudo systemctl start docker'",
            )
        except FileNotFoundError:
            return CheckResult(
                "Docker Daemon", CheckStatus.SKIPPED,
                "Docker CLI not installed",
            )
        except Exception as exc:
            return CheckResult(
                "Docker Daemon", CheckStatus.ERROR, str(exc),
                fix_hint="Start Docker Desktop or run 'sudo systemctl start docker'",
            )

    def check_gpu_drivers(self) -> CheckResult:
        """Detect NVIDIA GPU drivers (optional unless required)."""
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    gpu_info = result.stdout.strip().split("\n")[0]
                    return CheckResult("GPU Drivers", CheckStatus.OK, gpu_info)
            except Exception:
                pass

        # Try pynvml as fallback
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            pynvml.nvmlShutdown()
            return CheckResult("GPU Drivers", CheckStatus.OK, name)
        except Exception:
            pass

        if self._require_gpu:
            return CheckResult(
                "GPU Drivers", CheckStatus.ERROR,
                "No NVIDIA GPU detected",
                fix_hint="Install NVIDIA drivers from https://nvidia.com/drivers",
            )
        return CheckResult(
            "GPU Drivers", CheckStatus.WARNING,
            "No NVIDIA GPU detected (CPU-only mode will be used)",
        )

    @staticmethod
    def check_python_packages() -> CheckResult:
        """Verify critical Python packages are importable."""
        missing: List[str] = []
        for pkg in ("torch", "grpc", "psutil"):
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)

        # Optional packages
        optional_missing: List[str] = []
        for pkg in ("docker", "jwt", "cryptography", "zeroconf", "websockets", "aiohttp"):
            try:
                if pkg == "jwt":
                    __import__("jwt")
                else:
                    __import__(pkg)
            except ImportError:
                optional_missing.append(pkg)

        if missing:
            return CheckResult(
                "Python Packages", CheckStatus.ERROR,
                f"Missing required: {', '.join(missing)}",
                fix_hint=f"pip install {' '.join(missing)}",
            )
        if optional_missing:
            return CheckResult(
                "Python Packages", CheckStatus.WARNING,
                f"Missing optional: {', '.join(optional_missing)}",
                fix_hint=f"pip install {' '.join(optional_missing)}",
            )
        return CheckResult("Python Packages", CheckStatus.OK, "All packages available")

    @staticmethod
    def check_network() -> CheckResult:
        """Basic network connectivity check."""
        import socket
        try:
            sock = socket.create_connection(("8.8.8.8", 53), timeout=5)
            sock.close()
            return CheckResult("Network", CheckStatus.OK, "Internet connectivity available")
        except OSError:
            return CheckResult(
                "Network", CheckStatus.WARNING,
                "No internet connectivity (LAN-only mode available)",
            )

    def check_disk_space(self) -> CheckResult:
        """Verify sufficient disk space."""
        try:
            import shutil as _shutil
            from sandbox.config import CAI_SANDBOX_DIR

            # Check the drive where sandbox data will live
            check_path = CAI_SANDBOX_DIR if CAI_SANDBOX_DIR.exists() else Path.home()
            usage = _shutil.disk_usage(str(check_path))
            free_gb = usage.free / (1024 ** 3)

            if free_gb >= self._min_disk_gb:
                return CheckResult(
                    "Disk Space", CheckStatus.OK,
                    f"{free_gb:.1f} GB free",
                )
            return CheckResult(
                "Disk Space", CheckStatus.ERROR,
                f"{free_gb:.1f} GB free (need ≥ {self._min_disk_gb} GB)",
                fix_hint="Free up disk space or change CAI_SANDBOX_DIR",
            )
        except Exception as exc:
            return CheckResult("Disk Space", CheckStatus.WARNING, f"Could not check: {exc}")

    # ------------------------------------------------------------------
    # Docker-specific helpers
    # ------------------------------------------------------------------

    @staticmethod
    def check_nvidia_docker() -> CheckResult:
        """Check if NVIDIA Container Toolkit is installed for GPU passthrough."""
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "--gpus", "all", "nvidia/cuda:12.1.0-base-ubuntu22.04", "nvidia-smi"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                return CheckResult("NVIDIA Docker", CheckStatus.OK, "GPU passthrough available")
            return CheckResult(
                "NVIDIA Docker", CheckStatus.WARNING,
                "GPU passthrough not available",
                fix_hint="Install NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html",
            )
        except Exception as exc:
            return CheckResult(
                "NVIDIA Docker", CheckStatus.WARNING,
                f"Could not test: {exc}",
            )
