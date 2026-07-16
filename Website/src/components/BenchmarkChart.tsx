"use client";

import { useState } from "react";
import { BarChart3, Info, Zap, Clock } from "lucide-react";

type MetricKey = "power" | "energy" | "latency" | "throughput";

export default function BenchmarkChart() {
  const [activeMetric, setActiveMetric] = useState<MetricKey>("energy");

  // TODO: replace with real benchmark data from CAI evaluations
  const metricsData = {
    power: {
      title: "Average Cluster Power Draw (W)",
      description: "Average real-time power draw measured via NVML under continuous inference loads. Lower is better.",
      baselineLabel: "Single RTX 4090 Baseline",
      baselineValue: 380,
      caiLabel: "CAI Distributed Cluster (3x Low-End)",
      caiValue: 148,
      unit: "W",
      highlight: "61.0% Power Reduction",
      isLowerBetter: true,
    },
    energy: {
      title: "Total Energy Consumption (Wh)",
      description: "Cumulative energy consumed during a standard 1,000-inference test run. Lower is better.",
      baselineLabel: "Single RTX 4090 Baseline",
      baselineValue: 15.6,
      caiLabel: "CAI Distributed Cluster (3x Low-End)",
      caiValue: 6.2,
      unit: "Wh",
      highlight: "60.2% Energy Saved",
      isLowerBetter: true,
    },
    latency: {
      title: "Average Inference Latency (ms)",
      description: "Average end-to-end latency per query request. Lower is better. Note: network transit overhead increases latency.",
      baselineLabel: "Single RTX 4090 Baseline",
      baselineValue: 38,
      caiLabel: "CAI Distributed Cluster (3x Low-End)",
      caiValue: 86,
      unit: "ms",
      highlight: "Network Overhead Tradeoff",
      isLowerBetter: true,
    },
    throughput: {
      title: "Inference Throughput (tokens/s)",
      description: "Token generation throughput across the entire model pipeline. Higher is better.",
      baselineLabel: "Single RTX 4090 Baseline",
      baselineValue: 64,
      caiLabel: "CAI Distributed Cluster (3x Low-End)",
      caiValue: 28,
      unit: "tok/s",
      highlight: "Slower Pipeline Generation",
      isLowerBetter: false,
    }
  };

  const current = metricsData[activeMetric];

  // Calculate percentages for SVG bar widths
  const maxVal = Math.max(current.baselineValue, current.caiValue);
  const baselinePct = (current.baselineValue / maxVal) * 80; // keep some padding
  const caiPct = (current.caiValue / maxVal) * 80;

  return (
    <section className="py-24 relative overflow-hidden bg-slate-950/40 border-b border-slate-900">
      <div className="absolute inset-0 glow-overlay-green opacity-20 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">

        {/* Header */}
        <div className="max-w-3xl mx-auto text-center mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-brand-green/30 text-brand-green text-xs font-mono uppercase tracking-wider">
            <BarChart3 className="w-3.5 h-3.5" /> EMPIRICAL BENCHMARKS
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            How Cai Compares on Real Hardware
          </h2>
          <p className="text-slate-400 text-lg">
            Direct comparison of a standard single high-end GPU execution versus Cai running distributed inference on consumer cards.
          </p>
        </div>

        {/* Outer Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">

          {/* Left Controls */}
          <div className="lg:col-span-4 space-y-3">
            {(Object.keys(metricsData) as MetricKey[]).map((key) => {
              const item = metricsData[key];
              const isSelected = activeMetric === key;
              return (
                <button
                  key={key}
                  onClick={() => setActiveMetric(key)}
                  className={`w-full p-4 rounded-xl border text-left transition-all duration-300 flex items-center justify-between ${isSelected
                    ? "border-brand-green bg-slate-900/60 shadow-[0_0_15px_rgba(0,255,102,0.05)]"
                    : "border-slate-800 bg-slate-950/40 hover:bg-slate-900/30"
                    }`}
                >
                  <div className="space-y-1">
                    <p className={`text-sm font-bold font-sans ${isSelected ? "text-white" : "text-slate-300"}`}>
                      {key === "power" && "Power Draw (TDP)"}
                      {key === "energy" && "Cumulative Energy"}
                      {key === "latency" && "Inference Latency"}
                      {key === "throughput" && "Inference Throughput"}
                    </p>
                    <p className="text-[10px] text-slate-500 font-mono">{item.highlight}</p>
                  </div>
                  <div className={`p-1.5 rounded ${isSelected ? "bg-brand-green/20 text-brand-green" : "bg-slate-950 border border-white/5 text-slate-500"}`}>
                    {key === "power" || key === "energy" ? <Zap className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right SVG Chart Container */}
          <div className="lg:col-span-8">
            <div className="glass-panel p-6 md:p-8 rounded-2xl border-slate-800 bg-slate-950/70 font-mono space-y-6">

              {/* Chart Meta */}
              <div>
                <h3 className="text-white text-base font-bold mb-1">{current.title}</h3>
                <p className="text-slate-400 text-xs font-sans leading-relaxed">{current.description}</p>
              </div>

              {/* Custom SVG Bar Chart */}
              <div className="py-6 space-y-6">

                {/* Baseline Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400 font-bold">{current.baselineLabel}</span>
                    <span className="text-red-400 font-bold">{current.baselineValue} {current.unit}</span>
                  </div>
                  <div className="h-10 w-full bg-slate-900/60 rounded border border-white/5 overflow-hidden flex relative items-center">
                    <div
                      className="h-full bg-gradient-to-r from-red-950/50 to-red-500/20 border-r border-red-500/50 transition-all duration-700"
                      style={{ width: `${baselinePct}%` }}
                    />
                    <span className="absolute left-4 text-xs font-bold text-white/90">Baseline</span>
                  </div>
                </div>

                {/* Cai Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400 font-bold">{current.caiLabel}</span>
                    <span className="text-brand-green font-bold">{current.caiValue} {current.unit}</span>
                  </div>
                  <div className="h-10 w-full bg-slate-900/60 rounded border border-white/5 overflow-hidden flex relative items-center">
                    <div
                      className="h-full bg-gradient-to-r from-brand-cyan/20 to-brand-green/30 border-r border-brand-green/50 transition-all duration-700 shadow-[inset_0_0_10px_rgba(0,255,102,0.1)]"
                      style={{ width: `${caiPct}%` }}
                    />
                    <span className="absolute left-4 text-xs font-bold text-brand-green flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-brand-green animate-pulse" /> Cai Active
                    </span>
                  </div>
                </div>

              </div>

              {/* Honorable Tradeoffs Alert */}
              <div className="p-4 rounded-lg bg-slate-950 border border-white/5 flex gap-3 text-xs leading-relaxed">
                <div className="shrink-0 p-1 text-yellow-500 bg-yellow-500/5 border border-yellow-500/10 rounded-md self-start">
                  <Info className="w-4 h-4" />
                </div>
                <div className="text-slate-400 space-y-1">
                  <p className="font-bold text-slate-300">Technical Tradeoff Disclosure</p>
                  <p>
                    Distributed pipeline parallelism introduces serialization and network routing overhead. As shown, Cai takes a performance hit on latency and total throughput compared to a single enterprise RTX 4090.
                  </p>
                  <p className="text-[11px] text-brand-cyan">
                    Key Wedge: Cai is designed for energy efficiency and accessibility, enabling massive model runs on affordable hardware.
                  </p>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
