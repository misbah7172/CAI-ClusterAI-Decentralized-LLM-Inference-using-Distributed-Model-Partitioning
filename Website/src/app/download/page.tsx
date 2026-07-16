import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import { Monitor, Terminal, Container, Cpu } from "lucide-react";

export const metadata: Metadata = {
  title: "Download Cai — Inference Runtime",
  description: "Download Cai Studio for Windows, Linux, or macOS. Or pull the Docker container and CLI for scriptable inference.",
};

const platforms = [
  { icon: <Monitor className="w-8 h-8" />, os: "Windows", ext: ".exe installer", version: "v0.1.0-alpha", note: "Windows 10/11 · CUDA 11.8+ required", color: "text-accent-blue", border: "border-accent-blue/20 hover:border-accent-blue/40" },
  { icon: <Terminal className="w-8 h-8" />, os: "Linux", ext: ".AppImage / .deb", version: "v0.1.0-alpha", note: "Ubuntu 22.04+ · CUDA 12.0+ or CPU-only", color: "text-brand-green", border: "border-brand-green/20 hover:border-brand-green/40" },
  { icon: <Cpu className="w-8 h-8" />, os: "macOS", ext: ".dmg (Apple Silicon)", version: "v0.1.0-alpha", note: "macOS 13+ · CPU inference only (no CUDA)", color: "text-brand-cyan", border: "border-brand-cyan/20 hover:border-brand-cyan/40" },
];

export default function DownloadPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Download Cai
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Get started with the Cai Studio management app, CLI, or Docker runtime. All builds target the same core inference engine.
          </p>
        </div>
      </div>

      {/* Cai Studio Downloads */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-5xl mx-auto px-6 space-y-10">
          <h2 className="text-2xl font-bold text-white text-center">Cai Studio</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {platforms.map((p) => (
              <div key={p.os} className={`glass-panel p-6 rounded-xl border ${p.border} transition-all duration-300 flex flex-col gap-4`}>
                <div className={`${p.color}`}>{p.icon}</div>
                <div>
                  <h3 className="text-white font-bold text-lg">{p.os}</h3>
                  <p className="text-slate-400 text-xs mt-1 font-sans">{p.note}</p>
                </div>
                <div className="mt-auto space-y-2">
                  <p className="text-[10px] font-mono text-slate-500">{p.version} · {p.ext}</p>
                  <a
                    href="https://github.com/misbah7172/GreenCluster-AI-Cai/releases"
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`w-full flex justify-center items-center gap-2 py-2 rounded-lg border ${p.border} ${p.color} text-xs font-mono font-bold hover:bg-white/5 transition-all duration-300`}
                  >
                    Download from GitHub
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Docker & CLI */}
      <section className="py-24 border-b border-slate-900">
        <div className="container max-w-4xl mx-auto px-6 space-y-10">
          <h2 className="text-2xl font-bold text-white text-center">Docker & CLI</h2>

          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3 mb-4">
                <Container className="w-6 h-6 text-accent-blue" />
                <h3 className="text-white font-bold">Docker Container</h3>
              </div>
              <div className="bg-slate-950 rounded-lg border border-white/5 p-4 font-mono text-sm space-y-2">
                <p className="text-slate-400"># Pull the Cai runtime image</p>
                <p className="text-brand-green">docker pull ghcr.io/misbah7172/Cai-runtime:latest</p>
                <p className="text-slate-400 mt-3"># Run a chunk server on port 50051</p>
                <p className="text-brand-cyan">docker run --gpus all -p 50051:50051 Cai-runtime chunk-server --layers 0-7</p>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3 mb-4">
                <Terminal className="w-6 h-6 text-brand-green" />
                <h3 className="text-white font-bold">CLI Quickstart</h3>
              </div>
              <div className="bg-slate-950 rounded-lg border border-white/5 p-4 font-mono text-sm space-y-2">
                <p className="text-slate-400"># Clone the repository</p>
                <p className="text-brand-cyan">git clone https://github.com/misbah7172/GreenCluster-AI-Cai.git && cd GreenCluster-AI-Cai</p>
                <p className="text-slate-400 mt-3"># Install Python dependencies</p>
                <p className="text-brand-cyan">pip install -r requirements.txt</p>
                <p className="text-slate-400 mt-3"># Start sandbox cluster and run inference</p>
                <p className="text-brand-green">python cai_cli.py start --sandbox --num-nodes 3</p>
                <p className="text-brand-green">python cai_cli.py run --model phi-2 --prompt &quot;Explain pipeline parallelism&quot;</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* System Requirements */}
      <section className="py-24">
        <div className="container max-w-4xl mx-auto px-6 space-y-8">
          <h2 className="text-2xl font-bold text-white text-center">System Requirements</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { title: "Minimum (Sandbox Mode)", items: ["CPU: 4-core x86/ARM", "RAM: 8 GB system memory", "Storage: 20 GB free space", "GPU: Optional (CPU-only supported)", "OS: Windows 10 / Ubuntu 22.04 / macOS 13"] },
              { title: "Recommended (Real Cluster)", items: ["GPU: NVIDIA GTX 1060+ (6 GB VRAM)", "RAM: 16 GB per node", "Network: 1 Gbps LAN (100 Mbps min)", "CUDA: 11.8 or 12.x", "NVIDIA driver: 525+"] },
            ].map((req) => (
              <div key={req.title} className="glass-panel p-6 rounded-xl border border-slate-800">
                <h3 className="text-brand-cyan font-bold font-mono text-sm mb-4">{req.title}</h3>
                <ul className="space-y-2">
                  {req.items.map((item) => (
                    <li key={item} className="text-slate-400 text-xs font-sans flex items-start gap-2">
                      <span className="text-brand-green mt-0.5">✓</span>
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
