# KAI Multi-GPU Setup — Quick Start (2 Laptops)

Connect your **RTX 3050 Ti (3.9GB)** laptop and **MX350 (2GB)** laptop to run distributed inference across both GPUs.

---

## Option 1: Simple Local Mode (Easiest — No Kubernetes)

**Best for:** Quick testing, 2-3 machines, shared local network.

### Prerequisites
- Both laptops on **same Wi-Fi or Ethernet network**
- Both have NVIDIA drivers installed
- Both have KAI installed (same code, same Python venv)

### Step 1: Install KAI on Both Laptops

**On Laptop 2 (MX350):**

```bash
# Clone or copy KAI to Laptop 2
cd d:\
git clone https://github.com/misbah7172/GreenCluster-AI-KAI.git KAI

# Create CUDA environment
cd KAI
python -m venv .venv310
.\.venv310\Scripts\activate.ps1
pip install -r requirements.txt
```

### Step 2: Verify GPU Detection on Laptop 2

```bash
d:\CODE\KAI\.venv310\Scripts\python.exe kai_cli.py scan
```

Expected output:
```
[KAI] Scanning resources (mode=local)...
Cluster Summary:
  Nodes: 1
  GPU nodes: 1
  CPU-only nodes: 0
  Total GPU VRAM: 2048 MB (MX350)
  Total RAM: 8192 MB (approx)
  Total usable: 1548 MB
```

### Step 3: Run Inference in Local Mode (Single Machine)

Test Laptop 2 independently first:

```bash
d:\CODE\KAI\.venv310\Scripts\python.exe kai_cli.py run \
  --model openai-community/gpt2 \
  --prompt "Hello from MX350" \
  --max-tokens 32 \
  --device cuda:0
```

Once both laptops work individually, proceed to **Kubernetes mode** (Option 2) for true distributed inference.

---

## Option 2: Kubernetes Mode (Recommended for Production)

**Best for:** True distributed inference, automatic layer partitioning, energy tracking.

### Prerequisites
- Both laptops on **same network** (Ethernet **strongly recommended**)
- WSL2 + Ubuntu on Windows (or native Linux)
- Docker + NVIDIA Container Toolkit
- K3s installed on both machines

### Step 1: Install K3s on Laptop 1 (Control Plane)

**On Laptop 1 (RTX 3050 Ti) — inside WSL2 Ubuntu:**

```bash
# Install K3s server
curl -sfL https://get.k3s.io | sh -

# Wait ~20 seconds for K3s to start
sleep 20

# Get the join token
sudo cat /var/lib/rancher/k3s/server/node-token
# Save this token; you'll need it for Laptop 2

# Get your machine's LAN IP
hostname -I
# Example: 192.168.1.100
```

**Verify K3s is running:**
```bash
kubectl get nodes
# NAME            STATUS   ROLES           AGE   VERSION
# laptop1-wsl2    Ready    control-plane   1m    v1.28.x
```

### Step 2: Install K3s on Laptop 2 (Worker Node)

**On Laptop 2 (MX350) — inside WSL2 Ubuntu:**

```bash
# Replace these with values from Laptop 1:
export K3S_URL="https://192.168.1.100:6443"
export K3S_TOKEN="K1234567890abcdefg..."

curl -sfL https://get.k3s.io | sh -
```

**Back on Laptop 1, verify both nodes:**

```bash
kubectl get nodes -w
# NAME            STATUS   ROLES           AGE   VERSION
# laptop1-wsl2    Ready    control-plane   5m    v1.28.x
# laptop2-wsl2    Ready    worker          2m    v1.28.x
```

### Step 3: Deploy NVIDIA GPU Support

**On Laptop 1 (control plane):**

```bash
# Deploy NVIDIA device plugin to both nodes
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml

# Verify GPUs are detected
kubectl get nodes -L nvidia.com/gpu
# Should show:
#   laptop1-wsl2    Ready    control-plane   ...   1 (RTX 3050 Ti)
#   laptop2-wsl2    Ready    worker          ...   1 (MX350)
```

### Step 4: Build & Share Docker Images

**On Laptop 1:**

```bash
cd D:\CODE\KAI

# Build KAI images
python kai_cli.py build --tag kai:latest

# Export images to files
docker save kai-chunk:latest -o kai-chunk.tar
docker save kai-gateway:latest -o kai-gateway.tar
docker save kai-monitor:latest -o kai-monitor.tar
```

**Copy to Laptop 2 (via SCP or USB):**

```bash
# On Laptop 2, import images:
docker load -i kai-chunk.tar
docker load -i kai-gateway.tar
docker load -i kai-monitor.tar

# Verify images are loaded
docker images | grep kai
```

### Step 5: Deploy Model Across Both Nodes

