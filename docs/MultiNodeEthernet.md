# CAI Multi-Node Ethernet Setup

This guide documents the step-by-step process for running CAI on two Windows laptops connected directly with an Ethernet cable. It is based on a primary laptop named `mighty` and a worker laptop named `bat-machine47`, but the same process works for any two machines.

## Target Topology

```text
Primary laptop / control plane
  Windows Ethernet IP: 192.168.100.1
  WSL distro: Ubuntu-22.04
  K3s role: control-plane
  Example node name: mighty

Worker laptop
  Windows Ethernet IP: 192.168.100.2
  WSL distro: Ubuntu-22.04
  K3s role: worker
  Example node name: bat-machine47

K3s API exposed to worker:
  https://192.168.100.1:6444
```

Port `6444` is used because Docker Desktop or another local Kubernetes installation may already use `6443`.

## 1. Prerequisites

Install or verify these on both laptops:

- Windows 10/11 with WSL2 enabled.
- Ubuntu-22.04 WSL distro.
- NVIDIA Windows driver installed.
- Ethernet cable connected between both laptops.
- A copy of the CAI repository on each laptop.
- Administrator PowerShell access.

Check WSL:

```powershell
wsl -l -v
```

Check NVIDIA inside WSL:

```powershell
wsl -d Ubuntu-22.04 -- nvidia-smi
```

If `nvidia-smi` fails inside WSL, fix the Windows NVIDIA driver/WSL GPU support before continuing.

## 2. Configure Static Ethernet IPs

A direct laptop-to-laptop Ethernet cable usually has no DHCP server. If Windows shows a `169.254.x.x` address, configure static IPs.

On the primary laptop, run PowerShell as Administrator:

```powershell
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.100.1 -PrefixLength 24
```

On the worker laptop, run PowerShell as Administrator:

```powershell
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.100.2 -PrefixLength 24
```

If the adapter is not named `Ethernet`, list adapters:

```powershell
Get-NetAdapter
```

Then use the correct `InterfaceAlias`.

Verify connectivity from the primary laptop:

```powershell
ping 192.168.100.2
```

Expected result:

```text
Reply from 192.168.100.2
```

## 3. Start the Primary K3s Node

On the primary laptop, open PowerShell as Administrator:

```powershell
cd D:\CODE\CAI
powershell -ExecutionPolicy Bypass -File scripts\windows\setup-primary.ps1 -ServerIp 192.168.100.1
```

The script installs dependencies in WSL, starts K3s, and writes the join token.

Expected token location on the primary laptop:

```text
D:\CODE\CAI\logs\k3s-node-token.txt
```

If the token file is missing, check K3s inside WSL:

```powershell
wsl -d Ubuntu-22.04 -- sudo systemctl status k3s --no-pager -l
wsl -d Ubuntu-22.04 -- sudo journalctl -u k3s --no-pager -n 120
```

## 4. Handle Port 6443 Conflict

If K3s fails with this error:

```text
listen tcp :6443: bind: address already in use
```

move K3s to port `6444`.

On the primary laptop, write a K3s service file that uses `6444`:

```powershell
$service = @'
[Unit]
Description=Lightweight Kubernetes
Documentation=https://k3s.io
Wants=network-online.target
After=network-online.target

[Install]
WantedBy=multi-user.target

[Service]
Type=notify
EnvironmentFile=-/etc/default/%N
EnvironmentFile=-/etc/sysconfig/%N
EnvironmentFile=-/etc/systemd/system/k3s.service.env
KillMode=process
Delegate=yes
User=root
LimitNOFILE=1048576
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
TimeoutStartSec=0
Restart=always
RestartSec=5s
ExecStartPre=-/sbin/modprobe br_netfilter
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/k3s server --write-kubeconfig-mode 644 --tls-san 192.168.100.1 --https-listen-port 6444
'@

$service | wsl -d Ubuntu-22.04 -- sudo tee /etc/systemd/system/k3s.service > $null
```

Restart K3s and copy the token to the Windows repo folder:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "sudo systemctl daemon-reload && sudo systemctl restart k3s && sleep 10 && sudo mkdir -p /root/.CAI && sudo cat /var/lib/rancher/k3s/server/node-token | sudo tee /root/.CAI/k3s-node-token.txt >/dev/null && cp /root/.CAI/k3s-node-token.txt /mnt/d/CODE/CAI/logs/k3s-node-token.txt"
```

Verify the primary node:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get nodes -o wide
```

## 5. Expose the WSL K3s API to the Ethernet Network

K3s is running inside WSL, so the worker laptop cannot directly reach it until Windows forwards `192.168.100.1:6444` to the WSL IP.

