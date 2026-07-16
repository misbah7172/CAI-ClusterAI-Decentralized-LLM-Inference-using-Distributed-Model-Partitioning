"use client";

import { ExternalLink, Activity } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-slate-950/80 border-t border-slate-900 py-16 relative overflow-hidden font-sans">
      <div className="absolute inset-0 circuit-grid opacity-[0.02] pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10 grid grid-cols-1 md:grid-cols-12 gap-12">

        {/* Brand Info */}
        <div className="md:col-span-5 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-gradient-to-r from-brand-cyan to-brand-green flex items-center justify-center text-slate-950 font-mono font-black text-sm shadow-[0_0_15px_rgba(0,240,255,0.2)]">
              K
            </div>
            <span className="text-white font-bold text-lg tracking-wider font-mono uppercase">CAI Inference</span>
          </div>

          <p className="text-slate-400 text-xs md:text-sm leading-relaxed max-w-md">
            Decentralized, energy-aware AI inference runtime. Run big models on small hardware. Same output, a fraction of the power. Empowering sustainable and accessible AI.
          </p>

          {/* Social Stats Block */}
          <div className="flex items-center gap-4 pt-2">
            <a
              href="https://github.com/misbah7172/GreenCluster-AI-CAI"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs font-mono transition-all duration-300 hover:border-slate-700"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-brand-cyan">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
              </svg> GitHub Repository
            </a>
          </div>
        </div>

        {/* Links Grid */}
        <div className="md:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-8">

          {/* Project Column */}
          <div className="space-y-4">
            <h4 className="text-white font-mono text-xs font-bold uppercase tracking-widest">Project</h4>
            <ul className="space-y-2.5 text-xs text-slate-400">
              <li>
                <a href="/architecture" className="hover:text-brand-cyan transition-colors duration-200">
                  Architecture
                </a>
              </li>
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/issues" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  Issue Tracker <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/releases" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  Releases <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
            </ul>
          </div>

          {/* Resources Column */}
          <div className="space-y-4">
            <h4 className="text-white font-mono text-xs font-bold uppercase tracking-widest">Resources</h4>
            <ul className="space-y-2.5 text-xs text-slate-400">
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/blob/main/README.md" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  System CLI <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/blob/main/docs/SINGLE_GPU_AUDIT_AND_PLAN.md" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  Architecture docs <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/blob/main/BUILD_GUIDE.md" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  Build Guide <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
            </ul>
          </div>

          {/* Research Column */}
          <div className="space-y-4 col-span-2 sm:col-span-1">
            <h4 className="text-white font-mono text-xs font-bold uppercase tracking-widest">Telemetry</h4>
            <ul className="space-y-2.5 text-xs text-slate-400">
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/blob/main/docs/PERFORMANCE_ENHANCEMENTS.md" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  Telemetry docs <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
              <li>
                <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/tree/main/analysis" target="_blank" className="hover:text-brand-cyan transition-colors duration-200 flex items-center gap-1">
                  Post-Analysis <ExternalLink className="w-3 h-3 text-slate-600" />
                </a>
              </li>
            </ul>
          </div>

        </div>

      </div>

      {/* Copyright/Footer note */}
      <div className="container max-w-7xl mx-auto px-6 mt-16 pt-8 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-500 font-mono">
        <p>© 2026 CAI Project. Released under the MIT License.</p>
        <p className="flex items-center gap-1">
          <Activity className="w-3.5 h-3.5 text-brand-green animate-pulse" /> Energy-efficiency validated via NVML telemetry.
        </p>
      </div>
    </footer>
  );
}
