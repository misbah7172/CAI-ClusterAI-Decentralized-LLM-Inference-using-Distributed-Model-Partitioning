"""
Low-level Docker operations for the CAI Sandbox.

Manages image lifecycle, container creation/teardown, network setup,
volume management, and GPU passthrough configuration.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sandbox.config import (
    SANDBOX_NETWORK_NAME,
    SANDBOX_IMAGE_PREFIX,
    SANDBOX_NODE_IMAGE,
    CAI_SANDBOX_DIR,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ContainerInfo:
    """Describes a running or stopped Docker container."""
    container_id: str
    name: str
    image: str
    status: str
    ports: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def is_running(self) -> bool:
        return "running" in self.status.lower()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id[:12],
            "name": self.name,
            "image": self.image,
            "status": self.status,
            "ports": self.ports,
            "labels": self.labels,
            "is_running": self.is_running,
        }


@dataclass
class ContainerConfig:
    """Configuration for creating a new Docker container."""
    name: str
    image: str
    environment: Dict[str, str] = field(default_factory=dict)
    ports: Dict[str, str] = field(default_factory=dict)  # host:container
    volumes: Dict[str, str] = field(default_factory=dict)  # host_path:container_path
    labels: Dict[str, str] = field(default_factory=dict)
    network: str = SANDBOX_NETWORK_NAME
    cpus: Optional[float] = None  # CPU limit (e.g. 2.0)
    memory: Optional[str] = None  # Memory limit (e.g. "4g")
    gpus: Optional[str] = None  # GPU spec (e.g. "all" or "1")
    command: Optional[str] = None
    restart_policy: str = "unless-stopped"
    detach: bool = True


class DockerManager:
    """Manages Docker operations for the sandbox runtime.

    Uses the Docker CLI directly rather than the Docker SDK to minimize
    dependencies and maintain compatibility across platforms.

    Parameters
    ----------
    project_root : Path
        Root directory of the CAI project (for building images).
    """

    def __init__(self, project_root: Optional[Path] = None):
        self._project_root = project_root or Path(__file__).resolve().parents[2]
        self._docker_bin = self._find_docker()

    # ------------------------------------------------------------------
    # Docker detection
    # ------------------------------------------------------------------

    @staticmethod
    def _find_docker() -> str:
        """Locate the docker binary."""
        import shutil
        docker = shutil.which("docker")
        if docker:
            return docker
        # Windows fallback
        docker = shutil.which("docker.exe")
        if docker:
            return docker
        raise RuntimeError(
            "Docker not found on PATH. Install Docker Desktop from https://docker.com"
        )

    def is_docker_running(self) -> bool:
        """Check if the Docker daemon is responsive."""
        try:
            result = subprocess.run(
                [self._docker_bin, "info"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def has_gpu_support(self) -> bool:
        """Check if NVIDIA GPU passthrough is available."""
        try:
            result = subprocess.run(
                [self._docker_bin, "info", "--format", "{{.Runtimes}}"],
                capture_output=True, text=True, timeout=10,
            )
            return "nvidia" in result.stdout.lower() or "gpu" in result.stdout.lower()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Network management
    # ------------------------------------------------------------------

    def ensure_network(self, name: str = SANDBOX_NETWORK_NAME) -> None:
        """Create the sandbox Docker network if it doesn't exist."""
        try:
            result = subprocess.run(
                [self._docker_bin, "network", "inspect", name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                logger.debug("Docker network '%s' already exists", name)
                return
        except Exception:
            pass

        logger.info("Creating Docker network '%s'", name)
        subprocess.run(
            [self._docker_bin, "network", "create", "--driver", "bridge", name],
            capture_output=True, text=True, timeout=15,
            check=True,
        )

    def remove_network(self, name: str = SANDBOX_NETWORK_NAME) -> None:
        """Remove the sandbox Docker network."""
        try:
            subprocess.run(
                [self._docker_bin, "network", "rm", name],
                capture_output=True, text=True, timeout=10,
            )
            logger.info("Removed Docker network '%s'", name)
        except Exception as exc:
            logger.debug("Could not remove network '%s': %s", name, exc)

    # ------------------------------------------------------------------
    # Image management
    # ------------------------------------------------------------------

    def image_exists(self, image: str) -> bool:
        """Check if a Docker image exists locally."""
        try:
            result = subprocess.run(
                [self._docker_bin, "image", "inspect", image],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def pull_image(self, image: str) -> bool:
        """Pull a Docker image from a registry."""
        logger.info("Pulling Docker image: %s", image)
        try:
            result = subprocess.run(
                [self._docker_bin, "pull", image],
                capture_output=True, text=True, timeout=600,
            )
            return result.returncode == 0
        except Exception as exc:
            logger.error("Failed to pull image %s: %s", image, exc)
            return False

    def build_image(
        self,
        dockerfile: str,
        tag: str,
        context: Optional[Path] = None,
    ) -> bool:
        """Build a Docker image from a Dockerfile."""
        ctx = str(context or self._project_root)
        logger.info("Building Docker image: %s (from %s)", tag, dockerfile)
        try:
            result = subprocess.run(
                [self._docker_bin, "build", "-f", dockerfile, "-t", tag, ctx],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                logger.error("Build failed: %s", result.stderr[-500:] if result.stderr else "unknown")
                return False
            logger.info("Built image: %s", tag)
            return True
        except Exception as exc:
            logger.error("Build error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    def create_container(self, config: ContainerConfig) -> Optional[str]:
        """Create and start a Docker container.

        Returns the container ID on success, None on failure.
        """
        cmd = [self._docker_bin, "run"]

        if config.detach:
            cmd.append("-d")

        cmd.extend(["--name", config.name])
        cmd.extend(["--network", config.network])
        cmd.extend(["--restart", config.restart_policy])

        # Labels
        for k, v in config.labels.items():
            cmd.extend(["--label", f"{k}={v}"])

        # Environment
        for k, v in config.environment.items():
            cmd.extend(["-e", f"{k}={v}"])

        # Ports
        for host_port, container_port in config.ports.items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])

        # Volumes
        for host_path, container_path in config.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Resource limits
        if config.cpus is not None:
            cmd.extend(["--cpus", str(config.cpus)])
        if config.memory is not None:
            cmd.extend(["--memory", config.memory])

        # GPU
        if config.gpus is not None:
            cmd.extend(["--gpus", config.gpus])

        cmd.append(config.image)

        if config.command:
            cmd.extend(config.command.split())

        logger.info("Creating container: %s (image=%s)", config.name, config.image)
        logger.debug("Docker command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.error(
                    "Failed to create container '%s': %s",
                    config.name, result.stderr.strip(),
                )
                return None

            container_id = result.stdout.strip()
            logger.info("Container '%s' started (ID: %s)", config.name, container_id[:12])
            return container_id
        except Exception as exc:
            logger.error("Error creating container '%s': %s", config.name, exc)
            return None

    def stop_container(self, name_or_id: str, timeout: int = 10) -> bool:
        """Stop a running container gracefully."""
        try:
            result = subprocess.run(
                [self._docker_bin, "stop", "-t", str(timeout), name_or_id],
                capture_output=True, text=True, timeout=timeout + 15,
            )
            if result.returncode == 0:
                logger.info("Stopped container: %s", name_or_id)
                return True
            logger.warning("Failed to stop container '%s': %s", name_or_id, result.stderr.strip())
            return False
        except Exception as exc:
            logger.error("Error stopping container '%s': %s", name_or_id, exc)
            return False

    def remove_container(self, name_or_id: str, force: bool = False) -> bool:
        """Remove a container."""
        cmd = [self._docker_bin, "rm"]
        if force:
            cmd.append("-f")
        cmd.append(name_or_id)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("Removed container: %s", name_or_id)
                return True
            return False
        except Exception as exc:
            logger.error("Error removing container '%s': %s", name_or_id, exc)
            return False

    def stop_and_remove(self, name_or_id: str) -> bool:
        """Stop and remove a container."""
        self.stop_container(name_or_id)
        return self.remove_container(name_or_id, force=True)

    # ------------------------------------------------------------------
    # Container inspection
    # ------------------------------------------------------------------

    def get_container_info(self, name_or_id: str) -> Optional[ContainerInfo]:
        """Inspect a container and return its info."""
        try:
            result = subprocess.run(
                [
                    self._docker_bin, "inspect",
                    "--format",
                    '{"id":"{{.Id}}","name":"{{.Name}}","image":"{{.Config.Image}}","status":"{{.State.Status}}"}',
                    name_or_id,
                ],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None

            data = json.loads(result.stdout.strip())
            return ContainerInfo(
                container_id=data.get("id", ""),
                name=data.get("name", "").lstrip("/"),
                image=data.get("image", ""),
                status=data.get("status", "unknown"),
            )
        except Exception:
            return None

    def list_containers(
        self,
        label_filter: Optional[str] = None,
        all_containers: bool = False,
    ) -> List[ContainerInfo]:
        """List containers, optionally filtered by label."""
        cmd = [self._docker_bin, "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"]
        if all_containers:
            cmd.append("-a")
        if label_filter:
            cmd.extend(["--filter", f"label={label_filter}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return []

            containers: List[ContainerInfo] = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 4:
                    containers.append(ContainerInfo(
                        container_id=parts[0],
                        name=parts[1],
                        image=parts[2],
                        status=parts[3],
                    ))
            return containers
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Health checking
    # ------------------------------------------------------------------

    def wait_for_healthy(
        self,
        name_or_id: str,
        timeout_s: float = 60.0,
        poll_interval: float = 2.0,
    ) -> bool:
        """Wait until a container is running and healthy."""
        start = time.monotonic()
        while time.monotonic() - start < timeout_s:
            info = self.get_container_info(name_or_id)
            if info and info.is_running:
                return True
            time.sleep(poll_interval)
        return False

    # ------------------------------------------------------------------
    # Compose helpers
    # ------------------------------------------------------------------

    def compose_up(
        self,
        compose_file: Path,
        project_name: str = "Cai-sandbox",
        detach: bool = True,
        build: bool = False,
    ) -> bool:
        """Run docker compose up."""
        cmd = [
            self._docker_bin, "compose",
            "-f", str(compose_file),
            "-p", project_name,
            "up",
        ]
        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")

        logger.info("Running docker compose up (project=%s)", project_name)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error("Compose up failed: %s", result.stderr[-500:] if result.stderr else "")
                return False
            return True
        except Exception as exc:
            logger.error("Compose up error: %s", exc)
            return False

    def compose_down(
        self,
        compose_file: Path,
        project_name: str = "Cai-sandbox",
        volumes: bool = False,
    ) -> bool:
        """Run docker compose down."""
        cmd = [
            self._docker_bin, "compose",
            "-f", str(compose_file),
            "-p", project_name,
            "down",
        ]
        if volumes:
            cmd.append("-v")

        logger.info("Running docker compose down (project=%s)", project_name)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception as exc:
            logger.error("Compose down error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_sandbox_containers(self) -> int:
        """Remove all containers with the sandbox label."""
        containers = self.list_containers(
            label_filter=f"Cai.sandbox=true",
            all_containers=True,
        )
        count = 0
        for c in containers:
            if self.stop_and_remove(c.name):
                count += 1
        if count:
            logger.info("Cleaned up %d sandbox container(s)", count)
        return count
