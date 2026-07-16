"use client";

import { useState } from "react";
import { Network, Cpu, Zap, Shield, Monitor, ArrowRightLeft, Thermometer, Share2, Server, Layers, Wifi, Container, Eye } from "lucide-react";

const features = [
  {
    icon: <Network className="w-5 h-5" />,
    title: "Distributed AI Inference",
    desc: "Split transformer layers across multiple nodes via gRPC pipeline parallelism. No single machine needs full VRAM.",
    color: "text-brand-cyan",
    bg: "bg-brand-cyan/10",
    border: "border-brand-cyan/20",
  },
  {
    icon: <Zap className="w-5 h-5" />,
    title: "Energy-Aware Scheduling (DEAS)",
    desc: "Closed-loop PID controller monitors GPU power via NVML and dynamically adjusts batch size, precision, and power limits.",
    color: "text-brand-green",
    bg: "bg-brand-green/10",
    border: "border-brand-green/20",
  },
  {
    icon: <Container className="w-5 h-5" />,
    title: "Sandbox Runtime",
    desc: "Simulate a full multi-node cluster on one laptop — virtual nodes on local ports before touching real hardware.",
    color: "text-accent-blue",
    bg: "bg-accent-blue/10",
    border: "border-accent-blue/20",
  },
  {
    icon: <Wifi className="w-5 h-5" />,
    title: "Remote Node Management",
    desc: "Register and manage physical nodes over encrypted channels. Continuous health pings, live status, and auto-recovery.",
    color: "text-accent-teal",
    bg: "bg-accent-teal/10",
    border: "border-accent-teal/20",
  },
  {
    icon: <Cpu className="w-5 h-5" />,
    title: "GPU + CPU Offloading",
    desc: "FlexGen-style tiered weight management: GPU VRAM → System RAM → Disk. Double-buffered prefetching hides latency.",
    color: "text-brand-cyan",
    bg: "bg-brand-cyan/10",
    border: "border-brand-cyan/20",
  },
  {
    icon: <ArrowRightLeft className="w-5 h-5" />,
    title: "Dynamic Layer Migration",
    desc: "Pause, checkpoint, and migrate active model layers to healthier nodes without output corruption.",
    color: "text-brand-green",
    bg: "bg-brand-green/10",
    border: "border-brand-green/20",
  },
  {
    icon: <Thermometer className="w-5 h-5" />,
    title: "Real-Time Energy Monitoring",
    desc: "Sub-100ms NVML sampling with ring buffers, TDP auto-detection, trapezoidal energy integration, and threshold alerts.",
    color: "text-accent-blue",
    bg: "bg-accent-blue/10",
    border: "border-accent-blue/20",
  },
  {
    icon: <Layers className="w-5 h-5" />,
    title: "Model Partitioning",
    desc: "HuggingFace models partitioned at transformer block boundaries. Smart auto-partitioner assigns layers proportionally by VRAM.",
    color: "text-accent-teal",
    bg: "bg-accent-teal/10",
    border: "border-accent-teal/20",
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: "Secure Node Communication",
    desc: "TLS-encrypted gRPC channels between pipeline nodes. Isolated namespaces and access-controlled cluster admission.",
    color: "text-brand-cyan",
    bg: "bg-brand-cyan/10",
    border: "border-brand-cyan/20",
  },
  {
    icon: <Server className="w-5 h-5" />,
    title: "Hybrid Cluster Mode",
    desc: "Combine sandbox virtual nodes, local GPUs, and remote Kubernetes pods in a single inference pipeline.",
    color: "text-brand-green",
    bg: "bg-brand-green/10",
    border: "border-brand-green/20",
  },
  {
    icon: <Eye className="w-5 h-5" />,
    title: "Single Node Mode",
    desc: "Run oversized models on one GPU using layer streaming, adaptive batch sizing, and runtime precision adaptation.",
    color: "text-accent-blue",
    bg: "bg-accent-blue/10",
    border: "border-accent-blue/20",
  },
  {
    icon: <Share2 className="w-5 h-5" />,
    title: "Kubernetes Integration",
    desc: "Deploy chunk servers, gateways, and monitors as Kubernetes pods with automatic NVML DaemonSet metric collection.",
    color: "text-accent-teal",
    bg: "bg-accent-teal/10",
    border: "border-accent-teal/20",
  },
  {
    icon: <Monitor className="w-5 h-5" />,
    title: "Automatic Hardware Detection",
    desc: "ResourceDetector scans GPU VRAM, system RAM, and CPU cores across all cluster nodes before partitioning.",
    color: "text-brand-cyan",
    bg: "bg-brand-cyan/10",
    border: "border-brand-cyan/20",
  },
];

export default function FeatureHighlights() {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <section id="features" className="py-24 relative overflow-hidden bg-bg-dark border-b border-slate-900 scroll-mt-20">
      <div className="absolute inset-0 circuit-dots opacity-10 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-brand-cyan/30 text-brand-cyan text-xs font-mono uppercase tracking-wider">
            <Network className="w-3.5 h-3.5" /> Platform Features
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Everything You Need to Run AI at Scale
          </h2>
          <p className="text-slate-400 text-lg font-sans">
            CAI is built from the ground up for distributed, energy-efficient inference. Not a wrapper — a runtime.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {features.map((feat, idx) => (
            <div
              key={idx}
              onMouseEnter={() => setHovered(idx)}
              onMouseLeave={() => setHovered(null)}
              className={`p-5 rounded-xl border transition-all duration-300 cursor-default ${hovered === idx
                  ? `${feat.border} bg-slate-900/70 shadow-lg`
                  : "border-slate-900 bg-slate-950/40 hover:border-slate-800"
                }`}
            >
              <div className={`w-10 h-10 rounded-lg ${feat.bg} ${feat.color} flex items-center justify-center mb-4`}>
                {feat.icon}
              </div>
              <h3 className="text-white text-sm font-bold mb-2 leading-snug">{feat.title}</h3>
              <p className="text-slate-400 text-xs font-sans leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
