"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { ArrowRight, Check } from "lucide-react"
import { Button } from "@/components/ui/button"

const container = {
   hidden: { opacity: 0 },
   show: {
      opacity: 1,
      transition: {
         staggerChildren: 0.1,
         delayChildren: 0.3,
      }
   }
}

const item = {
   hidden: { opacity: 0, y: 20 },
   show: { opacity: 1, y: 0 }
}

export function Hero() {
   return (
      <section className="relative pt-24 pb-12 md:pt-32 md:pb-20 px-4 md:px-6 overflow-hidden">
         {/* Subtle gradient background */}
         <div className="absolute inset-x-0 top-0 h-[500px] bg-gradient-to-b from-accent/10 via-transparent to-transparent pointer-events-none" />

         <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="container mx-auto max-w-6xl relative"
         >
            <div className="text-center space-y-6 md:space-y-8 mb-12 md:mb-16">
               <motion.div variants={item} className="inline-block">
                  <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary border border-border text-[10px] md:text-xs font-medium text-white/70">
                     <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                     Now in beta
                  </span>
               </motion.div>

               <motion.h1
                  variants={item}
                  className="text-4xl xs:text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight text-balance max-w-5xl mx-auto leading-[1.1]"
               >
                  Maintenance made
                  <span className="block text-accent">effortless</span>
               </motion.h1>

               <motion.p
                  variants={item}
                  className="text-sm md:text-xl text-white/50 max-w-2xl mx-auto text-balance px-4 leading-relaxed"
               >
                  Intelligent automation for modern maintenance workflows. Fix issues faster, track everything, and keep your systems running smoothly.
               </motion.p>

               <motion.div variants={item} className="flex flex-col sm:flex-row items-center justify-center gap-3 md:gap-4 pt-4 px-8 sm:px-0">
                  <Link href="/dashboard" className="w-full sm:w-auto">
                     <Button size="lg" className="w-full sm:w-auto h-12 md:h-14 px-8 rounded-full gap-2 group shadow-2xl shadow-white/5 bg-white text-black hover:bg-white/90">
                        Get Started
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                     </Button>
                  </Link>
                  <Link href="#demo" className="w-full sm:w-auto">
                     <Button size="lg" variant="secondary" className="w-full sm:w-auto h-12 md:h-14 px-8 rounded-full border border-white/10 bg-white/5 text-white hover:bg-white/10">
                        View Demo
                     </Button>
                  </Link>
               </motion.div>

               <motion.div variants={item} className="flex flex-col items-center justify-center gap-3 pt-8 text-[11px] md:text-sm text-white/40 font-medium sm:flex-row sm:gap-x-8">
                  <div className="flex items-center gap-2">
                     <Check className="w-3.5 h-3.5 md:w-4 md:h-4 text-accent" />
                     <span>No credit card required</span>
                  </div>
                  <div className="flex items-center gap-2">
                     <Check className="w-3.5 h-3.5 md:w-4 md:h-4 text-accent" />
                     <span>Free 14-day trial</span>
                  </div>
               </motion.div>
            </div>

            {/* Clean dashboard preview */}
            <motion.div
               initial={{ opacity: 0, y: 40 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ duration: 1, delay: 0.6, ease: "easeOut" }}
               className="relative max-w-5xl mx-auto group px-2"
            >
               <div className="relative rounded-xl md:rounded-2xl border border-white/15 bg-[#0a0a0a] p-1.5 md:p-3 shadow-2xl ring-1 ring-white/10">
                  <div className="rounded-lg md:rounded-xl border border-white/10 bg-[#0c0c0c] p-4 md:p-8 space-y-4 md:space-y-6 overflow-hidden">
                     {/* Simplified high-fidelity dashboard wireframe */}
                     <div className="flex items-center justify-between pb-4 md:pb-6 border-b border-white/5">
                        <div className="flex items-center gap-2 md:gap-4">
                           <div className="h-6 w-6 md:h-8 md:w-8 bg-white/5 rounded-lg border border-white/5" />
                           <div className="h-2.5 w-20 md:h-3 md:w-32 bg-white/5 rounded-full" />
                        </div>
                        <div className="flex gap-2 md:gap-3">
                           <div className="hidden xs:block h-7 w-20 md:w-24 bg-white/5 rounded-lg border border-white/5" />
                           <div className="h-7 w-7 md:h-8 md:w-8 bg-accent/20 rounded-lg border border-accent/20" />
                        </div>
                     </div>

                     <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-6">
                        {[1, 2, 3].map((i) => (
                           <div key={i} className="h-24 md:h-32 bg-white/[0.02] rounded-lg md:rounded-xl border border-white/5 p-3 md:p-4">
                              <div className="h-1.5 w-8 bg-white/10 rounded-full mb-2" />
                              <div className="h-3 w-16 bg-white/5 rounded-full" />
                           </div>
                        ))}
                     </div>

                     <div className="grid grid-cols-1 md:grid-cols-5 gap-3 md:gap-6">
                        <div className="md:col-span-3 h-40 md:h-56 bg-white/[0.02] rounded-lg md:rounded-xl border border-white/5" />
                        <div className="md:col-span-2 h-40 md:h-56 bg-white/[0.02] rounded-lg md:rounded-xl border border-white/5" />
                     </div>
                  </div>
               </div>

               {/* Subtle accent glow */}
               <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-accent/20 rounded-full blur-[100px] md:blur-[140px] -z-10 opacity-50" />
            </motion.div>
         </motion.div>
      </section>
   )
}
