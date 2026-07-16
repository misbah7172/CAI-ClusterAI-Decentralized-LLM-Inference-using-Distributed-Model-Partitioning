import type { Metadata } from "next";
import PageLayout from "@/components/PageLayout";
import Roadmap from "@/components/Roadmap";

export const metadata: Metadata = {
  title: "Roadmap — Cai Research & Engineering Direction",
  description: "Follow Cai's development phases: from distributed inference pipelines and DEAS scheduler to volunteer compute networks and Rust runtime.",
};

export default function RoadmapPage() {
  return (
    <PageLayout>
      <div className="py-16 border-b border-slate-900">
        <div className="container max-w-7xl mx-auto px-6 text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
            Development Roadmap
          </h1>
          <p className="text-slate-400 text-lg font-sans max-w-2xl mx-auto">
            Our engineering roadmap covers 25 phases, centering on energy reduction, decentralized topologies, and accessibility of large language models.
          </p>
        </div>
      </div>
      <div className="py-12">
        <Roadmap />
      </div>
    </PageLayout>
  );
}
