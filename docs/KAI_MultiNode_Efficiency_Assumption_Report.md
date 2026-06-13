# KAI Multi-Node Efficiency Assumption Report

## Purpose

This report is a code-backed assumption analysis for KAI multi-node efficiency on a two-laptop cluster. It is intended for progress reporting before a full measured benchmark is available.

Important: the values in this report are projected estimates, not measured experimental results. They are designed to be realistic and defensible because they are based on the current KAI code paths, hardware constraints, and known memory/throughput behavior of quantized LLM inference. Do not present these numbers as final benchmark results.

## Hardware Assumption

| Node | GPU | CPU | RAM | Assumed Usable VRAM | Role |
|---|---:|---|---:|---:|---|
| Node A | RTX 3050 Ti Laptop GPU, 4 GB | Intel i5 11th Gen H-series | 16 GB | 3.5 GB | Primary GPU/control node |
| Node B | GTX 1080-class GPU, 2 GB as provided | Intel i5 10th Gen | 16 GB | 1.5 GB | Secondary worker/offload node |

KAI code uses a conservative memory rule in `model/resource_detector.py`: GPU usable memory is approximately `VRAM - 500 MB`. CPU-only usable RAM is approximately `70% of RAM`.

For this setup:

```text
Usable GPU memory = (4.0 - 0.5) + (2.0 - 0.5) = 5.0 GB
Usable system RAM = 0.70 * 16 + 0.70 * 16 = 22.4 GB
Combined usable memory pool for offload-aware execution = about 27.4 GB
```

## Codebase Basis

The projection is based on these KAI modules:

| Code path | Efficiency role |
|---|---|
| `model/resource_detector.py` | Detects GPU VRAM, RAM, CPU cores, and estimates usable memory. |
| `model/auto_partitioner.py` | Assigns contiguous model layers to nodes proportional to usable memory. |
| `model/gateway.py` | Runs the multi-node pipeline by serializing tensors and forwarding them through gRPC chunk services. |
| `model/chunk_server.py` | Hosts one model chunk and executes it on the configured `DEVICE`. |
| `model/tiered_weight_manager.py` | Places weights across GPU VRAM, system RAM, and disk. |
| `model/prefetch_engine.py` | Hides some RAM/disk transfer latency with double-buffered prefetching. |
| `model/energy_feedback_loop.py` | Defines energy-per-token and efficiency scoring concepts. |
| `kubernetes/controller.py` | Deploys KAI chunk/gateway/monitor pods. Current AMD-safe path is `--cpu-only`; NVIDIA GPU path requires `nvidia.com/gpu`. |

## Model Memory Assumptions

Approximate model weight sizes:

| Model class | FP16 weights | INT8 weights | INT4 weights | Runtime note |
|---|---:|---:|---:|---|
| 7B | 14 GB | 7 GB | 3.5-4.5 GB | Feasible only with 4-bit plus offload on this cluster. |
| 13B | 26 GB | 13 GB | 6.5-8.5 GB | Feasible only with aggressive 4-bit plus CPU/RAM offload; slow. |

The KAI partitioner adds a rough 20% overhead in its layer memory estimate. KV cache, activations, tokenizer buffers, PyTorch allocator fragmentation, and gRPC serialization add additional pressure.

## Efficiency Interpretation

KAI is efficient in this setup mainly in memory feasibility, not raw speed. A single 4 GB GPU cannot comfortably host 7B or 13B models without quantization/offload. KAI improves feasibility by combining GPU VRAM, system RAM, disk offload, partitioning, and scheduling.

Expected benefits:

- Higher model feasibility than a single low-VRAM laptop.
- Lower peak VRAM pressure on the RTX 3050 Ti.
- Ability to use the second laptop as a CPU/RAM worker or, if NVIDIA CUDA is available, a small GPU worker.
- Better instrumentation for TTFT, PTGT, tokens/sec, energy per token, routing, and worker efficiency.

Expected costs:

- gRPC tensor serialization adds latency between chunks.
- 1 Gbps Ethernet limits inter-node transfer bandwidth.
- GTX 1080-class 2 GB VRAM is too small for large layer groups; it contributes mostly small chunks/offload support.
- 13B models will be memory-feasible only with aggressive offload and will be slow.

## Projection Method

The CSV estimates use these assumptions:

```text
usable_vram_gb = total_vram_gb - 0.5 GB per NVIDIA GPU
usable_ram_gb = 0.70 * system_ram_gb
model_fp16_gb = parameters_billion * 2 bytes
model_int4_runtime_gb = model_fp16_gb * 0.28 to 0.35 including overhead
network_effective_bandwidth = 90 to 110 MB/s on 1 Gbps Ethernet
multi_node_gain = memory-pressure reduction - network/serialization overhead
energy_per_100_tokens_wh = average_power_w * generation_time_seconds / 3600
```

The estimates assume 4-bit quantization for 7B and 13B runs. FP16 is included only to show infeasibility on this hardware.

## Summary Projection

| Scenario | Feasibility | Expected behavior |
|---|---|---|
| 7B FP16 single node | Not feasible | 14+ GB weights cannot fit in 4 GB VRAM. |
| 7B INT4 single RTX with offload | Feasible but slow | Heavy CPU/RAM offload; acceptable for short demos. |
| 7B INT4 KAI two-node | Feasible | Better memory distribution, modest throughput gain if second node can execute chunks. |
| 13B FP16 single node | Not feasible | 26+ GB weights exceed local GPU/RAM comfort. |
| 13B INT4 single RTX with offload | Marginal | Can run only with aggressive offload and low token count. |
| 13B INT4 KAI two-node | Marginal/Research-only | Feasible as a demonstration of large-model orchestration, not fast inference. |

## Key Result for Professor Update

KAI's projected multi-node value on the given hardware is strongest for memory feasibility:

```text
7B model: projected from single-node offload demo to distributed/offload demo with about 25-35% better tokens/sec and 25-30% lower peak VRAM pressure on the primary node.
13B model: projected from barely feasible single-node offload to research-feasible multi-node/offload execution, but still slow due to low VRAM and Ethernet overhead.
```

The CSV file `KAI_MultiNode_Efficiency_Assumption_Report.csv` contains the structured scenario estimates.

## Submission Note

Use the wording `projected`, `estimated`, or `assumption-based` when showing this data. The dataset is suitable for explaining expected KAI behavior and experimental design, but it should be replaced by measured CSV logs after the cluster runs successfully.
