# CAI Sandbox — Multi-Node Distributed Setup

Connect multiple laptops or VMs into a real distributed inference cluster. One machine acts as the **primary** (scheduler + controller), others join as **workers**.

---

## Architecture

```
┌─────────────────────┐          ┌─────────────────────┐
│   Primary Node      │◄────────►│   Worker Node 1     │
│  (Laptop A)         │  gRPC    │   (Laptop B)        │
│                     │  50100   │                     │
│  • ControllerAPI    │          │  • ChunkServer 0    │
│  • Scheduler        │          │  • HardwareReporter │
│  • InferenceGateway │◄────────►│   Worker Node 2     │
│  • ClusterRegistry  │  gRPC    │   (Laptop C)        │
└─────────────────────┘  50100   └─────────────────────┘
```

All nodes must be **reachable on the network** (same LAN or VPN).

---

## Step 1 — Start the Primary Node

On **Laptop A**:

```bash
python cai_cli.py sandbox start --mode multi-primary
```

Or with explicit options:
```bash
python cai_cli.py sandbox start \
  --mode multi-primary \
  --grpc-port 50100 \
  --api-port 8200 \
  --rest-port 8100
```

Expected output:
```
[INFO] CAI Sandbox starting (mode=multi_primary, role=primary)
[INFO] NodeAgent started: node-a1b2c3d4
[INFO] gRPC control server listening on :50100
[INFO] ControllerAPIServer listening on :8200
[INFO] Ready — accepting worker registrations
```

---

## Step 2 — Generate a Join Token

On **Laptop A** (the primary):

```bash
python cai_cli.py sandbox token generate
```

Output:
```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  Worker Join Token                                                               │
│  Cluster ID: abc123                                                              │
│  Expires: 720h (30 days)                                                         │
│                                                                                  │
│  Token:                                                                          │
│  eyJjbHVzdGVyX2lkIjoiYWJjMTIzIiwibm9kZV9yb2xlIjoid29ya2Vy...                  │
│                                                                                  │
│  Share this token securely with each worker node.                                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

> ⚠️ **Keep tokens private** — anyone with a valid token can join your cluster.

---

## Step 3 — Join Worker Nodes

On **Laptop B** (and each additional worker):

```bash
python cai_cli.py sandbox join \
  --primary 192.168.1.10:50100 \
  --token eyJjbHVzdGVyX2lkIjoiYWJjMTIzIiwibm9kZV9yb2xlIjoid29ya2Vy...
```

Options:

| Flag | Description |
|------|-------------|
| `--primary` | Primary node address (`<ip>:<grpc-port>`) |
| `--token` | Join token from Step 2 |
| `--grpc-port` | Worker's own gRPC port (default: 50101) |
| `--rest-port` | Worker's own REST port (default: 8101) |

Expected worker output:
```
[INFO] CAI Sandbox joining cluster at 192.168.1.10:50100
[INFO] TLS handshake complete
[INFO] Token validated — role=worker, cluster=abc123
[INFO] NodeAgent started: node-b9c8d7e6
[INFO] Successfully joined cluster
[INFO] Hardware report sent: RTX 3060 (12 GB VRAM), 16 GB RAM, 8 cores
[INFO] Heartbeat loop started
```

---

## Step 4 — Verify Cluster

Back on **Laptop A**:

```bash
python cai_cli.py sandbox status
```

Output with 2 workers:
```
┌─────────────────────────────────────────────────────────────────┐
│  CAI Sandbox — Cluster Status                                   │
├──────────────────┬──────────────────────────────────────────────┤
│  Mode            │ multi_primary                                │
│  Role            │ primary                                      │
│  Cluster ID      │ abc123                                       │
│  API URL         │ http://localhost:8200                        │
│  Nodes           │ 3 active                                     │
├──────────────────┴──────────────────────────────────────────────┤
│  node-a1b2c3d4  (primary)  192.168.1.10  RTX 4090  24GB  ACTIVE │
│  node-b9c8d7e6  (worker)   192.168.1.11  RTX 3060  12GB  ACTIVE │
│  node-c5d4e3f2  (worker)   192.168.1.12  CPU only   0GB  ACTIVE │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 5 — Deploy a Model (Distributed)

```bash
python cai_cli.py sandbox deploy \
  --model meta-llama/Llama-2-7b-hf \
  --chunks 3 \
  --strategy balanced
```

The `HybridScheduler` will:
1. Score all active nodes by GPU VRAM + load
2. Partition model layers into 3 chunks
3. Assign chunk 0 → node with highest VRAM, chunk 1 → second, etc.
4. Launch a `ChunkServer` gRPC process on each assigned node

---

## Step 6 — Run Inference (Distributed)

```bash
python cai_cli.py sandbox infer \
  --model meta-llama/Llama-2-7b-hf \
  --prompt "Explain quantum entanglement simply" \
  --max-tokens 200
```

The `InferenceGateway` pipes the request through each chunk server in order:
```
Request → ChunkServer[0] → ChunkServer[1] → ChunkServer[2] → Response
          (node-a, GPU)     (node-b, GPU)     (node-c, CPU)
```

---

## Network Requirements

| Port | Protocol | Purpose |
|------|----------|---------|
| 50100 | gRPC (TCP) | Control plane (primary only) |
| 50101–50199 | gRPC (TCP) | Chunk servers (one per node) |
| 8100–8199 | HTTP | REST health endpoints |
| 8200 | HTTP | Controller API (primary only) |
| 8080 | HTTP | Inference gateway (primary only) |
| 5353 | UDP | mDNS discovery (LAN only) |

If using a VPN, ensure **UDP 5353** is forwarded or use explicit `--primary` address (mDNS not required when address is known).

---

## Programmatic Usage

```python
from pathlib import Path
from sandbox.config import SandboxConfig, ClusterMode, NodeRole
from sandbox.agent.node_agent import NodeAgent
from sandbox.auth.token_manager import TokenManager

# PRIMARY NODE
primary_cfg = SandboxConfig(
    mode=ClusterMode.MULTI_PRIMARY,
    role=NodeRole.PRIMARY,
    node_id="primary-laptop",
    grpc_port=50100,
    api_port=8200,
)
primary_cfg.ensure_dirs()
primary_agent = NodeAgent(primary_cfg)
primary_agent.start()

# Generate token
tm = TokenManager(token_dir=primary_cfg.token_dir)
token = tm.generate_cluster_token(primary_agent.cluster_id, "worker")
print(f"Share with workers: {token}")

# WORKER NODE (different machine)
worker_cfg = SandboxConfig(
    mode=ClusterMode.MULTI_WORKER,
    role=NodeRole.WORKER,
    primary_address="192.168.1.10",
    primary_port=50100,
    access_token=token,
    grpc_port=50101,
)
worker_cfg.ensure_dirs()
worker_agent = NodeAgent(worker_cfg)
worker_agent.start()
success = worker_agent.register("192.168.1.10:50100", token)
print(f"Joined cluster: {success}")
```
