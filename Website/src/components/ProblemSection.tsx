"use client";

import { useState } from "react";
import { AlertTriangle, ShieldCheck, Thermometer, Zap, AlertCircle } from "lucide-react";

export default function ProblemSection() {
  const [activeTab, setActiveTab] = useState<"standard" | "CAI">("CAI");

  return (
    <section className="py-24 relative overflow-hidden bg-slate-950/40 border-y border-slate-900">
      <div className="absolute inset-0 glow-overlay-cyan opacity-40 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">

        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white">
            The Distributed Inference Dilemma
          </h2>
          <p className="text-slate-400 text-lg">
            Running modern LLMs typically requires high-end, capital-intensive GPUs that pull excessive power. CAI solves this by orchestrating inference across the hardware you already own.
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex justify-center mb-12">
          <div className="p-1 rounded-xl bg-slate-900 border border-slate-800 flex gap-2">
            <button
              onClick={() => setActiveTab("standard")}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium font-mono transition-all duration-300 ${activeTab === "standard"
                ? "bg-red-500/10 text-red-400 border border-red-500/20"
                : "text-slate-400 hover:text-white"
                }`}
            >
              Standard Execution
            </button>
            <button
              onClick={() => setActiveTab("CAI")}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium font-mono transition-all duration-300 ${activeTab === "CAI"
                ? "bg-brand-green/10 text-brand-green border border-brand-green/20 shadow-[0_0_15px_rgba(0,255,102,0.1)]"
                : "text-slate-400 hover:text-white"
                }`}
            >
              CAI Orchestrated
            </button>
          </div>
        </div>

        {/* Side by Side Comparison Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">

          {/* Left Cards */}
          <div className="lg:col-span-6 space-y-6">
            {activeTab === "standard" ? (
              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-xl border-red-500/20 bg-slate-950/60 relative overflow-hidden transition-all duration-500">
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Thermometer className="w-24 h-24 text-red-500" />
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-red-500/10 text-red-400">
                      <AlertTriangle className="w-6 h-6" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold text-white">Inefficient Energy Consumption</h3>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        A single enterprise-grade GPU (like an A100 or H100) running inference pulls up to 400W–700W continuously. This generates intense local thermal loads and high carbon footprint, even when batch utilization is low.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="glass-panel p-6 rounded-xl border-red-500/20 bg-slate-950/60 relative overflow-hidden transition-all duration-500">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-red-500/10 text-red-400">
                      <AlertCircle className="w-6 h-6" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold text-white">Hardware Bottlenecks</h3>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        If a model exceeds the VRAM of a single local GPU, inference fails immediately with an Out-of-Memory (OOM) error. Upgrading hardware is slow, highly expensive, and introduces single-point-of-failure vulnerabilities.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-xl border-brand-green/20 bg-slate-950/60 relative overflow-hidden transition-all duration-500 shadow-[0_0_20px_rgba(0,255,102,0.02)]">
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Zap className="w-24 h-24 text-brand-green" />
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-brand-green/10 text-brand-green">
                      <Zap className="w-6 h-6" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold text-white">Dynamic Energy Management (DEAS)</h3>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        CAI uses Dynamic Energy-Aware Scheduling to partition layers and throttle power limits dynamically. It monitors NVML telemetries and adjusts batch size and precision matching, cutting power draw by up to 64%.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="glass-panel p-6 rounded-xl border-brand-cyan/20 bg-slate-950/60 relative overflow-hidden transition-all duration-500">
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-brand-cyan/10 text-brand-cyan">
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold text-white">Modular Cluster Aggregation</h3>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        Instead of wasting budget on a single massive GPU, CAI links consumer cards (e.g., RTX 3050s, GTX 1660s) or CPU RAM via gRPC pipeline parallelism. It aggregates local VRAM, scaling up capacity dynamically.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Power Meter Visual */}
          <div className="lg:col-span-6 flex flex-col justify-center">
            <div className="glass-panel p-6 rounded-xl border-slate-800 bg-slate-950/70 font-mono">
              <div className="flex justify-between items-center mb-6">
                <span className="text-slate-500 text-xs uppercase tracking-wider">Total Power Usage Comparison</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">Peak TDP Draw</span>
              </div>

              {/* Graphic Comparison */}
              <div className="space-y-8">
                {/* Standard GPU */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400 font-bold">Single Heavy GPU (RTX 4090 Peak)</span>
                    <span className="text-red-400 font-bold">450 Watts</span>
                  </div>
                  <div className="h-6 w-full bg-slate-900 rounded border border-white/5 overflow-hidden flex">
                    <div
                      className={`h-full bg-gradient-to-r from-red-600/80 to-red-500 transition-all duration-1000 flex items-center justify-end px-3 text-[10px] text-white font-bold ${activeTab === "standard" ? "w-[100%]" : "w-[60%]"
                        }`}
                    >
                      {activeTab === "standard" && "100% LOAD"}
                    </div>
                  </div>
                </div>

                {/* CAI Cluster */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400 font-bold">CAI Distributed Cluster (3 Low-End Nodes)</span>
                    <span className="text-brand-green font-bold">160 Watts</span>
                  </div>
                  <div className="h-6 w-full bg-slate-900 rounded border border-white/5 overflow-hidden flex">
                    <div
                      className={`h-full bg-gradient-to-r from-brand-cyan to-brand-green transition-all duration-1000 flex items-center justify-end px-3 text-[10px] text-black font-bold ${activeTab === "CAI" ? "w-[35%] shadow-[0_0_10px_#00ff66]" : "w-[20%]"
                        }`}
                    >
                      {activeTab === "CAI" && "SAVED 64%"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Technical Footnote */}
              <div className="mt-8 pt-6 border-t border-white/5 text-[11px] text-slate-500 space-y-1.5 leading-relaxed">
                <p>• Standard setup relies on 1 x RTX 4090 requiring 450W power draw under constant query loads.</p>
                <p>• CAI setup partitions layers across 2 x 75W consumer GPUs + CPU offloading, keeping total cluster draw at ~160W peak.</p>
                <p>• Accuracy metrics remain mathematically identical (FP16 weights loaded proportionally with zero truncation error).</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
