import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import DEASDiagram from "@/components/DEASDiagram";

export const metadata: Metadata = {
  title: "Energy Efficiency — Cai",
  description: "Cai reduces GPU power draw, energy per token, and cluster carbon footprint through Dynamic Energy-Aware Scheduling (DEAS).",
};

export default function EnergyPage() {
  // Simple custom SVG comparison chart data
  const metrics = [
    { label: "GPU Power Draw", single: 380, Cai: 148, unit: "W", note: "61% less power" },
    { label: "Energy per 1K Tokens", single: 15.6, Cai: 6.2, unit: "Wh", note: "60% less energy" },
    { label: "Peak GPU Temperature", single: 83, Cai: 67, unit: "°C", note: "Cooler sustained workloads" },
    { label: "Carbon Intensity (est.)", single: 124, Cai: 49, unit: "gCO₂eq", note: "60% less carbon per run" },
  ];

  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Energy Efficiency
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Cai doesn&apos;t just distribute inference — it actively optimizes for energy. Every scheduling decision is measured in watts, not just milliseconds.
          </p>
        </div>
      </div>

      {/* Comparison Chart */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-5xl mx-auto px-6 space-y-12">
          <h2 className="text-2xl font-bold text-white text-center">Single GPU vs. Cai Distributed Cluster</h2>

          <div className="space-y-8">
            {metrics.map((m) => {
              const max = Math.max(m.single, m.Cai);
              return (
                <div key={m.label} className="glass-panel p-6 rounded-xl border border-slate-800 space-y-4">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-bold text-white">{m.label}</span>
                    <span className="text-brand-green text-xs font-mono">{m.note}</span>
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-400">Single RTX 4090</span>
                        <span className="text-red-400 font-bold">{m.single} {m.unit}</span>
                      </div>
                      <div className="h-8 bg-slate-900 rounded border border-white/5 overflow-hidden flex items-center relative">
                        <div className="h-full bg-gradient-to-r from-red-900/50 to-red-500/30 border-r border-red-500/50 flex-shrink-0" style={{ width: `${(m.single / max) * 85}%` }} />
                        <span className="absolute left-3 text-xs font-bold text-white/80">Baseline</span>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-400">Cai Cluster (3 Nodes)</span>
                        <span className="text-brand-green font-bold">{m.Cai} {m.unit}</span>
                      </div>
                      <div className="h-8 bg-slate-900 rounded border border-white/5 overflow-hidden flex items-center relative">
                        <div className="h-full bg-gradient-to-r from-brand-cyan/20 to-brand-green/40 border-r border-brand-green/50 shadow-[0_0_10px_rgba(0,255,102,0.1)] flex-shrink-0" style={{ width: `${(m.Cai / max) * 85}%` }} />
                        <span className="absolute left-3 text-xs font-bold text-brand-green">Cai</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-[11px] text-slate-500 font-mono text-center">
            * Placeholder benchmark data. Replace with real NVML telemetry from cai_cli.py benchmark runs.
          </p>
        </div>
      </section>

      {/* DEAS Section */}
      <DEASDiagram />
    </PageLayout>
  );
}
