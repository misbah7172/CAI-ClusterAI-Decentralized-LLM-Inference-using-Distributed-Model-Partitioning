import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";

export const metadata: Metadata = {
  title: "Cai Studio — Cluster Management App",
  description: "Cai Studio is the central management application for controlling your distributed inference cluster, models, and energy policies.",
};

const screens = [
  {
    id: "dashboard",
    label: "Dashboard",
    content: {
      title: "Cluster Overview Dashboard",
      items: ["Active nodes: 3/3", "Model: microsoft/phi-2", "Cluster power: 118W", "Energy saved: 61%", "Inference rate: 47 tok/s", "DEAS scheduler: ACTIVE"],
    },
  },
  {
    id: "cluster",
    label: "Cluster View",
    content: {
      title: "Node Topology",
      items: ["Node-0 (RTX 3050 Ti) — Layers 0-7 — ONLINE", "Node-1 (GTX 1660) — Layers 8-19 — ONLINE", "Node-2 (CPU RAM) — Layers 20-31 — ONLINE", "gRPC latency: 0.38ms avg", "Pipeline health: OPTIMAL"],
    },
  },
  {
    id: "nodes",
    label: "Node Monitor",
    content: {
      title: "Real-Time Node Telemetry",
      items: ["GPU util: 72%", "GPU temp: 67°C", "Power draw: 78W", "VRAM: 3.8/4.0 GB", "CPU: 24%", "Memory: 2.2/16.0 GB"],
    },
  },
  {
    id: "models",
    label: "Model Library",
    content: {
      title: "Available Models",
      items: ["microsoft/phi-2 (2.7B) — 3 chunks — LOADED", "mistralai/Mistral-7B (7B) — 4 chunks — CACHED", "meta-llama/Llama-2-13B — 6 chunks — NOT LOADED", "Qwen/Qwen2-7B — 4 chunks — CACHED"],
    },
  },
  {
    id: "power",
    label: "Power Monitor",
    content: {
      title: "Energy Instrumentation",
      items: ["Sampling rate: 100ms", "Ring buffer: 512 samples", "TDP auto-detected: 75W (RTX 3050 Ti)", "Power threshold: 70W (93.3% TDP)", "EER score: 2.14", "Energy events: 0 alerts"],
    },
  },
  {
    id: "topology",
    label: "Topology Graph",
    content: {
      title: "Visual Pipeline Map",
      items: ["Gateway → Node-0 (gRPC:50051)", "Node-0 → Node-1 (gRPC:50052)", "Node-1 → Node-2 (gRPC:50053)", "Node-2 → Gateway (HTTP response)", "All channels: ENCRYPTED TLS"],
    },
  },
  {
    id: "scheduler",
    label: "Scheduler",
    content: {
      title: "DEAS Scheduler Config",
      items: ["Strategy: cost-aware + EER", "Cooldown: 30s adaptive", "Migration threshold: 2.14 EER", "Top-K plans: 3", "Precision mode: AUTO (FP16/INT8)", "Batch size: ADAPTIVE"],
    },
  },
];

export default function StudioPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Cai Studio
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            The central management application for your distributed inference cluster. Monitor nodes, manage models, tune the energy scheduler, and inspect the pipeline topology — all in one place.
          </p>
        </div>
      </div>

      {/* Screen Tabs — server rendered as grid of panels */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 space-y-8">
          <h2 className="text-2xl font-bold text-white text-center">Dashboard Screens</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {screens.map((screen) => (
              <div key={screen.id} className="glass-panel p-5 rounded-xl border border-slate-800 hover:border-brand-cyan/30 transition-all duration-300">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{screen.label}</p>
                  <span className="w-2 h-2 rounded-full bg-brand-green animate-pulse" />
                </div>
                <h3 className="text-white font-bold text-sm mb-3">{screen.content.title}</h3>
                <ul className="space-y-1.5">
                  {screen.content.items.map((item) => (
                    <li key={item} className="text-[11px] font-mono text-slate-400 flex items-start gap-2">
                      <span className="text-brand-cyan mt-0.5 flex-shrink-0">›</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
