"""
Central configuration for the CAI Sandbox system.

All tunable constants, port assignments, directory paths, and mode
enumerations live here so every other module can import a single
source of truth.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClusterMode(Enum):
    """How this sandbox node participates in a cluster."""
    SINGLE = "single"
    MULTI_PRIMARY = "multi_primary"
    MULTI_WORKER = "multi_worker"


class NodeRole(Enum):
    """Role of a node inside a sandbox cluster."""
    PRIMARY = "primary"
    WORKER = "worker"


class NodeState(Enum):
    """Lifecycle state of a sandbox node in the cluster registry."""
    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    REMOVED = "removed"


# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------

def _default_data_dir() -> Path:
    """Return the platform-appropriate data directory for CAI Sandbox."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "cai_sandbox"


CAI_SANDBOX_DIR: Path = Path(os.environ.get("CAI_SANDBOX_DIR", str(_default_data_dir())))


# ---------------------------------------------------------------------------
# Network ports
# ---------------------------------------------------------------------------

GRPC_PORT: int = int(os.environ.get("CAI_SANDBOX_GRPC_PORT", "50100"))
REST_PORT: int = int(os.environ.get("CAI_SANDBOX_REST_PORT", "8100"))
WS_PORT: int = int(os.environ.get("CAI_SANDBOX_WS_PORT", "8101"))
CONTROLLER_API_PORT: int = int(os.environ.get("CAI_SANDBOX_API_PORT", "8200"))

# Inference (reused from existing CAI)
INFERENCE_GRPC_PORT: int = 50051
GATEWAY_HTTP_PORT: int = 8080
MONITOR_HTTP_PORT: int = 9090


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

SANDBOX_NETWORK_NAME: str = "cai_sandbox_net"
SANDBOX_IMAGE_PREFIX: str = "Cai-sandbox"
SANDBOX_NODE_IMAGE: str = f"{SANDBOX_IMAGE_PREFIX}-node:latest"
SANDBOX_COMPOSE_PROJECT: str = "Cai-sandbox"


# ---------------------------------------------------------------------------
# Auth & TLS
# ---------------------------------------------------------------------------

TOKEN_EXPIRY_HOURS: int = int(os.environ.get("CAI_SANDBOX_TOKEN_EXPIRY_HOURS", "720"))  # 30 days
TOKEN_SECRET_ENV: str = "CAI_SANDBOX_TOKEN_SECRET"  # override via env
CERT_DIR: Path = CAI_SANDBOX_DIR / "certs"
TOKEN_DIR: Path = CAI_SANDBOX_DIR / "tokens"


# ---------------------------------------------------------------------------
# mDNS / Discovery
# ---------------------------------------------------------------------------

MDNS_SERVICE_TYPE: str = "_cai-sandbox._tcp.local."
MDNS_SERVICE_NAME: str = "CAI Sandbox Node"


# ---------------------------------------------------------------------------
# Heartbeat / Health
# ---------------------------------------------------------------------------

HEARTBEAT_INTERVAL_S: float = float(os.environ.get("CAI_SANDBOX_HEARTBEAT_S", "5.0"))
HEARTBEAT_TIMEOUT_S: float = float(os.environ.get("CAI_SANDBOX_HEARTBEAT_TIMEOUT_S", "15.0"))
NODE_EXPIRY_S: float = float(os.environ.get("CAI_SANDBOX_NODE_EXPIRY_S", "30.0"))


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

MAX_SIMULATED_NODES: int = int(os.environ.get("CAI_SANDBOX_MAX_SIM_NODES", "10"))
SIM_CONTAINER_PREFIX: str = "Cai-sim-node"


# ---------------------------------------------------------------------------
# Composite config dataclass
# ---------------------------------------------------------------------------

@dataclass
class SandboxConfig:
    """Immutable snapshot of the current sandbox configuration.

    Useful for passing around to components that need to know multiple
    settings at once.
    """

    mode: ClusterMode = ClusterMode.SINGLE
    role: NodeRole = NodeRole.PRIMARY
    node_id: str = ""

    # Directories
    data_dir: Path = field(default_factory=lambda: CAI_SANDBOX_DIR)
    cert_dir: Path = field(default_factory=lambda: CERT_DIR)
    token_dir: Path = field(default_factory=lambda: TOKEN_DIR)

    # Ports
    grpc_port: int = GRPC_PORT
    rest_port: int = REST_PORT
    ws_port: int = WS_PORT
    api_port: int = CONTROLLER_API_PORT

    # Primary node address (workers connect here)
    primary_address: str = ""
    primary_port: int = GRPC_PORT

    # Auth
    access_token: str = ""

    # Docker
    docker_network: str = SANDBOX_NETWORK_NAME
    node_image: str = SANDBOX_NODE_IMAGE

    # Discovery
    enable_mdns: bool = True

    # Heartbeat
    heartbeat_interval: float = HEARTBEAT_INTERVAL_S
    heartbeat_timeout: float = HEARTBEAT_TIMEOUT_S

    def ensure_dirs(self) -> None:
        """Create all required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.token_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)
        (self.data_dir / "state").mkdir(exist_ok=True)
