"use client";

import { motion } from "framer-motion";
import { ChevronDown, ChevronUp, Cpu, ArrowRight, Info } from "lucide-react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Explanation } from "@/types/api-response";

interface ExplanationSectionProps {
   explanation: Explanation;
}

export function ExplanationSection({ explanation }: ExplanationSectionProps) {
   const [expandedSections, setExpandedSections] = useState<Set<string>>(
      new Set(["overview"])
   );

   if (!explanation) return null;

   const toggleSection = (section: string) => {
      setExpandedSections((prev) => {
         const newSet = new Set(prev);
         if (newSet.has(section)) {
            newSet.delete(section);
         } else {
            newSet.add(section);
         }
         return newSet;
      });
   };

   return (
      <motion.div
         initial={{ opacity: 0, y: 20 }}
         animate={{ opacity: 1, y: 0 }}
         transition={{ delay: 0.35 }}
         className="space-y-4"
      >
         <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="text-2xl">📚</span>
            How It Works
         </h2>

         <Card className="border-border/50 bg-secondary/30">
            <CardContent className="p-0 divide-y divide-white/10">
               {/* Overview Section */}
               <div>
                  <button
                     onClick={() => toggleSection("overview")}
                     className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                  >
                     <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center">
                           <Info className="w-4 h-4 text-accent" />
                        </div>
                        <span className="font-medium text-white/90">Overview</span>
                     </div>
                     {expandedSections.has("overview") ? (
                        <ChevronUp className="w-5 h-5 text-white/50" />
                     ) : (
                        <ChevronDown className="w-5 h-5 text-white/50" />
                     )}
                  </button>
                  {expandedSections.has("overview") && (
                     <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-4 pb-4"
                     >
                        <p className="text-white/70 leading-relaxed pl-11">
                           {explanation.overview}
                        </p>
                     </motion.div>
                  )}
               </div>

               {/* Component Functions Section */}
               {explanation.component_functions &&
                  explanation.component_functions.length > 0 && (
                     <div>
                        <button
                           onClick={() => toggleSection("components")}
                           className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                        >
                           <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                                 <Cpu className="w-4 h-4 text-emerald-400" />
                              </div>
                              <span className="font-medium text-white/90">
                                 Component Functions
                              </span>
                              <span className="text-xs text-white/50 px-2 py-0.5 rounded-full bg-white/10">
                                 {explanation.component_functions.length}
                              </span>
                           </div>
                           {expandedSections.has("components") ? (
                              <ChevronUp className="w-5 h-5 text-white/50" />
                           ) : (
                              <ChevronDown className="w-5 h-5 text-white/50" />
                           )}
                        </button>
                        {expandedSections.has("components") && (
                           <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="px-4 pb-4"
                           >
                              <div className="pl-11 space-y-3">
                                 {explanation.component_functions.map((comp, index) => (
                                    <motion.div
                                       key={index}
                                       initial={{ opacity: 0, x: -10 }}
                                       animate={{ opacity: 1, x: 0 }}
                                       transition={{ delay: index * 0.05 }}
                                       className="p-3 rounded-lg bg-white/5 border border-white/10"
                                    >
                                       <h4 className="font-medium text-white/90 mb-1">
                                          {comp.name}
                                       </h4>
                                       <p className="text-sm text-white/60">
                                          {comp.description}
                                       </p>
                                    </motion.div>
                                 ))}
                              </div>
                           </motion.div>
                        )}
                     </div>
                  )}

               {/* Data Flow Section */}
               {explanation.data_flow && (
                  <div>
                     <button
                        onClick={() => toggleSection("dataflow")}
                        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                     >
                        <div className="flex items-center gap-3">
                           <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                              <ArrowRight className="w-4 h-4 text-blue-400" />
                           </div>
                           <span className="font-medium text-white/90">Data Flow</span>
                        </div>
                        {expandedSections.has("dataflow") ? (
                           <ChevronUp className="w-5 h-5 text-white/50" />
                        ) : (
                           <ChevronDown className="w-5 h-5 text-white/50" />
                        )}
                     </button>
                     {expandedSections.has("dataflow") && (
                        <motion.div
                           initial={{ height: 0, opacity: 0 }}
                           animate={{ height: "auto", opacity: 1 }}
                           exit={{ height: 0, opacity: 0 }}
                           className="px-4 pb-4"
                        >
                           <p className="text-white/70 leading-relaxed pl-11">
                              {explanation.data_flow}
                           </p>
                        </motion.div>
                     )}
                  </div>
               )}
            </CardContent>
         </Card>
      </motion.div>
   );
}
