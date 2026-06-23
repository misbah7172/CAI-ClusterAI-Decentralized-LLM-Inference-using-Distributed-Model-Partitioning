"use client";

import { useState } from "react";
import { Layers, Network, Server, Play } from "lucide-react";

export default function ArchitectureDiagram() {
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);

  return (
    <section id="architecture" className="py-24 relative overflow-hidden bg-bg-dark border-b border-slate-900 scroll-mt-12">
      <div className="absolute inset-0 circuit-dots opacity-10 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">

        {/* Title */}
        <div className="max-w-3xl mx-auto text-center mb-16 space-y-4">
          <div className="inline-flex items-center gap-1 text-accent-blue text-xs font-mono tracking-wider uppercase">
            <Network className="w-4.5 h-4.5" /> Pipeline Parallelism
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            How CAI Works: Layer-Wise Pipeline
          </h2>
          <p className="text-slate-400 text-lg">
            CAI partitions massive neural network models at transformer block boundaries. Each node only loads and executes its assigned subset of layers.
          </p>
        </div>

        {/* Pipeline Diagram (Grid/Visual Layout) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch mb-12">

          {/* Card: Input Model */}
          <div className="lg:col-span-3 flex flex-col justify-center">
            <div className="glass-panel p-6 rounded-xl border-slate-800 bg-slate-950/60 space-y-4 text-center h-full flex flex-col justify-between">
              <div className="space-y-4">
                <div className="mx-auto w-12 h-12 rounded-lg bg-accent-blue/10 flex items-center justify-center text-accent-blue">
                  <Layers className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-lg font-bold text-white">Full LLM Model</h3>
                  <p className="text-slate-400 text-xs font-mono">e.g. Phi-2 (32 Layers)</p>
                </div>
                <p className="text-slate-500 text-xs leading-relaxed">
                  The model layers are extracted at startup. Instead of loading all weights to one GPU, CAI prepares them for pipeline chunking.
                </p>
              </div>

              {/* Dynamic status */}
              <div className="pt-4 border-t border-white/5 font-mono text-[10px] text-accent-blue">
                AUTO-PARTITIONER ACTIVE
              </div>
            </div>
          </div>

          {/* Core Pipeline Nodes */}
          <div className="lg:col-span-9 flex flex-col justify-between">
            <div className="glass-panel p-6 md:p-8 rounded-xl border-slate-800 bg-slate-950/60 h-full flex flex-col justify-between">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative">

                {/* SVG Connections for Desktop (Visible on md+) */}
                <div className="hidden md:block absolute top-[50px] left-[15%] right-[15%] h-[4px] bg-slate-900 -z-10 overflow-hidden">
                  <div className="w-[200%] h-full bg-gradient-to-r from-transparent via-brand-cyan to-transparent animate-dash"
                    style={{
                      backgroundImage: "linear-gradient(to right, rgba(0, 240, 255, 0.8) 0%, rgba(0, 255, 102, 0.8) 50%, rgba(0, 240, 255, 0.8) 100%)",
                      backgroundSize: "50% 100%",
                      animation: "dash 4s linear infinite"
                    }}
                  />
                </div>

                {/* Node 1 */}
                <div
                  className={`w-full md:w-[28%] p-4 rounded-xl border transition-all duration-300 ${hoveredNode === 1
                      ? "border-brand-cyan bg-slate-900/60 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                      : "border-slate-800 bg-slate-950/80"
                    }`}
                  onMouseEnter={() => setHoveredNode(1)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono text-slate-500">NODE 01</span>
                    <span className="w-2 h-2 rounded-full bg-brand-cyan animate-pulse" />
                  </div>
                  <h4 className="text-white font-bold text-sm mb-1 flex items-center gap-1.5">
                    <Server className="w-4 h-4 text-brand-cyan" /> RTX 3050 Ti
                  </h4>
                  <div className="font-mono text-xs text-brand-cyan bg-brand-cyan/5 border border-brand-cyan/15 rounded p-1.5 text-center mt-2">
                    Layers 00 - 07
                  </div>
                  <p className="text-[10px] text-slate-500 mt-2 font-mono">VRAM: 3.8 GB / 4.0 GB</p>
                </div>

                {/* Node 2 */}
                <div
                  className={`w-full md:w-[28%] p-4 rounded-xl border transition-all duration-300 ${hoveredNode === 2
                      ? "border-brand-cyan bg-slate-900/60 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                      : "border-slate-800 bg-slate-950/80"
                    }`}
                  onMouseEnter={() => setHoveredNode(2)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono text-slate-500">NODE 02</span>
                    <span className="w-2 h-2 rounded-full bg-brand-cyan animate-pulse" />
                  </div>
                  <h4 className="text-white font-bold text-sm mb-1 flex items-center gap-1.5">
                    <Server className="w-4 h-4 text-brand-cyan" /> GTX 1660
                  </h4>
                  <div className="font-mono text-xs text-brand-cyan bg-brand-cyan/5 border border-brand-cyan/15 rounded p-1.5 text-center mt-2">
                    Layers 08 - 19
                  </div>
                  <p className="text-[10px] text-slate-500 mt-2 font-mono">VRAM: 5.6 GB / 6.0 GB</p>
                </div>

                {/* Node 3 */}
                <div
                  className={`w-full md:w-[28%] p-4 rounded-xl border transition-all duration-300 ${hoveredNode === 3
                      ? "border-brand-green bg-slate-900/60 shadow-[0_0_15px_rgba(0,255,102,0.15)]"
                      : "border-slate-800 bg-slate-950/80"
                    }`}
                  onMouseEnter={() => setHoveredNode(3)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono text-slate-500">NODE 03 (CPU)</span>
                    <span className="w-2 h-2 rounded-full bg-brand-green animate-pulse" />
                  </div>
                  <h4 className="text-white font-bold text-sm mb-1 flex items-center gap-1.5">
                    <Server className="w-4 h-4 text-brand-green" /> System RAM
                  </h4>
                  <div className="font-mono text-xs text-brand-green bg-brand-green/5 border border-brand-green/15 rounded p-1.5 text-center mt-2">
                    Layers 20 - 31
                  </div>
                  <p className="text-[10px] text-slate-500 mt-2 font-mono">RAM: 2.2 GB / 16.0 GB</p>
                </div>

              </div>

              {/* Step Descriptions based on hover */}
              <div className="mt-8 p-4 rounded-lg bg-slate-950 border border-white/5 min-h-[90px] flex items-center">
                {hoveredNode === null && (
                  <p className="text-slate-400 text-xs leading-relaxed flex items-center gap-2">
                    <Play className="w-4 h-4 text-brand-cyan animate-pulse shrink-0" /> Hover over a node block to view gRPC pipeline execution metrics and system role details.
                  </p>
                )}
                {hoveredNode === 1 && (
                  <div className="space-y-1">
                    <p className="text-white font-bold text-xs uppercase text-brand-cyan font-mono">Node 01 — Pipeline Gateway & Initial Embeddings</p>
                    <p className="text-slate-400 text-xs leading-relaxed">
                      Loads model embedding layer and transformer layers 0 to 7. Receives inputs via HTTP and streams token tensor computations to Node 02 using gRPC interfaces.
                    </p>
                  </div>
                )}
                {hoveredNode === 2 && (
                  <div className="space-y-1">
                    <p className="text-white font-bold text-xs uppercase text-brand-cyan font-mono">Node 02 — Pipeline Intermediate Chunk Processor</p>
                    <p className="text-slate-400 text-xs leading-relaxed">
                      Loads layers 8 to 19. Highly optimized with pynvml telemetry, listening on a gRPC port. Emits processed tensors downstream.
                    </p>
                  </div>
                )}
                {hoveredNode === 3 && (
                  <div className="space-y-1">
                    <p className="text-white font-bold text-xs uppercase text-brand-green font-mono">Node 03 — CPU Offloading & Output Generation</p>
                    <p className="text-slate-400 text-xs leading-relaxed">
                      Runs the final chunk (layers 20 to 31) plus the Output LM Head. Uses double-buffered prefetching to run layers in RAM, avoiding GPU OOM, and streams tokens back to the client.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>

        {/* Small descriptive text footer */}
        <div className="text-center font-mono text-[10px] text-slate-500">
          *COMMUNICATION LAYER OVERHEAD IN CAI STAYS BELOW 0.38MS VIA HIGH-FREQUENCY CACHED LATENCY PROBES.
        </div>
      </div>
    </section>
  );
}
