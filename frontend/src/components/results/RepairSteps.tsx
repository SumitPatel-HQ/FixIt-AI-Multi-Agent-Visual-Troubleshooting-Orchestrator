"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
   Play,
   Pause,
   CheckCircle2,
   Circle,
   ChevronDown,
   ChevronUp,
   Volume2,
   VolumeX,
   Clock,
   Eye,
   AlertTriangle,
   ChevronLeft,
   ChevronRight,
   CheckSquare,
   Square,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { TroubleshootingStep, AnswerType } from "@/types/api-response";

interface RepairStepsProps {
   steps: TroubleshootingStep[];
   answerType: AnswerType;
   audioInstructions?: string;
   onStepComplete?: (stepNumber: number) => void;
   onComponentHighlight?: (overlayRef: string) => void;
}

const getSectionTitle = (answerType: AnswerType): { icon: string; title: string } => {
   switch (answerType) {
      case "locate_only":
         return { icon: "📍", title: "Location Guide" };
      case "explain_only":
         return { icon: "📚", title: "How It Works" };
      case "troubleshoot_steps":
      default:
         return { icon: "🔧", title: "Repair Steps" };
   }
};

export function RepairSteps({
   steps,
   answerType,
   audioInstructions,
   onStepComplete,
   onComponentHighlight,
}: RepairStepsProps) {
   const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
   const [expandedStep, setExpandedStep] = useState<number | null>(null);
   const [activeStep, setActiveStep] = useState<number>(1);
   const [isPlaying, setIsPlaying] = useState(false);
   const [isMuted, setIsMuted] = useState(false);
   const [audioProgress, setAudioProgress] = useState(0);
   const speechRef = useRef<SpeechSynthesisUtterance | null>(null);

   // Mobile swipe handling
   const [touchStart, setTouchStart] = useState<number | null>(null);

   const { icon, title } = getSectionTitle(answerType);
   const progress = (completedSteps.size / steps.length) * 100;

   const handleToggleComplete = (stepNumber: number) => {
      setCompletedSteps((prev) => {
         const newSet = new Set(prev);
         if (newSet.has(stepNumber)) {
            newSet.delete(stepNumber);
         } else {
            newSet.add(stepNumber);
            onStepComplete?.(stepNumber);
            // Auto-advance to next step
            if (stepNumber < steps.length) {
               setActiveStep(stepNumber + 1);
            }
         }
         return newSet;
      });
   };

   const handleToggleExpand = (stepNumber: number) => {
      setExpandedStep((prev) => (prev === stepNumber ? null : stepNumber));
   };

   const handleStepClick = (stepNumber: number) => {
      setActiveStep(stepNumber);
      const step = steps.find((s) => s.step === stepNumber);
      if (step?.overlay_reference) {
         onComponentHighlight?.(step.overlay_reference);
      }
   };

   // Text-to-Speech for audio instructions
   const handlePlayAudio = () => {
      if (!audioInstructions) return;

      if (isPlaying) {
         window.speechSynthesis.cancel();
         setIsPlaying(false);
         return;
      }

      const utterance = new SpeechSynthesisUtterance(audioInstructions);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = isMuted ? 0 : 1;

      utterance.onend = () => {
         setIsPlaying(false);
         setAudioProgress(100);
      };

      utterance.onboundary = (event) => {
         // Approximate progress based on character position
         const progress = (event.charIndex / audioInstructions.length) * 100;
         setAudioProgress(progress);
      };

      speechRef.current = utterance;
      window.speechSynthesis.speak(utterance);
      setIsPlaying(true);
   };

   const handleToggleMute = () => {
      setIsMuted((prev) => !prev);
      if (speechRef.current) {
         speechRef.current.volume = isMuted ? 1 : 0;
      }
   };

   // Mobile navigation
   const handleTouchStart = (e: React.TouchEvent) => {
      setTouchStart(e.touches[0].clientX);
   };

   const handleTouchEnd = (e: React.TouchEvent) => {
      if (touchStart === null) return;

      const touchEnd = e.changedTouches[0].clientX;
      const diff = touchStart - touchEnd;

      if (Math.abs(diff) > 50) {
         if (diff > 0 && activeStep < steps.length) {
            setActiveStep((prev) => prev + 1);
         } else if (diff < 0 && activeStep > 1) {
            setActiveStep((prev) => prev - 1);
         }
      }

      setTouchStart(null);
   };

   // Cleanup speech synthesis on unmount
   useEffect(() => {
      return () => {
         window.speechSynthesis.cancel();
      };
   }, []);

   if (!steps || steps.length === 0) return null;

   return (
      <motion.div
         initial={{ opacity: 0, y: 20 }}
         animate={{ opacity: 1, y: 0 }}
         transition={{ delay: 0.3 }}
         className="space-y-4"
      >
         {/* Section Header */}
         <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
               <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span>{icon}</span>
                  {title}
               </h2>
               <span className="text-sm text-white/50">
                  {completedSteps.size} of {steps.length} completed
               </span>
            </div>

            {/* Audio Playback Button */}
            {audioInstructions && (
               <div className="flex items-center gap-2">
                  <Button
                     variant={isPlaying ? "default" : "secondary"}
                     size="sm"
                     onClick={handlePlayAudio}
                     className="gap-2"
                  >
                     {isPlaying ? (
                        <>
                           <Pause className="w-4 h-4" />
                           <span className="hidden sm:inline">Pause</span>
                        </>
                     ) : (
                        <>
                           <Play className="w-4 h-4" />
                           <span className="hidden sm:inline">Play Audio</span>
                        </>
                     )}
                  </Button>
                  <Button
                     variant="ghost"
                     size="icon"
                     onClick={handleToggleMute}
                     className="h-9 w-9"
                  >
                     {isMuted ? (
                        <VolumeX className="w-4 h-4" />
                     ) : (
                        <Volume2 className="w-4 h-4" />
                     )}
                  </Button>
               </div>
            )}
         </div>

         {/* Progress Bar */}
         <div className="relative h-1.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div
               initial={{ width: 0 }}
               animate={{ width: `${progress}%` }}
               className="absolute h-full bg-gradient-to-r from-accent to-emerald-500 rounded-full"
            />
         </div>

         {/* Audio Progress (when playing) */}
         {isPlaying && (
            <div className="flex items-center gap-2">
               <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                     initial={{ width: 0 }}
                     animate={{ width: `${audioProgress}%` }}
                     className="h-full bg-accent/50"
                  />
               </div>
               <div className="flex items-center gap-1">
                  <Volume2 className="w-3 h-3 text-accent animate-pulse" />
                  <span className="text-xs text-white/50">Playing...</span>
               </div>
            </div>
         )}

         {/* Steps List - Desktop */}
         <div className="hidden md:block space-y-3">
            {steps.map((step, index) => {
               const isCompleted = completedSteps.has(step.step);
               const isActive = activeStep === step.step;
               const isExpanded = expandedStep === step.step;

               return (
                  <motion.div
                     key={step.step}
                     id={`repair-step-${step.step}`}
                     initial={{ opacity: 0, x: -20 }}
                     animate={{ opacity: 1, x: 0 }}
                     transition={{ delay: index * 0.05 }}
                  >
                     <Card
                        className={`
                  transition-all duration-300 cursor-pointer
                  ${isActive ? "border-accent/50 bg-accent/5" : "border-border/50"}
                  ${isCompleted ? "opacity-70" : ""}
                `}
                        onClick={() => handleStepClick(step.step)}
                     >
                        <CardContent className="p-4">
                           <div className="flex items-start gap-4">
                              {/* Checkbox */}
                              <button
                                 onClick={(e) => {
                                    e.stopPropagation();
                                    handleToggleComplete(step.step);
                                 }}
                                 className={`
                        flex-shrink-0 mt-1 transition-all duration-300
                        ${isCompleted ? "text-emerald-400" : "text-white/20 hover:text-white/40"}
                      `}
                              >
                                 {isCompleted ? (
                                    <CheckSquare className="w-6 h-6" />
                                 ) : (
                                    <Square className="w-6 h-6" />
                                 )}
                              </button>

                              {/* Step Content */}
                              <div className="flex-1 min-w-0">
                                 <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1">
                                       <div className="flex items-center gap-2 mb-1">
                                          <span className="text-xs font-bold text-accent uppercase tracking-wider">
                                             Step {step.step}
                                          </span>
                                       </div>
                                       <p
                                          className={`
                              text-white/90 leading-relaxed
                              ${isCompleted ? "line-through text-white/50" : ""}
                            `}
                                       >
                                          {step.instruction}
                                       </p>

                                       {/* Time Estimate */}
                                       <div className="flex items-center gap-3 mt-2">
                                          <span className="inline-flex items-center gap-1 text-xs text-white/50">
                                             <Clock className="w-3 h-3" />
                                             {step.estimated_time}
                                          </span>
                                          {step.visual_cue && (
                                             <span className="inline-flex items-center gap-1 text-xs text-blue-400">
                                                <Eye className="w-3 h-3" />
                                                {step.visual_cue}
                                             </span>
                                          )}
                                       </div>
                                    </div>

                                    {/* Expand Button */}
                                    {(step.safety_note || step.overlay_reference) && (
                                       <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={(e) => {
                                             e.stopPropagation();
                                             handleToggleExpand(step.step);
                                          }}
                                          className="flex-shrink-0"
                                       >
                                          {isExpanded ? (
                                             <ChevronUp className="w-4 h-4" />
                                          ) : (
                                             <ChevronDown className="w-4 h-4" />
                                          )}
                                       </Button>
                                    )}
                                 </div>

                                 {/* Expanded Details */}
                                 <AnimatePresence>
                                    {isExpanded && (
                                       <motion.div
                                          initial={{ height: 0, opacity: 0 }}
                                          animate={{ height: "auto", opacity: 1 }}
                                          exit={{ height: 0, opacity: 0 }}
                                          className="overflow-hidden"
                                       >
                                          <div className="pt-3 mt-3 border-t border-white/10 space-y-3">
                                             {step.safety_note && (
                                                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                                   <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                                                   <p className="text-sm text-amber-200/80">
                                                      {step.safety_note}
                                                   </p>
                                                </div>
                                             )}

                                             {step.overlay_reference && (
                                                <Button
                                                   variant="outline"
                                                   size="sm"
                                                   onClick={(e) => {
                                                      e.stopPropagation();
                                                      onComponentHighlight?.(step.overlay_reference!);
                                                   }}
                                                   className="gap-2"
                                                >
                                                   <Eye className="w-4 h-4" />
                                                   Show in Image
                                                </Button>
                                             )}
                                          </div>
                                       </motion.div>
                                    )}
                                 </AnimatePresence>
                              </div>
                           </div>
                        </CardContent>
                     </Card>
                  </motion.div>
               );
            })}
         </div>

         {/* Steps - Mobile (Swipeable Accordion) */}
         <div
            className="md:hidden"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
         >
            {/* Mobile Navigation */}
            <div className="flex items-center justify-between mb-3">
               <Button
                  variant="ghost"
                  size="icon"
                  disabled={activeStep <= 1}
                  onClick={() => setActiveStep((prev) => Math.max(1, prev - 1))}
               >
                  <ChevronLeft className="w-5 h-5" />
               </Button>
               <span className="text-sm text-white/70">
                  Step {activeStep} of {steps.length}
               </span>
               <Button
                  variant="ghost"
                  size="icon"
                  disabled={activeStep >= steps.length}
                  onClick={() => setActiveStep((prev) => Math.min(steps.length, prev + 1))}
               >
                  <ChevronRight className="w-5 h-5" />
               </Button>
            </div>

            {/* Active Step Card */}
            <AnimatePresence mode="wait">
               {steps
                  .filter((step) => step.step === activeStep)
                  .map((step) => {
                     const isCompleted = completedSteps.has(step.step);

                     return (
                        <motion.div
                           key={step.step}
                           id={`repair-step-mobile-${step.step}`}
                           initial={{ opacity: 0, x: 50 }}
                           animate={{ opacity: 1, x: 0 }}
                           exit={{ opacity: 0, x: -50 }}
                           transition={{ type: "spring", damping: 25 }}
                        >
                           <Card className="border-accent/30 bg-accent/5">
                              <CardContent className="p-5 space-y-4">
                                 {/* Step Header */}
                                 <div className="flex items-center justify-between">
                                    <span className="text-sm font-bold text-accent uppercase tracking-wider">
                                       Step {step.step}
                                    </span>
                                    <div className="flex items-center gap-2 text-sm text-white/50">
                                       <Clock className="w-4 h-4" />
                                       {step.estimated_time}
                                    </div>
                                 </div>

                                 <div className="flex items-start gap-3">
                                    <button
                                       onClick={() => handleToggleComplete(step.step)}
                                       className={`
                                 flex-shrink-0 mt-1 transition-all duration-300
                                 ${isCompleted ? "text-emerald-400" : "text-white/20 hover:text-white/40"}
                               `}
                                    >
                                       {isCompleted ? (
                                          <CheckSquare className="w-6 h-6" />
                                       ) : (
                                          <Square className="w-6 h-6" />
                                       )}
                                    </button>

                                    {/* Instruction */}
                                    <p
                                       className={`
                           text-lg text-white/90 leading-relaxed
                           ${isCompleted ? "line-through text-white/50" : ""}
                         `}
                                    >
                                       {step.instruction}
                                    </p>
                                 </div>

                                 {/* Visual Cue */}
                                 {step.visual_cue && (
                                    <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                       <Eye className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                                       <p className="text-sm text-blue-200/80">{step.visual_cue}</p>
                                    </div>
                                 )}

                                 {/* Safety Note */}
                                 {step.safety_note && (
                                    <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                       <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                                       <p className="text-sm text-amber-200/80">{step.safety_note}</p>
                                    </div>
                                 )}

                                 {/* Actions */}
                                 <div className="flex items-center gap-3 pt-2">
                                    <Button
                                       variant={isCompleted ? "secondary" : "default"}
                                       className="flex-1"
                                       onClick={() => handleToggleComplete(step.step)}
                                    >
                                       {isCompleted ? (
                                          <>
                                             <Circle className="w-4 h-4 mr-2" />
                                             Mark Incomplete
                                          </>
                                       ) : (
                                          <>
                                             <CheckCircle2 className="w-4 h-4 mr-2" />
                                             Mark Complete
                                          </>
                                       )}
                                    </Button>
                                    {step.overlay_reference && (
                                       <Button
                                          variant="outline"
                                          size="icon"
                                          onClick={() => onComponentHighlight?.(step.overlay_reference!)}
                                       >
                                          <Eye className="w-4 h-4" />
                                       </Button>
                                    )}
                                 </div>
                              </CardContent>
                           </Card>
                        </motion.div>
                     );
                  })}
            </AnimatePresence>

            {/* Step Progress Dots */}
            <div className="flex items-center justify-center gap-2 mt-4">
               {steps.map((step) => (
                  <button
                     key={step.step}
                     onClick={() => setActiveStep(step.step)}
                     className={`
                w-2 h-2 rounded-full transition-all duration-300
                ${completedSteps.has(step.step)
                           ? "bg-emerald-500"
                           : step.step === activeStep
                              ? "bg-accent w-4"
                              : "bg-white/20"
                        }
              `}
                  />
               ))}
            </div>
         </div>
      </motion.div>
   );
}
