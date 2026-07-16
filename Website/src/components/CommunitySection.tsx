import Link from "next/link";
import { ArrowUpRight, Star, BookOpen, MessageSquare, Mail } from "lucide-react";

export default function CommunitySection() {
  return (
    <section className="py-24 relative overflow-hidden bg-bg-dark border-b border-slate-900">
      <div className="absolute inset-0 glow-overlay-green opacity-20 pointer-events-none" />

      <div className="container max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Join the CAI Community
          </h2>
          <p className="text-slate-400 text-lg font-sans">
            CAI is an open-source research project. Star it, contribute, or follow the research.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              icon: <Star className="w-6 h-6" />,
              title: "Star on GitHub",
              desc: "View the codebase, report issues, submit PRs, and follow development progress.",
              href: "https://github.com/misbah7172/GreenCluster-AI-CAI",
              label: "GitHub",
              color: "text-brand-cyan",
              border: "border-brand-cyan/20 hover:border-brand-cyan/40",
            },
            {
              icon: <BookOpen className="w-6 h-6" />,
              title: "Read the Docs",
              desc: "System architecture, CLI reference, build guides, and performance enhancement notes.",
              href: "https://github.com/misbah7172/GreenCluster-AI-CAI/blob/main/README.md",
              label: "Documentation",
              color: "text-brand-green",
              border: "border-brand-green/20 hover:border-brand-green/40",
            },
            {
              icon: <MessageSquare className="w-6 h-6" />,
              title: "Research Discussion",
              desc: "Topics: Green AI, distributed systems, edge computing, and energy-efficient LLM inference.",
              href: "https://github.com/misbah7172/GreenCluster-AI-CAI/discussions",
              label: "Discussions",
              color: "text-accent-blue",
              border: "border-accent-blue/20 hover:border-accent-blue/40",
            },
            {
              icon: <Mail className="w-6 h-6" />,
              title: "Stay Updated",
              desc: "Follow major milestones, new phase completions, and research paper publications via GitHub watch.",
              href: "https://github.com/misbah7172/GreenCluster-AI-CAI/releases",
              label: "Release Notes",
              color: "text-accent-teal",
              border: "border-accent-teal/20 hover:border-accent-teal/40",
            },
          ].map((item) => (
            <a
              key={item.title}
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
              className={`group p-6 rounded-xl glass-panel border ${item.border} transition-all duration-300 hover:bg-slate-900/40 block`}
            >
              <div className={`${item.color} mb-4`}>{item.icon}</div>
              <h3 className="text-white font-bold text-base mb-2 group-hover:text-brand-cyan transition-colors">{item.title}</h3>
              <p className="text-slate-400 text-xs font-sans leading-relaxed mb-4">{item.desc}</p>
              <span className={`text-[10px] font-mono ${item.color} flex items-center gap-1`}>
                {item.label} <ArrowUpRight className="w-3 h-3" />
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
