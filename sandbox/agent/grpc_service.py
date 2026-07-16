"""
gRPC service implementation for CAI Sandbox inter-node communication.

Implements the NodeAgentService defined in sandbox.proto and provides
helper functions for client-side RPC calls.

The service reuses the existing ``InferenceService`` from inference.proto
for actual inference. This module handles control-plane RPCs only.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent import futures
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight request/response dataclasses (avoids proto compilation
# requirement while maintaining full compatibility).
# When protobuf stubs are generated, these can be replaced.
# ---------------------------------------------------------------------------

class _SimpleMessage:
    """Minimal message wrapper for JSON-serialised gRPC payloads."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# gRPC Servicer (server side)
# ---------------------------------------------------------------------------

class NodeAgentServicer:
    """gRPC servicer for the NodeAgentService.

    Delegates all logic to a ``NodeAgent`` instance so this class
    contains only RPC plumbing.

    Parameters
    ----------
    agent : NodeAgent
        The local node agent instance.
    """

    def __init__(self, agent):
        self._agent = agent

    # -- Registration -------------------------------------------------------

    def Register(self, request, context):
        """Handle a worker node's registration."""
        hardware = {}
        if hasattr(request, "hardware"):
            hw = request.hardware
            hardware = {
                "gpu_type": getattr(hw, "gpu_type", ""),
                "gpu_vram_mb": getattr(hw, "gpu_vram_mb", 0),
                "ram_mb": getattr(hw, "ram_mb", 0),
                "cpu_cores": getattr(hw, "cpu_cores", 0),
                "has_gpu": getattr(hw, "has_gpu", False),
                "power_draw_w": getattr(hw, "power_draw_w", 0),
            }

        result = self._agent.handle_worker_registration(
            node_id=request.node_id,
            access_token=request.access_token,
            hardware=hardware,
            address=getattr(request, "address", ""),
        )

        return _SimpleMessage(**result)

    # -- Heartbeat -----------------------------------------------------------

    def Heartbeat(self, request, context):
        """Handle a worker heartbeat."""
        hardware = {}
        energy = {}
        if hasattr(request, "hardware"):
            hardware = request.hardware if isinstance(request.hardware, dict) else {}
        if hasattr(request, "energy"):
            energy = request.energy if isinstance(request.energy, dict) else {}

        result = self._agent.handle_worker_heartbeat(
            node_id=request.node_id,
            hardware=hardware,
            energy=energy,
            load_pct=getattr(request, "load_pct", 0.0),
            active_chunks=list(getattr(request, "active_chunks", [])),
        )
        return _SimpleMessage(**result)

    # -- Chunk Assignment ----------------------------------------------------

    def AssignChunk(self, request, context):
        """Assign a model chunk to this node."""
        data = {
            "chunk_id": request.chunk_id,
            "num_chunks": getattr(request, "num_chunks", 0),
            "model_name": getattr(request, "model_name", ""),
            "model_type": getattr(request, "model_type", "transformer"),
        }
        result = self._agent.handle_chunk_assignment(data)
        return _SimpleMessage(**result)

    # -- Status --------------------------------------------------------------

    def GetStatus(self, request, context):
        """Return node status."""
        status = self._agent._handle_get_status()
        hw = self._agent._handle_get_hardware()
        metrics = self._agent._handle_get_metrics()
        return _SimpleMessage(
            node_id=self._agent.node_id,
            state=self._agent.state.value,
            hardware=hw,
            energy=metrics,
            active_chunks=self._agent.active_chunks,
            uptime_s=status.get("uptime_s", 0),
            version="0.1.0",
        )

    # -- Deregistration ------------------------------------------------------

    def Deregister(self, request, context):
        """Handle a worker's graceful departure."""
        result = self._agent.handle_worker_deregistration(
            node_id=request.node_id,
            reason=getattr(request, "reason", "user_request"),
        )
        return _SimpleMessage(**result)


# ---------------------------------------------------------------------------
# gRPC server management
# ---------------------------------------------------------------------------

