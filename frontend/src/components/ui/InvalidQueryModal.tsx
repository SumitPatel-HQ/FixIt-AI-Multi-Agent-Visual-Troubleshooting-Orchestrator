'use client';

import { useEffect } from 'react';

interface InvalidQueryModalProps {
   query: string;
   deviceType: string;
   isMismatch?: boolean;
   suggestions?: string[];
   onRetry: () => void;
}

export function InvalidQueryModal({
   query,
   deviceType,
   isMismatch = false,
   suggestions = [],
   onRetry,
}: InvalidQueryModalProps) {
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
               <div className="w-16 h-16 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center">
                  <svg
                     className="w-8 h-8 text-accent"
                     fill="none"
                     stroke="currentColor"
                     viewBox="0 0 24 24"
                  >
                     <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                     />
                  </svg>
               </div>
            </div>

            {/* Content */}
            <div className="px-8 pb-8 space-y-6">
               {/* Title */}
               <div className="text-center space-y-2">
                  <h2 className="text-2xl font-display font-bold text-foreground">
                     I Need More Information
                  </h2>
                  <p className="text-sm text-muted-foreground">
                     Let&apos;s clarify your question
                  </p>
               </div>

               {/* Main Message */}
               <div className="bg-background/50 border border-border/50 rounded-xl p-4 space-y-3">
                  <div className="flex items-start gap-3">
                     <div className="shrink-0 w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center mt-0.5">
                        <span className="text-accent text-xs font-bold">!</span>
                     </div>
                     <div className="flex-1 space-y-2">
                        {isMismatch ? (
                           <p className="text-sm text-foreground leading-relaxed">
                              The query <span className="font-semibold text-accent">&apos;{query}&apos;</span> asks about a component or feature that doesn&apos;t apply to this{' '}
                              <span className="font-semibold">{deviceType}</span>. Please ask about components relevant to this device type.
                           </p>
                        ) : (
                           <p className="text-sm text-foreground leading-relaxed">
                              The query <span className="font-semibold text-accent">&apos;{query}&apos;</span> does not contain any
                              recognizable keywords or instructions. Please specify what you would like to know about this{' '}
                              <span className="font-semibold">{deviceType}</span>.
                           </p>
                        )}
                     </div>
                  </div>
               </div>

              

               {/* Retry Button */}
               <button
                  onClick={onRetry}
                  className="w-full h-12 bg-primary/10  text-primary hover:bg-primary/20 font-semibold rounded-xl transition-all active:scale-95 shadow-primary/5 border border-primary/10"
               >
                  Try Again
               </button>
            </div>
         </div>
      </div>
   );
}
