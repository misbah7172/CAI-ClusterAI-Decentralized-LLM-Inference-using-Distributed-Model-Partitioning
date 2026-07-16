# CAI Sandbox — Simulated Cluster Guide

Simulate an entire multi-node distributed CAI cluster on a single machine **without requiring multiple physical laptops**. This is powered by the `SimulationEngine`, which launches lightweight mock worker nodes.

---

## How Simulation Works

When you run CAI in simulated mode, the `SimulationEngine`:
1. Launches a primary control plane on local ports.
2. Spins up N virtual "worker" nodes in-process or via lightweight processes.
3. Assigns randomized or custom hardware profiles to each virtual node (e.g., RTX 3090, CPU-only, different RAM sizes).
4. Simulates dynamic metrics (load spikes, power draw fluctuations) over time.
5. Feeds these simulated metrics into the `HybridScheduler` for realistic routing tests.

---

## 1. Start a Simulated Cluster

To start a cluster with 3 simulated worker nodes (plus the primary):

```bash
python cai_cli.py sandbox start --mode single --simulated-nodes 3
```

Expected output:
```
[INFO] CAI Sandbox starting (simulated mode, workers=3)
[INFO] NodeAgent started: node-primary
[INFO] SimulationEngine initializing 3 virtual workers...
[INFO] Spawned worker-sim-1 (Profile: GPU RTX 3080, VRAM: 10GB)
[INFO] Spawned worker-sim-2 (Profile: GPU RTX 4090, VRAM: 24GB)
[INFO] Spawned worker-sim-3 (Profile: CPU-Only, RAM: 16GB)
[INFO] All 3 virtual workers successfully registered and sending heartbeats.
[INFO] ControllerAPIServer listening on :8200
```

---

## 2. Monitor Simulated Node Metrics

Because the nodes are running under the simulation engine, they will periodically report mock telemetry (power, temperature, load). You can see the cluster topology:

```bash
python cai_cli.py sandbox status
```

Output:
```
┌──────────────────────────────────────────────────────────────────┐
│  CAI Sandbox — Simulated Cluster                                 │
├──────────────────┬───────────────────────────────────────────────┤
│  Mode            │ single (simulated)                            │
│  Role            │ primary                                       │
│  Nodes           │ 4 active                                      │
├──────────────────┴───────────────────────────────────────────────┤
│  node-primary   (primary)  127.0.0.1  RTX 4080    16GB   ACTIVE  │
│  worker-sim-1   (worker)   127.0.0.1  RTX 3080    10GB   ACTIVE  │
│  worker-sim-2   (worker)   127.0.0.1  RTX 4090    24GB   ACTIVE  │
│  worker-sim-3   (worker)   127.0.0.1  CPU only     0GB   ACTIVE  │
└──────────────────────────────────────────────────────────────────┘
```

You can view the live telemetry stream (with mock power draw) using:
```bash
python cai_cli.py sandbox monitor
```

---

## 3. Test Hybrid Model Placement

With a simulated cluster, you can test how the scheduler splits a large model when local memory is tight.

For instance, to deploy a 4-chunk model:
```bash
python cai_cli.py sandbox deploy --model sshleifer/tiny-gpt2 --chunks 4 --strategy balanced
```

The scheduler will inspect the simulated hardware profiles and partition the model:
- **Chunk 0** → worker-sim-2 (24GB VRAM)
- **Chunk 1** → node-primary (16GB VRAM)
- **Chunk 2** → worker-sim-1 (10GB VRAM)
- **Chunk 3** → worker-sim-3 (CPU-Only)

---

## Hardware Profile Configurations

The virtual workers are assigned profiles from `sandbox/simulation/hardware_profiles.py`. Built-in profiles include:

| Profile Name | GPU Type | VRAM | RAM | CPU Cores |
|--------------|----------|------|-----|-----------|
| `high_end_gpu` | NVIDIA GeForce RTX 4090 | 24 GB | 64 GB | 16 |
| `mid_range_gpu` | NVIDIA GeForce RTX 3070 | 8 GB | 32 GB | 8 |
| `low_end_gpu` | NVIDIA GeForce GTX 1660 | 6 GB | 16 GB | 6 |
| `cpu_only` | None | 0 GB | 16 GB | 8 |

You can customize profiles by editing `sandbox/simulation/hardware_profiles.py`.

---

## Programmatic Usage

You can build custom simulation environments for automated testing:

```python
import time
from pathlib import Path
from sandbox.config import SandboxConfig, ClusterMode, NodeRole
from sandbox.agent.node_agent import NodeAgent
from sandbox.simulation.engine import SimulationEngine
from sandbox.controller.remote_controller import RemoteController

# 1. Setup primary node config
config = SandboxConfig(
    mode=ClusterMode.SINGLE,
    role=NodeRole.PRIMARY,
    data_dir=Path("./sim_data"),
)
config.ensure_dirs()

# 2. Start primary agent
agent = NodeAgent(config)
agent.start()

# 3. Create simulation engine and spawn 4 workers
sim_engine = SimulationEngine(primary_agent=agent)
sim_engine.start()
sim_engine.spawn_worker(node_id="virtual-gpu-1", profile="high_end_gpu")
sim_engine.spawn_worker(node_id="virtual-cpu-1", profile="cpu_only")

# Let workers connect and register
time.sleep(2)

# 4. Interact with the cluster via controller
controller = RemoteController(agent, discovery=None, config=config)
print("Active Nodes:", len(controller.list_nodes()))

# 5. Clean up simulation
sim_engine.stop()
agent.stop()
```
