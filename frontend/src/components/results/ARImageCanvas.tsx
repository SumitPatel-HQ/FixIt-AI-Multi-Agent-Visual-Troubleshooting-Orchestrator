"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
   ZoomIn,
   ZoomOut,
   RotateCcw,
   Tag,
   Square,
   Maximize2,
   X,
   ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
   Visualization,
   LocalizationResult,
   ComponentStatus,
} from "@/types/api-response";

interface ARImageCanvasProps {
   imageUrl: string;
   visualizations: Visualization[];
   localizationResults: LocalizationResult[];
   highlightedId?: string | null;
   onComponentClick?: (component: Visualization | LocalizationResult) => void;
}

const STATUS_COLORS: Record<ComponentStatus, { border: string; bg: string; text: string }> = {
   found: {
      border: "stroke-emerald-500",
      bg: "bg-emerald-500/20",
      text: "text-emerald-400",
   },
   not_visible: {
      border: "stroke-amber-500",
      bg: "bg-amber-500/20",
      text: "text-amber-400",
   },
   not_present: {
      border: "stroke-blue-500",
      bg: "bg-blue-500/20",
      text: "text-blue-400",
   },
   ambiguous: {
      border: "stroke-orange-500",
      bg: "bg-orange-500/20",
      text: "text-orange-400",
   },
};

