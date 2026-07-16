import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";

export const metadata: Metadata = {
  title: "Supported Models — Cai",
  description: "See which open-source LLMs Cai supports out of the box, along with VRAM requirements, recommended cluster sizes, and quantization options.",
};

const models = [
  { name: "Llama 2 / 3", org: "meta-llama", sizes: ["7B", "13B", "70B"], vram: { "7B": "14 GB", "13B": "26 GB", "70B": "140 GB" }, nodes: { "7B": 2, "13B": 3, "70B": 8 }, quant: ["FP16", "INT8", "INT4"], status: "Supported" },
  { name: "Mistral", org: "mistralai", sizes: ["7B"], vram: { "7B": "14 GB" }, nodes: { "7B": 2 }, quant: ["FP16", "INT8", "INT4"], status: "Supported" },
  { name: "Qwen 2", org: "Qwen", sizes: ["7B", "14B"], vram: { "7B": "14 GB", "14B": "28 GB" }, nodes: { "7B": 2, "14B": 4 }, quant: ["FP16", "INT8"], status: "Supported" },
  { name: "Phi-2 / Phi-3", org: "microsoft", sizes: ["2.7B", "7B"], vram: { "2.7B": "5.4 GB", "7B": "14 GB" }, nodes: { "2.7B": 1, "7B": 2 }, quant: ["FP16", "INT8", "INT4"], status: "Supported" },
  { name: "Gemma 2", org: "google", sizes: ["2B", "9B", "27B"], vram: { "2B": "4 GB", "9B": "18 GB", "27B": "54 GB" }, nodes: { "2B": 1, "9B": 3, "27B": 6 }, quant: ["FP16", "INT8"], status: "Supported" },
  { name: "GPT-NeoX", org: "EleutherAI", sizes: ["20B"], vram: { "20B": "40 GB" }, nodes: { "20B": 5 }, quant: ["FP16", "INT8"], status: "Supported" },
  { name: "Falcon", org: "tiiuae", sizes: ["7B", "40B"], vram: { "7B": "14 GB", "40B": "80 GB" }, nodes: { "7B": 2, "40B": 10 }, quant: ["FP16", "INT8"], status: "Community" },
  { name: "BLOOM", org: "bigscience", sizes: ["7B", "176B"], vram: { "7B": "14 GB", "176B": "352 GB" }, nodes: { "7B": 2, "176B": 44 }, quant: ["INT8", "INT4"], status: "Community" },
  { name: "OPT", org: "facebook", sizes: ["6.7B", "13B", "30B"], vram: { "6.7B": "13 GB", "13B": "26 GB", "30B": "60 GB" }, nodes: { "6.7B": 2, "13B": 3, "30B": 7 }, quant: ["FP16", "INT8"], status: "Community" },
];

export default function ModelsPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Supported Models
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Cai is compatible with any HuggingFace-format transformer model. These models have been tested and validated with the pipeline parallel runtime.
          </p>
        </div>
      </div>

      <section className="py-24">
        <div className="container max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {models.map((model) => (
              <div key={model.name} className="glass-panel p-6 rounded-xl border border-slate-800 hover:border-brand-cyan/30 transition-all duration-300">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-white font-bold text-base">{model.name}</h3>
                    <p className="text-slate-500 text-[10px] font-mono">{model.org}/...</p>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${model.status === "Supported"
                      ? "border-brand-green/30 text-brand-green bg-brand-green/5"
                      : "border-yellow-500/30 text-yellow-500 bg-yellow-500/5"
                    }`}>
                    {model.status}
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">Available Sizes</p>
                    <div className="flex flex-wrap gap-2">
                      {model.sizes.map((size) => (
                        <div key={size} className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono">
                          <span className="text-white">{size}</span>
                          <span className="text-slate-500 ml-1">/ {(model.vram as Record<string, any>)[size]}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">Quantization</p>
                    <div className="flex flex-wrap gap-1.5">
                      {model.quant.map((q) => (
                        <span key={q} className="px-2 py-0.5 rounded bg-brand-cyan/5 border border-brand-cyan/20 text-[10px] font-mono text-brand-cyan">{q}</span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1.5">Recommended Nodes</p>
                    <div className="flex flex-wrap gap-1.5">
                      {model.sizes.map((size) => (
                        <span key={size} className="text-[10px] font-mono text-slate-400">
                          {size}: <span className="text-white">{(model.nodes as Record<string, any>)[size]} nodes</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
