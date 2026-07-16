"use client";

import { useState } from "react";
import { User, Monitor, Container, Cpu, Server, MessageSquare, CheckCircle } from "lucide-react";

const steps = [
  {
    icon: <User className="w-5 h-5" />,
    label: "User",
    desc: "Sends a query to the CAI gateway — either via CLI, HTTP API, or CAI Studio UI.",
    color: "text-slate-300",
    accent: "border-slate-600",
  },
  {
    icon: <Monitor className="w-5 h-5" />,
    label: "CAI Studio",
    desc: "Central management app handles cluster topology, model selection, energy policies, and routes the request.",
    color: "text-brand-cyan",
    accent: "border-brand-cyan",
  },
  {
    icon: <Container className="w-5 h-5" />,
    label: "Sandbox Runtime",
    desc: "Sandboxed execution context validates inputs, enforces isolation policies, and initializes the pipeline session.",
    color: "text-accent-blue",
    accent: "border-accent-blue",
  },
  {
    icon: <Cpu className="w-5 h-5" />,
    label: "CAI Agent",
    desc: "The DEAS scheduler assigns layers to available nodes, monitors power, and adjusts batch size and precision in real time.",
    color: "text-accent-teal",
    accent: "border-accent-teal",
  },
  {
    icon: <Server className="w-5 h-5" />,
    label: "Distributed Nodes",
    desc: "Each node executes its assigned transformer layers via gRPC, streams partial activations to the next node in the pipeline.",
    color: "text-brand-green",
    accent: "border-brand-green",
  },
  {
    icon: <CheckCircle className="w-5 h-5" />,
    label: "Model Execution",
    desc: "The final node generates output tokens. The LM head produces logits, samples the next token, and passes it back upstream.",
    color: "text-brand-green",
    accent: "border-brand-green",
  },
  {
    icon: <MessageSquare className="w-5 h-5" />,
    label: "Streaming Response",
    desc: "Tokens stream back to the client in real time — no waiting for the full response. Same quality as a single-GPU run.",
    color: "text-brand-cyan",
    accent: "border-brand-cyan",
  },
];

export default function HowItWorks() {
  const [active, setActive] = useState<number | null>(null);

  return (
    <section className="py-24 relative overflow-hidden bg-slate-950/30 border-b border-slate-900">
      <div className="container max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-accent-blue/30 text-accent-blue text-xs font-mono uppercase tracking-wider">
            <Server className="w-3.5 h-3.5" /> End-to-End Flow
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">How CAI Works</h2>
          <p className="text-slate-400 text-lg font-sans">
            From query to response, every step is optimized for energy efficiency and distributed throughput.
          </p>
        </div>

        <div className="max-w-3xl mx-auto">
          <div className="relative">
            {/* Vertical Line */}
            <div className="absolute left-6 top-0 bottom-0 w-px bg-gradient-to-b from-brand-cyan via-brand-green to-slate-800" />

            <div className="space-y-2">
              {steps.map((step, idx) => (
                <div
                  key={idx}
                  className={`relative flex gap-6 p-5 rounded-xl border transition-all duration-300 cursor-pointer ml-12 ${active === idx
                      ? `${step.accent} bg-slate-900/60 shadow-lg`
                      : "border-transparent hover:border-slate-800 hover:bg-slate-950/40"
                    }`}
                  onClick={() => setActive(active === idx ? null : idx)}
                >
                  {/* Step Circle */}
                  <div className={`absolute -left-[52px] w-10 h-10 rounded-full border-2 ${step.accent} bg-slate-950 flex items-center justify-center ${step.color} shadow-lg flex-shrink-0 z-10`}>
                    {step.icon}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-[10px] font-mono text-slate-500">Step {idx + 1}</span>
                    </div>
                    <h3 className={`text-sm font-bold mb-1 ${step.color}`}>{step.label}</h3>
                    <p className="text-slate-400 text-xs font-sans leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
