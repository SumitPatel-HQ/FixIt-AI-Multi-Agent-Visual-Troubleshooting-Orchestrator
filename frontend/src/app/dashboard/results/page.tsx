"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
   SessionData,
   APIResponse,
   LoadingStage,
   Visualization,
   LocalizationResult,
} from "@/types/api-response";
import {
   StatusBanner,
   ARImageCanvas,
   DiagnosisPanel,
   RepairSteps,
   ComponentsDetected,
   // FollowUpInput,
   SuccessInfoPanel,
   LoadingProgress,
   LoadingSkeleton,
   ClarifyingQuestions,
   ExplanationSection,
   SafetyWarningOnly,
   InvalidImagePanel,
   SourcesList,
} from "@/components/results";
import { getSession, storeSession, troubleshoot } from "@/lib/api";

// Mock session data for development - replace with actual API call
const getMockSessionData = (sessionId: string): SessionData => ({
   sessionId,
   imageUrl: "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80",
   originalQuery: "My router keeps disconnecting. Can you identify the issue?",
   timestamp: new Date().toISOString(),
   response: {
      answer_type: "troubleshoot_steps",
      needs_clarification: false,
      cannot_comply_reason: null,
      device_info: {
         device_category: "Networking",
         device_type: "Wireless Router",
         brand: "TP-Link",
         model: "Archer AX6000",
         brand_model_guidance: "High-end WiFi 6 router with dual-band support",
         confidence: 0.92,
      },
      localization_results: [
         {
            target: "WAN Port",
            status: "found",
            bounding_box: { x_min: 0.1, y_min: 0.6, x_max: 0.2, y_max: 0.8 },
            spatial_description: "Left side, bottom section",
            landmark_description: "Near the power connector",
            reasoning: "Identified by blue coloring typical of WAN ports",
            suggested_action: "Check if cable is firmly connected",
            confidence: 0.95,
            disambiguation_needed: false,
         },
         {
            target: "Power LED",
            status: "found",
            bounding_box: { x_min: 0.4, y_min: 0.1, x_max: 0.5, y_max: 0.2 },
            spatial_description: "Front panel, center",
            landmark_description: "Front indicator LED strip",
            reasoning: "Green LED visible in power-on state",
            suggested_action: "Verify LED is solid green",
            confidence: 0.88,
            disambiguation_needed: false,
         },
         {
            target: "Reset Button",
            status: "not_visible",
            bounding_box: null,
            spatial_description: "Usually on the back or bottom",
            landmark_description: "Recessed pinhole button",
            reasoning: "Not visible from this angle",
            suggested_action: "Check the back panel for a small pinhole",
            confidence: 0.6,
            disambiguation_needed: false,
         },
         {
            target: "WiFi Antenna",
            status: "found",
            bounding_box: { x_min: 0.7, y_min: 0.2, x_max: 0.9, y_max: 0.7 },
            spatial_description: "Right side, external antennas",
            landmark_description: "Dual external antennas",
            reasoning: "External antennas clearly visible",
            suggested_action: "Ensure antennas are positioned properly",
            confidence: 0.98,
            disambiguation_needed: false,
         },
      ],
      diagnosis: {
         issue:
            "Intermittent disconnections may be caused by channel interference, firmware issues, or overheating. The router appears to be functioning but may need configuration adjustments.",
         severity: "medium",
         safety_warning: null,
         possible_causes: [
            "WiFi channel congestion from nearby networks",
            "Outdated firmware version",
            "Router overheating due to poor ventilation",
            "ISP connection instability",
         ],
         indicators: [
            "Frequent disconnections",
            "Slow speeds during peak hours",
            "Need to reboot often",
         ],
      },
      troubleshooting_steps: [
         {
            step: 1,
            instruction:
               "Power cycle your router by unplugging it for 30 seconds, then reconnecting the power.",
            visual_cue: "Wait for all LEDs to stabilize to solid green/blue",
            estimated_time: "2 minutes",
            overlay_reference: "power_led",
            safety_note: undefined,
         },
         {
            step: 2,
            instruction:
               "Check that the WAN cable (internet) is firmly connected to the blue WAN port.",
            visual_cue: "Look for a click when inserting the ethernet cable",
            estimated_time: "30 seconds",
            overlay_reference: "wan_port",
            safety_note: undefined,
         },
         {
            step: 3,
            instruction:
               "Access router settings at 192.168.0.1 and check for firmware updates.",
            visual_cue: "Look for 'Firmware Update' or 'System Update' in settings",
            estimated_time: "5 minutes",
            overlay_reference: null,
            safety_note: "Do not power off during firmware update",
         },
         {
            step: 4,
            instruction:
               "Change WiFi channel to a less congested one (try channels 1, 6, or 11 for 2.4GHz).",
            visual_cue: "Find 'Wireless Settings' > 'Channel' in router admin",
            estimated_time: "3 minutes",
            overlay_reference: null,
            safety_note: undefined,
         },
         {
            step: 5,
            instruction:
               "Ensure router has adequate ventilation - move away from walls and other electronics.",
            visual_cue: "Router should have at least 6 inches clearance on all sides",
            estimated_time: "1 minute",
            overlay_reference: null,
            safety_note: undefined,
         },
      ],
      visualizations: [
         {
            target: "WAN Port",
            bounding_box: { x_min: 0.1, y_min: 0.6, x_max: 0.2, y_max: 0.8 },
            arrow_hint: null,
            label: "WAN Port",
            landmark_description: "Blue ethernet port for internet connection",
            confidence: 0.95,
            overlay_id: "wan_port",
            disambiguation_needed: false,
            ambiguity_note: null,
         },
         {
            target: "Power LED",
            bounding_box: { x_min: 0.4, y_min: 0.1, x_max: 0.5, y_max: 0.2 },
            arrow_hint: null,
            label: "Power LED",
            landmark_description: "Status indicator on front panel",
            confidence: 0.88,
            overlay_id: "power_led",
            disambiguation_needed: false,
            ambiguity_note: null,
         },
         {
            target: "WiFi Antenna",
            bounding_box: { x_min: 0.7, y_min: 0.2, x_max: 0.9, y_max: 0.7 },
            arrow_hint: {
               from: { x: 0.65, y: 0.3 },
               to: { x: 0.75, y: 0.35 },
            },
            label: "WiFi Antenna",
            landmark_description: "External dual-band antennas",
            confidence: 0.98,
            overlay_id: "wifi_antenna",
            disambiguation_needed: false,
            ambiguity_note: null,
         },
      ],
      audio_instructions:
         "To fix your router disconnection issues, start by power cycling the router. Unplug it for 30 seconds, then reconnect. Next, check that your internet cable is firmly connected to the blue WAN port. Then access your router settings to check for firmware updates. Finally, try changing your WiFi channel and ensure proper ventilation around the router.",
      clarifying_questions: undefined,
      web_grounding_used: true,
      grounding_sources: [
         {
            id: "source-1",
            type: "manual",
            title: "TP-Link Archer AX6000 User Manual",
            url: "https://www.tp-link.com/us/support/download/archer-ax6000/",
            domain: "tp-link.com",
            excerpt: "When the power LED is off, check the power adapter connection. If the LED is flashing green, the system is starting up. Solid red indicates no internet connection.",
            relevance: "high",
            referenced_in_steps: [1, 2],
            published_date: "Jan 15, 2024",
         },
         {
            id: "source-2",
            type: "web",
            title: "How to Troubleshoot TP-Link Router Connection Issues",
            url: "https://community.tp-link.com/en/home/forum/topic/265432",
            domain: "community.tp-link.com",
            excerpt: "Many users report that changing the channel width to 40MHz stabilizes the 2.4GHz connection. Also ensure the firmware is up to date.",
            relevance: "medium",
            referenced_in_steps: [4],
            published_date: "Nov 20, 2023",
         },
         {
            id: "source-3",
            type: "video",
            title: "Fix WiFi Disconnecting Randomly - Router Settings",
            url: "https://youtube.com/watch?v=example",
            domain: "youtube.com",
            excerpt: "This video guide walks through the optimal settings for AX series routers to prevent random drops, including disabling Smart Connect.",
            relevance: "medium",
            referenced_in_steps: [3, 4],
            published_date: "Aug 10, 2023",
         }
      ] as any[], // Use any[] temporarily if TS complains about GroundingSource structure mismatch if not fully propagated
   },
});

