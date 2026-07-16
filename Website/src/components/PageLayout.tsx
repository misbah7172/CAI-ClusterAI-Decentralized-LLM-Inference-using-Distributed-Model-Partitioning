import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { ReactNode } from "react";

export default function PageLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg-dark flex flex-col selection:bg-brand-cyan/30 selection:text-white">
      <Header />
      <main className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
