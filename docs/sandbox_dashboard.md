# CAI Sandbox — Desktop Management Dashboard

Manage, simulate, and orchestrate your entire decentralized CAI Sandbox cluster visually from a desktop GUI.

---

## Launching the Dashboard

You can start the unified CAI Pro Dashboard (which now includes the **Sandbox Manager** tab) via the CAI CLI:

```bash
python cai_cli.py dashboard
```

Alternatively, launch it directly via Streamlit:
```bash
streamlit run dashboard/comprehensive_dashboard.py
```

Once running, open the URL in your web browser (typically `http://localhost:8501`) and select the **Sandbox Manager** option in the sidebar navigation.

---

## Features

The Sandbox Manager GUI provides three main tabs corresponding to different cluster lifecycle phases:

### 1. Control Plane & Nodes
* **Config & Launch**: Define cluster modes (`single`, `multi_primary`, `multi_worker`), roles (`primary`, `worker`), custom node IDs, and network port configurations.
* **Direct Joining**: Workers can supply a Primary Node address and access token to join a remote cluster directly from the GUI.
* **Cluster Topology Table**: View a real-time table of all active nodes in the cluster registry, detailing addresses, status, and hardware parameters.
* **Resource Distribution Visualization**: Visual charts displaying GPU count, total VRAM, and total system RAM allocated to the cluster.

### 2. Virtual Cluster Simulation
* **Spawn Virtual Workers**: Spin up 1 to 5 virtual worker nodes in background threads. 
* **Hardware Profiles**: Test heterogeneous hardware scheduling (e.g., mixtures of `high_gpu` RTX 4090, `mid_gpu` RTX 3060, `cpu_only` nodes, and low-power Jetson Nano edge platforms).
* **Live Telemetry Streams**: Monitor real-time virtual metrics (load averages, GPU temperature readings, and simulated power draw) plotted as graphs.

### 3. Model Deployment & Inference
* **Select & Partition**: Choose popular models (e.g., Phi-2, Gemma-2B, Llama-2-13B), configuration strategy (`balanced`, `energy`, `latency`), and number of partitions.
* **One-Click Deploy**: Deploy and partition weights across the cluster with a single click, instantly displaying layer placement details.
* **Interactive Chat Prompt**: Enter prompts, customize token length and temperature, and run distributed text generation with full generation time and throughput metrics.
