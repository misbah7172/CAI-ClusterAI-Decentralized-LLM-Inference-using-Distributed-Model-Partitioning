"use client";

import { useState } from "react";
import { Laptop, Cpu, Terminal, Network, Info } from "lucide-react";

export default function SandboxSection() {
  const [mode, setMode] = useState<"sandbox" | "cluster">("sandbox");

  return (
    <section className="py-24 relative overflow-hidden bg-bg-dark border-b border-slate-900">
      <div className="absolute inset-0 circuit-dots opacity-10 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">

        {/* Header */}
        <div className="max-w-3xl mx-auto text-center mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-brand-cyan/30 text-brand-cyan text-xs font-mono uppercase tracking-wider">
            <Laptop className="w-3.5 h-3.5" /> ZERO HARDWARE FRICTION
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Seamless Local Sandbox Simulation
          </h2>
          <p className="text-slate-400 text-lg">
            Adopting distributed systems is hard. CAI removes the barrier by letting you simulate a full multi-node cluster on a single laptop before deployment.
          </p>
        </div>

        {/* Layout Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">

          {/* Left Side: Features and Command Mockup */}
          <div className="lg:col-span-6 space-y-6">
            <div className="space-y-4">
              <h3 className="text-2xl font-bold text-white leading-tight">
                Simulate Before Deploying
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                CAI&apo;s Sandbox Mode spins up multiple virtual gRPC chunk servers bound to local ports. You can scan virtual RAM budgets, draft auto-partition schemas, and debug pipeline serialization overhead locally.
              </p>
            </div>

            {/* Selector Toggles */}
            <div className="flex gap-4">
              <button
                onClick={() => setMode("sandbox")}
                className={`flex-1 p-4 rounded-xl border text-left transition-all duration-300 font-sans ${mode === "sandbox"
                  ? "border-brand-cyan bg-slate-900/60 shadow-[0_0_15px_rgba(0,240,255,0.05)]"
                  : "border-slate-800 bg-slate-950/40 opacity-70 hover:opacity-100"
                  }`}
              >
                <div className="font-bold text-white text-sm mb-1 flex items-center gap-2">
                  <Laptop className="w-4 h-4 text-brand-cyan" /> Sandbox Mode
                </div>
                <span className="text-slate-400 text-xs font-mono">1 Laptop, 3 Virtual Nodes</span>
              </button>

              <button
                onClick={() => setMode("cluster")}
                className={`flex-1 p-4 rounded-xl border text-left transition-all duration-300 font-sans ${mode === "cluster"
                  ? "border-brand-cyan bg-slate-900/60 shadow-[0_0_15px_rgba(0,240,255,0.05)]"
                  : "border-slate-800 bg-slate-950/40 opacity-70 hover:opacity-100"
                  }`}
              >
                <div className="font-bold text-white text-sm mb-1 flex items-center gap-2">
                  <Network className="w-4 h-4 text-brand-cyan" /> Real Cluster
                </div>
                <span className="text-slate-400 text-xs font-mono">3 Physical GPUs / Nodes</span>
              </button>
            </div>

            {/* Terminal Block */}
            <div className="relative glass-panel rounded-xl border border-slate-800 overflow-hidden bg-slate-950/80">
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-slate-950">
                <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-brand-cyan" /> TERMINAL
                </span>
                <span className="text-[10px] text-slate-600 font-mono">powershell</span>
              </div>
              <div className="p-4 font-mono text-xs text-slate-300 space-y-2 select-all">
                {mode === "sandbox" ? (
                  <>
                    <p className="text-slate-500"># Run local multi-container sandbox cluster simulation</p>
                    <p className="text-white">
                      <span className="text-brand-cyan">python</span> cai_cli.py partition --model microsoft/phi-2 --num-nodes 3
                    </p>
                    <p className="text-slate-500"># Spawning virtual nodes on localhost:50051-50053...</p>
                    <p className="text-brand-green">✓ Partition verified. Active pipeline: Node[0-2] online.</p>
                  </>
                ) : (
                  <>
                    <p className="text-slate-500"># Deploy model chunks to active Kubernetes nodes</p>
                    <p className="text-white">
                      <span className="text-brand-cyan">python</span> -m kubernetes.controller deploy --num-chunks 3 --model phi-2
                    </p>
                    <p className="text-slate-500"># Connecting to cluster context...</p>
                    <p className="text-brand-green">✓ Deployed 3 chunk pods + gateway node successfully.</p>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Side: Graphic Visual of Mode */}
          <div className="lg:col-span-6 flex items-center justify-center min-h-[300px]">
            <div className="relative w-full max-w-[420px] p-6 glass-panel rounded-xl border border-white/5 bg-slate-950/40 text-center font-mono">
              <div className="mb-6 flex justify-between items-center border-b border-white/5 pb-3">
                <span className="text-xs text-slate-500 uppercase">ACTIVE CONFIGURATION</span>
                <span className="text-[10px] text-brand-cyan px-2 py-0.5 rounded bg-brand-cyan/5 border border-brand-cyan/20">
                  {mode === "sandbox" ? "SIMULATION" : "K8S ORCHESTRATION"}
                </span>
              </div>

              {/* Graphical Layout */}
              <div className="py-8 flex flex-col items-center justify-center relative min-h-[160px]">
                {mode === "sandbox" ? (
                  // Sandbox Laptop splitting to 3 virtual nodes
                  <div className="space-y-6 w-full flex flex-col items-center">
                    <Laptop className="w-16 h-16 text-brand-cyan animate-pulse" />

                    {/* Simulated split blocks */}
                    <div className="flex justify-center gap-3 w-full">
                      <div className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                        <p className="text-brand-cyan">localhost:50051</p>
                        <p className="text-[9px] text-slate-500 mt-0.5">Virtual Node 1</p>
                      </div>
                      <div className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                        <p className="text-brand-cyan">localhost:50052</p>
                        <p className="text-[9px] text-slate-500 mt-0.5">Virtual Node 2</p>
                      </div>
                      <div className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                        <p className="text-brand-green">localhost:50053</p>
                        <p className="text-[9px] text-slate-500 mt-0.5">Virtual Node 3 (CPU)</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Real Cluster - 3 distinct physical devices connected by dotted links
                  <div className="flex flex-col items-center space-y-4 w-full">
                    <div className="flex justify-around w-full items-center">
                      <div className="flex flex-col items-center space-y-1">
                        <Cpu className="w-10 h-10 text-brand-cyan" />
                        <span className="text-[9px] text-slate-300">PC-A [GPU0]</span>
                      </div>
                      <div className="w-8 border-t border-dashed border-brand-cyan/40" />
                      <div className="flex flex-col items-center space-y-1">
                        <Cpu className="w-10 h-10 text-brand-cyan" />
                        <span className="text-[9px] text-slate-300">PC-B [GPU1]</span>
                      </div>
                      <div className="w-8 border-t border-dashed border-brand-cyan/40" />
                      <div className="flex flex-col items-center space-y-1">
                        <Cpu className="w-10 h-10 text-brand-green" />
                        <span className="text-[9px] text-slate-300">PC-C [CPU]</span>
                      </div>
                    </div>

                    <div className="text-slate-500 text-[10px] pt-4">
                      Connected across local subnets using gRPC interfaces.
                    </div>
                  </div>
                )}
              </div>

              {/* Info text box */}
              <div className="mt-4 p-3 rounded bg-slate-950 border border-white/5 text-[10px] text-left text-slate-400 flex gap-2">
                <Info className="w-4 h-4 text-brand-cyan shrink-0" />
                <span>
                  {mode === "sandbox"
                    ? "Sandbox utilizes ports 50051–50053 on loopback. Network serialization matches 100% with production cluster constraints."
                    : "Kubernetes coordinates worker status, power threshold notifications, and coordinates migrations automatically."
                  }
                </span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
