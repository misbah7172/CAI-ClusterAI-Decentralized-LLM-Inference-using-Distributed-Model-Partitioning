import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cai — Energy-Efficient Decentralized AI Inference Runtime",
  description: "Run large AI models across multiple low-end GPUs or PCs with no accuracy loss and a fraction of the power. Powered by DEAS (Dynamic Energy-Aware Scheduling) and gRPC pipeline parallelism.",
  keywords: "decentralized AI, distributed inference, green computing, energy-aware scheduling, GPU pipeline parallelism, LLM inference, green cluster, sustainable AI",
  openGraph: {
    title: "Cai — Energy-Efficient Decentralized AI Inference",
    description: "Run big models on small hardware. Same output, a fraction of the power.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} min-h-screen font-sans bg-bg-dark text-slate-100 antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
