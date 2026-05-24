"use client";

import { motion } from "framer-motion";
import { LoadingStage, LOADING_STAGE_CONFIG } from "@/types/api-response";

interface LoadingProgressProps {
   stage: LoadingStage;
   isComplete?: boolean;
}

export function LoadingProgress({ stage, isComplete }: LoadingProgressProps) {
   const config = LOADING_STAGE_CONFIG[stage];

   return (
      <div className="fixed top-0 left-0 right-0 z-60">
         {/* Progress Bar */}
         <div className="h-1 bg-white/5">
            <motion.div
               initial={{ width: 0 }}
               animate={{ width: `${config.progress}%` }}
               transition={{ duration: 0.5, ease: "easeOut" }}
               className={`h-full ${isComplete
                     ? "bg-white"
                     : "bg-gradient-to-r from-secondary to-primary"
                  }`}
            />
         </div>

         {/* Stage Indicator */}
         {!isComplete && (
            <motion.div
               initial={{ opacity: 0, y: -10 }}
               animate={{ opacity: 1, y: 0 }}
               className="absolute top-3 left-1/2 -translate-x-1/2"
            >
               <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-secondary/90 backdrop-blur-md border border-white/10 shadow-xl">
                  {/* Spinner */}
                  <div className="relative w-5 h-5">
                     <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full"
                     />
                  </div>

                  {/* Icon and Message */}
                  <div className="flex items-center gap-2">
                     <span className="text-lg">{config.icon}</span>
                     <span className="text-sm font-medium text-white/80">
                        {config.message}
                     </span>
                  </div>

                  {/* Progress Percentage */}
                  <span className="text-xs text-white/50 font-mono">
                     {config.progress}%
                  </span>
               </div>
            </motion.div>
         )}
      </div>
   );
}

// Skeleton components for loading states
export function SkeletonCard({ className = "" }: { className?: string }) {
   return (
      <div className={`rounded-xl bg-secondary/50 border border-border/50 p-6 ${className}`}>
         <div className="space-y-4">
            <div className="h-6 bg-white/5 rounded-lg w-1/3 animate-pulse" />
            <div className="space-y-2">
               <div className="h-4 bg-white/5 rounded w-full animate-pulse" />
               <div className="h-4 bg-white/5 rounded w-5/6 animate-pulse" />
               <div className="h-4 bg-white/5 rounded w-4/6 animate-pulse" />
            </div>
         </div>
      </div>
   );
}

export function SkeletonImage() {
   return (
      <div className="rounded-xl bg-secondary/50 border border-border/50 overflow-hidden">
         <div className="aspect-video bg-white/5 animate-pulse flex items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-white/10 animate-pulse" />
         </div>
      </div>
   );
}

export function LoadingSkeleton() {
   return (
      <div className="space-y-6 animate-in fade-in duration-500">
         {/* Image Skeleton */}
         <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-2">
               <SkeletonImage />
            </div>
            <div className="lg:col-span-3 space-y-4">
               <SkeletonCard />
               <SkeletonCard />
            </div>
         </div>

         {/* Steps Skeleton */}
         <SkeletonCard className="h-48" />
      </div>
   );
}
