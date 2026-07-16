"""
CLI commands for CAI Sandbox platform.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from sandbox.config import SandboxConfig, ClusterMode, NodeRole
from sandbox.agent.node_agent import NodeAgent
from sandbox.discovery.discovery_service import ClusterDiscoveryService
from sandbox.controller.remote_controller import RemoteController
from sandbox.controller.api_server import ControllerAPIServer
from sandbox.auth.token_manager import TokenManager
from sandbox.simulation.engine import SimulationEngine

# Configure default logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cai_sandbox_cli")


def _get_api_url(config: SandboxConfig, endpoint: str) -> str:
    """Helper to construct API URL for the controller."""
    # If the user specified primary address (like host:port), extract the host.
    host = "localhost"
    if config.primary_address:
        if ":" in config.primary_address:
            host = config.primary_address.rsplit(":", 1)[0]
        else:
            host = config.primary_address
    return f"http://{host}:{config.api_port}{endpoint}"


def _api_request(url: str, method: str = "GET", data: dict = None, token: str = None) -> dict:
    """Helper to make HTTP API requests to the controller."""
    try:
        payload = json.dumps(data).encode("utf-8") if data else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        req = urllib.request.Request(url, data=payload, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            err_data = json.loads(err.read().decode("utf-8"))
            return {"success": False, "error": err_data.get("error", err.reason)}
        except Exception:
            return {"success": False, "error": f"HTTP {err.code}: {err.reason}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

def cmd_start(args):
    """Start a sandbox node agent, and controller if primary."""
    print("==================================================")
    print(f"Starting CAI Sandbox Node (mode={args.mode}, role={args.role})")
    print("==================================================")

    config = SandboxConfig(
        mode=ClusterMode(args.mode),
        role=NodeRole(args.role),
        node_id=args.node_id,
        primary_address=args.primary or "",
    )
    config.ensure_dirs()

    # 1. Initialize & Start Node Agent
    agent = NodeAgent(config)
    agent.start()

    controller = None
    api_server = None
    discovery = None

    # 2. If PRIMARY, run cluster discovery service and API/control plane
    if config.role == NodeRole.PRIMARY:
        logger.info("Initializing primary cluster control plane...")
        discovery = ClusterDiscoveryService(config)
        discovery.start()
        
        # Start Remote Controller
        controller = RemoteController(agent, discovery, config)
        
        # Start API Server
        api_server = ControllerAPIServer(controller, agent, port=config.api_port)
        api_server.start()

        # If a token was not specified, verify or generate a default token for workers
        tm = TokenManager(token_dir=config.token_dir)
        default_token = tm.generate_cluster_token(agent.cluster_id, "worker")
        print("\n--- CLUSTER INFORMATION ---")
        print(f"Cluster ID:   {agent.cluster_id}")
        print(f"Primary Node: {agent.node_id}")
        print(f"API Port:     {config.api_port}")
        print(f"gRPC Port:    {config.grpc_port}")
        print(f"Worker Token: {default_token}")
        print("---------------------------\n")

    # 3. If WORKER and primary address is specified, register directly
    elif config.role == NodeRole.WORKER and args.primary:
        if not args.token:
            print("[Error] A joining token is required to register with a primary node.")
            agent.stop()
            sys.exit(1)
        
        print(f"Connecting to primary cluster at {args.primary}...")
        registered = agent.register(args.primary, args.token)
        if not registered:
            print("[Error] Failed to register with the primary node.")
            agent.stop()
            sys.exit(1)

    print("CAI Sandbox running. Press Ctrl+C to terminate.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down CAI Sandbox...")
    finally:
        if api_server:
            api_server.stop()
        if discovery:
            discovery.stop()
        agent.stop()
        print("Shutdown complete.")


def cmd_join(args):
    """Register a worker node with an active primary node."""
    config = SandboxConfig(
        mode=ClusterMode.MULTI_WORKER,
        role=NodeRole.WORKER,
        node_id=args.node_id,
        primary_address=args.primary,
    )
    config.ensure_dirs()

    agent = NodeAgent(config)
    agent.start()

    print(f"Joining cluster at {args.primary}...")
    success = agent.register(args.primary, args.token)
    if not success:
        print("[Error] Registration rejected by primary.")
        agent.stop()
        sys.exit(1)

    print("Successfully joined cluster. Press Ctrl+C to leave.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nLeaving cluster...")
    finally:
        agent.stop()
        print("Deregistered.")


def cmd_token(args):
    """Generate or list security tokens."""
    config = SandboxConfig()
    tm = TokenManager(token_dir=config.token_dir)

    if args.token_action == "generate":
        cluster_id = args.cluster_id or "Cai-sandbox-cluster"
        role = args.role
        token = tm.generate_cluster_token(cluster_id, role, expiry_hours=args.expires)
        print(f"Token generated successfully for role '{role}':\n")
        print(token)
        print(f"\nExpires in {args.expires} hours.")
    else:
        # List tokens
        tokens = tm.list_active_tokens()
        if not tokens:
            print("No active tokens found.")
            return
        print(f"{'Token ID':<15} {'Cluster ID':<25} {'Role':<10} {'Expires At':<25}")
        print("-" * 75)
        for t in tokens:
            print(f"{t['token_id']:<15} {t.get('cluster_id', 'unknown'):<25} {t.get('node_role', 'worker'):<10} {t.get('expires_at', 'never')}")


def cmd_simulate(args):
    """Launch a simulation of virtual CAI Sandbox nodes on this machine."""
    print(f"Starting Simulation Engine with {args.nodes} virtual nodes...")

    # SimulationEngine does not take a config — it takes an optional registry
    engine = SimulationEngine()

    try:
        engine.simulate(num_nodes=args.nodes, profile_type=args.profile)
        print("Simulation active. Virtual nodes are reporting metrics.")
        print("Press Ctrl+C to stop simulation.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping simulation...")
    finally:
        engine.stop_simulation()
        print("Simulation terminated.")


def cmd_cluster(args):
    """Interact with cluster state (list nodes, check metrics)."""
    config = SandboxConfig()
    
    if args.cluster_action == "nodes":
        url = _get_api_url(config, "/api/v1/cluster/nodes")
        res = _api_request(url)
        if "error" in res:
            print(f"[Error] Failed to fetch nodes: {res['error']}")
            return
        
        nodes = res.get("nodes", [])
        print(f"Active Nodes in Cluster ({len(nodes)} total):")
        print(f"{'Node ID':<15} {'Role':<10} {'Address':<22} {'Status':<12} {'GPU Type':<15} {'VRAM (MB)':<10}")
        print("-" * 90)
        for node in nodes:
            hw = node.get("hardware", {})
            gpu_type = hw.get("gpu_type", "None")
            gpu_vram = hw.get("gpu_vram_mb", 0)
            addr = node.get("address", "local")
            print(f"{node['node_id']:<15} {node.get('role', 'worker'):<10} {addr:<22} {node.get('state', 'active'):<12} {gpu_type:<15} {gpu_vram:<10.1f}")
            
    elif args.cluster_action == "metrics":
        url = _get_api_url(config, "/api/v1/cluster/metrics")
        res = _api_request(url)
        if "error" in res:
            print(f"[Error] Failed to fetch metrics: {res['error']}")
            return
        
        print("Cluster Performance & Energy Metrics:")
        print("-" * 40)
        for k, v in res.items():
            print(f"  {k.replace('_', ' ').title():<25}: {v}")
        print("-" * 40)


def cmd_deploy(args):
    """Deploy model chunk layers across cluster nodes."""
    config = SandboxConfig()
    url = _get_api_url(config, "/api/v1/models/deploy")
    
    data = {
        "model_name": args.model,
        "strategy": args.strategy,
        "dtype": args.dtype,
    }
    if args.num_chunks:
        data["num_chunks"] = args.num_chunks
    if args.nodes:
        data["target_nodes"] = args.nodes.split(",")
        
    print(f"Requesting deployment of '{args.model}'...")
    res = _api_request(url, method="POST", data=data)
    
    if "error" in res or not res.get("success"):
        print(f"[Error] Deployment failed: {res.get('error', res.get('message'))}")
        return
        
    print("\nModel Deployed Successfully!")
    print(f"Deployment ID:    {res['deployment_id']}")
    print(f"Gateway Endpoint: {res['gateway_endpoint']}")
    print("\nChunk Placements:")
    print(f"{'Chunk ID':<10} {'Node ID':<15} {'Endpoint':<22}")
    print("-" * 50)
    for p in res.get("placements", []):
        print(f"{p['chunk_id']:<10} {p['node_id']:<15} {p.get('endpoint', 'loading'):<22}")


def cmd_infer(args):
    """Run text generation prompt on a deployed model in the cluster."""
    config = SandboxConfig()
    url = _get_api_url(config, "/api/v1/inference/run")
    
    data = {
        "model_name": args.model,
        "prompt": args.prompt,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    
    print(f"Running inference on model '{args.model}'...")
    t0 = time.time()
    res = _api_request(url, method="POST", data=data)
    elapsed = time.time() - t0
    
    if "error" in res or not res.get("success"):
        print(f"[Error] Inference failed: {res.get('error', res.get('message'))}")
        return
        
    print("\nGenerated Text:")
    print("=" * 60)
    print(res.get("text", ""))
    print("=" * 60)
    print(f"Tokens generated: {res.get('tokens_generated', 0)}")
    print(f"Time taken:       {elapsed:.2f}s")


# ---------------------------------------------------------------------------
# CLI Parser Setup
# ---------------------------------------------------------------------------

def main(args=None):
    parser = argparse.ArgumentParser(
        prog="cai_sandbox",
        description="CAI Sandbox Decentralized Node Platform CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Start command
    p_start = subparsers.add_parser("start", help="Start CAI sandbox agent/controller")
    p_start.add_argument("--mode", choices=["single", "multi_primary", "multi_worker"], default="single",
                         help="Cluster participation mode")
    p_start.add_argument("--role", choices=["primary", "worker"], default="primary",
                         help="Node cluster role")
    p_start.add_argument("--node-id", type=str, default="", help="Custom node identifier")
    p_start.add_argument("--primary", type=str, default="", help="Primary node address (host:port) to connect to")
    p_start.add_argument("--token", type=str, default="", help="Access token to join cluster")
    p_start.set_defaults(func=cmd_start)

    # 2. Join command
    p_join = subparsers.add_parser("join", help="Join an existing cluster")
    p_join.add_argument("--primary", type=str, required=True, help="Primary node address (host:port)")
    p_join.add_argument("--token", type=str, required=True, help="Access token")
    p_join.add_argument("--node-id", type=str, default="", help="Custom node identifier")
    p_join.set_defaults(func=cmd_join)

    # 3. Token command
    p_token = subparsers.add_parser("token", help="Generate or list security tokens")
    s_token = p_token.add_subparsers(dest="token_action", required=True)
    
    t_gen = s_token.add_parser("generate", help="Generate worker access token")
    t_gen.add_argument("--cluster-id", type=str, default="", help="Cluster identifier")
    t_gen.add_argument("--role", choices=["primary", "worker"], default="worker", help="Node role permissions")
    t_gen.add_argument("--expires", type=int, default=720, help="Expiration in hours")
    
    s_token.add_parser("list", help="List all generated active tokens")
    p_token.set_defaults(func=cmd_token)

    # 4. Simulate command
    p_sim = subparsers.add_parser("simulate", help="Run simulated nodes")
    p_sim.add_argument("--nodes", type=int, default=3, help="Number of virtual nodes to spawn")
    p_sim.add_argument("--profile", type=str, default="mixed", help="Profile combination (mixed, gpu, cpu)")
    p_sim.set_defaults(func=cmd_simulate)

    # 5. Cluster command
    p_clust = subparsers.add_parser("cluster", help="Manage/inspect cluster topology")
    s_clust = p_clust.add_subparsers(dest="cluster_action", required=True)
    s_clust.add_parser("nodes", help="List nodes in the cluster")
    s_clust.add_parser("metrics", help="Show cluster metrics")
    p_clust.set_defaults(func=cmd_cluster)

    # 6. Deploy command
    p_dep = subparsers.add_parser("deploy", help="Deploy model across cluster")
    p_dep.add_argument("--model", type=str, required=True, help="Model name or HF model identifier")
    p_dep.add_argument("--num-chunks", type=int, default=None, help="Number of chunks")
    p_dep.add_argument("--strategy", choices=["balanced", "energy", "latency"], default="balanced",
                       help="Layer assignment scheduling strategy")
    p_dep.add_argument("--nodes", type=str, default=None, help="Comma-separated list of target node IDs")
    p_dep.add_argument("--dtype", type=str, default="float16", help="Weights model datatype")
    p_dep.set_defaults(func=cmd_deploy)

    # 7. Infer command
    p_inf = subparsers.add_parser("infer", help="Run text generation inference prompt")
    p_inf.add_argument("--model", type=str, required=True, help="Model identifier")
    p_inf.add_argument("--prompt", type=str, required=True, help="Text prompt")
    p_inf.add_argument("--max-tokens", type=int, default=50, help="Maximum generated tokens")
    p_inf.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    p_inf.set_defaults(func=cmd_infer)

    parsed = parser.parse_args(args)
    parsed.func(parsed)


if __name__ == "__main__":
    main()
