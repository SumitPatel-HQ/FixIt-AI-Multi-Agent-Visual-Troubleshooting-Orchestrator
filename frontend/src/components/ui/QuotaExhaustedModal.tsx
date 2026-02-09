'use client';

import { useEffect } from 'react';

interface QuotaExhaustedModalProps {
   onClose: () => void;
   retryAfter?: string;
}

export function QuotaExhaustedModal({
   onClose,
   retryAfter = 'tomorrow',
}: QuotaExhaustedModalProps) {
   // Prevent body scroll when modal is open
   useEffect(() => {
      document.body.style.overflow = 'hidden';
      return () => {
         document.body.style.overflow = 'unset';
      };
   }, []);

   return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
         {/* Modal Container */}
         <div className="relative w-full max-w-lg bg-secondary/90 backdrop-blur-md border border-border rounded-4xl shadow-2xl animate-in fade-in zoom-in duration-300">
            {/* Icon Header */}
            <div className="flex justify-center pt-8 pb-4">
               <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                  <svg
                     className="w-8 h-8 text-amber-500"
                     fill="none"
                     stroke="currentColor"
                     viewBox="0 0 24 24"
                  >
                     <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                     />
                  </svg>
               </div>
            </div>

            {/* Content */}
            <div className="px-8 pb-8 space-y-6">
               {/* Title */}
               <div className="text-center space-y-2">
                  <h2 className="text-2xl font-display font-bold text-foreground">
                     AI Service Temporarily Unavailable
                  </h2>
                  <p className="text-sm text-muted-foreground">
                     We&apos;ve reached our daily limit
                  </p>
               </div>

               {/* Main Message */}
               <div className="bg-background/50 border border-border/50 rounded-xl p-5 space-y-4">
                  <div className="flex items-start gap-3">
                     <div className="shrink-0 w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center mt-0.5">
                        <span className="text-amber-500 text-xs font-bold">!</span>
                     </div>
                     <div className="flex-1 space-y-3">
                        <p className="text-sm text-foreground leading-relaxed">
                           Our AI analysis service has reached its free tier quota limit for today. This happens when we process too many requests in a short period.
                        </p>
                        <div className="bg-secondary/30 rounded-lg p-3 space-y-2">
                           <p className="text-xs font-semibold text-amber-500 uppercase tracking-wide">
                              What This Means
                           </p>
                           <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                              <li>The service will be available again {retryAfter}</li>
                              <li>Your image and query were not processed</li>
                              <li>This is a temporary limitation of our free tier</li>
                           </ul>
                        </div>
                     </div>
                  </div>
               </div>

               {/* Suggestions */}
               <div className="bg-primary/5 border border-primary/10 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2">
                     <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                     </svg>
                     <p className="text-xs font-semibold text-primary uppercase tracking-wide">
                        What You Can Do
                     </p>
                  </div>
                  <ul className="text-sm text-foreground space-y-2">
                     <li className="flex items-start gap-2">
                        <span className="text-primary mt-0.5">•</span>
                        <span>Try again {retryAfter} when quota resets</span>
                     </li>
                     <li className="flex items-start gap-2">
                        <span className="text-primary mt-0.5">•</span>
                        <span>Bookmark this page and return later</span>
                     </li>
                     <li className="flex items-start gap-2">
                        <span className="text-primary mt-0.5">•</span>
                        <span>Contact support if this issue persists</span>
                     </li>
                  </ul>
               </div>

               {/* Close Button */}
               <button
                  onClick={onClose}
                  className="w-full h-12 bg-primary/10 text-primary hover:bg-primary/20 font-semibold rounded-xl transition-all active:scale-95 shadow-primary/5 border border-primary/10"
               >
                  Got It
               </button>
            </div>
         </div>
      </div>
   );
}
