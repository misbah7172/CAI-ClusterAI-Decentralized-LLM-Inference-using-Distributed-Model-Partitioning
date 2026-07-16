import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import ArchitectureDiagram from "@/components/ArchitectureDiagram";

export const metadata: Metadata = {
  title: "Architecture — Cai Distributed Inference",
  description: "Explore Cai's pipeline parallelism architecture: layer splitting across nodes, gRPC transport, auto-partitioning, and DEAS scheduling.",
};

export default function ArchitecturePage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            System Architecture
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Cai splits models at transformer block boundaries and distributes execution across a gRPC pipeline. No model duplication. No accuracy loss.
          </p>
        </div>
      </div>
      <ArchitectureDiagram />

      {/* Component Details */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-white mb-12 text-center">System Components</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { title: "Cai Studio", desc: "Central management UI. Handles cluster topology, model selection, energy policies, and routes inference requests." },
              { title: "Cai Runtime", desc: "Core inference engine. Manages layer chunking, weight loading, and pipeline execution across distributed nodes." },
              { title: "Sandbox", desc: "Isolated execution context. Simulates multi-node clusters locally on a single machine using loopback gRPC ports." },
              { title: "Node Agent", desc: "Per-machine process that registers nodes, reports GPU/CPU telemetry, accepts layer assignments, and handles layer migration." },
              { title: "Scheduler (DEAS)", desc: "Dynamic Energy-Aware Scheduler. Monitors NVML telemetry, scores node EER, and migrates layers to minimize power draw." },
              { title: "Gateway", desc: "HTTP-to-gRPC bridge. Receives inference requests and chains them through the chunk pipeline, returning streamed tokens." },
              { title: "Monitoring", desc: "NVML DaemonSet. Sub-100ms GPU power sampling, CPU tracking, ring buffers, and power threshold event publishing." },
              { title: "Energy Manager", desc: "Closed-loop PID feedback controller. Continuously adjusts batch size, GPU power limits, and precision based on telemetry." },
              { title: "Model Cache", desc: "Chunk-level weight storage. Each node loads only its assigned layers. Supports quantized (INT4/INT8) weight formats." },
              { title: "Chunk Workers", desc: "Individual gRPC microservices, each running a subset of transformer layers and streaming activations to the next node." },
            ].map((item) => (
              <div key={item.title} className="p-5 rounded-xl border border-slate-900 bg-slate-950/40 hover:border-slate-800 transition-all duration-300">
                <h3 className="text-brand-cyan font-bold font-mono text-sm mb-2">{item.title}</h3>
                <p className="text-slate-400 text-xs font-sans leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
