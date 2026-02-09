"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Check, Eye, AlertCircle, HelpCircle, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LocalizationResult, ComponentStatus } from "@/types/api-response";

interface ComponentsDetectedProps {
   components: LocalizationResult[];
   onComponentClick?: (component: LocalizationResult) => void;
   onHighlightInImage?: (component: LocalizationResult) => void;
}

type FilterType = "all" | "found" | "not_found";

const STATUS_CONFIG: Record<
   ComponentStatus,
   { icon: React.ReactNode; label: string; color: string; bg: string }
> = {
   found: {
      icon: <Check className="w-3.5 h-3.5" />,
      label: "Found",
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
   },
   not_visible: {
      icon: <Eye className="w-3.5 h-3.5" />,
      label: "Not Visible",
      color: "text-amber-400",
      bg: "bg-amber-500/10",
   },
   not_present: {
      icon: <X className="w-3.5 h-3.5" />,
      label: "Not Present",
      color: "text-red-400",
      bg: "bg-red-500/10",
   },
   ambiguous: {
      icon: <HelpCircle className="w-3.5 h-3.5" />,
      label: "Ambiguous",
      color: "text-orange-400",
      bg: "bg-orange-500/10",
   },
};

export function ComponentsDetected({
   components,
   onComponentClick,
   onHighlightInImage,
}: ComponentsDetectedProps) {
   const [isExpanded, setIsExpanded] = useState(false);
   const [filter, setFilter] = useState<FilterType>("all");

   const filteredComponents = useMemo(() => {
      if (!components) return [];
      switch (filter) {
         case "found":
            return components.filter((c) => c.status === "found");
         case "not_found":
            return components.filter((c) => c.status !== "found");
         default:
            return components;
      }
   }, [components, filter]);

   const counts = useMemo(() => ({
      all: components?.length ?? 0,
      found: components?.filter((c) => c.status === "found").length ?? 0,
      not_found: components?.filter((c) => c.status !== "found").length ?? 0,
   }), [components]);

   // Auto-expand on desktop
   const handleToggle = () => {
      setIsExpanded((prev) => !prev);
   };

   if (!components || components.length === 0) {
      return (
         <Card className="border-border/50 bg-secondary/30">
            <CardContent className="py-8 text-center">
               <AlertCircle className="w-10 h-10 text-white/30 mx-auto mb-3" />
               <p className="text-white/50">No components were identified</p>
            </CardContent>
         </Card>
      );
   }

   return (
      <motion.div
         initial={{ opacity: 0, y: 20 }}
         animate={{ opacity: 1, y: 0 }}
         transition={{ delay: 0.25 }}
      >
         <Card className="border-border/50 bg-secondary/30 overflow-hidden">
            {/* Header - Clickable to expand */}
            <CardHeader
               className="cursor-pointer hover:bg-white/5 transition-colors"
               onClick={handleToggle}
            >
               <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-white/90">
                     {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-white/50" />
                     ) : (
                        <ChevronDown className="w-5 h-5 text-white/50" />
                     )}
                     Components Detected
                     <span className="ml-1 px-2 py-0.5 rounded-full bg-accent/20 text-accent text-sm font-normal">
                        {components.length}
                     </span>
                  </CardTitle>

                  {/* Quick Stats */}
                  <div className="flex items-center gap-2">
                     <span className="flex items-center gap-1 text-xs text-emerald-400">
                        <Check className="w-3 h-3" />
                        {counts.found}
                     </span>
                     {counts.not_found > 0 && (
                        <span className="flex items-center gap-1 text-xs text-amber-400">
                           <AlertCircle className="w-3 h-3" />
                           {counts.not_found}
                        </span>
                     )}
                  </div>
               </div>
            </CardHeader>

            {/* Expanded Content */}
            <AnimatePresence>
               {isExpanded && (
                  <motion.div
                     initial={{ height: 0 }}
                     animate={{ height: "auto" }}
                     exit={{ height: 0 }}
                     transition={{ duration: 0.3 }}
                     className="overflow-hidden"
                  >
                     <CardContent className="pt-0 space-y-4">
                        {/* Filter Buttons */}
                        <div className="flex items-center gap-2">
                           {(["all", "found", "not_found"] as FilterType[]).map((f) => (
                              <Button
                                 key={f}
                                 variant={filter === f ? "default" : "secondary"}
                                 size="sm"
                                 onClick={() => setFilter(f)}
                                 className="capitalize"
                              >
                                 {f === "not_found" ? "Not Found" : f}
                                 <span className="ml-1.5 text-xs opacity-70">
                                    ({counts[f]})
                                 </span>
                              </Button>
                           ))}
                        </div>

                        {/* Components Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                           {filteredComponents.map((component, index) => {
                              const config = STATUS_CONFIG[component.status];

                              return (
                                 <motion.div
                                    key={component.target + index}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                    className={`
                          p-3 rounded-lg border border-white/10 
                          hover:border-accent/30 hover:bg-white/5
                          transition-all cursor-pointer group
                          ${config.bg}
                        `}
                                    onClick={() => onComponentClick?.(component)}
                                 >
                                    <div className="flex items-start justify-between gap-2">
                                       <div className="flex-1 min-w-0">
                                          {/* Component Name */}
                                          <h4 className="font-medium text-white/90 truncate">
                                             {component.target}
                                          </h4>

                                          {/* Status Badge */}
                                          <div
                                             className={`
                                inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-xs
                                ${config.bg} ${config.color}
                              `}
                                          >
                                             {config.icon}
                                             {config.label}
                                          </div>

                                          {/* Spatial Hint */}
                                          {component.spatial_description && (
                                             <p className="text-xs text-white/50 mt-1.5 line-clamp-1">
                                                {component.spatial_description}
                                             </p>
                                          )}
                                       </div>

                                       {/* Highlight Button */}
                                       {component.status === "found" && component.bounding_box && (
                                          <Button
                                             variant="ghost"
                                             size="icon"
                                             className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                                             onClick={(e) => {
                                                e.stopPropagation();
                                                onHighlightInImage?.(component);
                                             }}
                                          >
                                             <Eye className="w-4 h-4" />
                                          </Button>
                                       )}
                                    </div>

                                    {/* Confidence Bar */}
                                    <div className="mt-3">
                                       <div className="flex items-center justify-between text-xs text-white/40 mb-1">
                                          <span>Confidence</span>
                                          <span>{Math.round(component.confidence * 100)}%</span>
                                       </div>
                                       <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                          <motion.div
                                             initial={{ width: 0 }}
                                             animate={{ width: `${component.confidence * 100}%` }}
                                             transition={{ delay: index * 0.05 + 0.2 }}
                                             className={`h-full rounded-full ${component.confidence >= 0.8
                                                ? "bg-emerald-500"
                                                : component.confidence >= 0.5
                                                   ? "bg-amber-500"
                                                   : "bg-red-500"
                                                }`}
                                          />
                                       </div>
                                    </div>

                                    {/* Disambiguation Warning */}
                                    {component.disambiguation_needed && (
                                       <div className="flex items-center gap-1.5 mt-2 text-xs text-orange-400">
                                          <HelpCircle className="w-3 h-3" />
                                          Needs clarification
                                       </div>
                                    )}
                                 </motion.div>
                              );
                           })}
                        </div>

                        {/* Empty State for Filter */}
                        {filteredComponents.length === 0 && (
                           <div className="text-center py-6">
                              <p className="text-white/50 text-sm">
                                 No components match this filter
                              </p>
                           </div>
                        )}
                     </CardContent>
                  </motion.div>
               )}
            </AnimatePresence>
         </Card>
      </motion.div>
   );
}
