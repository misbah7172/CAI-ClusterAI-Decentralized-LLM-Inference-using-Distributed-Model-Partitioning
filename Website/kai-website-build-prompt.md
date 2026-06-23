# CAI Landing Page — Build Prompt

Use this prompt as-is (or lightly edited) with a coding agent like Claude Code to scaffold and build the site.

---

## Project Context

Build a marketing/landing page for **CAI** — an energy-efficient, decentralized AI inference runtime. CAI lets people run large AI models across multiple low-end GPUs/PCs (instead of needing one expensive high-end GPU), with no accuracy loss, while cutting total power consumption. It uses gRPC pipeline parallelism to split model layers across nodes, real-time energy-aware scheduling (DEAS), quantization, and a Sandbox Mode that simulates a multi-node cluster on a single laptop before connecting real hardware.

This is a single-page (or lightly multi-section) landing page to showcase CAI as a product/research project — not the actual runtime, just the site.

## Positioning & Tone

- **One-line pitch:** "Run big models on small hardware. Same output. A fraction of the power."
- CAI's wedge vs. other distributed inference projects (Petals, vLLM, Ray Serve, etc.) is **energy efficiency**, not just throughput or scale. Every section should reinforce "less power, same accuracy, decentralized."
- Tone: technical but confident, research-grade credibility — not hypey SaaS marketing. Think "serious systems project," closer to how Modal, Together AI, or an arXiv-paper-with-a-website would present themselves, not a typical AI-wrapper startup.
- Copy should be concise. Short sentences. No fluff adjectives. Assume the visitor is technical (ML engineers, systems engineers, researchers).

## Tech Stack

- **Next.js** (App Router, latest stable) + **TypeScript**
- **Tailwind CSS** for styling
- Animated diagrams via **SVG/Canvas** for lightweight pieces (node network, energy meter) — avoid pulling in a heavy animation library just for simple effects
- **Framer Motion** only where it earns its weight: scroll-triggered reveals, the node-network pulse animation, hover/interaction states. Keep bundle size in mind — don't add it if a CSS animation/transition does the job
- Optional: a small **D3** scale/interpolation helper if the benchmark chart needs real data-driven scaling, but a hand-rolled SVG bar/line chart is preferred over a full charting library for a handful of static benchmark numbers
- Fully responsive (mobile-first breakpoints), dark theme as default/only theme
- No backend needed — this is a static marketing site. Use placeholder content where real benchmark numbers aren't available yet, clearly marked as placeholder in code comments so it's easy to swap in real data later

## Visual Direction

- **Dark background** (near-black, e.g. `#0a0e14` range) as the base
- **Palette:** electric blue / cyan as primary accent, with a teal/green undertone mixed in (not pure neon-AI-purple branding — the green/teal reinforces "energy efficiency / sustainable tech" rather than generic "AI futurism")
- **Motif:** circuit/network aesthetic — nodes connected by glowing lines, with light pulses traveling along edges to represent inference flowing through the pipeline. This motif should recur across multiple sections (hero, architecture, energy loop), not just once
- Typography: clean technical sans-serif (e.g. Inter, or similar) for body; consider a monospace accent font for stats/code-like elements (benchmark numbers, terminal snippets) to reinforce the systems/engineering feel
- Generous whitespace/dark-space — avoid a cluttered, gradient-soup look. Let the glowing node animations be the visual interest, keep everything else restrained

## Page Sections (in order)

1. **Hero**
   - The one-line pitch as the headline
   - Subhead: 1–2 sentences explaining what CAI does (distributed, energy-aware, no accuracy loss)
   - Primary CTA (e.g. "View on GitHub" or "Get Early Access" — use placeholder link) + secondary CTA ("See how it works" anchor-scrolls to architecture section)
   - Animated background or embedded visual: a small network of nodes lighting up in sequence, with a simulated energy meter/wattage number ticking down as work distributes across nodes. This should feel alive within ~2–3 seconds of page load, no user interaction required

2. **The Problem**
   - Short framing: one high-end GPU running hot/expensive vs. a small cluster of cheaper nodes doing the same job for less total power
   - Visual: animated or static before/after wattage comparison (single big bar vs. several small bars, with total watt labels)