**On Laptop 1:**

```bash
# Partition a small model into 2 chunks (one per GPU)
python kai_cli.py prepare --model openai-community/gpt2 --num-chunks 2

# Deploy to Kubernetes (splits across nodes automatically)
python -m kubernetes.controller deploy --num-chunks 2 --model openai-community/gpt2

# Verify pods are spread across nodes
kubectl get pods -n kai -o wide
# NAME                 READY   STATUS    NODE            IP
# kai-chunk-0-xxxx     1/1     Running   laptop1-wsl2    10.x.x.x
# kai-chunk-1-xxxx     1/1     Running   laptop2-wsl2    10.x.x.x
# kai-gateway-xxxx     1/1     Running   laptop1-wsl2    10.x.x.x
```

### Step 6: Run Inference via Gateway

**On Laptop 1:**

```bash
# Find the gateway service IP
kubectl get svc -n kai
# NAME           TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)
# kai-gateway    ClusterIP   10.43.201.150   <none>        8080/TCP

# Run inference through the gateway
curl -X POST http://10.43.201.150:8080/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Distributed inference across RTX 3050 Ti and MX350", "max_tokens": 64}'

# Check cluster health
curl http://10.43.201.150:8080/health
```

---

## Option 3: Direct gRPC Mode (Advanced)

If you want manual control over chunk distribution without Kubernetes:

**On Laptop 1 (RTX 3050 Ti):**

```bash
python -c "
from model.chunk_server import ChunkServer
server = ChunkServer(host='0.0.0.0', port=50051, device='cuda:0')
server.load_chunks(['chunk_0.pt'])
server.start()
"
```

**On Laptop 2 (MX350):**

```bash
python -c "
from model.chunk_server import ChunkServer
server = ChunkServer(host='0.0.0.0', port=50051, device='cuda:0')
server.load_chunks(['chunk_1.pt'])
server.start()
"
```

**On Laptop 1, run client:**

```bash
python -c "
from model.gateway import DistributedGateway
gateway = DistributedGateway(
    chunks=[
        ('192.168.1.100:50051', 0),  # Laptop 1's chunk 0
        ('192.168.1.105:50051', 1),  # Laptop 2's chunk 1 (replace IP)
    ]
)
result = gateway.generate('Hello', max_tokens=50)
print(result)
"
```

---

## Troubleshooting

### K3s Won't Start
```bash
# Check logs
sudo journalctl -u k3s -f

# Reinstall if corrupted
sudo /usr/local/bin/k3s-uninstall.sh
curl -sfL https://get.k3s.io | sh -
```

### GPU Not Detected in K8s
```bash
# Verify NVIDIA plugin is running
kubectl get pods -n kube-system | grep nvidia

# If missing, reinstall:
kubectl delete -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml
```

### Network Latency Between Nodes
- Use **Ethernet** instead of Wi-Fi for lower latency and higher bandwidth
- Disable Wi-Fi interference: disable other APs on 2.4GHz band
- Check latency: `ping <other-laptop-ip>` (aim for < 5ms)

### MX350 (2GB) Out of Memory
- Use quantization: `--quantize 8bit` (reduces model size ~2x)
- Use smaller model: `openai-community/gpt2` (~350M params) fits in 2GB
- Enable offload: `--offload --gpu-budget-mb 1500`

---

## Recommended Setup for Your Hardware

**For RTX 3050 Ti (3.9GB) + MX350 (2GB) = 5.9GB total:**

| Model | Params | FP16 Size | Fits? | Notes |
|---|---|---|---|---|
| GPT-2 | 124M | 250MB | ✅ | Run on MX350 alone |
| Phi-2 | 2.7B | 5.4GB | ✅ | Split: Phi-2 on RTX 3050 Ti only |
| Mistral-7B | 7.3B | 14.6GB | ⚠️ | Requires 8-bit quantization or offload |
| Falcon-7B | 8.5B | 17GB | ⚠️ | Requires disk offload |

**Recommended command for your setup:**

```bash
python kai_cli.py run \
  --model mistralai/Mistral-7B-v0.1 \
  --prompt "Your prompt here" \
  --max-tokens 64 \
  --offload \
  --device cuda:0 \
  --gpu-budget-mb 5000 \
  --disk-swap-dir ./swap
```

---

## Next Steps

1. **Quick test:** Run Option 1 (Local Mode) first to verify both laptops work
2. **Production setup:** Move to Option 2 (Kubernetes) for true distributed inference
3. **Monitor energy:** Use KAI's energy-aware scheduling to balance load between GPUs
4. **Scale up:** Add more machines by repeating the worker node setup

For detailed multi-node documentation, see [multiNodeSetup.md](./multiNodeSetup.md).
