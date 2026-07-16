"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, Menu, X, ArrowUpRight } from "lucide-react";

export default function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const pathname = usePathname();

  const toggleDropdown = (name: string) => {
    setActiveDropdown(activeDropdown === name ? null : name);
  };

  const closeAll = () => {
    setIsOpen(false);
    setActiveDropdown(null);
  };

  const productLinks = [
    { name: "Features", href: "/#features", desc: "Core energy-aware scheduling features" },
    { name: "Architecture", href: "/architecture", desc: "Pipeline parallelism layer split details" },
    { name: "Sandbox Runtime", href: "/sandbox", desc: "Local multi-node cluster simulation" },
    { name: "Distributed AI", href: "/distributed-ai", desc: "Dynamic layer migration & streaming" },
    { name: "CAI Studio", href: "/studio", desc: "Centralized cluster management app" },
    { name: "Remote Cluster", href: "/remote-cluster", desc: "Decentralized networks & global map" },
  ];

  const resourceLinks = [
    { name: "Research & Edge AI", href: "/research", desc: "Green computing and future publications" },
    { name: "Benchmarks", href: "/benchmarks", desc: "Traditional GPU vs. CAI cluster stats" },
    { name: "Supported Models", href: "/models", desc: "VRAM specs & node recommendations" },
    { name: "Roadmap", href: "/roadmap", desc: "Completed and planned research phases" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full glass-panel border-b border-white/5 py-4 px-6">
      <div className="container max-w-7xl mx-auto flex items-center justify-between">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group" onClick={closeAll}>
          <div className="w-8 h-8 rounded bg-gradient-to-r from-brand-cyan to-brand-green flex items-center justify-center text-slate-950 font-mono font-black text-sm shadow-[0_0_10px_rgba(0,240,255,0.2)] group-hover:shadow-[0_0_15px_rgba(0,255,102,0.4)] transition-all duration-300">
            K
          </div>
          <span className="text-white font-bold text-sm tracking-wider font-mono uppercase group-hover:text-brand-cyan transition-colors duration-300">
            CAI
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden lg:flex items-center gap-8 text-xs font-mono text-slate-400">

          <Link href="/" className={`hover:text-brand-cyan transition-colors duration-200 ${pathname === "/" ? "text-brand-cyan" : ""}`}>
            Home
          </Link>

          {/* Product Dropdown */}
          <div className="relative group/drop">
            <button className="flex items-center gap-1 hover:text-brand-cyan transition-colors duration-200 py-2 focus:outline-none">
              Product <ChevronDown className="w-3.5 h-3.5" />
            </button>
            <div className="absolute top-full left-1/2 -translate-x-1/2 w-80 mt-1 p-3 glass-panel border border-white/5 rounded-xl invisible group-hover/drop:visible opacity-0 group-hover/drop:opacity-100 bg-slate-950/95 shadow-2xl transition-all duration-200">
              <div className="grid gap-1">
                {productLinks.map((link) => (
                  <Link
                    key={link.name}
                    href={link.href}
                    className="p-2 rounded-lg hover:bg-white/5 transition-colors group/item block text-left"
                    onClick={closeAll}
                  >
                    <p className="text-xs font-bold text-white group-hover/item:text-brand-cyan transition-colors">{link.name}</p>
                    <p className="text-[10px] text-slate-500 font-sans mt-0.5 leading-normal">{link.desc}</p>
                  </Link>
                ))}
              </div>
            </div>
          </div>

          {/* Resources Dropdown */}
          <div className="relative group/drop">
            <button className="flex items-center gap-1 hover:text-brand-cyan transition-colors duration-200 py-2 focus:outline-none">
              Research <ChevronDown className="w-3.5 h-3.5" />
            </button>
            <div className="absolute top-full left-1/2 -translate-x-1/2 w-80 mt-1 p-3 glass-panel border border-white/5 rounded-xl invisible group-hover/drop:visible opacity-0 group-hover/drop:opacity-100 bg-slate-950/95 shadow-2xl transition-all duration-200">
              <div className="grid gap-1">
                {resourceLinks.map((link) => (
                  <Link
                    key={link.name}
                    href={link.href}
                    className="p-2 rounded-lg hover:bg-white/5 transition-colors group/item block text-left"
                    onClick={closeAll}
                  >
                    <p className="text-xs font-bold text-white group-hover/item:text-brand-cyan transition-colors">{link.name}</p>
                    <p className="text-[10px] text-slate-500 font-sans mt-0.5 leading-normal">{link.desc}</p>
                  </Link>
                ))}
              </div>
            </div>
          </div>

          <Link href="/download" className={`hover:text-brand-cyan transition-colors duration-200 ${pathname === "/download" ? "text-brand-cyan" : ""}`}>
            Download
          </Link>
        </nav>

        {/* Right CTA */}
        <div className="hidden lg:flex items-center gap-4">
          <a
            href="https://github.com/misbah7172/GreenCluster-AI-CAI"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 hover:text-white hover:border-brand-cyan/40 transition-all duration-300 flex items-center gap-1"
          >
            GitHub <ArrowUpRight className="w-3 h-3" />
          </a>
          <Link
            href="/download"
            className="px-4 py-1.5 rounded bg-gradient-to-r from-brand-cyan to-brand-green text-slate-950 text-[10px] font-mono font-bold hover:opacity-90 transition-opacity duration-300"
            onClick={closeAll}
          >
            Download CAI
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white focus:outline-none"
        >
          {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Nav Menu */}
      {isOpen && (
        <div className="lg:hidden mt-4 p-4 glass-panel border border-white/5 rounded-xl bg-slate-950/98 space-y-1 font-mono text-xs">
          <Link href="/" className="block p-3 hover:bg-white/5 rounded-lg text-white" onClick={closeAll}>Home</Link>

          <div className="border-t border-white/5 my-2" />
          <p className="text-[10px] text-slate-500 px-3 uppercase tracking-widest font-bold">Product</p>
          {productLinks.map((link) => (
            <Link key={link.name} href={link.href} className="block p-3 pl-5 hover:bg-white/5 rounded-lg text-slate-300" onClick={closeAll}>
              {link.name}
            </Link>
          ))}

          <div className="border-t border-white/5 my-2" />
          <p className="text-[10px] text-slate-500 px-3 uppercase tracking-widest font-bold">Research</p>
          {resourceLinks.map((link) => (
            <Link key={link.name} href={link.href} className="block p-3 pl-5 hover:bg-white/5 rounded-lg text-slate-300" onClick={closeAll}>
              {link.name}
            </Link>
          ))}

          <div className="border-t border-white/5 my-2" />
          <Link href="/download" className="block p-3 hover:bg-white/5 rounded-lg text-brand-green font-bold" onClick={closeAll}>
            Download CAI
          </Link>
        </div>
      )}
    </header>
  );
}