3. **How It Works**
   - Simplified architecture diagram: Model → Layer Split → Node A → Node B → Node C (gRPC pipeline) → Output
   - Keep this diagram simpler than the full system architecture — just enough for a first-time visitor to grasp the mental model in ~10 seconds
   - Animate the "flow" — a pulse or token moving along the pipeline path on scroll-into-view or on loop

4. **Energy-Aware Scheduling (DEAS)** — primary USP, give it real visual space
   - Small interactive or looping diagram showing the feedback loop: Monitor power (NVML) → Adjust (batch size / precision / power limits) → repeat
   - Could be a circular/cyclical diagram rather than linear, to visually distinguish it from the pipeline diagram above

5. **Sandbox Mode**
   - Big selling point: "Test the full cluster experience on one laptop before touching real hardware"
   - This removes the main adoption barrier (needing multiple machines just to try it)
   - Visual: a single laptop icon "splitting" into multiple virtual node icons, or a toggle/switch UI mockup showing Sandbox Mode vs. Real Cluster Mode side by side
   - If feasible, this section is a good candidate for a lightweight interactive element (e.g. a toggle that visually switches between "simulated" and "real" node states) — optional stretch goal, not required for v1

6. **Benchmarks**
   - Comparison chart: baseline (single high-end GPU) vs. CAI (distributed low-power nodes) across power (W), energy (Wh), latency, throughput
   - Use a simple custom SVG bar chart, not a heavy charting library
   - Use clearly-marked placeholder numbers for now (code comment: `// TODO: replace with real benchmark data`)
   - Frame copy honestly — note the known tradeoff (slower than single high-end GPU due to network overhead) in small print near the chart. Credibility matters more than overselling here

7. **Roadmap / Research Direction**
   - Short list/timeline of what's next: Sandbox Mode (CLI), Energy Feedback Loop, Model Placement Engine, Node Agent, Desktop App
   - Frame as an evolving research project, not a finished product — this builds trust with a technical audience
   - Simple vertical or horizontal timeline component, minimal animation needed (subtle fade/slide on scroll is enough)

8. **CTA / Footer**
   - Final call to action: GitHub link, docs link, or "join early access" — use placeholder links
   - Footer with project name, short tagline repeat, links (GitHub, research paper/docs if applicable, contact)

## Animation & Interaction Guidelines

- Favor **subtlety and purpose** over decoration — every animation should reinforce a concept (energy flowing, nodes communicating, power dropping), not just exist for flash
- Use scroll-triggered reveals (fade/slide-up, ~400–600ms, ease-out) for section entrances via Framer Motion's `whileInView`
- The hero node-network animation and the architecture pipeline animation should loop continuously and not require hover/click to play, since many visitors won't interact
- Respect `prefers-reduced-motion` — provide a static fallback (no animation, or a single fade-in) for users with that preference set
- Keep all animations performant on lower-end devices (this is a project literally about efficiency — janky animations would undercut the message)

## Content Notes

- Write all copy concisely, in the user's preferred plain, natural style — no résumé-speak, no excessive jargon-stacking, no marketing clichés ("revolutionary," "game-changing," etc.)
- It's fine to acknowledge current limitations honestly (network overhead, setup complexity) in small, secondary copy — this is a research/engineering audience that will trust the project more for showing its real tradeoffs
- Use placeholder/lorem-ipsum-free copy throughout — write real, plausible draft copy for every section rather than literal "Lorem ipsum," so the site reads correctly even before final copy review

## Deliverables

- A working Next.js + Tailwind project with all sections above implemented
- Organized as reusable components (e.g. `Hero.tsx`, `ProblemSection.tsx`, `ArchitectureDiagram.tsx`, `EnergyLoopDiagram.tsx`, `SandboxSection.tsx`, `BenchmarkChart.tsx`, `Roadmap.tsx`, `Footer.tsx`)
- Clean, commented code, especially around the custom SVG/Canvas animation components, so it's easy to extend later
- Mobile-responsive at minimum 375px width up through desktop
- README with setup instructions (`npm install`, `npm run dev`)
