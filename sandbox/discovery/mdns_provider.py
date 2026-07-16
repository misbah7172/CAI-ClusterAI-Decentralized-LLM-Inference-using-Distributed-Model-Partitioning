"""
mDNS provider for CAI Sandbox LAN auto-discovery.

Uses the ``zeroconf`` library to advertise and discover CAI Sandbox
nodes on the local network. Falls back gracefully when zeroconf is
not installed.

Usage::

    provider = MDNSProvider(node_id="mynode-abc", port=50100)
    provider.start_advertising()

    # On another machine:
    provider.start_scanning(on_found=lambda info: print(info))
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from sandbox.config import MDNS_SERVICE_TYPE, MDNS_SERVICE_NAME

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredNode:
    """Information about a discovered CAI Sandbox node."""
    node_id: str
    cluster_id: str
    role: str  # "primary" or "worker"
    address: str  # ip:port
    version: str = "0.1.0"
    properties: Dict[str, str] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "cluster_id": self.cluster_id,
            "role": self.role,
            "address": self.address,
            "version": self.version,
        }


class MDNSProvider:
    """mDNS-based service advertisement and discovery.

    Parameters
    ----------
    node_id : str
        Unique node identifier.
    port : int
        Port the node agent is listening on.
    cluster_id : str
        Cluster this node belongs to.
    role : str
        Node role (``"primary"`` or ``"worker"``).
    """

    def __init__(
        self,
        node_id: str,
        port: int = 50100,
        cluster_id: str = "",
        role: str = "primary",
    ):
        self._node_id = node_id
        self._port = port
        self._cluster_id = cluster_id
        self._role = role

        self._zeroconf = None
        self._service_info = None
        self._browser = None

        # Discovery results
        self._discovered: Dict[str, DiscoveredNode] = {}
        self._lock = threading.Lock()

        # Callbacks
        self._on_found: Optional[Callable[[DiscoveredNode], None]] = None
        self._on_lost: Optional[Callable[[str], None]] = None

    # ------------------------------------------------------------------
    # Advertising (announce this node on the LAN)
    # ------------------------------------------------------------------

    def start_advertising(self) -> bool:
        """Advertise this node on the local network via mDNS.

        Returns True if advertising started successfully.
        """
        try:
            from zeroconf import Zeroconf, ServiceInfo
        except ImportError:
            logger.warning(
                "zeroconf not installed — mDNS discovery disabled. "
                "Install with: pip install zeroconf"
            )
            return False

        try:
            local_ip = self._get_local_ip()
            ip_bytes = socket.inet_aton(local_ip)

            properties = {
                "node_id": self._node_id,
                "cluster_id": self._cluster_id,
                "role": self._role,
                "version": "0.1.0",
            }

            service_name = f"{self._node_id}.{MDNS_SERVICE_TYPE}"
            self._service_info = ServiceInfo(
                MDNS_SERVICE_TYPE,
                service_name,
                addresses=[ip_bytes],
                port=self._port,
                properties=properties,
                server=f"{self._node_id}.local.",
            )

            self._zeroconf = Zeroconf()
            self._zeroconf.register_service(self._service_info)

            logger.info(
                "mDNS advertising started: %s @ %s:%d",
                self._node_id, local_ip, self._port,
            )
            return True

        except Exception as exc:
            logger.error("Failed to start mDNS advertising: %s", exc)
            return False

    def stop_advertising(self) -> None:
        """Stop mDNS advertisement."""
        if self._zeroconf and self._service_info:
            try:
                self._zeroconf.unregister_service(self._service_info)
            except Exception:
                pass
            self._service_info = None

    # ------------------------------------------------------------------
    # Scanning (find other nodes on the LAN)
    # ------------------------------------------------------------------

    def start_scanning(
        self,
        on_found: Optional[Callable[[DiscoveredNode], None]] = None,
        on_lost: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Start scanning for other CAI Sandbox nodes on the LAN.

        Parameters
        ----------
        on_found : callable, optional
            Called when a new node is discovered.
        on_lost : callable, optional
            Called when a node disappears.
        """
        self._on_found = on_found
        self._on_lost = on_lost

        try:
            from zeroconf import Zeroconf, ServiceBrowser
        except ImportError:
            logger.warning("zeroconf not installed — scanning disabled")
            return False

        try:
            if self._zeroconf is None:
                self._zeroconf = Zeroconf()

            self._browser = ServiceBrowser(
                self._zeroconf, MDNS_SERVICE_TYPE, self,
            )

            logger.info("mDNS scanning started for %s", MDNS_SERVICE_TYPE)
            return True

        except Exception as exc:
            logger.error("Failed to start mDNS scanning: %s", exc)
            return False

    def stop_scanning(self) -> None:
        """Stop mDNS scanning."""
        if self._browser:
            try:
                self._browser.cancel()
            except Exception:
                pass
            self._browser = None

    # ------------------------------------------------------------------
    # ServiceBrowser callbacks (called by zeroconf)
    # ------------------------------------------------------------------

    def add_service(self, zc, service_type: str, name: str) -> None:
        """Called when a new service is found."""
        try:
            from zeroconf import Zeroconf
            info = zc.get_service_info(service_type, name)
            if info is None:
                return

            # Parse properties
            properties = {}
            if info.properties:
                for k, v in info.properties.items():
                    key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                    val = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                    properties[key] = val

            node_id = properties.get("node_id", name.split(".")[0])

            # Skip self
            if node_id == self._node_id:
                return

            # Get address
            addresses = info.parsed_addresses()
            if not addresses:
                return
            address = f"{addresses[0]}:{info.port}"

            node = DiscoveredNode(
                node_id=node_id,
                cluster_id=properties.get("cluster_id", ""),
                role=properties.get("role", "worker"),
                address=address,
                version=properties.get("version", ""),
                properties=properties,
            )

            with self._lock:
                self._discovered[node_id] = node

            logger.info("Discovered node: %s @ %s (role=%s)", node_id, address, node.role)

            if self._on_found:
                self._on_found(node)

        except Exception as exc:
            logger.debug("Error processing discovered service: %s", exc)

    def remove_service(self, zc, service_type: str, name: str) -> None:
        """Called when a service disappears."""
        node_id = name.split(".")[0]
        with self._lock:
            if node_id in self._discovered:
                del self._discovered[node_id]

        logger.info("Lost node: %s", node_id)
        if self._on_lost:
            self._on_lost(node_id)

    def update_service(self, zc, service_type: str, name: str) -> None:
        """Called when a service is updated."""
        self.add_service(zc, service_type, name)

    # ------------------------------------------------------------------
    # Discovery results
    # ------------------------------------------------------------------

    def get_discovered_nodes(self) -> List[DiscoveredNode]:
        """Return all currently discovered nodes."""
        with self._lock:
            return list(self._discovered.values())

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Shut down all mDNS operations."""
        self.stop_scanning()
        self.stop_advertising()
        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception:
                pass
            self._zeroconf = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_local_ip() -> str:
        """Get the machine's LAN IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
