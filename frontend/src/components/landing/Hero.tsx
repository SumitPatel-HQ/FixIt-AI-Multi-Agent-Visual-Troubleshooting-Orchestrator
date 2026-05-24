"use client"

import { motion } from "framer-motion"
import { ArrowRight, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SignInButton, useUser } from "@clerk/nextjs"
import { useRouter } from "next/navigation"

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

function StartAnalysisButton() {
   const { isSignedIn } = useUser()
   const router = useRouter()

   if (isSignedIn) {
      return (
         <Button
            size="lg"
            className="w-full sm:w-auto h-12 md:h-14 px-8 rounded-full gap-2 group shadow-2xl shadow-white/5 bg-white text-black hover:bg-white/90"
            onClick={() => router.push("/dashboard")}
         >
            Start Free Analysis
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
         </Button>
      )
   }

   return (
      <SignInButton fallbackRedirectUrl="/dashboard" signUpFallbackRedirectUrl="/dashboard">
         <Button
            size="lg"
            className="w-full sm:w-auto h-12 md:h-14 px-8 rounded-full gap-2 group shadow-2xl shadow-white/5 bg-white text-black hover:bg-white/90"
         >
            Start Free Analysis
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
         </Button>
      </SignInButton>
   )
}

export function Hero() {
   return (
      <section className="relative pt-24 pb-12 md:pt-48 md:pb-20 px-4 md:px-6 overflow-hidden">
         {/* Subtle gradient background */}
         <div className="absolute inset-x-0 top-0 h-[1500px] bg-gradient-to-b from-accent/10 via-transparent to-transparent pointer-events-none" />

         <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="container mx-auto max-w-6xl relative"
         >
            <div className="text-center space-y-6 md:space-y-8 mb-12 md:mb-16">

               <motion.h1
                  variants={item}
                  className="text-4xl xs:text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight scale-y-125 text-balance max-w-5xl mx-auto leading-[1.1]"
               >
                  See the Problem.
                  <span className="block text-accent">Fix it Fast.</span>
               </motion.h1>

               <motion.p
                  variants={item}
                  className="text-sm md:text-2xl text-white/50 max-w-8xl mx-auto text-balance px-4 leading-relaxed"
               >
                  AI-powered visual troubleshooting that identifies issues, guides repairs step-by-step, and keeps your devices running smoothly—no technical expertise required.

               </motion.p>

               <motion.div variants={item} className="flex flex-col sm:flex-row items-center justify-center gap-3 md:gap-4 pt-4 px-8 sm:px-0">
                  <StartAnalysisButton />
               </motion.div>

               <motion.div variants={item} className="flex flex-col items-center justify-center gap-3 pt-8 text-[11px] md:text-sm text-white/40 font-medium sm:flex-row sm:gap-x-8">
                  <div className="flex items-center gap-2">
                     <Check className="w-3.5 h-3.5 md:w-4 md:h-4 text-accent" />
                     <span>No credit card required</span>
                  </div>
                  <div className="flex items-center gap-2">
                     <Check className="w-3.5 h-3.5 md:w-4 md:h-4 text-accent" />
                     <span>Instant AI diagnosis</span>
                  </div>
                  <div className="flex items-center gap-2">
                     <Check className="w-3.5 h-3.5 md:w-4 md:h-4 text-accent" />
                     <span>90% success rate</span>
                  </div>
               </motion.div>
            </div>

            {/* Clean dashboard preview */}
            <motion.div
               initial={{ opacity: 0, y: 40 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ duration: 1, delay: 0.6, ease: "easeOut" }}
               className="relative max-w-6xl mx-auto group px-2"
            >
               <div className="relative rounded-xl md:rounded-3xl border border-white/10 bg-[#0a0a0a] p-1 md:p-1.5 shadow-2xl ring-1 ring-white/5">
                  <div className="rounded-lg md:rounded-2xl border border-white/5 bg-black overflow-hidden relative aspect-[16/10] md:aspect-[16/9]">
                     <video
                        autoPlay
                        loop
                        muted
                        playsInline
                        className="w-full h-full object-cover"
                     >
                        <source src="/demo.mp4" type="video/mp4" />
                        Your browser does not support the video tag.
                     </video>
                     {/* Overlay to soften the video if needed */}
                     <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none" />
                  </div>
               </div>

               {/* Subtle accent glow */}
               <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-accent/20 rounded-full blur-[100px] md:blur-[140px] -z-10 opacity-50" />
            </motion.div>
         </motion.div>
      </section>
   )
}
