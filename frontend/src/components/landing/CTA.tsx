"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"

export function CTA() {
   return (
      <section className="py-16 md:py-24 px-4 md:px-6">
         <div className="container mx-auto max-w-4xl">
            <div className="relative rounded-2xl md:rounded-[2.5rem] border border-white/10 bg-gradient-to-br from-accent/10 via-secondary/50 to-secondary/50 p-8 md:p-16 text-center overflow-hidden shadow-2xl">
               {/* Decorative elements */}
               <div className="absolute top-0 right-0 w-48 md:w-64 h-48 md:h-64 bg-accent/5 rounded-full blur-3xl" />
               <div className="absolute bottom-0 left-0 w-48 md:w-64 h-48 md:h-64 bg-accent/5 rounded-full blur-3xl" />

               <div className="relative space-y-6 md:space-y-8">
                  <h2 className="text-3xl md:text-6xl font-bold tracking-tight text-balance">
                     Ready to get started?
                  </h2>
                  <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto px-4">
                     Join thousands of teams already using Fixit to streamline their maintenance workflows.
                  </p>
                  <div className="flex flex-col sm:flex-row items-center justify-center gap-3 md:gap-4 pt-4 px-4">
                     <Link href="/dashboard" className="w-full sm:w-auto">
                        <Button size="lg" className="w-full sm:w-auto h-12 md:h-14 px-8 md:px-10 rounded-full gap-2 group shadow-xl shadow-accent/20">
                           Start Free Trial
                           <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </Button>
                     </Link>
                     <Button size="lg" variant="secondary" className="w-full sm:w-auto h-12 md:h-14 px-8 md:px-10 rounded-full">
                        Schedule Demo
                     </Button>
                  </div>
               </div>
            </div>
         </div>
      </section>
   )
}
