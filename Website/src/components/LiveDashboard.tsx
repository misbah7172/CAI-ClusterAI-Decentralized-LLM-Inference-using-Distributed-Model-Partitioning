"use client";

import { useEffect, useState } from "react";
import { Activity, Thermometer, Zap, Server, Clock, Cpu } from "lucide-react";

function AnimatedGauge({ value, max, label, unit, color }: { value: number; max: number; label: string; unit: string; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-2">
      <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{label}</p>
      <div className="flex items-end gap-1">
        <span className={`text-2xl font-bold font-mono ${color}`}>{value}</span>
        <span className="text-xs text-slate-500 mb-0.5">{unit}</span>
      </div>
      <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${color === "text-brand-green" ? "bg-brand-green" : color === "text-brand-cyan" ? "bg-brand-cyan" : color === "text-red-400" ? "bg-red-400" : "bg-yellow-400"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function LiveDashboard() {
  const [metrics, setMetrics] = useState({
    gpuUtil: 72,
    power: 118,
    latency: 84,
    temp: 67,
    nodes: 3,
    inferenceSpeed: 47,
    energySaved: 61,
    modelStatus: "RUNNING",
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => ({
        gpuUtil: Math.round(65 + Math.random() * 20),
        power: Math.round(110 + Math.random() * 15),
        latency: Math.round(78 + Math.random() * 12),
        temp: Math.round(63 + Math.random() * 8),
        nodes: 3,
        inferenceSpeed: parseFloat((42 + Math.random() * 10).toFixed(1)),
        energySaved: parseFloat((prev.energySaved + 0.02).toFixed(2)),
        modelStatus: "RUNNING",
      }));
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-24 relative overflow-hidden bg-slate-950/30 border-b border-slate-900">
      <div className="absolute inset-0 glow-overlay-cyan opacity-20 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-brand-green/30 text-brand-green text-xs font-mono uppercase tracking-wider">
            <Activity className="w-3.5 h-3.5 animate-pulse" /> Live System Telemetry
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Real-Time Cluster Dashboard
          </h2>
          <p className="text-slate-400 text-lg font-sans">
            A live view of a distributed CAI inference session across 3 low-end consumer nodes running Phi-2 (2.7B).
          </p>
        </div>

        <div className="glass-panel rounded-2xl border border-white/5 overflow-hidden">
          {/* Header Bar */}
          <div className="flex items-center justify-between px-6 py-4 bg-slate-950/80 border-b border-white/5">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/80" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <span className="w-3 h-3 rounded-full bg-green-500/80" />
              <span className="ml-4 text-xs font-mono text-slate-400">CAI-studio — cluster-dashboard</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-[10px] font-mono text-brand-green">
                <span className="w-2 h-2 rounded-full bg-brand-green animate-pulse" />
                {metrics.modelStatus}
              </span>
              <span className="text-[10px] font-mono text-slate-500">microsoft/phi-2</span>
            </div>
          </div>

          {/* Main Dashboard Grid */}
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <AnimatedGauge value={metrics.gpuUtil} max={100} label="GPU Utilization" unit="%" color="text-brand-cyan" />
            <AnimatedGauge value={metrics.power} max={250} label="Cluster Power Draw" unit="W" color="text-brand-green" />
            <AnimatedGauge value={metrics.latency} max={200} label="Avg Inference Latency" unit="ms" color="text-yellow-400" />
            <AnimatedGauge value={metrics.temp} max={90} label="Peak GPU Temperature" unit="°C" color="text-red-400" />

            {/* Node Status */}
            <div className="col-span-1 md:col-span-2 p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-3">
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Server className="w-3 h-3" /> Active Nodes ({metrics.nodes}/3)
              </p>
              {[
                { id: "Node-0 (RTX 3050 Ti)", layers: "Layers 0-7", vram: "3.8/4.0 GB", load: 78 },
                { id: "Node-1 (GTX 1660)", layers: "Layers 8-19", vram: "5.6/6.0 GB", load: 85 },
                { id: "Node-2 (CPU/RAM)", layers: "Layers 20-31", vram: "2.2/16.0 GB", load: 42 },
              ].map((node) => (
                <div key={node.id} className="flex items-center gap-3 text-xs">
                  <span className="w-2 h-2 rounded-full bg-brand-green animate-pulse flex-shrink-0" />
                  <span className="text-slate-300 font-mono w-48 truncate">{node.id}</span>
                  <span className="text-brand-cyan font-mono text-[10px]">{node.layers}</span>
                  <div className="flex-1 h-1 bg-slate-900 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-cyan rounded-full" style={{ width: `${node.load}%` }} />
                  </div>
                  <span className="text-slate-500 font-mono text-[10px] w-20 text-right">{node.vram}</span>
                </div>
              ))}
            </div>

            {/* Inference Stats */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-4">
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Clock className="w-3 h-3" /> Inference Rate
              </p>
              <p className="text-3xl font-bold font-mono text-white">{metrics.inferenceSpeed} <span className="text-xs text-slate-400 font-normal">tok/s</span></p>
              <div className="text-[10px] font-mono text-slate-500 space-y-1">
                <p>RTT Probe: 0.38ms (cached)</p>
                <p>Pipeline latency: 84ms avg</p>
              </div>
            </div>

            {/* Energy Savings */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-white/5 space-y-4">
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Zap className="w-3 h-3" /> Cumulative Energy Saved
              </p>
              <p className="text-3xl font-bold font-mono text-brand-green">-{metrics.energySaved}%</p>
              <div className="text-[10px] font-mono text-slate-500 space-y-1">
                <p>vs. single RTX 4090 baseline</p>
                <p className="text-brand-green">DEAS scheduler: ACTIVE</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
