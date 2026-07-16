import Header from "@/components/Header";
import Hero from "@/components/Hero";
import ProblemSection from "@/components/ProblemSection";
import ArchitectureDiagram from "@/components/ArchitectureDiagram";
import DEASDiagram from "@/components/DEASDiagram";
import SandboxSection from "@/components/SandboxSection";
import BenchmarkChart from "@/components/BenchmarkChart";
import Roadmap from "@/components/Roadmap";
import Footer from "@/components/Footer";
import FeatureHighlights from "@/components/FeatureHighlights";
import HowItWorks from "@/components/HowItWorks";
import LiveDashboard from "@/components/LiveDashboard";
import CommunitySection from "@/components/CommunitySection";

export default function Home() {
  return (
    <div className="min-h-screen bg-bg-dark flex flex-col selection:bg-brand-cyan/30 selection:text-white">
      <Header />

      {/* Main Sections */}
      <main className="flex-1">
        <Hero />
        <FeatureHighlights />
        <HowItWorks />
        <ProblemSection />
        <ArchitectureDiagram />
        <DEASDiagram />
        <SandboxSection />
        <LiveDashboard />
        <div id="benchmarks" className="scroll-mt-16">
          <BenchmarkChart />
        </div>
        <Roadmap />
        <CommunitySection />
      </main>

      <Footer />
    </div>
  );
}
