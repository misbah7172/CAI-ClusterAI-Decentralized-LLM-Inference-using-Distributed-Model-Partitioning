"use client";

import { Calendar, CheckCircle2, Circle, Clock, GitMerge } from "lucide-react";

export default function Roadmap() {
  const items = [
    {
      quarter: "PHASE 1 - 20 (Q1 2026)",
      title: "Core Sandbox CLI & Instrumentation",
      status: "completed",
      description: "Implemented layer-wise transformer splitting, high-frequency pynvml GPU telemetry, async event buses, and a command line launcher for local multi-node simulation.",
    },
    {
      quarter: "PHASE 21 - 24 (Q2 2026)",
      title: "Closed-Loop Energy Feedback Controller",
      status: "completed",
      description: "Added predictive Dynamic Energy-Aware Scheduling (DEAS), PID feedback controller, dynamic batch adjustment, runtime precision managers (FP16 ↔ INT8), and speculative decoding.",
    },
    {
      quarter: "PHASE 25 (CURRENT)",
      title: "ILP / Heuristics Model Placement",
      status: "active",
      description: "Building production-grade scheduler with multi-criteria worker selection (FCIM), Jain's fairness indexes, anti-affinity, and hybrid ILP+heuristic solving for large deployments.",
    },
    {
      quarter: "PHASE 26 (Q4 2026)",
      title: "Fault-Tolerant Node Agent Daemon",
      status: "planned",
      description: "Developing automatic pipeline failure detection, checkpoint-based recovery, and dynamic gRPC route relinking to reassign layers to healthy nodes without output corruption.",
    },
    {
      quarter: "FUTURE (2027)",
      title: "CAI Desktop Client",
      status: "planned",
      description: "Designing a turn-key graphical desktop client to easily connect idle consumer hardware into shared sustainable inference pools.",
    }
  ];

  return (
    <section className="py-24 relative overflow-hidden bg-bg-dark border-b border-slate-900">
      <div className="absolute inset-0 circuit-dots opacity-10 pointer-events-none" />

      <div className="container max-w-5xl mx-auto px-6 relative z-10">

        {/* Header */}
        <div className="max-w-3xl mx-auto text-center mb-20 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-accent-blue/30 text-accent-blue text-xs font-mono uppercase tracking-wider">
            <GitMerge className="w-3.5 h-3.5" /> Project Evolution
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Engineering & Systems Research Roadmap
          </h2>
          <p className="text-slate-400 text-lg font-sans">
            CAI is an evolving research project aimed at reducing the carbon and financial footprints of generative AI. Follow our milestones.
          </p>
        </div>

        {/* Timeline Layout */}
        <div className="relative border-l border-slate-800 ml-4 md:ml-32 space-y-12">
          {items.map((item, idx) => {
            const isCompleted = item.status === "completed";
            const isActive = item.status === "active";

            return (
              <div key={idx} className="relative pl-8 md:pl-12 group">

                {/* Quarter Tag for Desktop */}
                <div className="hidden md:block absolute right-full mr-8 top-1.5 text-right w-44">
                  <span className={`text-xs font-mono font-bold tracking-wider uppercase ${isCompleted ? "text-slate-500" : isActive ? "text-brand-cyan" : "text-slate-600"
                    }`}>
                    {item.quarter}
                  </span>
                </div>

                {/* Timeline node icon */}
                <div className="absolute left-0 -translate-x-1/2 top-1.5 z-10">
                  {isCompleted ? (
                    <div className="w-6 h-6 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center text-brand-green bg-bg-dark">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  ) : isActive ? (
                    <div className="w-6 h-6 rounded-full bg-slate-950 border border-brand-cyan flex items-center justify-center text-brand-cyan bg-bg-dark shadow-[0_0_10px_#00f0ff]">
                      <Clock className="w-4 h-4 animate-pulse" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-600 bg-bg-dark">
                      <Circle className="w-4 h-4" />
                    </div>
                  )}
                </div>

                {/* Content Block */}
                <div className={`p-6 rounded-xl border transition-all duration-300 ${isActive
                    ? "border-brand-cyan bg-slate-900/40 shadow-[0_0_15px_rgba(0,240,255,0.05)]"
                    : "border-slate-900 bg-slate-950/20 hover:border-slate-800"
                  }`}>
                  {/* Mobile Quarter Tag */}
                  <span className="block md:hidden text-[10px] font-mono font-bold text-slate-500 mb-2 uppercase">
                    {item.quarter}
                  </span>

                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <h3 className="text-base font-bold text-white group-hover:text-brand-cyan transition-colors duration-300">
                      {item.title}
                    </h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase border ${isCompleted
                        ? "bg-slate-900 border-slate-800 text-slate-400"
                        : isActive
                          ? "bg-brand-cyan/10 border-brand-cyan/20 text-brand-cyan"
                          : "bg-slate-950 border-slate-900 text-slate-600"
                      }`}>
                      {item.status}
                    </span>
                  </div>

                  <p className="text-slate-400 text-xs md:text-sm leading-relaxed font-sans">
                    {item.description}
                  </p>
                </div>

              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
