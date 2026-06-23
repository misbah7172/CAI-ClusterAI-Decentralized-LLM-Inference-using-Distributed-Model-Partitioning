import Hero from "@/components/Hero";
import ProblemSection from "@/components/ProblemSection";
import ArchitectureDiagram from "@/components/ArchitectureDiagram";
import DEASDiagram from "@/components/DEASDiagram";
import SandboxSection from "@/components/SandboxSection";
import BenchmarkChart from "@/components/BenchmarkChart";
import Roadmap from "@/components/Roadmap";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <div className="min-h-screen bg-bg-dark flex flex-col selection:bg-brand-cyan/30 selection:text-white">
      {/* Floating Header */}
      <header className="sticky top-0 z-50 w-full glass-panel border-b border-white/5 py-4 px-6">
        <div className="container max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-gradient-to-r from-brand-cyan to-brand-green flex items-center justify-center text-slate-950 font-mono font-black text-xs shadow-[0_0_10px_rgba(0,240,255,0.2)]">
              K
            </div>
            <span className="text-white font-bold text-sm tracking-wider font-mono uppercase">CAI</span>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-mono text-slate-400">
            <a href="#" className="hover:text-brand-cyan transition-colors duration-200">Overview</a>
            <a href="#architecture" className="hover:text-brand-cyan transition-colors duration-200">Architecture</a>
            <a href="#benchmarks" className="hover:text-brand-cyan transition-colors duration-200">Benchmarks</a>
            <a href="https://github.com/misbah7172/GreenCluster-AI-CAI/blob/main/README.md" target="_blank" className="hover:text-brand-cyan transition-colors duration-200">Docs</a>
          </nav>

          {/* CTA */}
          <div>
            <a
              href="https://github.com/misbah7172/GreenCluster-AI-CAI"
              target="_blank"
              rel="noopener noreferrer"
              className="px-3.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 hover:text-white hover:border-slate-700 transition-all duration-300"
            >
              GitHub Stars
            </a>
          </div>
        </div>
      </header>

      {/* Main Sections */}
      <main className="flex-1">
        <Hero />
        <ProblemSection />
        <ArchitectureDiagram />
        <DEASDiagram />
        <SandboxSection />
        <div id="benchmarks" className="scroll-mt-16">
          <BenchmarkChart />
        </div>
        <Roadmap />
      </main>

      <Footer />
    </div>
  );
}
