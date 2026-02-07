import { Navbar } from "@/components/layout/Navbar";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { CTA } from "@/components/landing/CTA";

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <Hero />
      <Features />
      <CTA />

      <footer className="border-t border-border py-12 px-6">
        <div className="container mx-auto max-w-6xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-primary rounded-md" />
              <span className="font-semibold text-foreground">Fixit</span>
            </div>
            <p>© 2026 Fixit. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
