import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";

export const metadata: Metadata = {
  title: "Distributed AI — Cai Pipeline Parallelism",
  description: "Understand how Cai partitions models, assigns layers, executes pipeline inference, migrates chunks, and streams tokens across nodes.",
};

const concepts = [
  {
    title: "Model Partitioning",
    detail: "Cai's HFModelLoader extracts each transformer block's parameters without loading full weights. AutoPartitioner assigns layers proportionally based on node VRAM and RAM budgets.",
    mono: "cai_cli.py partition --model phi-2 --num-nodes 3",
  },
  {
    title: "Layer Assignment",
    detail: "ResourceDetector scans each node's GPU VRAM, system RAM, and CPU cores. Layers are assigned in contiguous blocks: Node-0 gets Layers 0-7, Node-1 gets 8-19, Node-2 gets 20-31.",
    mono: "cai_cli.py scan  →  Auto-partitioned into 3 chunks",
  },
  {
    title: "Pipeline Execution",
    detail: "The DistributedGenerator chains chunk gRPC microservices in sequence. Node-0 computes its layers and streams activations to Node-1 via binary tensor serialization, then to Node-2.",
    mono: "gRPC: Chunk-0 → Chunk-1 → Chunk-2 → Gateway",
  },
  {
    title: "Chunk Migration",
    detail: "If a node becomes overloaded, DEAS triggers Pause → Checkpoint → Migrate → Relink → Resume. Active pipeline weights are serialized, transferred, and reloaded on a healthier node without output corruption.",
    mono: "DEAS EER threshold: 2.14 → migration triggered",
  },
  {
    title: "Checkpointing",
    detail: "Before migration, each chunk server serializes its current layer weights and optimizer state to a checkpoint file. The target node resumes from the same position in the sequence.",
    mono: "Checkpoint saved: /tmp/cai_chunk1_ckpt.pt",
  },
  {
    title: "Streaming Inference",
    detail: "Tokens stream back to the client as they are generated — no need to wait for the full sequence. Cai uses autoregressive generation with temperature, top-k, top-p sampling identically to single-GPU runs.",
    mono: "cai_cli.py run --stream --max-tokens 200",
  },
];

export default function DistributedAIPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Distributed AI Inference
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Cai uses pipeline parallelism to split transformer models across nodes. Each node executes only the layers it owns, reducing VRAM requirements and total power draw.
          </p>
        </div>
      </div>

      {/* Concepts */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-5xl mx-auto px-6 space-y-6">
          {concepts.map((c, idx) => (
            <div key={idx} className="glass-panel p-6 rounded-xl border border-slate-800 hover:border-brand-cyan/20 transition-all duration-300 grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
              <div className="md:col-span-1 text-brand-cyan font-mono font-bold text-lg">{String(idx + 1).padStart(2, "0")}</div>
              <div className="md:col-span-7 space-y-2">
                <h3 className="text-white font-bold text-base">{c.title}</h3>
                <p className="text-slate-400 text-sm font-sans leading-relaxed">{c.detail}</p>
              </div>
              <div className="md:col-span-4">
                <div className="p-3 rounded-lg bg-slate-950 border border-white/5 font-mono text-[10px] text-brand-green leading-relaxed">
                  {c.mono}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Animated Pipeline Visual */}
      <section className="py-24">
        <div className="container max-w-5xl mx-auto px-6 text-center space-y-12">
          <h2 className="text-2xl font-bold text-white">Pipeline Data Flow</h2>
          <div className="flex flex-wrap justify-center items-center gap-3 font-mono text-sm">
            {["Input Tokens", "Embedding Layer", "Node-0 (Layers 0-7)", "gRPC →", "Node-1 (Layers 8-19)", "gRPC →", "Node-2 (Layers 20-31)", "LM Head", "Streaming Output"].map((step, idx) => (
              <div key={idx} className={`px-4 py-2 rounded-lg border ${step === "gRPC →"
                ? "border-transparent text-brand-cyan text-xs"
                : idx === 8
                  ? "border-brand-green/40 bg-brand-green/5 text-brand-green"
                  : "border-slate-800 bg-slate-950/60 text-slate-300"
                }`}>
                {step}
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
