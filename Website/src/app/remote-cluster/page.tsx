import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import { Shield, Lock, Globe, Server, Wifi, Activity } from "lucide-react";

export const metadata: Metadata = {
  title: "Remote Cluster — Cai Decentralized Networks",
  description: "Connect physical nodes across the globe into a secure, TLS-encrypted Cai inference cluster using secure node IDs and encrypted gRPC channels.",
};

const features = [
  { icon: <Shield className="w-5 h-5" />, title: "Secure Node IDs", desc: "Each physical node receives a cryptographically unique ID. Node registration is verified before admitting to the cluster." },
  { icon: <Lock className="w-5 h-5" />, title: "TLS-Encrypted Channels", desc: "All gRPC communication between pipeline nodes uses TLS mutual authentication. No plaintext inference data in transit." },
  { icon: <Globe className="w-5 h-5" />, title: "Remote Deployment", desc: "Deploy chunk server processes on remote machines via SSH scripting. The scheduler handles layer assignment automatically." },
  { icon: <Server className="w-5 h-5" />, title: "Cluster Management", desc: "Add, remove, or migrate nodes from the Cai Studio UI without restarting the inference session." },
  { icon: <Wifi className="w-5 h-5" />, title: "Node Health Monitoring", desc: "Continuous health pings (default 5s interval). Unresponsive nodes are automatically detected and trigger DEAS migration." },
  { icon: <Activity className="w-5 h-5" />, title: "Encrypted Communication", desc: "Activation tensors between pipeline nodes are serialized as binary blobs over encrypted gRPC streams — no raw weight exposure." },
];

// Stylized world map with pulsing node dots
function WorldMap() {
  const nodes = [
    { x: "18%", y: "35%", label: "US-East" },
    { x: "30%", y: "28%", label: "EU-West" },
    { x: "48%", y: "42%", label: "ME" },
    { x: "62%", y: "30%", label: "India" },
    { x: "75%", y: "38%", label: "SEA" },
    { x: "85%", y: "55%", label: "AU" },
  ];

  return (
    <div className="relative w-full h-64 glass-panel rounded-xl border border-slate-800 overflow-hidden">
      {/* Background grid dots */}
      <div className="absolute inset-0 circuit-dots opacity-20" />

      {/* Connection lines */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line x1="18" y1="35" x2="30" y2="28" stroke="rgba(0,240,255,0.15)" strokeWidth="0.2" strokeDasharray="0.5 0.5" />
        <line x1="30" y1="28" x2="48" y2="42" stroke="rgba(0,240,255,0.15)" strokeWidth="0.2" strokeDasharray="0.5 0.5" />
        <line x1="48" y1="42" x2="62" y2="30" stroke="rgba(0,240,255,0.15)" strokeWidth="0.2" strokeDasharray="0.5 0.5" />
        <line x1="62" y1="30" x2="75" y2="38" stroke="rgba(0,240,255,0.15)" strokeWidth="0.2" strokeDasharray="0.5 0.5" />
        <line x1="75" y1="38" x2="85" y2="55" stroke="rgba(0,240,255,0.15)" strokeWidth="0.2" strokeDasharray="0.5 0.5" />
      </svg>

      {nodes.map((node, idx) => (
        <div
          key={idx}
          className="absolute flex flex-col items-center"
          style={{ left: node.x, top: node.y, transform: "translate(-50%, -50%)" }}
        >
          <div className="relative">
            <div className="w-3 h-3 rounded-full bg-brand-cyan shadow-[0_0_10px_rgba(0,240,255,0.8)] z-10 relative" />
            <div className="absolute inset-0 rounded-full bg-brand-cyan/30 animate-ping" />
          </div>
          <span className="text-[8px] font-mono text-brand-cyan/70 mt-1 whitespace-nowrap">{node.label}</span>
        </div>
      ))}

      <div className="absolute bottom-3 left-3 text-[10px] font-mono text-slate-500">
        6 nodes · 5 connections · All TLS
      </div>
    </div>
  );
}

export default function RemoteClusterPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Remote Cluster
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Connect machines across the internet into a unified, secure inference cluster. Cai handles node registration, encrypted transport, and automatic failover.
          </p>
        </div>
      </div>

      {/* World Map */}
      <section className="py-16 border-b border-slate-900">
        <div className="container max-w-4xl mx-auto px-6 space-y-6">
          <h2 className="text-xl font-bold text-white text-center">Globally Distributed Node Network</h2>
          <WorldMap />
        </div>
      </section>

      {/* Features */}
      <section className="py-24">
        <div className="container max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="p-6 rounded-xl border border-slate-900 bg-slate-950/40 hover:border-brand-cyan/20 transition-all duration-300 group">
                <div className="text-brand-cyan mb-4 group-hover:scale-110 transition-transform">{f.icon}</div>
                <h3 className="text-white font-bold text-sm mb-2">{f.title}</h3>
                <p className="text-slate-400 text-xs font-sans leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
