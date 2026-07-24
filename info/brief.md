# CAI: Closed-Loop Orchestration for Distributed AI Inference

## Project Summary

CAI is a distributed AI inference platform designed to run Large Language Models across heterogeneous, resource-constrained devices using a real-time closed-loop feedback control system to optimize energy efficiency and thermal stability.

---

## 1. Core Focus

**Real-Time Closed-Loop Feedback Control**

CAI treats distributed inference as a control systems problem rather than a static scheduling problem — continuously sensing node state, computing deviation from target operating conditions, and actuating corrections in real time.

---

## 2. Telemetry & Sensing (Input)

Continuously monitors node-level metrics in real time, including:

- GPU/CPU temperature
- Power draw and throttling state
- Memory utilization (VRAM / RAM / disk)
- Inference latency and throughput per node

---

## 3. Control Logic & Decision Engine (Process)

- Uses a feedback loop controller to calculate the deviation between real-time node states and predefined operational envelopes (e.g., thermal limits, power budgets, latency targets).
- Deviation is fed back into the controller to determine corrective actuation before the node breaches safe operating bounds.

---

## 4. Dynamic Actuation & Adaptation (Output)

### 4.1 Dynamic Chunk Migration
Dynamically reallocates model layers/chunks from a worker node's GPU — when it's at risk of overheating or being power-throttled — to cooler, more efficient peer nodes.

### 4.2 Adaptive Offloading & Quantization
Adjusts memory offloading strategy (CPU vs. GPU vs. Disk) on the fly, without interrupting active token generation streams.

### 4.3 Energy Routing
Directs inference traffic through the path of maximum power efficiency, using the **DEAS** (Dynamic Energy-Aware Scheduling) algorithm.

---

## System Flow

```
Telemetry & Sensing → Control Logic & Decision Engine → Dynamic Actuation & Adaptation
        (Input)                  (Process)                       (Output)
            └────────────────── feedback loop ──────────────────────┘
```