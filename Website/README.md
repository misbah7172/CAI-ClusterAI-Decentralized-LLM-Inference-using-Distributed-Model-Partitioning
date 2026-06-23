# CAI Showcase Landing Page

A premium, energy-efficient, and highly interactive marketing and research-grade showcase website for the **CAI** decentralized AI inference runtime.

Built with **Next.js (App Router)**, **TypeScript**, **Tailwind CSS v4**, **Framer Motion**, and **Lucide React**.

---

## Features

1. **Hero**: Highlights the core value proposition ("Run big models on small hardware. A fraction of the power") alongside a live 2D Canvas-based particle network representing distributed token generation telemetry.
2. **dilemma Section**: Compares standard enterprise node execution (RTX 4090 peak TDP draw) vs CAI's multi-node low-power clusters.
3. **Pipeline Architecture**: Visual representation of layer chunking and gRPC pipeline execution.
4. **DEAS Feedback Loop**: Demonstrates Dynamic Energy-Aware Scheduling feedback loop mechanisms.
5. **Local Sandbox Mode**: Switchable command visual comparing local port simulations vs production Kubernetes orchestration.
6. **Empirical Benchmarks**: Custom SVG bar charts for power, energy, latency, and throughput comparison.
7. **Systems Evolution Timeline**: Vertical roadmap highlighting past milestones, active Phase 25 schedulers, and planned fault-tolerance daemons.

---

## Getting Started

### Prerequisites

Ensure you have [Node.js (v18.x or later)](https://nodejs.org) installed on your system.

### Installation

1. Install npm dependencies:
   ```bash
   npm install
   ```

2. Run the development server locally:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

## Technical Stack & Configuration

- **Next.js 16** (React 19) App Router structure.
- **Tailwind CSS v4** configures custom color palettes (sustainable emerald greens, neon teals, and glowing cyans) and animation routines inside `src/app/globals.css`.
- Fully responsive styling down to 375px mobile screens.
