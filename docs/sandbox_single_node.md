# CAI Sandbox — Single-Node Quickstart

Run the full CAI inference stack on a single laptop with **zero cluster setup** — ideal for
development, demos, and offline use.

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Python | 3.10+ |
| RAM | 8 GB |
| Disk | 10 GB free |
| OS | Windows 10+, Linux, macOS |
| Docker (optional) | 24+ |

Install CAI dependencies:

```bash
pip install -r requirements.txt
```

---

## 1. Start Single-Node Sandbox

```bash
python cai_cli.py sandbox start --mode single
```

This starts:
- **NodeAgent** — hardware monitor + gRPC control plane
- **ClusterDiscoveryService** — mDNS listener (local only)
- **ControllerAPIServer** — REST API at `http://localhost:8200`
- **InferenceGateway** — HTTP inference at `http://localhost:8080`

Expected output:
```
[INFO] CAI Sandbox starting (mode=single, role=primary)
[INFO] NodeAgent started: node-<uuid>
[INFO] ControllerAPIServer listening on :8200
[INFO] Ready — single-node mode active
```

---

## 2. Check Node Status

```bash
python cai_cli.py sandbox status
```

Output:
```
┌─────────────────────────────────────────────────────────┐
│  CAI Sandbox — Cluster Status                           │
├─────────────────────┬───────────────────────────────────┤
│  Mode               │ single                            │
│  Role               │ primary                           │
│  Node ID            │ node-a1b2c3d4                     │
│  API URL            │ http://localhost:8200             │
│  Nodes in cluster   │ 1 (this node)                    │
│  Active deployments │ 0                                 │
└─────────────────────┴───────────────────────────────────┘
```

---

## 3. Deploy a Model

```bash
python cai_cli.py sandbox deploy --model sshleifer/tiny-gpt2
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | required | HuggingFace model name or local path |
| `--chunks` | 1 | Number of pipeline chunks |
| `--strategy` | balanced | Placement: `balanced`, `gpu_first`, `cpu_only` |

Example with options:
```bash
python cai_cli.py sandbox deploy \
  --model microsoft/phi-2 \
  --chunks 2 \
  --strategy gpu_first
```

---

## 4. Run Inference

```bash
python cai_cli.py sandbox infer \
  --model sshleifer/tiny-gpt2 \
  --prompt "The future of AI is"
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt` | required | Input text prompt |
| `--max-tokens` | 128 | Max tokens to generate |
| `--temperature` | 0.7 | Sampling temperature (0.0 = greedy) |
| `--stream` | false | Stream tokens to stdout |

Sample output:
```json
{
  "model": "sshleifer/tiny-gpt2",
  "prompt": "The future of AI is",
  "text": "The future of AI is evolving rapidly...",
  "tokens_generated": 12,
  "latency_ms": 284
}
```

---

## 5. Monitor Resources

```bash
python cai_cli.py sandbox monitor
```

Displays live hardware metrics: CPU load, RAM usage, GPU VRAM, power draw, and temperature — updated every 2 seconds.

---

## 6. Stop the Sandbox

```bash
python cai_cli.py sandbox stop
```

---

## Programmatic Usage

```python
from pathlib import Path
from sandbox.config import SandboxConfig, ClusterMode, NodeRole
from sandbox.agent.node_agent import NodeAgent
from sandbox.discovery.discovery_service import ClusterDiscoveryService
from sandbox.controller.remote_controller import RemoteController
from sandbox.controller.api_server import ControllerAPIServer

config = SandboxConfig(
    mode=ClusterMode.SINGLE,
    role=NodeRole.PRIMARY,
    data_dir=Path("~/.cai_sandbox").expanduser(),
)
config.ensure_dirs()

agent = NodeAgent(config)
agent.start()

discovery = ClusterDiscoveryService(config)
discovery.start()

controller = RemoteController(agent, discovery, config)
api_server = ControllerAPIServer(controller, agent, port=8200)
api_server.start()

# Deploy and run inference
result = controller.deploy_model("sshleifer/tiny-gpt2", num_chunks=1)
inference = controller.trigger_inference(
    model_name="sshleifer/tiny-gpt2",
    prompt="Hello, CAI!",
    max_tokens=32,
)
print(inference["text"])

# Shutdown
api_server.stop()
discovery.stop()
agent.stop()
```
