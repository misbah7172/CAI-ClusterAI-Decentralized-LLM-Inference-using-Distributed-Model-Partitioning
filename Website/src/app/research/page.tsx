import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import { BookOpen, Leaf, Server, Brain, Radio, Globe } from "lucide-react";

export const metadata: Metadata = {
  title: "Research — Cai Green AI Platform",
  description: "Cai is a research platform for energy-efficient AI, sustainable distributed systems, and edge inference. Explore methodologies, benchmarks, and future publications.",
};

const topics = [
  { icon: <Leaf className="w-6 h-6" />, title: "Energy Efficient AI", desc: "Research into minimizing joules-per-token and per-inference watt-hours across heterogeneous consumer hardware clusters.", color: "text-brand-green" },
  { icon: <Globe className="w-6 h-6" />, title: "Green Computing", desc: "Reducing the carbon footprint of large language model inference through power-aware scheduling and hardware diversity.", color: "text-brand-cyan" },
  { icon: <Server className="w-6 h-6" />, title: "Distributed Systems", desc: "gRPC pipeline parallelism, fault-tolerant layer migration, checkpoint-resume protocols, and dynamic partition rebalancing.", color: "text-accent-blue" },
  { icon: <Brain className="w-6 h-6" />, title: "Large Language Models", desc: "Transformer-level partitioning strategies, quantization-aware inference (INT4/INT8/FP16), and auto-regressive generation pipelines.", color: "text-accent-teal" },
  { icon: <Radio className="w-6 h-6" />, title: "Edge AI", desc: "Running multi-billion parameter models on consumer edge hardware: laptops, desktop GPUs, and even CPU-only machines.", color: "text-brand-green" },
  { icon: <BookOpen className="w-6 h-6" />, title: "Sustainable AI Infrastructure", desc: "Volunteer compute networks, hybrid cloud nodes, and community-owned AI clusters as a long-term research direction.", color: "text-brand-cyan" },
];

export default function ResearchPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Research Platform
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Cai is built as a research-grade platform exploring the intersection of distributed computing, energy efficiency, and accessible large-scale AI inference.
          </p>
        </div>
      </div>

      {/* Topics */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-white text-center mb-12">Research Areas</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {topics.map((t) => (
              <div key={t.title} className="p-6 rounded-xl border border-slate-900 bg-slate-950/40 hover:border-brand-cyan/20 transition-all duration-300 group">
                <div className={`${t.color} mb-4 group-hover:scale-110 transition-transform`}>{t.icon}</div>
                <h3 className="text-white font-bold text-base mb-2">{t.title}</h3>
                <p className="text-slate-400 text-sm font-sans leading-relaxed">{t.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benchmark Methodology */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-4xl mx-auto px-6 space-y-8">
          <h2 className="text-2xl font-bold text-white text-center">Benchmark Methodology</h2>
          <div className="glass-panel p-8 rounded-xl border border-slate-800 space-y-6">
            {[
              { title: "Hardware Baseline", text: "Single NVIDIA RTX 4090 at 450W TDP, running inference for identical prompts at FP16 precision using Hugging Face Transformers." },
              { title: "Cai Cluster Setup", text: "3 consumer nodes (RTX 3050 Ti 75W + GTX 1660 80W + CPU 35W). Total cluster TDP: ~190W. Layers partitioned proportionally by VRAM." },
              { title: "Power Measurement", text: "NVML nvidia-smi power samples at 100ms intervals. Trapezoidal integration for energy-per-inference in Wh. 10-run averages reported." },
              { title: "Accuracy Verification", text: "Output logits compared via KL-divergence between single-GPU and Cai distributed runs. No statistically significant divergence observed." },
              { title: "Future Publications", text: "Full benchmark methodology paper targeting conference submission in Q2 2026. Data will be released as open datasets." },
            ].map((item) => (
              <div key={item.title} className="space-y-1">
                <h3 className="text-brand-cyan font-bold font-mono text-sm">{item.title}</h3>
                <p className="text-slate-400 text-sm font-sans leading-relaxed">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
