import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import SandboxSection from "@/components/SandboxSection";
import { Container, Shield, Package, Repeat, Cpu, Globe } from "lucide-react";

export const metadata: Metadata = {
  title: "Sandbox Runtime — Cai",
  description: "Test the full Cai cluster experience on a single laptop before connecting real hardware. Portable, secure, reproducible.",
};

const benefits = [
  { icon: <Package className="w-5 h-5" />, title: "Portable", desc: "Self-contained sandbox runs identically across Windows, Linux, and macOS without dependency conflicts." },
  { icon: <Shield className="w-5 h-5" />, title: "Secure", desc: "Isolated namespace prevents cluster operations from affecting the host OS. GPU passthrough is strictly sandboxed." },
  { icon: <Repeat className="w-5 h-5" />, title: "Reproducible", desc: "Every sandbox session produces identical results. Perfect for benchmarking, CI testing, and experiments." },
  { icon: <Container className="w-5 h-5" />, title: "No Dependency Conflicts", desc: "Containerized runtime installs CUDA, protobuf, and gRPC tools without touching your host Python environment." },
  { icon: <Cpu className="w-5 h-5" />, title: "GPU Passthrough", desc: "Sandbox grants direct access to your NVIDIA GPU via NVML, enabling real power monitoring even in simulation mode." },
  { icon: <Globe className="w-5 h-5" />, title: "Identical Runtime Everywhere", desc: "The same container image runs in sandbox, on bare metal nodes, and inside Kubernetes pods — zero runtime drift." },
];

export default function SandboxPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Sandbox Runtime
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            The biggest barrier to distributed AI is hardware. Cai removes it. Simulate a full multi-node cluster on one laptop, then scale to real nodes — same code, zero changes.
          </p>
        </div>
      </div>

      <SandboxSection />

      {/* Benefits Grid */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-white mb-12 text-center">Why Run Inside a Sandbox?</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {benefits.map((b) => (
              <div key={b.title} className="p-6 rounded-xl border border-slate-900 bg-slate-950/40 hover:border-brand-cyan/20 transition-all duration-300 group">
                <div className="text-brand-cyan mb-4 group-hover:scale-110 transition-transform">{b.icon}</div>
                <h3 className="text-white font-bold text-sm mb-2">{b.title}</h3>
                <p className="text-slate-400 text-xs font-sans leading-relaxed">{b.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Illustration */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-3xl mx-auto px-6 text-center space-y-8">
          <h2 className="text-2xl font-bold text-white">Execution Stack</h2>
          {[
            { label: "Host OS", sub: "Windows / Linux / macOS", color: "border-slate-700 text-slate-300" },
            { label: "Sandbox Runtime", sub: "Containerized gRPC + CUDA environment", color: "border-accent-blue text-accent-blue" },
            { label: "Cai Core", sub: "Scheduler · Chunker · Node Agents · DEAS", color: "border-brand-cyan text-brand-cyan" },
          ].map((layer, idx) => (
            <div key={idx} className="space-y-2">
              <div className={`p-5 rounded-xl border-2 ${layer.color} glass-panel mx-auto`}>
                <p className={`font-bold font-mono text-sm ${layer.color.split(" ")[1]}`}>{layer.label}</p>
                <p className="text-slate-500 text-xs mt-1 font-sans">{layer.sub}</p>
              </div>
              {idx < 2 && <div className="text-slate-600 font-mono text-xl">↓</div>}
            </div>
          ))}
        </div>
      </section>
    </PageLayout>
  );
}
