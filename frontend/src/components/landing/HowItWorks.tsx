"use client"

import { motion } from "framer-motion"
import { Camera, Brain, Wrench, ArrowRight, Check } from "lucide-react"

const steps = [
   {
      number: "01",
      title: "Capture",
      subtitle: "Snap or upload",
      features: ["Mobile & Web", "Supports blur", "Instant sync"],
      icon: Camera,
      color: "from-blue-500/20 to-cyan-500/20",
      accent: "text-blue-400"
   },
   {
      number: "02",
      title: "Analyze",
      subtitle: "AI processing",
      features: ["95% accuracy", "Spatial logic", "Safety checks"],
      icon: Brain,
      color: "from-purple-500/20 to-indigo-500/20",
      accent: "text-purple-400"
   },
   {
      number: "03",
      title: "Resolve",
      subtitle: "Guided repair",
      features: ["Visual cues", "Audio directions", "Live tracking"],
      icon: Wrench,
      color: "from-emerald-500/20 to-teal-500/20",
      accent: "text-emerald-400"
   }
]

export function HowItWorks() {
   return (
      <section id="process" className="py-24 md:py-32 px-4 md:px-6 relative overflow-hidden">
         {/* Background Depth Elements */}
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-accent/5 rounded-full blur-[150px] pointer-events-none" />

         <div className="container mx-auto max-w-6xl relative z-10">
            <div className="flex flex-col items-center text-center mb-12 md:mb-15">
               <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] text-white/70 text-xs font-semibold uppercase tracking-widest mb-6"
               >
                  <span className="relative flex h-2 w-2">
                     <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                     <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
                  </span>
                  Intelligent Workflow
               </motion.div>
               <motion.h2
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 }}
                  className="text-5xl md:text-7xl font-bold tracking-tight text-white/90 pb-2"
               >
                  How it <span className="text-accent">Works</span>
               </motion.h2>
            </div>

            <div className="relative">
               {/* Curved Connector Line (Desktop) */}
               <div className="hidden md:block absolute top-[44px] left-[16.5%] right-[16.5%] h-[24px] z-0 pointer-events-none">
                  <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                     <path d="M0 24 C 25 24, 25 0, 50 0 C 75 0, 75 24, 100 24" stroke="rgba(255,255,255,0.08)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                     <motion.path
                        d="M0 24 C 25 24, 25 0, 50 0 C 75 0, 75 24, 100 24"
                        stroke="url(#gradient-line)"
                        strokeWidth="2"
                        vectorEffect="non-scaling-stroke"
                        initial={{ pathLength: 0, opacity: 0 }}
                        whileInView={{ pathLength: 1, opacity: 1 }}
                        transition={{ duration: 1.5, ease: "easeInOut", delay: 0.4 }}
                     />
                     <defs>
                        <linearGradient id="gradient-line" x1="0%" y1="0%" x2="100%" y2="0%">
                           <stop offset="0%" stopColor="transparent" />
                           <stop offset="50%" stopColor="rgba(255,255,255,0.5)" />
                           <stop offset="100%" stopColor="transparent" />
                        </linearGradient>
                     </defs>
                  </svg>
               </div>

               <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 relative z-10">
                  {steps.map((step, index) => (
                     <motion.div
                        key={step.title}
                        initial={{ opacity: 0, y: 40 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.2, duration: 0.7, ease: "easeOut" }}
                        viewport={{ once: true, margin: "-50px" }}
                        className={`group relative flex flex-col h-full ${index === 1 ? 'md:-translate-y-6' : ''
                           }`}
                     >
                        <div className={`relative flex flex-col h-full p-8 md:p-10 rounded-3xl backdrop-blur-xl transition-all duration-500 overflow-hidden ${index === 1
                              ? 'bg-white/[0.04] border-white/10 shadow-[0_0_40px_-15px_rgba(255,255,255,0.05)]'
                              : 'bg-white/[0.02] border-white/5 group-hover:bg-white/[0.04] group-hover:border-white/10'
                           } border`}>

                           {/* Spotlight / Radial Glow */}
                           <div className={`absolute -top-32 -right-32 w-64 h-64 bg-gradient-to-br ${step.color} blur-[100px] transition-opacity duration-700 pointer-events-none ${index === 1 ? 'opacity-40 group-hover:opacity-100' : 'opacity-0 group-hover:opacity-100'
                              }`} />

                           <div className="relative z-10 flex flex-col h-full">
                              {/* Header (Icon & Number) */}
                              <div className="flex items-start justify-between mb-10">
                                 <div className={`w-14 h-14 rounded-2xl flex items-center justify-center backdrop-blur-md transition-transform duration-500 group-hover:scale-110 group-hover:-rotate-3 ${index === 1 ? 'bg-white/10 border-white/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]' : 'bg-white/5 border-white/10 group-hover:bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]'
                                    } border`}>
                                    <step.icon className={`w-6 h-6 ${step.accent}`} />
                                 </div>
                                 <span className="text-6xl font-black text-white/[0.03] group-hover:text-white/[0.08] transition-colors duration-500 font-mono tracking-tighter">
                                    {step.number}
                                 </span>
                              </div>

                              <h3 className="text-2xl font-bold mb-3 text-white/90 group-hover:text-white transition-colors">{step.title}</h3>
                              <p className="text-sm font-medium text-white/40 mb-8 group-hover:text-white/60 transition-colors uppercase tracking-wider">
                                 {step.subtitle}
                              </p>

                              {/* Features Chips */}
                              <div className="flex flex-wrap gap-2 mt-auto">
                                 {step.features.map((feature, i) => (
                                    <div key={i} className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-colors ${index === 1
                                          ? 'bg-white/[0.06] border-white/10 text-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]'
                                          : 'bg-white/[0.03] border-white/5 text-white/50 group-hover:bg-white/[0.06] group-hover:text-white/70 group-hover:border-white/10'
                                       } border backdrop-blur-sm`}>
                                       {feature}
                                    </div>
                                 ))}
                              </div>

                              {/* Next Step Arrow (Mobile/Internal) */}
                              <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-white/30 group-hover:text-white/60 transition-colors duration-500">
                                 <span>{index === steps.length - 1 ? 'Complete' : 'Next Phase'}</span>
                                 {index < steps.length - 1 ? (
                                    <ArrowRight className="w-4 h-4 -translate-x-4 opacity-0 group-hover:translate-x-0 group-hover:opacity-100 transition-all duration-500" />
                                 ) : (
                                    <Check className="w-4 h-4 -translate-x-4 opacity-0 group-hover:translate-x-0 group-hover:opacity-100 transition-all duration-500 text-emerald-400" />
                                 )}
                              </div>
                           </div>
                        </div>
                     </motion.div>
                  ))}
               </div>
            </div>
         </div>
      </section>
   )
}
