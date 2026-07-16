"""
Sandbox Runtime Manager.

Orchestrates the full CAI sandbox lifecycle: pre-flight checks,
Docker service initialization, and runtime state management.

Usage::

    from sandbox.runtime.manager import SandboxRuntimeManager
    from sandbox.config import SandboxConfig, ClusterMode

    config = SandboxConfig(mode=ClusterMode.SINGLE)
    manager = SandboxRuntimeManager(config)
    manager.start()
    print(manager.status())
    manager.stop()
"""

from __future__ import annotations

import json
import logging
import os
import platform
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sandbox.config import (
    ClusterMode,
    NodeRole,
    SandboxConfig,
    SANDBOX_NETWORK_NAME,
    INFERENCE_GRPC_PORT,
    GATEWAY_HTTP_PORT,
    MONITOR_HTTP_PORT,
)
from sandbox.runtime.dependency_checker import DependencyChecker, PreflightReport
from sandbox.runtime.docker_manager import DockerManager, ContainerConfig, ContainerInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class RuntimeState:
    """Tracks the current state of the sandbox runtime."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceStatus:
    """Status of an individual sandbox service."""
    name: str
    running: bool
    container_id: str = ""
    port: int = 0
    health: str = "unknown"
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "running": self.running,
            "container_id": self.container_id[:12] if self.container_id else "",
            "port": self.port,
            "health": self.health,
            "error": self.error,
        }


@dataclass
class SandboxStatus:
    """Overall sandbox runtime status."""
    state: str = RuntimeState.STOPPED
    node_id: str = ""
    mode: str = ""
    role: str = ""
    uptime_s: float = 0.0
    services: List[ServiceStatus] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "node_id": self.node_id,
            "mode": self.mode,
            "role": self.role,
            "uptime_s": round(self.uptime_s, 1),
            "services": [s.to_dict() for s in self.services],
            "error": self.error,
        }

    def summary(self) -> str:
        lines = [
            f"[CAI Sandbox] Status: {self.state.upper()}",
            f"  Node ID:  {self.node_id}",
            f"  Mode:     {self.mode}",
            f"  Role:     {self.role}",
            f"  Uptime:   {self.uptime_s:.0f}s",
        ]
        if self.services:
            lines.append("  Services:")
            for s in self.services:
                icon = "●" if s.running else "○"
                port_str = f" (:{s.port})" if s.port else ""
                lines.append(f"    {icon} {s.name}{port_str} — {s.health}")
        if self.error:
            lines.append(f"  Error: {self.error}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class SandboxRuntimeManager:
    """Manages the full CAI sandbox lifecycle.

    Parameters
    ----------
    config : SandboxConfig
        Sandbox configuration.
    skip_preflight : bool
        If True, skip pre-flight checks (for testing).
    """

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        skip_preflight: bool = False,
    ):
        self._config = config or SandboxConfig()
        self._skip_preflight = skip_preflight
        self._state = RuntimeState.STOPPED
        self._start_time: float = 0.0
        self._node_id = self._config.node_id or self._generate_node_id()

        # Ensure data directories exist
        self._config.ensure_dirs()

        # Managers (lazy-initialized)
        self._docker: Optional[DockerManager] = None
        self._container_ids: Dict[str, str] = {}  # service_name -> container_id
        self._state_file = self._config.data_dir / "state" / "runtime.json"

        # Try to restore previous state
        self._restore_state()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == RuntimeState.RUNNING

    @property
    def config(self) -> SandboxConfig:
        return self._config

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start the sandbox runtime.

        Executes pre-flight checks, initializes Docker, starts CAI
        services, and transitions to RUNNING state.

        Returns True if started successfully.
        """
        if self._state == RuntimeState.RUNNING:
            logger.warning("Sandbox is already running")
            return True

        self._state = RuntimeState.STARTING
        logger.info("Starting CAI Sandbox (mode=%s, role=%s)", self._config.mode.value, self._config.role.value)

        try:
            # 1. Pre-flight checks
            if not self._skip_preflight:
                report = self.run_preflight()
                if not report.passed:
                    print(report.summary())
                    self._state = RuntimeState.ERROR
                    return False
                logger.info("Pre-flight checks passed")

            # 2. Initialize Docker manager
            self._docker = DockerManager()
            if not self._docker.is_docker_running():
                logger.error("Docker daemon is not running")
                self._state = RuntimeState.ERROR
                return False

            # 3. Create sandbox network
            self._docker.ensure_network(self._config.docker_network)

            # 4. Start CAI services
            self._start_services()

            # 5. Transition to running
            self._state = RuntimeState.RUNNING
            self._start_time = time.monotonic()
            self._save_state()

            logger.info(
                "CAI Sandbox started successfully (node_id=%s)",
                self._node_id,
            )
            return True

        except Exception as exc:
            logger.exception("Failed to start sandbox: %s", exc)
            self._state = RuntimeState.ERROR
            return False

    def stop(self) -> bool:
        """Stop the sandbox runtime and all services."""
        if self._state == RuntimeState.STOPPED:
            logger.warning("Sandbox is already stopped")
            return True

        self._state = RuntimeState.STOPPING
        logger.info("Stopping CAI Sandbox...")

        try:
            self._stop_services()
            self._state = RuntimeState.STOPPED
            self._start_time = 0.0
            self._save_state()
            logger.info("CAI Sandbox stopped")
            return True
        except Exception as exc:
            logger.exception("Error stopping sandbox: %s", exc)
            self._state = RuntimeState.ERROR
            return False

    def restart(self) -> bool:
        """Restart the sandbox runtime."""
        self.stop()
        return self.start()

    def status(self) -> SandboxStatus:
        """Return the current sandbox status."""
        uptime = time.monotonic() - self._start_time if self._start_time > 0 else 0.0

        services: List[ServiceStatus] = []
        if self._docker and self._state == RuntimeState.RUNNING:
            services = self._check_services()

        return SandboxStatus(
            state=self._state,
            node_id=self._node_id,
            mode=self._config.mode.value,
            role=self._config.role.value,
            uptime_s=uptime,
            services=services,
        )

    # ------------------------------------------------------------------
    # Pre-flight
    # ------------------------------------------------------------------

    def run_preflight(self) -> PreflightReport:
        """Run pre-flight dependency checks."""
        checker = DependencyChecker(require_gpu=False)
        return checker.run_all()

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def _start_services(self) -> None:
        """Start all CAI services based on the current mode."""
        assert self._docker is not None

        mode = self._config.mode
        has_gpu = self._docker.has_gpu_support()

        if mode == ClusterMode.SINGLE:
            self._start_single_node_services(has_gpu)
        elif mode == ClusterMode.MULTI_PRIMARY:
            self._start_primary_services(has_gpu)
        elif mode == ClusterMode.MULTI_WORKER:
            self._start_worker_services(has_gpu)

    def _start_single_node_services(self, has_gpu: bool) -> None:
        """Start services for single-node mode."""
        assert self._docker is not None

        # Monitor service
        monitor_id = self._docker.create_container(ContainerConfig(
            name=f"Cai-sandbox-monitor-{self._node_id[:8]}",
            image=self._resolve_image("monitor"),
            environment={
                "MONITOR_PORT": str(MONITOR_HTTP_PORT),
                "GPU_INDEX": "0",
                "SAMPLING_RATE": "1.0",
                "ENABLE_GPU": "true" if has_gpu else "false",
            },
            ports={str(MONITOR_HTTP_PORT): str(MONITOR_HTTP_PORT)},
            labels={"Cai.sandbox": "true", "Cai.service": "monitor", "Cai.node_id": self._node_id},
            gpus="all" if has_gpu else None,
        ))
        if monitor_id:
            self._container_ids["monitor"] = monitor_id

        logger.info("Single-node services started (GPU=%s)", has_gpu)

    def _start_primary_services(self, has_gpu: bool) -> None:
        """Start services for multi-node primary mode."""
        # Primary runs monitor + is ready to accept workers
        self._start_single_node_services(has_gpu)
        logger.info("Primary node services started. Waiting for workers...")

    def _start_worker_services(self, has_gpu: bool) -> None:
        """Start services for multi-node worker mode."""
        assert self._docker is not None

        # Worker runs monitor only (chunk server started on model deployment)
        monitor_id = self._docker.create_container(ContainerConfig(
            name=f"Cai-sandbox-monitor-{self._node_id[:8]}",
            image=self._resolve_image("monitor"),
            environment={
                "MONITOR_PORT": str(MONITOR_HTTP_PORT),
                "GPU_INDEX": "0",
                "SAMPLING_RATE": "1.0",
                "ENABLE_GPU": "true" if has_gpu else "false",
            },
            ports={str(MONITOR_HTTP_PORT): str(MONITOR_HTTP_PORT)},
            labels={"Cai.sandbox": "true", "Cai.service": "monitor", "Cai.node_id": self._node_id},
            gpus="all" if has_gpu else None,
        ))
        if monitor_id:
            self._container_ids["monitor"] = monitor_id

        logger.info("Worker node services started (GPU=%s)", has_gpu)

    def _stop_services(self) -> None:
        """Stop all sandbox containers."""
        if not self._docker:
            return

        for service_name, container_id in list(self._container_ids.items()):
            logger.info("Stopping service: %s", service_name)
            self._docker.stop_and_remove(container_id)

        self._container_ids.clear()

        # Also cleanup any orphaned sandbox containers
        self._docker.cleanup_sandbox_containers()

    def _check_services(self) -> List[ServiceStatus]:
        """Check the health of all running services."""
        services: List[ServiceStatus] = []
        if not self._docker:
            return services

        for service_name, container_id in self._container_ids.items():
            info = self._docker.get_container_info(container_id)
            if info:
                services.append(ServiceStatus(
                    name=service_name,
                    running=info.is_running,
                    container_id=container_id,
                    health="running" if info.is_running else "stopped",
                ))
            else:
                services.append(ServiceStatus(
                    name=service_name,
                    running=False,
                    health="not found",
                    error="Container not found",
                ))

        return services

    # ------------------------------------------------------------------
    # Image resolution
    # ------------------------------------------------------------------

    def _resolve_image(self, component: str) -> str:
        """Resolve the Docker image for a CAI component.

        Falls back to building from local Dockerfiles if image not found.
        """
        assert self._docker is not None

        image_map = {
            "chunk": "Cai-chunk:latest",
            "gateway": "Cai-gateway:latest",
            "monitor": "Cai-monitor:latest",
        }
        image = image_map.get(component, f"Cai-{component}:latest")

        if self._docker.image_exists(image):
            return image

        # Try to build from local Dockerfile
        dockerfile_map = {
            "chunk": "docker/Dockerfile.chunk",
            "gateway": "docker/Dockerfile.gateway",
            "monitor": "docker/Dockerfile.monitor",
        }
        dockerfile = dockerfile_map.get(component)
        if dockerfile:
            df_path = self._docker._project_root / dockerfile
            if df_path.exists():
                logger.info("Building image for '%s' from %s", component, dockerfile)
                if self._docker.build_image(str(df_path), image):
                    return image

        logger.warning("Image '%s' not available; using base Python image", image)
        return "python:3.11-slim"

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        """Persist runtime state to disk."""
        state = {
            "node_id": self._node_id,
            "state": self._state,
            "mode": self._config.mode.value,
            "role": self._config.role.value,
            "container_ids": self._container_ids,
            "timestamp": time.time(),
        }
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Could not save state: %s", exc)

    def _restore_state(self) -> None:
        """Restore runtime state from disk (if any)."""
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            saved_node_id = data.get("node_id", "")
            if saved_node_id:
                self._node_id = saved_node_id
            # Don't restore RUNNING state — we need to verify containers
            self._container_ids = data.get("container_ids", {})
        except Exception as exc:
            logger.debug("Could not restore state: %s", exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_node_id() -> str:
        """Generate a unique node identifier."""
        hostname = platform.node() or "unknown"
        short_uuid = uuid.uuid4().hex[:8]
        return f"{hostname}-{short_uuid}"

    # ------------------------------------------------------------------
    # Chunk server management (used by model deployment)
    # ------------------------------------------------------------------

    def start_chunk_server(
        self,
        chunk_id: int,
        num_chunks: int,
        model_type: str = "transformer",
        weights_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Start a chunk server container for distributed inference.

        Returns the container ID on success.
        """
        if not self._docker:
            logger.error("Docker manager not initialized")
            return None

        has_gpu = self._docker.has_gpu_support()
        port = INFERENCE_GRPC_PORT + chunk_id

        container_id = self._docker.create_container(ContainerConfig(
            name=f"Cai-sandbox-chunk-{chunk_id}-{self._node_id[:8]}",
            image=self._resolve_image("chunk"),
            environment={
                "CHUNK_ID": str(chunk_id),
                "NUM_CHUNKS": str(num_chunks),
                "MODEL_TYPE": model_type,
                "WEIGHTS_DIR": "/data/chunks",
                "PORT": str(INFERENCE_GRPC_PORT),
                "DEVICE": "cuda:0" if has_gpu else "cpu",
            },
            ports={str(port): str(INFERENCE_GRPC_PORT)},
            volumes={weights_dir: "/data/chunks"} if weights_dir else {},
            labels={
                "Cai.sandbox": "true",
                "Cai.service": "chunk",
                "Cai.chunk_id": str(chunk_id),
                "Cai.node_id": self._node_id,
            },
            gpus="all" if has_gpu else None,
        ))

        if container_id:
            self._container_ids[f"chunk-{chunk_id}"] = container_id
            self._save_state()

        return container_id

    def start_gateway(self, chunk_hosts: List[str]) -> Optional[str]:
        """Start the inference gateway pointing to chunk hosts.

        Parameters
        ----------
        chunk_hosts : list[str]
            Ordered list of ``host:port`` for each chunk server.
        """
        if not self._docker:
            return None

        container_id = self._docker.create_container(ContainerConfig(
            name=f"Cai-sandbox-gateway-{self._node_id[:8]}",
            image=self._resolve_image("gateway"),
            environment={
                "GATEWAY_PORT": str(GATEWAY_HTTP_PORT),
                "CHUNK_HOSTS": ",".join(chunk_hosts),
            },
            ports={str(GATEWAY_HTTP_PORT): str(GATEWAY_HTTP_PORT)},
            labels={"Cai.sandbox": "true", "Cai.service": "gateway", "Cai.node_id": self._node_id},
        ))

        if container_id:
            self._container_ids["gateway"] = container_id
            self._save_state()

        return container_id
