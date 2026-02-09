import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GroundingSource } from "@/types/api-response";

interface SourcesListProps {
   sources: GroundingSource[];
   onSourceClick?: (source: GroundingSource) => void;
   onReferenceClick?: (stepNumber: number) => void;
}

export function SourcesList({ sources, onSourceClick, onReferenceClick }: SourcesListProps) {
   const [filter, setFilter] = useState<string>("all");

   const filteredSources = (sources || []).filter((source) => {
      if (filter === "all") return true;
      return source.type === filter;
   });

   const getSourceIcon = (type: GroundingSource["type"]) => {
      switch (type) {
         case "manual": return "📄";
         case "web": return "🌐";
         case "video": return "🎥";
         case "forum": return "💬";
         case "pdf": return "📑";
         case "knowledge_base": return "🧠";
         default: return "🔗";
      }
   };

   const getRelevanceColor = (relevance: GroundingSource["relevance"]) => {
      switch (relevance) {
         case "high": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
         case "medium": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
         case "low": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      }
   };

   return (
      <div className="space-y-6">
         {/* Header */}
         <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
               <h2 className="text-xl font-semibold text-white">Reference Materials</h2>
               <span className="px-2 py-0.5 rounded-full bg-white/10 text-xs font-medium text-white/70">
                  {sources?.length || 0} sources
               </span>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1 bg-secondary/30 p-1 rounded-lg overflow-x-auto">
               {["all", "manual", "web", "forum", "video"].map((type) => (
                  <button
                     key={type}
                     onClick={() => setFilter(type)}
                     className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap ${filter === type
                        ? "bg-accent text-white shadow-sm"
                        : "text-muted-foreground hover:text-white hover:bg-white/5"
                        }`}
                  >
                     {type === "all" ? "All Sources" : type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
               ))}
            </div>
         </div>

         {/* Sources List */}
         <div className="space-y-4">
            <AnimatePresence mode="popLayout">
               {filteredSources.map((source) => (
                  <SourceCard
                     key={source.id}
                     source={source}
                     icon={getSourceIcon(source.type)}
                     relevanceColor={getRelevanceColor(source.relevance)}
                     onReferenceClick={onReferenceClick}
                  />
               ))}
            </AnimatePresence>

            {filteredSources.length === 0 && (
               <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-12 text-muted-foreground bg-secondary/10 rounded-xl border border-white/5"
               >
                  <p>No sources found for this category.</p>
               </motion.div>
            )}
         </div>
      </div>
   );
}

function SourceCard({
   source,
   icon,
   relevanceColor,
   onReferenceClick
}: {
   source: GroundingSource;
   icon: string;
   relevanceColor: string;
   onReferenceClick?: (step: number) => void;
}) {
   const [isExpanded, setIsExpanded] = useState(false);
   const [copied, setCopied] = useState(false);

   const handleCopy = () => {
      navigator.clipboard.writeText(source.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
   };

   return (
      <motion.div
         layout
         initial={{ opacity: 0, y: 10 }}
         animate={{ opacity: 1, y: 0 }}
         exit={{ opacity: 0, scale: 0.95 }}
         className="group relative p-5 rounded-xl bg-card border border-border/50 hover:border-accent/30 transition-all hover:bg-card/80"
      >
         <div className="flex flex-col gap-4">
            {/* Header Row */}
            <div className="flex items-start justify-between gap-4">
               <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                     <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/5 text-xs font-medium text-white/70 border border-white/10 uppercase tracking-wider">
                        {icon} {source.type}
                     </span>
                     <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md border ${relevanceColor}`}>
                        {source.relevance === "high" && "★★★★★"}
                        {source.relevance === "medium" && "★★★☆☆"}
                        {source.relevance === "low" && "★☆☆☆☆"}
                        <span className="ml-1 capitalize">{source.relevance} Relevance</span>
                     </span>
                  </div>

                  <a
                     href={source.url}
                     target="_blank"
                     rel="noopener noreferrer"
                     className="block text-lg font-semibold text-white group-hover:text-accent transition-colors"
                  >
                     {source.title}
                  </a>

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                     {source.favicon_url && <img src={source.favicon_url} alt="" className="w-3 h-3 rounded-sm" />}
                     <span className="font-medium text-white/60">{source.domain}</span>
                     {source.published_date && (
                        <>
                           <span>•</span>
                           <span>{source.published_date}</span>
                        </>
                     )}
                  </div>
               </div>

               <div className="flex gap-2 shrink-0">
                  <button
                     onClick={handleCopy}
                     className="p-2 rounded-lg bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-white transition-colors"
                     title="Copy Link"
                  >
                     {copied ? "✓" : (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                     )}
                  </button>
                  <a
                     href={source.url}
                     target="_blank"
                     rel="noopener noreferrer"
                     className="p-2 rounded-lg bg-accent/10 text-accent hover:bg-accent hover:text-white transition-colors"
                     title="Open Source"
                  >
                     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                     </svg>
                  </a>
               </div>
            </div>

            {/* Excerpt */}
            <div className="bg-secondary/20 p-3 rounded-lg border border-white/5">
               <p className={`text-sm text-neutral-300 leading-relaxed ${!isExpanded && "line-clamp-2"}`}>
                  "{source.excerpt}"
               </p>
               {source.excerpt.length > 150 && (
                  <button
                     onClick={() => setIsExpanded(!isExpanded)}
                     className="text-xs font-medium text-accent hover:underline mt-1"
                  >
                     {isExpanded ? "Show less" : "Read more"}
                  </button>
               )}
            </div>

            {/* Footer - Used In */}
            {source.referenced_in_steps && source.referenced_in_steps.length > 0 && (
               <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                  <span className="text-xs text-muted-foreground">Referenced in:</span>
                  <div className="flex flex-wrap gap-1.5">
                     {source.referenced_in_steps.map((step) => (
                        <button
                           key={step}
                           onClick={() => onReferenceClick?.(step)}
                           className="px-2 py-0.5 rounded-md bg-white/5 text-xs text-neutral-300 hover:bg-accent/20 hover:text-accent transition-colors border border-dashed border-white/10 hover:border-accent/40"
                        >
                           Step {step}
                        </button>
                     ))}
                  </div>
               </div>
            )}
         </div>
      </motion.div>
   );
}