// Empty state component when no session data
function EmptyState() {
   const router = useRouter();

   return (
      <motion.div
         initial={{ opacity: 0, y: 20 }}
         animate={{ opacity: 1, y: 0 }}
         className="flex items-center justify-center min-h-[500px]"
      >
         <div className="text-center space-y-6 max-w-md mx-auto">
            <div className="w-20 h-20 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto">
               <svg
                  className="w-10 h-10 text-accent"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
               >
                  <path
                     strokeLinecap="round"
                     strokeLinejoin="round"
                     strokeWidth={1.5}
                     d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
               </svg>
            </div>
            <div className="space-y-2">
               <h2 className="text-2xl font-display font-bold text-white">
                  No Analysis Results
               </h2>
               <p className="text-muted-foreground">
                  Submit an image and query from the Input Hub to see diagnostic results here.
               </p>
            </div>
            <button
               onClick={() => router.push("/dashboard")}
               className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 transition-colors"
            >
               <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
               >
                  <path
                     strokeLinecap="round"
                     strokeLinejoin="round"
                     strokeWidth={2}
                     d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                  />
               </svg>
               Go to Input Hub
            </button>
         </div>
      </motion.div>
   );
}

function ResultsContent() {
   const router = useRouter();
   const searchParams = useSearchParams();
   const tabParam = searchParams.get("tab");
   const activeTab = tabParam === "sources" ? "sources" : "steps";
   const sessionId = searchParams.get("session");

   const handleTabChange = (tab: "steps" | "sources") => {
      const params = new URLSearchParams(searchParams.toString());
      if (tab === "steps") {
         params.delete("tab");
      } else {
         params.set("tab", "sources");
      }
      router.push(`?${params.toString()}`, { scroll: false });
   };

   // State
   const [sessionData, setSessionData] = useState<SessionData | null>(null);
   const [loadingStage, setLoadingStage] = useState<LoadingStage>("device_recognition");
   const [isLoading, setIsLoading] = useState(false);
   const [isSubmittingFollowUp, setIsSubmittingFollowUp] = useState(false);
   const [error, setError] = useState<string | null>(null);
   const [highlightedComponent, setHighlightedComponent] = useState<string | null>(null);

   // Load session data when sessionId is present
   useEffect(() => {
      if (!sessionId) {
         setSessionData(null);
         setIsLoading(false);
         return;
      }

      const loadData = async () => {
         setIsLoading(true);
         setError(null);

         try {
            // Try to load from session storage first (real API results)
            const storedSession = getSession(sessionId);

            if (storedSession) {
               // Real data from backend
               console.log("[Results] Loaded session from storage:", sessionId);

               // Quick loading animation for better UX
               setLoadingStage("device_recognition");
               await new Promise((r) => setTimeout(r, 200));
               setLoadingStage("visual_analysis");
               await new Promise((r) => setTimeout(r, 200));
               setLoadingStage("diagnosis");
               await new Promise((r) => setTimeout(r, 150));
               setLoadingStage("action_steps");
               await new Promise((r) => setTimeout(r, 150));

               setSessionData(storedSession);
               setLoadingStage("complete");
            } else {
               // Fallback to mock data for development/testing
               console.warn("[Results] Session not found, using mock data for:", sessionId);

               // Full loading animation for mock data
               setLoadingStage("device_recognition");
               await new Promise((r) => setTimeout(r, 600));
               setLoadingStage("visual_analysis");
               await new Promise((r) => setTimeout(r, 600));
               setLoadingStage("diagnosis");
               await new Promise((r) => setTimeout(r, 500));
               setLoadingStage("action_steps");
               await new Promise((r) => setTimeout(r, 400));

               const data = getMockSessionData(sessionId);
               setSessionData(data);
               setLoadingStage("complete");
            }

            setIsLoading(false);
         } catch (err) {
            console.error("[Results] Error loading session:", err);
            setError("Failed to load results. Please try again.");
            setIsLoading(false);
         }
      };

      loadData();
   }, [sessionId]);

   // Handle follow-up query submission
   const handleFollowUpSubmit = async (query: string) => {
      setIsSubmittingFollowUp(true);
      try {
         // TODO: Implement actual API call
         // const response = await fetch('/api/troubleshoot', {
         //   method: 'POST',
         //   body: JSON.stringify({ query, sessionId, imageUrl: sessionData?.imageUrl })
         // });

         // Simulate API delay
         await new Promise((r) => setTimeout(r, 2000));

         console.log("Follow-up query:", query);
         // Handle response and update session data
      } catch (err) {
         console.error("Follow-up submission failed:", err);
      } finally {
         setIsSubmittingFollowUp(false);
      }
   };

   // Handle clarifying question selection
   const handleClarifyingSubmit = async (selectedOption: string) => {
      setIsSubmittingFollowUp(true);
      try {
         console.log("Selected option:", selectedOption);
         await new Promise((r) => setTimeout(r, 2000));
      } catch (err) {
         console.error("Clarifying submission failed:", err);
      } finally {
         setIsSubmittingFollowUp(false);
      }
   };

   // Handle retry/upload new actions
   const handleRetry = () => {
      if (sessionId) {
         setSessionData(null);
         setIsLoading(true);
         // Re-trigger load
         window.location.reload();
      }
   };

   const handleUploadNew = () => {
      router.push("/dashboard");
   };

   // Handle component highlighting
   const handleComponentClick = useCallback(
      (component: Visualization | LocalizationResult) => {
         const id = "overlay_id" in component ? component.overlay_id : component.target;
         setHighlightedComponent(id);
      },
      []
   );

   const handleStepComplete = useCallback((stepNumber: number) => {
      console.log(`Step ${stepNumber} completed`);
   }, []);

   const handleComponentHighlight = useCallback((overlayRef: string) => {
      setHighlightedComponent(overlayRef);
      // Scroll to image if needed
      document.getElementById("ar-canvas")?.scrollIntoView({ behavior: "smooth" });
   }, []);

   // No session - show empty state
   if (!sessionId && !isLoading && !sessionData) {
      return (
         <div className="space-y-6">
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
               <p className="text-muted-foreground text-lg">
                  View diagnostic results and repair recommendations
               </p>
            </div>
            <EmptyState />
         </div>
      );
   }

   // Loading state
   if (isLoading) {
      return (
         <div className="space-y-6">
            <LoadingProgress stage={loadingStage} />
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
               <p className="text-muted-foreground text-lg">
                  Analyzing your device...
               </p>
            </div>
            <LoadingSkeleton />
         </div>
      );
   }

   // Error state
   if (error || !sessionData) {
      return (
         <div className="space-y-6">
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
               <p className="text-muted-foreground text-lg">
                  {error || "Results not found"}
               </p>
            </div>
            <div className="flex justify-center pt-8">
               <button
                  onClick={handleUploadNew}
                  className="text-accent hover:underline"
               >
                  Go back to Input Hub
               </button>
            </div>
         </div>
      );
   }

   const { response } = sessionData;
   const { answer_type, cannot_comply_reason } = response;

   // Render special states
   if (answer_type === "safety_warning_only" && response.diagnosis?.safety_warning) {
      return (
         <div className="space-y-6">
            <LoadingProgress stage="complete" isComplete />
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
            </div>
            <SafetyWarningOnly
               safetyMessage={response.diagnosis.safety_warning}
               onContactProfessional={() => { }}
            />
         </div>
      );
   }

   if (answer_type === "reject_invalid_image" || answer_type === "ask_for_better_input") {
      return (
         <div className="space-y-6">
            <LoadingProgress stage="complete" isComplete />
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
            </div>
            <InvalidImagePanel
               reason={cannot_comply_reason}
               explanation={response.diagnosis?.issue}
               onRetry={handleRetry}
               onUploadNew={handleUploadNew}
            />
         </div>
      );
   }

   if (answer_type === "ask_clarifying_questions" && response.clarifying_questions) {
      return (
         <div className="space-y-6">
            <LoadingProgress stage="complete" isComplete />
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
            </div>
            <ClarifyingQuestions
               questions={response.clarifying_questions}
               mainMessage="Your question covers multiple topics. Which would you like help with first?"
               onSubmit={handleClarifyingSubmit}
               isLoading={isSubmittingFollowUp}
            />
         </div>
      );
   }

   // Main results view
   return (
      <div className="space-y-6 pb-32">
         {/* Page Header */}
         <div className="space-y-2">
            <h1 className="text-4xl font-display font-bold text-foreground">
               Results
            </h1>
            <div className="flex items-center gap-3">
               <p className="text-muted-foreground text-lg">
                  {response.device_info.device_type}
                  {response.device_info.brand && ` • ${response.device_info.brand}`}
                  {response.device_info.model && ` ${response.device_info.model}`}
               </p>
               {response.device_info.confidence && (
                  <div className={`
                    flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-sm font-medium border
                    ${response.device_info.confidence > 0.8
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : response.device_info.confidence > 0.5
                           ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                           : "bg-red-500/10 text-red-400 border-red-500/20"
                     }
                  `}>
                     <div className={`w-1.5 h-1.5 rounded-full ${response.device_info.confidence > 0.8
                        ? "bg-emerald-400"
                        : response.device_info.confidence > 0.5
                           ? "bg-amber-400"
                           : "bg-red-400"
                        }`} />
                     {Math.round(response.device_info.confidence * 100)}%
                  </div>
               )}
            </div>
         </div>

         {/* Status Banner */}
         <StatusBanner
            answerType={answer_type}
            deviceInfo={response.device_info}
            cannotComplyReason={cannot_comply_reason}
            onRetry={handleRetry}
            onUploadNew={handleUploadNew}
         />

         {/* Main Content */}
         <AnimatePresence mode="wait">
            <motion.div
               key="results"
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               className="space-y-8"
            >
               {/* Two Column Layout on Desktop */}
               <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Left Column - AR Image Canvas */}
                  <div className="" id="ar-canvas">
                     <ARImageCanvas
                        imageUrl={sessionData.imageUrl}
                        visualizations={response.visualizations}
                        localizationResults={response.localization_results}
                        highlightedId={highlightedComponent}
                        onComponentClick={handleComponentClick}
                     />
                  </div>

                  {/* Right Column - Info Panels */}
                  <div className="space-y-6">
                     {/* Success Info */}
                     <SuccessInfoPanel
                        answerType={answer_type}
                        deviceInfo={response.device_info}
                        localizationResults={response.localization_results}
                     />

                     {/* Diagnosis */}
                     <DiagnosisPanel
                        diagnosis={response.diagnosis}
                        cannotComplyReason={cannot_comply_reason}
                     />

                     {/* Components Detected */}
                     <ComponentsDetected
                        components={response.localization_results}
                        onComponentClick={(c) => handleComponentClick(c)}
                        onHighlightInImage={(c) => handleComponentHighlight(c.target)}
                     />
                  </div>
               </div>

               {/* Tab Navigation & Content Area */}
               <div className="space-y-6">
                  {/* Tabs */}
                  <div className="border-b border-border/40">
                     <div className="flex items-center gap-8">
                        <button
                           onClick={() => handleTabChange("steps")}
                           className={`pb-4 text-base font-medium transition-all relative ${activeTab === "steps"
                              ? "text-accent"
                              : "text-muted-foreground hover:text-foreground"
                              }`}
                        >
                           Repair Steps
                           {activeTab === "steps" && (
                              <motion.div
                                 layoutId="activeTab"
                                 className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
                              />
                           )}
                        </button>

                        <button
                           onClick={() => handleTabChange("sources")}
                           className={`pb-4 text-base font-medium transition-all relative ${activeTab === "sources"
                              ? "text-accent"
                              : "text-muted-foreground hover:text-foreground"
                              }`}
                        >
                           Sources
                           {response.grounding_sources && response.grounding_sources.length > 0 && (
                              <span className="ml-2 px-1.5 py-0.5 rounded-full bg-accent/10 text-xs font-semibold">
                                 {response.grounding_sources.length}
                              </span>
                           )}
                           {activeTab === "sources" && (
                              <motion.div
                                 layoutId="activeTab"
                                 className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
                              />
                           )}
                        </button>
                     </div>
                  </div>

                  {/* Tab Content */}
                  <div className="min-h-[400px]">
                     <AnimatePresence mode="wait">
                        {activeTab === "steps" ? (
                           <motion.div
                              key="steps"
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              transition={{ duration: 0.2 }}
                           >
                              {response.troubleshooting_steps && response.troubleshooting_steps.length > 0 ? (
                                 <RepairSteps
                                    steps={response.troubleshooting_steps}
                                    answerType={answer_type}
                                    audioInstructions={response.audio_instructions}
                                    onStepComplete={handleStepComplete}
                                    onComponentHighlight={handleComponentHighlight}
                                 />
                              ) : (
                                 <div className="text-center py-12 text-muted-foreground">
                                    No repair steps available.
                                 </div>
                              )}
                           </motion.div>
                        ) : (
                           <motion.div
                              key="sources"
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              transition={{ duration: 0.2 }}
                           >
                              {response.grounding_sources ? (
                                 <SourcesList
                                    sources={response.grounding_sources}
                                    onReferenceClick={(step) => {
                                       handleTabChange("steps");
                                       // Scroll to steps area if needed, or implement highlight logic
                                    }}
                                 />
                              ) : (
                                 /* Empty State for Sources */
                                 <div className="flex flex-col items-center justify-center py-16 text-center space-y-4 bg-secondary/10 rounded-xl border border-white/5">
                                    <div className="w-12 h-12 rounded-full bg-secondary/30 flex items-center justify-center text-muted-foreground">
                                       <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                       </svg>
                                    </div>
                                    <div className="space-y-1">
                                       <h3 className="text-lg font-medium text-white">Sources Currently Unavailable</h3>
                                       <p className="text-muted-foreground max-w-md mx-auto">
                                          We couldn't retrieve external sources at this time. The repair steps use general knowledge for this device type.
                                       </p>
                                    </div>
                                    <div className="pt-2 flex flex-col items-center gap-2 text-sm text-accent">
                                       <span>For your specific model, please consult:</span>
                                       <div className="flex gap-4">
                                          <span className="flex items-center gap-1">
                                             <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                             Manufacturer Documentation
                                          </span>
                                          <span className="flex items-center gap-1">
                                             <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>
                                             Device Support Page
                                          </span>
                                       </div>
                                    </div>
                                 </div>
                              )}
                           </motion.div>
                        )}
                     </AnimatePresence>
                  </div>
               </div>
            </motion.div>
         </AnimatePresence>

         {/* Follow-up Input - Sticky Bottom */}
         {/* <FollowUpInput
            sessionId={sessionId || ""}
            isLoading={isSubmittingFollowUp}
            onSubmit={handleFollowUpSubmit}
         /> */}
      </div>
   );
}

export default function ResultsPage() {
   return (
      <Suspense fallback={
         <div className="space-y-6">
            <LoadingProgress stage="device_recognition" />
            <div className="space-y-2">
               <h1 className="text-4xl font-display font-bold text-foreground">
                  Results
               </h1>
               <p className="text-muted-foreground text-lg">
                  Loading results...
               </p>
            </div>
            <LoadingSkeleton />
         </div>
      }>
         <ResultsContent />
      </Suspense>
   );
}
