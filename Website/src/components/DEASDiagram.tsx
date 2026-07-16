"use client";

import { useState, useEffect } from "react";
import { Activity, Shield, Thermometer, Zap, RefreshCw } from "lucide-react";

export default function DEASDiagram() {
  const [activeStep, setActiveStep] = useState(0);

  // Auto-cycle through the loop stages
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 3);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const steps = [
    {
      title: "1. Monitor (NVML Telemetry)",
      icon: <Thermometer className="w-5 h-5 text-brand-cyan" />,
      desc: "High-frequency NVML monitors sample GPU power usage and temperature metrics in sub-100ms intervals, storing them in ring buffers for immediate telemetry.",
      metric: "GPU TDP draw, thermal trends"
    },
    {
      title: "2. Analyze (PID Controller)",
      icon: <Activity className="w-5 h-5 text-accent-blue" />,
      desc: "Our closed-loop PID controller calculates the Energy Efficiency Ratio (EER). It triggers predictive rebalancing alerts based on telemetry degradation trends.",
      metric: "EER Ratio score calculation"
    },
    {
      title: "3. Adapt (Dynamic Throttling)",
      icon: <Zap className="w-5 h-5 text-brand-green" />,
      desc: "CAI dynamically throttles batch sizes, adjusts execution precision (FP16 ↔ INT8 ↔ INT4), and updates GPU power limits to maximize cluster hardware efficiency.",
      metric: "Batch scaling, precision swaps"
    }
  ];

  return (
    <section className="py-24 relative overflow-hidden bg-slate-950/20 border-b border-slate-900">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] glow-overlay-cyan opacity-25 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">

        {/* Title */}
        <div className="max-w-3xl mx-auto text-center mb-16 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-panel border border-brand-green/30 text-brand-green text-xs font-mono uppercase tracking-wider">
            <Shield className="w-3.5 h-3.5" /> USP: Energy Feedback Loop
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Dynamic Energy-Aware Scheduling (DEAS)
          </h2>
          <p className="text-slate-400 text-lg">
            Unlike static schedulers, DEAS is an active, closed-loop system that matches model execution parameters to physical hardware constraints in real time.
          </p>
        </div>

        {/* Circular Loop Graphic & Text */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">

          {/* Left Side: Text breakdown of steps */}
          <div className="lg:col-span-6 space-y-6">
            <div className="space-y-4">
              {steps.map((step, idx) => (
                <div
                  key={idx}
                  onClick={() => setActiveStep(idx)}
                  className={`p-5 rounded-xl border transition-all duration-300 cursor-pointer ${activeStep === idx
                    ? "border-brand-cyan/40 bg-slate-900/60 shadow-[0_0_15px_rgba(0,240,255,0.05)]"
                    : "border-slate-800 bg-slate-950/40 opacity-60 hover:opacity-90"
                    }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded bg-slate-950 border border-white/5">
                      {step.icon}
                    </div>
                    <h3 className="text-base font-bold text-white">{step.title}</h3>
                  </div>
                  <p className="text-slate-400 text-xs leading-relaxed pl-11">
                    {step.desc}
                  </p>
                  <div className="mt-3 pl-11 flex items-center gap-2">
                    <span className="text-[10px] text-slate-500 font-mono uppercase">Telemetry Node:</span>
                    <span className="text-[10px] text-brand-cyan font-mono">{step.metric}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Side: Interactive Circular Visual */}
          <div className="lg:col-span-6 flex justify-center">
            <div className="relative w-[320px] h-[320px] md:w-[360px] md:h-[360px] flex items-center justify-center">

              {/* Spinning/Looping Border */}
              <div className="absolute inset-0 rounded-full border border-dashed border-slate-800 animate-[spin_60s_linear_infinite]" />

              {/* Inner Glow Circle */}
              <div className="absolute w-[80%] h-[80%] rounded-full border border-brand-cyan/20 flex items-center justify-center">
                <div className="absolute w-[90%] h-[90%] rounded-full border border-brand-green/10" />
              </div>

              {/* Loop Center: DEAS Engine */}
              <div className="relative z-10 w-24 h-24 rounded-full bg-slate-950 border-2 border-brand-cyan flex flex-col items-center justify-center shadow-[0_0_30px_rgba(0,240,255,0.15)]">
                <RefreshCw className="w-6 h-6 text-brand-cyan animate-[spin_10s_linear_infinite] mb-1" />
                <span className="text-[10px] font-bold text-white font-mono uppercase tracking-wider">DEAS Engine</span>
              </div>

              {/* Step 1 Node (Top) */}
              <div
                onClick={() => setActiveStep(0)}
                className={`absolute top-0 -translate-y-1/2 px-4 py-2 rounded-lg border font-mono text-xs cursor-pointer transition-all duration-300 flex items-center gap-2 ${activeStep === 0
                  ? "border-brand-cyan bg-slate-900 text-white shadow-[0_0_15px_#00f0ff]"
                  : "border-slate-800 bg-slate-950 text-slate-400"
                  }`}
              >
                <Thermometer className="w-3.5 h-3.5 text-brand-cyan" /> MONITOR
              </div>

              {/* Step 2 Node (Bottom Right) */}
              <div
                onClick={() => setActiveStep(1)}
                className={`absolute bottom-6 right-0 translate-x-1/4 px-4 py-2 rounded-lg border font-mono text-xs cursor-pointer transition-all duration-300 flex items-center gap-2 ${activeStep === 1
                  ? "border-accent-blue bg-slate-900 text-white shadow-[0_0_15px_#38bdf8]"
                  : "border-slate-800 bg-slate-950 text-slate-400"
                  }`}
              >
                <Activity className="w-3.5 h-3.5 text-accent-blue" /> ANALYZE
              </div>

              {/* Step 3 Node (Bottom Left) */}
              <div
                onClick={() => setActiveStep(2)}
                className={`absolute bottom-6 left-0 -translate-x-1/4 px-4 py-2 rounded-lg border font-mono text-xs cursor-pointer transition-all duration-300 flex items-center gap-2 ${activeStep === 2
                  ? "border-brand-green bg-slate-900 text-white shadow-[0_0_15px_#00ff66]"
                  : "border-slate-800 bg-slate-950 text-slate-400"
                  }`}
              >
                <Zap className="w-3.5 h-3.5 text-brand-green" /> ADAPT
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