class GrpcAgentServer:
    """Manages the gRPC server for the Node Agent.

    Parameters
    ----------
    agent : NodeAgent
        The local node agent.
    port : int
        Port to listen on.
    max_workers : int
        Thread pool size.
    """

    def __init__(self, agent, port: int = 50100, max_workers: int = 4):
        self._agent = agent
        self._port = port
        self._max_workers = max_workers
        self._server = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the gRPC server."""
        try:
            import grpc
            from concurrent import futures

            self._server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=self._max_workers),
            )

            servicer = NodeAgentServicer(self._agent)

            # Register using a generic service handler since we avoid
            # requiring proto compilation. The JSON-over-gRPC approach
            # uses a custom generic handler.
            _register_generic_handler(self._server, servicer)

            self._server.add_insecure_port(f"0.0.0.0:{self._port}")
            self._server.start()
            logger.info("gRPC Agent server started on port %d", self._port)
            return True

        except ImportError:
            logger.warning("grpcio not available — gRPC server disabled")
            return False
        except Exception as exc:
            logger.error("Failed to start gRPC server: %s", exc)
            return False

    def stop(self, grace: float = 5.0) -> None:
        """Stop the gRPC server."""
        if self._server:
            self._server.stop(grace)
            self._server = None
            logger.info("gRPC Agent server stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None


def _register_generic_handler(server, servicer):
    """Register the servicer methods as a generic gRPC handler.

    This avoids requiring compiled protobuf stubs by using
    ``grpc.method_service_handler`` with JSON serialisation.
    """
    import grpc

    method_map = {
        "Register": servicer.Register,
        "Heartbeat": servicer.Heartbeat,
        "AssignChunk": servicer.AssignChunk,
        "GetStatus": servicer.GetStatus,
        "Deregister": servicer.Deregister,
    }

    handlers = {}
    for name, fn in method_map.items():
        full_name = f"/Cai.sandbox.NodeAgentService/{name}"
        handlers[full_name] = grpc.unary_unary_rpc_method_handler(
            _json_handler(fn),
            request_deserializer=_json_deserialize,
            response_serializer=_json_serialize,
        )

    server.add_generic_rpc_handlers([_GenericHandler(handlers)])


class _GenericHandler:
    """Generic gRPC handler mapping method names to handlers."""

    def __init__(self, handlers: dict):
        self._handlers = handlers

    def service(self, handler_call_details):
        method = handler_call_details.method
        return self._handlers.get(method)


def _json_serialize(msg) -> bytes:
    """Serialise a response message to JSON bytes."""
    if hasattr(msg, "to_dict"):
        return json.dumps(msg.to_dict()).encode("utf-8")
    if isinstance(msg, dict):
        return json.dumps(msg).encode("utf-8")
    return json.dumps({"data": str(msg)}).encode("utf-8")


def _json_deserialize(data: bytes):
    """Deserialise JSON bytes into a simple message object."""
    try:
        d = json.loads(data.decode("utf-8"))
        return _SimpleMessage(**d)
    except Exception:
        return _SimpleMessage()


def _json_handler(fn):
    """Wrap a servicer method to handle JSON messages."""
    def wrapper(request, context):
        result = fn(request, context)
        return result
    return wrapper


# ---------------------------------------------------------------------------
# Client-side RPC helpers (used by NodeAgent)
# ---------------------------------------------------------------------------

def make_register_request(
    channel,
    node_id: str,
    access_token: str,
    hw_report,
    role: str,
    address: str,
    agent,
) -> bool:
    """Send a Register RPC to the primary node.

    Returns True on successful registration.
    """
    try:
        import grpc

        request_data = {
            "node_id": node_id,
            "access_token": access_token,
            "hardware": hw_report.to_dict() if hasattr(hw_report, "to_dict") else {},
            "role": role,
            "address": address,
            "version": "0.1.0",
        }

        # Use the JSON-over-gRPC approach
        method = "/Cai.sandbox.NodeAgentService/Register"
        response_bytes = channel.unary_unary(
            method,
            request_serializer=_json_serialize,
            response_deserializer=_json_deserialize,
        )(request_data)

        if hasattr(response_bytes, "accepted") and response_bytes.accepted:
            if hasattr(response_bytes, "cluster_id"):
                agent._cluster_id = response_bytes.cluster_id
            return True
        return False

    except Exception as exc:
        logger.debug("Register RPC failed: %s", exc)
        return False


def make_heartbeat_request(channel, data: Dict[str, Any]) -> bool:
    """Send a Heartbeat RPC to the primary node."""
    try:
        method = "/Cai.sandbox.NodeAgentService/Heartbeat"
        response = channel.unary_unary(
            method,
            request_serializer=_json_serialize,
            response_deserializer=_json_deserialize,
        )(data)
        return getattr(response, "acknowledged", False)
    except Exception:
        return False


def make_deregister_request(channel, node_id: str, reason: str) -> bool:
    """Send a Deregister RPC to the primary node."""
    try:
        method = "/Cai.sandbox.NodeAgentService/Deregister"
        data = {"node_id": node_id, "reason": reason}
        response = channel.unary_unary(
            method,
            request_serializer=_json_serialize,
            response_deserializer=_json_deserialize,
        )(data)
        return getattr(response, "acknowledged", False)
    except Exception:
        return False
