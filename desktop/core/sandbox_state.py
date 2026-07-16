"""
Core sandbox state manager for CAI Sandbox Desktop GUI.
Integrates the in-process CAI services with Qt signals.
"""

import logging
import io
import sys
import traceback
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from sandbox.config import SandboxConfig, ClusterMode, NodeRole, NodeState
from sandbox.agent.node_agent import NodeAgent
from sandbox.discovery.discovery_service import ClusterDiscoveryService
from sandbox.controller.remote_controller import RemoteController
from sandbox.simulation.engine import SimulationEngine
from sandbox.auth.token_manager import TokenManager

# Set up custom log capture handler
class QtSignalingLogHandler(logging.Handler):
    def __init__(self, signal: pyqtSignal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signal.emit(msg)
        except Exception:
            self.handleError(record)


class SandboxStateManager(QObject):
    # Signals for UI communication
    log_received = pyqtSignal(str)
    nodes_updated = pyqtSignal(list)
    sim_metrics_updated = pyqtSignal(list)
    inference_completed = pyqtSignal(bool, str, dict) # success, text, metrics
    status_changed = pyqtSignal(str) # description of current state

    def __init__(self):
        super().__init__()
        self.agent: Optional[NodeAgent] = None
        self.discovery: Optional[ClusterDiscoveryService] = None
        self.controller: Optional[RemoteController] = None
        self.sim_engine: Optional[SimulationEngine] = None
        self.config: Optional[SandboxConfig] = None
        
        self.sandbox_active = False
        self.sim_active = False
        self.deployments: List[Dict[str, Any]] = []
        self.join_token = ""

        # Setup logging redirection
        self.log_handler = QtSignalingLogHandler(self.log_received)
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(self.log_handler)
        
        # Intercept stdout/stderr as well
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = StreamToSignal(self.log_received)
        sys.stderr = StreamToSignal(self.log_received)

    def start_sandbox(self, mode: str, role: str, node_id: str, grpc_port: int, api_port: int, primary_address: str = "", access_token: str = ""):
        try:
            self.status_changed.emit("Initializing Sandbox Configuration...")
            self.config = SandboxConfig(
                mode=ClusterMode(mode),
                role=NodeRole(role),
                node_id=node_id,
                grpc_port=grpc_port,
                api_port=api_port,
                primary_address=primary_address or f"localhost:{grpc_port}",
                access_token=access_token
            )
            self.config.ensure_dirs()

            self.status_changed.emit("Starting Node Agent...")
            self.agent = NodeAgent(self.config)
            self.agent.start()

            if self.config.role == NodeRole.PRIMARY:
                self.status_changed.emit("Starting Cluster Discovery...")
                self.discovery = ClusterDiscoveryService(self.config)
                self.discovery.start()

                self.status_changed.emit("Starting Cluster Controller...")
                self.controller = RemoteController(self.agent, self.discovery, self.config)

                # Generate join token
                tm = TokenManager(token_dir=self.config.token_dir)
                self.join_token = tm.generate_cluster_token(self.agent.cluster_id, "worker")
                
            elif self.config.role == NodeRole.WORKER and primary_address:
                self.status_changed.emit(f"Registering worker with primary at {primary_address}...")
                registered = self.agent.register(primary_address, access_token)
                if not registered:
                    self.agent.stop()
                    raise ValueError("Registration rejected by primary node. Check token and connection.")

            self.sandbox_active = True
            self.status_changed.emit(f"Sandbox Control Plane active as {role.upper()}")
            return True, "Sandbox started successfully"
        except Exception as e:
            traceback.print_exc()
            self.stop_sandbox()
            self.status_changed.emit(f"Start failed: {str(e)}")
            return False, str(e)

    def stop_sandbox(self):
        self.status_changed.emit("Stopping Sandbox services...")
        
        # Stop simulation first
        if self.sim_active:
            self.stop_simulation()

        if self.discovery:
            try:
                self.discovery.stop()
            except Exception:
                pass
            self.discovery = None

        if self.agent:
            try:
                self.agent.stop()
            except Exception:
                pass
            self.agent = None

        self.controller = None
        self.sandbox_active = False
        self.deployments.clear()
        self.join_token = ""
        self.status_changed.emit("Sandbox Control Plane stopped")

    def start_simulation(self, num_nodes: int, profile_mix: str):
        if not self.sandbox_active or self.config.role != NodeRole.PRIMARY:
            return False, "Control plane must be active as PRIMARY to run simulation"
        
        try:
            self.status_changed.emit(f"Starting simulation of {num_nodes} workers...")
            self.sim_engine = SimulationEngine(registry=self.discovery.registry)
            self.sim_engine.simulate(num_nodes=num_nodes, profile_type=profile_mix)
            self.sim_active = True
            self.status_changed.emit("Virtual Node Simulation Active")
            return True, "Simulation started"
        except Exception as e:
            self.sim_active = False
            self.sim_engine = None
            return False, str(e)

    def stop_simulation(self):
        if self.sim_engine:
            self.status_changed.emit("Stopping virtual simulation...")
            try:
                self.sim_engine.stop_simulation()
            except Exception:
                pass
            self.sim_engine = None
        self.sim_active = False
        self.status_changed.emit("Simulation stopped")

    def update_metrics(self):
        """Called periodically by UI to gather and emit nodes/sim metrics updates."""
        if not self.sandbox_active:
            return

        # Emit nodes list
        if self.controller:
            try:
                nodes = self.controller.list_nodes()
                self.nodes_updated.emit(nodes)
            except Exception:
                pass

        # Emit simulated telemetry
        if self.sim_active and self.sim_engine:
            try:
                sim_metrics = []
                with self.sim_engine._lock:
                    for nid, node in self.sim_engine._nodes.items():
                        info = node.get_info()
                        met = info.get("metrics", {})
                        sim_metrics.append({
                            "node_id": nid,
                            "state": info.get("state"),
                            "gpu_temp": met.get("gpu_temperature_c", 0.0),
                            "cpu_load": met.get("cpu_utilization_pct", 0.0) * 100,
                            "power_draw": met.get("power_draw_w", 0.0)
                        })
                self.sim_metrics_updated.emit(sim_metrics)
            except Exception:
                pass

    def deploy_model(self, model_name: str, num_chunks: int, strategy: str):
        if not self.controller:
            return False, "No active controller"
        
        try:
            self.status_changed.emit(f"Deploying model '{model_name}' to cluster...")
            res = self.controller.deploy_model(
                model_name=model_name,
                num_chunks=num_chunks,
                strategy=strategy
            )
            if res.get("success"):
                self.deployments.append({
                    "deployment_id": res["deployment_id"],
                    "model_name": model_name,
                    "placements": res["placements"]
                })
                self.status_changed.emit(f"Model '{model_name}' deployed successfully")
                return True, res
            else:
                return False, res.get("message", "Unknown deployment error")
        except Exception as e:
            return False, str(e)

    def trigger_inference(self, model_name: str, prompt: str, max_tokens: int, temperature: float):
        if not self.controller:
            self.inference_completed.emit(False, "No active controller", {})
            return
        
        import threading
        def run():
            try:
                self.status_changed.emit("Running inference on cluster...")
                inf_res = self.controller.trigger_inference(
                    model_name=model_name,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                if inf_res.get("success"):
                    comp = inf_res.get("completion", {})
                    metrics = {
                        "tokens_generated": comp.get("tokens_generated", 0),
                        "tps": comp.get("tokens_per_second", 0.0),
                        "time_taken": comp.get("time_taken_s", 0.0)
                    }
                    self.inference_completed.emit(True, inf_res.get("text", ""), metrics)
                    self.status_changed.emit("Inference completed")
                else:
                    self.inference_completed.emit(False, inf_res.get("message", "Inference failed"), {})
                    self.status_changed.emit("Inference failed")
            except Exception as e:
                self.inference_completed.emit(False, str(e), {})
                self.status_changed.emit("Inference execution error")

        threading.Thread(target=run, daemon=True).start()

    def restore_streams(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


class StreamToSignal(io.TextIOBase):
    def __init__(self, signal: pyqtSignal):
        self.signal = signal

    def write(self, s):
        if s.strip():
            self.signal.emit(s.strip())
        return len(s)
