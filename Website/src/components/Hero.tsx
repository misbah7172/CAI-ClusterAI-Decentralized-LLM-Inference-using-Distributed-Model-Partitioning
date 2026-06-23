"use client";

import { useEffect, useRef, useState } from "react";
import { Cpu, ArrowRight, Zap, RefreshCw } from "lucide-react";

export default function Hero() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [metrics, setMetrics] = useState({
    avgPower: 114.5,
    savedEnergy: 64.2,
    activeNodes: 3,
    inferenceRate: 48.2,
    targetModel: "microsoft/phi-2 (2.7B)"
  });

  // Telemetry updates simulation
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => ({
        ...prev,
        avgPower: parseFloat((112 + Math.random() * 5).toFixed(1)),
        savedEnergy: parseFloat((prev.savedEnergy + 0.01).toFixed(2)),
        inferenceRate: parseFloat((45 + Math.random() * 6).toFixed(1))
      }));
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  // Canvas particle network animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };
    window.addEventListener("resize", handleResize);

    // Nodes definition
    const nodeCount = 18;
    const nodes: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      pulse: number;
      pulseSpeed: number;
    }> = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 2.5 + 1.5,
        pulse: Math.random() * Math.PI,
        pulseSpeed: 0.02 + Math.random() * 0.03
      });
    }

    // Signals traveling along connections
    const signals: Array<{
      startX: number;
      startY: number;
      endX: number;
      endY: number;
      progress: number;
      speed: number;
    }> = [];

    const addSignal = () => {
      if (nodes.length < 2) return;
      const startIdx = Math.floor(Math.random() * nodes.length);
      let endIdx = Math.floor(Math.random() * nodes.length);
      while (endIdx === startIdx) {
        endIdx = Math.floor(Math.random() * nodes.length);
      }
      const start = nodes[startIdx];
      const end = nodes[endIdx];
      const dist = Math.hypot(end.x - start.x, end.y - start.y);
      // Only connect close nodes
      if (dist < 220) {
        signals.push({
          startX: start.x,
          startY: start.y,
          endX: end.x,
          endY: end.y,
          progress: 0,
          speed: 1.5 / dist // Speed relative to distance
        });
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Create a background circuit overlay grid
      ctx.strokeStyle = "rgba(0, 240, 255, 0.02)";
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Draw connections
      ctx.lineWidth = 0.5;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const n1 = nodes[i];
          const n2 = nodes[j];
          const dist = Math.hypot(n2.x - n1.x, n2.y - n1.y);

          if (dist < 180) {
            const alpha = (1 - dist / 180) * 0.15;
            ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.stroke();
          }
        }
      }

      // Update & Draw Signals
      if (Math.random() < 0.15 && signals.length < 12) {
        addSignal();
      }

      for (let i = signals.length - 1; i >= 0; i--) {
        const sig = signals[i];
        sig.progress += sig.speed;

        if (sig.progress >= 1) {
          signals.splice(i, 1);
          continue;
        }

        const currentX = sig.startX + (sig.endX - sig.startX) * sig.progress;
        const currentY = sig.startY + (sig.endY - sig.startY) * sig.progress;

        const grad = ctx.createRadialGradient(currentX, currentY, 0, currentX, currentY, 6);
        grad.addColorStop(0, "#00ff66");
        grad.addColorStop(0.5, "rgba(0, 240, 255, 0.8)");
        grad.addColorStop(1, "rgba(0, 240, 255, 0)");

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(currentX, currentY, 6, 0, Math.PI * 2);
        ctx.fill();
      }

      // Update & Draw Nodes
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;

        // Boundary checks
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        node.pulse += node.pulseSpeed;
        const currentRadius = node.radius + Math.sin(node.pulse) * 0.8;

        const isGreen = Math.sin(node.pulse) > 0.4;
        const shadowColor = isGreen ? "rgba(0, 255, 102, 0.4)" : "rgba(0, 240, 255, 0.4)";
        const nodeColor = isGreen ? "#00ff66" : "#00f0ff";

        ctx.shadowBlur = 10;
        ctx.shadowColor = shadowColor;
        ctx.fillStyle = nodeColor;

        ctx.beginPath();
        ctx.arc(node.x, node.y, currentRadius, 0, Math.PI * 2);
        ctx.fill();

        ctx.shadowBlur = 0; // Reset
      });

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <section className="relative min-h-[92vh] flex items-center justify-center overflow-hidden pt-20">
      {/* Background Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none opacity-50"
      />

      {/* Background glows */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 glow-overlay-cyan rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-96 h-96 glow-overlay-green rounded-full pointer-events-none" />

      {/* Grid Pattern */}
      <div className="absolute inset-0 circuit-grid opacity-10 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        {/* Left Side Copy */}
        <div className="lg:col-span-7 flex flex-col items-start text-left space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass-panel border border-accent-teal/30 text-accent-teal text-xs font-mono tracking-wider uppercase">
            <Zap className="w-3.5 h-3.5 animate-pulse text-brand-green" /> Energy-Aware distributed Inference
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-white leading-tight">
            Run big models on <span className="text-gradient font-extrabold">small hardware.</span>
            <br />
            Same output. <span className="text-accent-blue font-mono font-medium">A fraction of the power.</span>
          </h1>

          <p className="text-slate-400 text-lg md:text-xl max-w-2xl font-sans leading-relaxed">
            CAI is a decentralized AI inference runtime that splits oversized model layers across a pipeline of low-end GPUs and system RAM using Kubernetes. Real-time scheduling reduces cluster power usage with zero degradation in generation accuracy.
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-4">
            <a
              href="#architecture"
              className="inline-flex items-center justify-center px-6 py-3 rounded-lg font-medium text-black bg-gradient-to-r from-brand-cyan to-brand-green hover:from-white hover:to-white transition-all duration-300 shadow-[0_0_20px_rgba(0,240,255,0.2)] hover:shadow-[0_0_30px_rgba(255,255,255,0.4)] group"
            >
              See How It Works <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-300 group-hover:translate-x-1" />
            </a>
            <a
              href="https://github.com/misbah7172/GreenCluster-AI-CAI"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center px-6 py-3 rounded-lg font-medium text-slate-300 bg-slate-900/50 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all duration-300 gap-2 glass-panel"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
              </svg> View on GitHub
            </a>
          </div>
        </div>

        {/* Right Side HUD / Telemetry */}
        <div className="lg:col-span-5 relative">
          <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-brand-cyan/20 to-brand-green/20 blur-xl opacity-70" />

          <div className="relative glass-panel rounded-xl border border-white/10 overflow-hidden shadow-2xl font-mono">
            {/* Terminal Top Bar */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-white/5">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-500/80" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <span className="w-3 h-3 rounded-full bg-green-500/80" />
              </div>
              <span className="text-[10px] text-slate-500 uppercase tracking-widest flex items-center gap-1">
                <RefreshCw className="w-2.5 h-2.5 animate-spin text-accent-blue" /> telemetry-daemon
              </span>
            </div>

            {/* Terminal Body */}
            <div className="p-6 space-y-6 text-sm text-slate-300">
              <div className="space-y-1">
                <p className="text-slate-500 text-xs">MODEL ROUTED</p>
                <p className="text-white font-bold text-base flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-brand-cyan" /> {metrics.targetModel}
                </p>
              </div>

              {/* Grid of numbers */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg bg-slate-950/40 border border-white/5">
                  <p className="text-slate-500 text-[10px] uppercase">CLUSTER POWER</p>
                  <p className="text-2xl font-bold text-white tracking-tight mt-1">
                    {metrics.avgPower} <span className="text-xs text-slate-400 font-normal">W</span>
                  </p>
                  <div className="w-full bg-slate-900 h-1 rounded-full mt-2 overflow-hidden">
                    <div
                      className="bg-brand-cyan h-full rounded-full transition-all duration-1000"
                      style={{ width: `${(metrics.avgPower / 250) * 100}%` }}
                    />
                  </div>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950/40 border border-white/5">
                  <p className="text-slate-500 text-[10px] uppercase">ENERGY SAVED</p>
                  <p className="text-2xl font-bold text-brand-green tracking-tight mt-1">
                    -{metrics.savedEnergy}%
                  </p>
                  <p className="text-[10px] text-slate-500 mt-2">vs. Baseline RTX 4090</p>
                </div>
              </div>

              {/* Topology / Routing Map */}
              <div className="space-y-3 pt-2">
                <p className="text-slate-500 text-[10px] uppercase tracking-wider">PIPELINE ROUTING TOPOLOGY</p>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border-l-2 border-brand-cyan">
                    <span className="text-slate-200">Node-0 (Gateway)</span>
                    <span className="text-brand-cyan font-bold">Layers 0-7 (RTX 3050 Ti)</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border-l-2 border-brand-cyan">
                    <span className="text-slate-200">Node-1 (Worker)</span>
                    <span className="text-brand-cyan font-bold">Layers 8-19 (GTX 1660)</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border-l-2 border-brand-green">
                    <span className="text-slate-200">Node-2 (Offloader)</span>
                    <span className="text-brand-green font-bold">Layers 20-31 (Sys RAM)</span>
                  </div>
                </div>
              </div>

              {/* Telemetry Output Log */}
              <div className="p-3 rounded bg-slate-950 border border-white/5 text-[11px] text-slate-400 space-y-1 overflow-hidden select-none">
                <p className="text-brand-green flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-brand-green animate-ping" />
                  [CAI-DAEMON] DEAS scheduler initialized.
                </p>
                <p className="text-brand-cyan">[DEAS] EER score threshold: 2.14. Running cost-benefit evaluation.</p>
                <p>[DEAS] Partition verified. Offloading CPU prefetch stream active...</p>
                <p className="text-slate-500">RTT Probe: Node-0 ↔ Node-1 = 0.38ms (caching hits: 100%)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