On the primary laptop, run PowerShell as Administrator:

```powershell
$wslIp = (wsl -d Ubuntu-22.04 -- hostname -I).Trim().Split(" ")[0]

netsh interface portproxy delete v4tov4 listenaddress=192.168.100.1 listenport=6444
netsh interface portproxy add v4tov4 listenaddress=192.168.100.1 listenport=6444 connectaddress=$wslIp connectport=6444

New-NetFirewallRule -DisplayName "CAI K3s API 6444" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 6444
```

Verify:

```powershell
Test-NetConnection 192.168.100.1 -Port 6444
netsh interface portproxy show v4tov4
```

Expected result:

```text
TcpTestSucceeded : True

Listen on ipv4:             Connect to ipv4:
Address         Port        Address         Port
192.168.100.1   6444        <WSL-IP>        6444
```

## 6. Join the Worker Node

Copy this token file from the primary laptop:

```text
D:\CODE\CAI\logs\k3s-node-token.txt
```

to the worker repository folder, for example:

```text
C:\Users\nurer\Desktop\CAI\GreenCluster-AI-CAI\logs\k3s-node-token.txt
```

On the worker laptop, open PowerShell as Administrator from the worker repo folder:

```powershell
cd C:\Users\nurer\Desktop\CAI\GreenCluster-AI-CAI
```

Use the token-file command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup-worker.ps1 `
  -ServerUrl https://192.168.100.1:6444 `
  -TokenFile .\logs\k3s-node-token.txt
```

If the script fails because of an empty `-Token` argument, use the direct token workaround:

```powershell
$token = Get-Content .\logs\k3s-node-token.txt -Raw

powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup-worker.ps1 `
  -ServerUrl https://192.168.100.1:6444 `
  -Token $token
```

## 7. Verify Both Nodes

On the primary laptop:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get nodes -o wide
```

Expected result:

```text
NAME            STATUS   ROLES           INTERNAL-IP
mighty          Ready    control-plane   172.31.x.x
bat-machine47   Ready    <none>          172.17.x.x
```

The internal IPs are WSL-side addresses. That is normal.

## 8. Install NVIDIA Device Plugin

On the primary laptop:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml
```

Check plugin pods:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get pods -n kube-system -o wide
```

Check GPU capacity:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl describe nodes
```

Look for:

```text
nvidia.com/gpu: 1
```

## 9. Configure NVIDIA Container Toolkit

If the plugin logs show this:

```text
could not load NVML library: libnvidia-ml.so.1
```

install NVIDIA Container Toolkit on both WSL nodes.

On the primary laptop:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list && sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit"
```

On the worker laptop, run the same install command.

Configure the primary K3s server runtime:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default --config=/var/lib/rancher/k3s/agent/etc/containerd/config.toml && sudo systemctl restart k3s"
```

Configure the worker K3s agent runtime:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default --config=/var/lib/rancher/k3s/agent/etc/containerd/config.toml && sudo systemctl restart k3s-agent"
```

Restart the plugin from the primary laptop:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl delete pod -n kube-system -l name=nvidia-device-plugin-ds
```

## 10. WSL-Specific NVIDIA Troubleshooting

On WSL, `nvidia-smi` may work on the host while Kubernetes containers still do not advertise `nvidia.com/gpu`.

If plugin logs show:

```text
Detected NVML platform: found NVML library
No devices found. Waiting indefinitely.
```

or:

```text
Failed to initialize NVML: ERROR_DRIVER_NOT_LOADED
```

then K3s/containerd still cannot expose the WSL GPU device to the plugin container.

Useful checks:

```powershell
wsl -d Ubuntu-22.04 -- nvidia-smi
wsl -d Ubuntu-22.04 -- bash -lc "ls -l /usr/lib/wsl/lib/libnvidia-ml.so* /dev/dxg"
wsl -d Ubuntu-22.04 -- sudo k3s kubectl logs -n kube-system -l name=nvidia-device-plugin-ds --tail=100
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get node mighty -o jsonpath='{.status.capacity}'
```

Possible WSL patch for the device plugin:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc 'cat <<"EOF" >/tmp/nvidia-wsl-patch.json
[
  {"op":"add","path":"/spec/template/spec/volumes/-","value":{"name":"wsl-nvidia-lib","hostPath":{"path":"/usr/lib/wsl/lib","type":"Directory"}}},
  {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts/-","value":{"name":"wsl-nvidia-lib","mountPath":"/usr/lib/wsl/lib","readOnly":true}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"LD_LIBRARY_PATH","value":"/usr/lib/wsl/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64"}},
  {"op":"add","path":"/spec/template/spec/volumes/-","value":{"name":"wsl-dxg","hostPath":{"path":"/dev/dxg","type":"CharDevice"}}},
  {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts/-","value":{"name":"wsl-dxg","mountPath":"/dev/dxg"}},
  {"op":"replace","path":"/spec/template/spec/containers/0/securityContext","value":{"privileged":true}}
]
EOF
sudo k3s kubectl patch ds nvidia-device-plugin-daemonset -n kube-system --type=json --patch-file /tmp/nvidia-wsl-patch.json
sudo k3s kubectl rollout status ds/nvidia-device-plugin-daemonset -n kube-system --timeout=120s'
```

