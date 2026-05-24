"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { AnswerType, DeviceInfo, CannotComplyReason } from "@/types/api-response";

interface StatusBannerProps {
   answerType: AnswerType;
   deviceInfo?: DeviceInfo;
   cannotComplyReason?: CannotComplyReason;
   onRetry?: () => void;
   onUploadNew?: () => void;
}

const getConfidenceLevel = (confidence: number): { label: string; color: string } => {
   if (confidence >= 0.9) return { label: "High", color: "text-emerald-400" };
   if (confidence >= 0.7) return { label: "Medium", color: "text-amber-400" };
   return { label: "Low", color: "text-red-400" };
};

const isSuccessState = (answerType: AnswerType): boolean => {
   return ![
      "reject_invalid_image",
      "ask_for_better_input",
      "safety_warning_only",
   ].includes(answerType);
};

export function StatusBanner({
   answerType,
   deviceInfo,
   cannotComplyReason,
   onRetry,
   onUploadNew,
}: StatusBannerProps) {
   const [isVisible, setIsVisible] = useState(true);
   const [autoDismissed, setAutoDismissed] = useState(false);

   const success = isSuccessState(answerType);

   // Auto-dismiss after 8 seconds for success states
   useEffect(() => {
      if (success && !autoDismissed) {
         const timer = setTimeout(() => {
            setIsVisible(false);
            setAutoDismissed(true);
         }, 8000);
         return () => clearTimeout(timer);
      }
   }, [success, autoDismissed]);

   const handleDismiss = () => {
      setIsVisible(false);
   };

   const confidenceInfo = deviceInfo
      ? getConfidenceLevel(deviceInfo.confidence)
      : null;

   const getFailureMessage = (): string => {
      switch (cannotComplyReason) {
         case "invalid_image":
            return "This image doesn't appear to show an electronic device";
         case "not_visible":
            return "Requested component is not visible in this image";
         case "not_present":
            return "Requested component is not present on this device";
         case "low_confidence":
            return "Unable to confidently identify the device or components";
         case "safety_risk":
            return "Cannot proceed due to safety concerns";
         default:
            return "Analysis could not be completed";
      }
   };

   return (
      <AnimatePresence>
         {isVisible && (
            <motion.div
               initial={{ opacity: 0, y: -20, scale: 0.98 }}
               animate={{ opacity: 1, y: 0, scale: 1 }}
               exit={{ opacity: 0, y: -20, scale: 0.98 }}
               transition={{ type: "spring", damping: 30, stiffness: 400 }}
               className="fixed top-6 right-6 z-[100] w-full max-w-[400px]"
            >
               <div
                  className={`
              relative overflow-hidden rounded-xl backdrop-blur-md border shadow-2xl
              ${success
                        ? "bg-[#0A0A0A]/95 border-emerald-500/20 shadow-emerald-500/5"
                        : "bg-[#0A0A0A]/95 border-red-500/20 shadow-red-500/5"
                     }
            `}
               >
                  <div className="p-5 flex gap-4">
                     {/* Icon */}
                     <div className="flex-shrink-0 pt-0.5">
                        <div
                           className={`
                      w-10 h-10 rounded-full flex items-center justify-center
                      ${success
                                 ? "bg-emerald-500/10 text-emerald-500"
                                 : "bg-red-500/10 text-red-500"
                              }
                    `}
                        >
                           {success ? (
                              <CheckCircle2 className="w-5 h-5" strokeWidth={2.5} />
                           ) : (
                              <XCircle className="w-5 h-5" strokeWidth={2.5} />
                           )}
                        </div>
                     </div>

                     {/* Content */}
                     <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                           <div>
                              <h3 className="font-semibold text-[15px] text-white leading-tight">
                                 {success ? "Analysis Complete" : "Analysis Failed"}
                              </h3>
                              {deviceInfo && (
                                 <p className="mt-1 text-[13px] text-muted-foreground font-medium">
                                    {deviceInfo.brand} {deviceInfo.model}
                                 </p>
                              )}
                              {!success && (
                                 <p className="mt-1 text-[13px] text-muted-foreground leading-relaxed">
                                    {getFailureMessage()}
                                 </p>
                              )}
                           </div>

                           <button
                              onClick={handleDismiss}
                              className="text-muted-foreground/50 hover:text-white transition-colors p-1.5 -mr-1.5 -mt-1.5 rounded-md hover:bg-white/10"
                           >
                              <X className="w-4 h-4" />
                           </button>
                        </div>

                        {/* Metadata Tags */}
                        {success && deviceInfo && (
                           <div className="mt-3 flex items-center gap-2">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-white/5 text-muted-foreground border border-white/5">
                                 {deviceInfo.device_type}
                              </span>
                              {confidenceInfo && (
                                 <span className={`
                                       inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border
                                       ${deviceInfo.confidence >= 0.9
                                       ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                       : deviceInfo.confidence >= 0.7
                                          ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                                          : 'bg-red-500/10 text-red-500 border-red-500/20'}
                                    `}>
                                    {Math.round(deviceInfo.confidence * 100)}% Confidence
                                 </span>
                              )}
                           </div>
                        )}

                        {/* Action Buttons */}
                        {!success && (
                           <div className="mt-4 flex items-center gap-3">
                              <button
                                 onClick={onRetry}
                                 className="text-[13px] font-medium text-white hover:text-red-400 transition-colors flex items-center gap-1.5"
                              >
                                 <RefreshCw className="w-3.5 h-3.5" />
                                 Try Again
                              </button>
                              <span className="text-white/10">|</span>
                              <button
                                 onClick={onUploadNew}
                                 className="text-[13px] font-medium text-muted-foreground hover:text-white transition-colors"
                              >
                                 Upload New
                              </button>
                           </div>
                        )}
                     </div>
                  </div>
               </div>
            </motion.div>
         )}
      </AnimatePresence>
   );
}
