"use client"

import { motion } from "framer-motion"
import { Zap, Shield, BarChart3, Clock } from "lucide-react"

const features = [
   {
      icon: Zap,
      title: "Lightning Fast",
      description: "Resolve issues in minutes, not hours. Our intelligent system identifies problems instantly."
   },
   {
      icon: Shield,
      title: "Secure by Default",
      description: "Enterprise-grade security with end-to-end encryption and compliance certifications."
   },
   {
      icon: BarChart3,
      title: "Powerful Analytics",
      description: "Track performance, identify trends, and make data-driven maintenance decisions."
   },
   {
      icon: Clock,
      title: "24/7 Monitoring",
      description: "Round-the-clock system monitoring with instant alerts and automated responses."
   }
]

export function Features() {
   return (
      <section id="features" className="py-16 md:py-24 px-4 md:px-6">
         <div className="container mx-auto max-w-6xl">
            <div className="text-center mb-12 md:mb-16 space-y-3 md:space-y-4">
               <h2 className="text-3xl md:text-5xl font-bold tracking-tight">
                  Everything you need
               </h2>
               <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto px-4">
                  All the tools to keep your systems running at peak performance
               </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
               {features.map((feature, index) => (
                  <motion.div
                     key={feature.title}
                     initial={{ opacity: 0, y: 20 }}
                     whileInView={{ opacity: 1, y: 0 }}
                     transition={{ delay: index * 0.1 }}
                     viewport={{ once: true }}
                     className="group"
                  >
                     <div className="p-6 md:p-8 rounded-xl md:rounded-2xl border border-border bg-secondary/30 hover:bg-secondary transition-all hover:translate-y-[-4px] duration-300 h-full">
                        <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center mb-5 group-hover:bg-accent/20 transition-colors">
                           <feature.icon className="w-6 h-6 text-accent" />
                        </div>
                        <h3 className="text-lg md:text-xl font-semibold mb-2">{feature.title}</h3>
                        <p className="text-sm md:text-base text-muted-foreground leading-relaxed">{feature.description}</p>
                     </div>
                  </motion.div>
               ))}
            </div>
         </div>
      </section>
   )
}