If GPU capacity still does not appear, the cluster can still prove multi-node scheduling, but CAI GPU chunk pods will stay pending until Kubernetes advertises `nvidia.com/gpu`.

## 10.1 AMD or Non-NVIDIA Worker Nodes

CAI's CUDA GPU path uses NVIDIA CUDA and Kubernetes advertises those devices as:

```text
nvidia.com/gpu
```

An AMD laptop GPU will not appear as `nvidia.com/gpu`. On Windows/WSL, AMD ROCm support is also not a drop-in replacement for the current CUDA path. Treat AMD laptops as CPU/RAM workers unless a separate ROCm runtime is added.

For AMD, integrated GPU, or CPU-only worker nodes, deploy the CAI Kubernetes pipeline with CPU mode:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /opt/CAI && source .venv310/bin/activate && python kubernetes/controller.py deploy --num-chunks 2 --model transformer --cpu-only --wait"
```

CPU mode intentionally removes:

```text
nvidia.com/gpu: 1
nvidia.com/gpu.present=true
```

This lets chunk and monitor pods schedule on AMD/non-NVIDIA workers. It is slower than CUDA, but it will not damage the worker or the cluster. The default GPU deployment remains unchanged when `--cpu-only` is not used.

## 11. Deploy CAI After GPU Capacity Appears

Only run this when both nodes show GPU capacity or when the CAI deployment has been changed to CPU mode.

Build CAI images:

```powershell
cd D:\CODE\CAI
.\.venv310\Scripts\python.exe cai_cli.py build --tag CAI:latest
```

For K3s/containerd, import images into the primary node:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/d/CODE/CAI && sudo k3s ctr images import CAI-chunk.tar || true"
```

If using Docker image export, first create tar files:

```powershell
docker save CAI-chunk:latest -o CAI-chunk.tar
docker save CAI-gateway:latest -o CAI-gateway.tar
docker save CAI-monitor:latest -o CAI-monitor.tar
```

Import into K3s on each node:

```bash
sudo k3s ctr images import CAI-chunk.tar
sudo k3s ctr images import CAI-gateway.tar
sudo k3s ctr images import CAI-monitor.tar
```

Deploy CAI:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /opt/CAI && source .venv310/bin/activate && python kubernetes/controller.py deploy --num-chunks 2 --model transformer --wait"
```

Verify pod placement:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get pods -n CAI -o wide
```

Expected goal:

```text
CAI-chunk-0   Running   mighty
CAI-chunk-1   Running   bat-machine47
CAI-gateway   Running   mighty
CAI-monitor   Running   ...
```

## 12. Test CAI Gateway

CAI gateway uses NodePort `30080`.

Health check:

```powershell
curl http://192.168.100.1:30080/health
```

Inference request:

```powershell
curl -X POST http://192.168.100.1:30080/infer `
  -H "Content-Type: application/json" `
  -d '{"prompt":"Hello from CAI multi-node Ethernet","max_tokens":64}'
```

## 13. Security Cleanup

Never commit the K3s join token.

Add this to `.gitignore`:

```text
logs/k3s-node-token.txt
```

Remove it from Git tracking if it was committed:

```powershell
git rm --cached logs/k3s-node-token.txt
git commit -m "Remove K3s node token from repository"
git push
```

If the token was pushed to a public or shared repository, rotate it before using the cluster beyond a local lab setup.

## 14. Quick Status Commands

Primary node and worker list:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get nodes -o wide
```

All pods:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get pods -A -o wide
```

GPU capacity:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl describe nodes | findstr /i "nvidia.com/gpu"
```

CAI pods:

```powershell
wsl -d Ubuntu-22.04 -- sudo k3s kubectl get pods -n CAI -o wide
```

K3s logs:

```powershell
wsl -d Ubuntu-22.04 -- sudo journalctl -u k3s --no-pager -n 120
```

Worker agent logs, run on worker laptop:

```powershell
wsl -d Ubuntu-22.04 -- sudo journalctl -u k3s-agent --no-pager -n 120
```