export function ARImageCanvas({
   imageUrl,
   visualizations,
   localizationResults,
   highlightedId,
   onComponentClick,
}: ARImageCanvasProps) {
   const containerRef = useRef<HTMLDivElement>(null);
   const [zoom, setZoom] = useState(1);
   const [position, setPosition] = useState({ x: 0, y: 0 });
   const [isDragging, setIsDragging] = useState(false);
   const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
   const [showLabels, setShowLabels] = useState(true);
   const [showBoxes, setShowBoxes] = useState(true);
   const [isFullscreen, setIsFullscreen] = useState(false);
   const [selectedComponent, setSelectedComponent] = useState<
      Visualization | LocalizationResult | null
   >(null);
   const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });

   // Safely get visualizations array (may be null from API)
   const safeVisualizations = visualizations || [];
   const safeLocalizationResults = localizationResults || [];

   // Calculate component position in percentage with safety checks
   const getComponentStyle = (bbox: any, _isRetry = false) => {
      if (!bbox || typeof bbox !== 'object') return null;

      // Extract and validate numeric values immediately
      const x_min = Number(bbox.x_min);
      const y_min = Number(bbox.y_min);
      const x_max = Number(bbox.x_max);
      const y_max = Number(bbox.y_max);

      // Robust validation: check for missing, non-numeric, or NaN values
      if (
         isNaN(x_min) || isNaN(y_min) || isNaN(x_max) || isNaN(y_max)
      ) {
         // Silently skip - this is usually just empty or partial data
         return null;
      }

      // Check if coordinates are in expected 0-1 range
      // We allow a tiny margin for rounding errors (-0.05 to 1.05)
      const isNormalized =
         x_min >= -0.05 && x_max <= 1.05 &&
         y_min >= -0.05 && y_max <= 1.05;

      if (!isNormalized) {
         // If already retried, stop recursion to prevent infinite loops
         if (_isRetry) return null;

         // If not normalized, we MUST have image dimensions to convert pixels to %
         if (!imageDimensions.width || !imageDimensions.height) {
            console.debug("⏳ Waiting for image dimensions to compute pixel-based style for:", bbox);
            return null;
         }

         // Convert pixels to normalized 0-1
         const normBbox = {
            x_min: x_min / imageDimensions.width,
            y_min: y_min / imageDimensions.height,
            x_max: x_max / imageDimensions.width,
            y_max: y_max / imageDimensions.height,
         };
         return getComponentStyle(normBbox, true);
      }

      // At this point we have normalized coordinates

      // Validate box has area (prevents division by zero or invisible boxes)
      if (x_min >= x_max || y_min >= y_max) {
         console.warn("⚠️ Skipping zero-area or inverted bbox:", bbox);
         return null;
      }

      // CRITICAL FIX: Container has aspectRatio CSS matching the image,
      // so NO letterboxing occurs! Simply convert normalized coords to percentages.
      // The container and image are perfectly aligned, so 0-1 coords map directly to 0-100%.

      return {
         left: `${x_min * 100}%`,
         top: `${y_min * 100}%`,
         width: `${(x_max - x_min) * 100}%`,
         height: `${(y_max - y_min) * 100}%`,
      };
   };

   const handleZoomIn = () => {
      setZoom((prev) => Math.min(prev + 0.25, 3));
   };

   const handleZoomOut = () => {
      setZoom((prev) => Math.max(prev - 0.25, 0.5));
   };

   const handleReset = () => {
      setZoom(1);
      setPosition({ x: 0, y: 0 });
   };

   const handleMouseDown = (e: React.MouseEvent) => {
      if (zoom > 1) {
         setIsDragging(true);
         setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
      }
   };

   const handleMouseMove = (e: React.MouseEvent) => {
      if (isDragging && zoom > 1) {
         setPosition({
            x: e.clientX - dragStart.x,
            y: e.clientY - dragStart.y,
         });
      }
   };

   const handleMouseUp = () => {
      setIsDragging(false);
   };

   const handleWheel = useCallback((e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoom((prev) => Math.min(Math.max(prev + delta, 0.5), 3));
   }, []);

   useEffect(() => {
      const container = containerRef.current;
      if (container) {
         container.addEventListener("wheel", handleWheel, { passive: false });
         return () => container.removeEventListener("wheel", handleWheel);
      }
   }, [handleWheel]);

   const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
      const img = e.currentTarget;
      const dimensions = {
         width: img.naturalWidth,
         height: img.naturalHeight,
      };
      setImageDimensions(dimensions);

      console.log("🖼️ Image loaded:", dimensions);
      console.log("📦 Visualizations received:", safeVisualizations.length);
      safeVisualizations.forEach((viz, i) => {
         if (viz.bounding_box) {
            console.log(`  [${i}] ${viz.label}:`, viz.bounding_box);
         }
      });
   };

   const handleComponentClick = (comp: Visualization | LocalizationResult) => {
      setSelectedComponent(comp);
      onComponentClick?.(comp);
   };

   const toggleFullscreen = () => {
      setIsFullscreen((prev) => !prev);
   };

   const getStatusFromComponent = (
      comp: Visualization | LocalizationResult
   ): ComponentStatus => {
      if ("status" in comp) {
         return comp.status;
      }
      return "found";
   };

   return (
      <>
         {/* Main Canvas Container */}
         <div className="space-y-3">
            {/* Section Title */}
            <div className="flex items-center justify-between">
               <h3 className="text-lg font-semibold text-white/90">Visual Analysis</h3>
               <span className="text-xs text-white/50">
                  {safeVisualizations.length} component{safeVisualizations.length !== 1 ? "s" : ""} detected
               </span>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-2 pb-2">
               <div className="flex items-center gap-1 bg-secondary/50 rounded-lg p-1">
                  <Button
                     variant="ghost"
                     size="icon"
                     onClick={handleZoomIn}
                     className="h-8 w-8"
                     title="Zoom In"
                  >
                     <ZoomIn className="w-4 h-4" />
                  </Button>
                  <Button
                     variant="ghost"
                     size="icon"
                     onClick={handleZoomOut}
                     className="h-8 w-8"
                     title="Zoom Out"
                  >
                     <ZoomOut className="w-4 h-4" />
                  </Button>
                  <Button
                     variant="ghost"
                     size="icon"
                     onClick={handleReset}
                     className="h-8 w-8"
                     title="Reset View"
                  >
                     <RotateCcw className="w-4 h-4" />
                  </Button>
               </div>

               <div className="flex items-center gap-1 bg-secondary/50 rounded-lg p-1">
                  <Button
                     variant={showLabels ? "default" : "ghost"}
                     size="sm"
                     onClick={() => setShowLabels(!showLabels)}
                     className="h-8 gap-1.5"
                  >
                     <Tag className="w-3.5 h-3.5" />
                     <span className="hidden sm:inline text-xs">Labels</span>
                  </Button>
                  <Button
                     variant={showBoxes ? "default" : "ghost"}
                     size="sm"
                     onClick={() => setShowBoxes(!showBoxes)}
                     className="h-8 gap-1.5"
                  >
                     <Square className="w-3.5 h-3.5" />
                     <span className="hidden sm:inline text-xs">Boxes</span>
                  </Button>
               </div>

               <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleFullscreen}
                  className="h-8 w-8 ml-auto"
                  title="Fullscreen"
               >
                  <Maximize2 className="w-4 h-4" />
               </Button>
            </div>

            {/* Image Canvas */}
            <div
               ref={containerRef}
               className={`
            ar-canvas-container
            relative overflow-hidden rounded-xl border border-border bg-black/40
            ${isFullscreen ? "fixed inset-0 z-50 rounded-none" : "w-full"}
            ${zoom > 1 ? "cursor-grab" : "cursor-default"}
            ${isDragging ? "cursor-grabbing" : ""}
          `}
               style={{
                  aspectRatio: isFullscreen
                     ? undefined
                     : imageDimensions.width && imageDimensions.height
                        ? `${imageDimensions.width} / ${imageDimensions.height}`
                        : "16 / 9",
                  maxHeight: isFullscreen ? "100vh" : "80vh"
               }}
               onMouseDown={handleMouseDown}
               onMouseMove={handleMouseMove}
               onMouseUp={handleMouseUp}
               onMouseLeave={handleMouseUp}
            >
               {/* Zoom Indicator */}
               <div className="absolute top-3 left-3 z-20 bg-black/60 backdrop-blur-sm px-2 py-1 rounded-md text-xs text-white/70">
                  {Math.round(zoom * 100)}%
               </div>

               {/* Fullscreen Close Button */}
               {isFullscreen && (
                  <Button
                     variant="ghost"
                     size="icon"
                     onClick={toggleFullscreen}
                     className="absolute top-3 right-3 z-20 bg-black/60 backdrop-blur-sm"
                  >
                     <X className="w-5 h-5" />
                  </Button>
               )}

               {/* Image Layer */}
               <div
                  className="relative w-full h-full transition-transform duration-150 ease-out"
                  style={{
                     transform: `scale(${zoom}) translate(${position.x / zoom}px, ${position.y / zoom}px)`,
                  }}
               >
                  <img
                     src={imageUrl}
                     alt="Device under analysis"
                     className="w-full h-full object-contain"
                     onLoad={handleImageLoad}
                     draggable={false}
                  />

                  {/* AR Overlay Layer */}
                  {showBoxes && (
                     <div className="absolute inset-0">
                        {[
                           ...safeVisualizations,
                           ...safeLocalizationResults.map(lr => ({
                              ...lr,
                              label: lr.target,
                              overlay_id: lr.target,
                              landmark_description: lr.landmark_description || lr.spatial_description
                           }))
                        ]
                           .filter((viz) => {
                              // Ensure bounding_box exists and has valid numbers
                              const bbox = viz.bounding_box;
                              if (!bbox || typeof bbox !== 'object') return false;

                              const hasValues =
                                 typeof bbox.x_min === 'number' &&
                                 typeof bbox.x_max === 'number' &&
                                 (bbox.x_max - bbox.x_min > 0);

                              if (!hasValues) return false;
                              return true;
                           })
                           .map((viz, index) => {
                              const status = getStatusFromComponent(viz);
                              const colors = STATUS_COLORS[status];
                              const style = getComponentStyle(viz.bounding_box);

                              // Skip if style couldn't be computed
                              if (!style) return null;

                              const id = viz.overlay_id || (viz as any).target || index;
                              const isHighlighted = highlightedId === id;

                              // Check if box is near the top edge to flip label position
                              const isNearTop = (viz.bounding_box?.y_min || 0) < 0.1;

                              return (
                                 <motion.div
                                    key={id}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{
                                       opacity: 1,
                                       scale: isHighlighted ? 1.05 : 1,
                                       zIndex: isHighlighted ? 30 : 10
                                    }}
                                    transition={{
                                       delay: isHighlighted ? 0 : index * 0.05,
                                       duration: 0.3
                                    }}
                                    className={`
                        absolute border-2 md:border-4 rounded-lg cursor-pointer
                        transition-all duration-300
                        shadow-[0_0_15px_rgba(0,0,0,0.3)]
                        ${isHighlighted
                                          ? `shadow-[0_0_30px_rgba(255,255,255,0.8)] z-30 scale-105 border-white ring-4 ring-white/20`
                                          : `hover:shadow-[0_0_25px_rgba(255,255,255,0.6)] hover:z-20 border-opacity-80`
                                       }
                        ${colors.border.replace("stroke-", "border-")}
                        ${colors.bg}
                      `}
                                    style={style}
                                    onClick={() => handleComponentClick(viz)}
                                 >
                                    {/* Label */}
                                    {(showLabels || isHighlighted) && (
                                       <div
                                          className={`
                             absolute left-0 px-3 py-1.5 rounded-full text-xs font-bold tracking-wide
                             whitespace-nowrap backdrop-blur-md shadow-lg border border-white/20 z-10
                             ${isNearTop ? "top-2" : "-top-10"}
                             ${isHighlighted ? "bg-white text-black scale-110 shadow-white/20" : `${colors.bg} ${colors.text}`}
                           `}
                                       >
                                          {viz.label}
                                       </div>
                                    )}

                                    {/* Confidence indicator */}
                                    <div
                                       className={`
                           absolute -bottom-6 left-0 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/70 backdrop-blur-sm
                           border border-white/10
                           ${isHighlighted ? "text-white" : colors.text}
                         `}
                                    >
                                       {Math.round(viz.confidence * 100)}%
                                    </div>
                                 </motion.div>
                              );
                           })}

                        {/* Arrow hints */}
                        <svg className="absolute inset-0 w-full h-full pointer-events-none">
                           {safeVisualizations
                              .filter((v) => v.arrow_hint)
                              .map((viz, index) => (
                                 <motion.line
                                    key={`arrow-${index}`}
                                    initial={{ pathLength: 0 }}
                                    animate={{ pathLength: 1 }}
                                    transition={{ delay: index * 0.1 + 0.5 }}
                                    x1={`${viz.arrow_hint!.from.x * 100}%`}
                                    y1={`${viz.arrow_hint!.from.y * 100}%`}
                                    x2={`${viz.arrow_hint!.to.x * 100}%`}
                                    y2={`${viz.arrow_hint!.to.y * 100}%`}
                                    stroke="white"
                                    strokeWidth="2"
                                    strokeDasharray="4 4"
                                    opacity="0.7"
                                    markerEnd="url(#arrowhead)"
                                 />
                              ))}
                           <defs>
                              <marker
                                 id="arrowhead"
                                 markerWidth="10"
                                 markerHeight="7"
                                 refX="9"
                                 refY="3.5"
                                 orient="auto"
                              >
                                 <polygon points="0 0, 10 3.5, 0 7" fill="white" opacity="0.7" />
                              </marker>
                           </defs>
                        </svg>
                     </div>
                  )}
               </div>
            </div>
         </div>

         {/* Component Detail Slide-out Panel */}
         <AnimatePresence>
            {selectedComponent && (
               <>
                  {/* Backdrop */}
                  <motion.div
                     initial={{ opacity: 0 }}
                     animate={{ opacity: 1 }}
                     exit={{ opacity: 0 }}
                     className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
                     onClick={() => setSelectedComponent(null)}
                  />

                  {/* Panel */}
                  <motion.div
                     initial={{ x: "100%" }}
                     animate={{ x: 0 }}
                     exit={{ x: "100%" }}
                     transition={{ type: "spring", damping: 30, stiffness: 300 }}
                     className="fixed rounded-4xl top-3 right-0 bottom-3 w-full max-w-md z-50 bg-[#0c0c0c] border-l border-white/10 shadow-2xl overflow-y-auto"
                  >
                     <div className="p-8 space-y-8">
                        {/* Header */}
                        <div className="flex items-start justify-between">
                           <div className="space-y-2">
                              <h2 className="text-2xl font-display font-bold text-white">
                                 {"label" in selectedComponent
                                    ? selectedComponent.label
                                    : selectedComponent.target}
                              </h2>
                              <div
                                 className={`
                        inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold border
                        ${STATUS_COLORS[getStatusFromComponent(selectedComponent)].bg}
                        ${STATUS_COLORS[getStatusFromComponent(selectedComponent)].text}
                        ${STATUS_COLORS[getStatusFromComponent(selectedComponent)].border.replace("stroke-", "border-")}
                      `}
                              >
                                 {getStatusFromComponent(selectedComponent) === "found" && "✓ Found"}
                                 {getStatusFromComponent(selectedComponent) === "not_visible" && "⚠ Not Visible"}
                                 {getStatusFromComponent(selectedComponent) === "not_present" && "✗ Not Present"}
                                 {getStatusFromComponent(selectedComponent) === "ambiguous" && "? Ambiguous"}
                              </div>
                           </div>
                           <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setSelectedComponent(null)}
                              className="text-white/50 hover:text-white"
                           >
                              <X className="w-6 h-6" />
                           </Button>
                        </div>

                        {/* Details Grid */}
                        <div className="space-y-6">
                           {/* Location & Landmark Section */}
                           <div className="grid gap-6 p-5 rounded-2xl bg-white/5 border border-white/10">
                              {"spatial_description" in selectedComponent && selectedComponent.spatial_description && (
                                 <div>
                                    <h4 className="text-xs uppercase tracking-widest font-bold text-white/40 mb-2">Location</h4>
                                    <div className="flex items-start gap-2 text-white/90">
                                       <div className="p-1 rounded bg-white/10 mt-0.5">
                                          <Maximize2 className="w-3 h-3" />
                                       </div>
                                       {selectedComponent.spatial_description}
                                    </div>
                                 </div>
                              )}

                              {"landmark_description" in selectedComponent && selectedComponent.landmark_description && (
                                 <div>
                                    <h4 className="text-xs uppercase tracking-widest font-bold text-white/40 mb-2">Landmark</h4>
                                    <div className="flex items-start gap-2 text-white/90">
                                       <div className="p-1 rounded bg-white/10 mt-0.5">
                                          <Tag className="w-3 h-3" />
                                       </div>
                                       {selectedComponent.landmark_description}
                                    </div>
                                 </div>
                              )}
                           </div>

                           {/* Analysis / Reasoning */}
                           {"reasoning" in selectedComponent && selectedComponent.reasoning && (
                              <div>
                                 <h4 className="text-sm font-semibold text-white/70 mb-2">Analysis</h4>
                                 <p className="text-white/80 leading-relaxed text-sm">{selectedComponent.reasoning}</p>
                              </div>
                           )}

                           {/* Suggested Action - Highlighted */}
                           {"suggested_action" in selectedComponent && selectedComponent.suggested_action && (
                              <div className="bg-accent/10 border border-accent/20 rounded-xl p-5">
                                 <h4 className="text-sm font-bold text-accent mb-2 flex items-center gap-2">
                                    <ChevronRight className="w-4 h-4" />
                                    Suggested Action
                                 </h4>
                                 <p className="text-accent/90 pl-6">{selectedComponent.suggested_action}</p>
                              </div>
                           )}

                           {/* Confidence Bar */}
                           {"confidence" in selectedComponent && (
                              <div>
                                 <h4 className="text-xs uppercase tracking-widest font-bold text-white/40 mb-2">AI Confidence</h4>
                                 <div className="relative h-2 bg-white/10 rounded-full overflow-hidden">
                                    <motion.div
                                       initial={{ width: 0 }}
                                       animate={{ width: `${selectedComponent.confidence * 100}%` }}
                                       transition={{ duration: 1, ease: "easeOut" }}
                                       className={`absolute h-full rounded-full ${selectedComponent.confidence >= 0.8
                                          ? "bg-emerald-500"
                                          : selectedComponent.confidence >= 0.5
                                             ? "bg-amber-500"
                                             : "bg-red-500"
                                          }`}
                                    />
                                 </div>
                                 <p className="text-xs text-right text-white/40 mt-1.5 font-mono">
                                    {Math.round(selectedComponent.confidence * 100)}% Match
                                 </p>
                              </div>
                           )}
                        </div>

                        {/* Bottom Actions */}
                        <div className="pt-4 mt-auto">
                           <Button
                              variant="outline"
                              className="w-full h-12 text-base font-medium border-white/10 hover:bg-white/5"
                              onClick={() => setSelectedComponent(null)}
                           >
                              Close Details
                           </Button>
                        </div>
                     </div>
                  </motion.div>
               </>
            )}
         </AnimatePresence>
      </>
   );
}
