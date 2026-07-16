import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import BenchmarkChart from "@/components/BenchmarkChart";

export const metadata: Metadata = {
  title: "Benchmarks — Cai vs Traditional GPU",
  description: "Compare Cai distributed inference against traditional single-GPU setups across power, energy, latency, throughput, and carbon metrics.",
};

export default function BenchmarksPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Performance Benchmarks
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Real-hardware comparisons between a single enterprise GPU and a Cai distributed consumer cluster. Honest data — including the tradeoffs.
          </p>
        </div>
      </div>

      <BenchmarkChart />

      <section className="py-16 border-t border-slate-900">
        <div className="container max-w-4xl mx-auto px-6">
          <div className="glass-panel p-8 rounded-xl border border-slate-800 space-y-6">
            <h2 className="text-xl font-bold text-white">About These Numbers</h2>
            <div className="space-y-4 text-sm font-sans text-slate-400 leading-relaxed">
              <p>Cai is designed for <strong className="text-white">energy efficiency and accessibility</strong>, not raw throughput. Distributed pipeline parallelism introduces serialization and inter-node communication overhead that creates measurable latency and throughput tradeoffs compared to a single enterprise GPU.</p>
              <p>The correct framing is: <span className="text-brand-green font-bold">what can you run on $800 worth of consumer hardware vs. $3,500 for an RTX 4090?</span> Cai makes multi-billion parameter inference accessible on hardware most researchers and students already own.</p>
              <p className="text-[11px] text-slate-600">All numbers are based on controlled benchmark runs. Final published dataset will be released alongside the methodology paper.</p>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
