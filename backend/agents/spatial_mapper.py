"""
Spatial Mapper Agent
Locates components in device images with multi-stage reasoning.
Supports multi-target localization with per-target status tracking.
Only activates when appropriate and provides useful alternatives when localization fails.
"""

from typing import Dict, Any, List, Tuple, Optional
from PIL import Image
import json
import logging
from backend.utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

# Response schemas for structured output
SPATIAL_MULTI_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "component_name": {"type": "string"},
                    "target": {"type": "string", "description": "EXACT component name from the requested targets list"},
                    "status": {"type": "string", "enum": ["found", "not_visible", "not_present", "ambiguous"]},
                    "component_visible": {"type": "boolean"},
                    "spatial_description": {"type": "string"},
                    "landmark_description": {"type": "string"},
                    "bounding_box": {
                        "type": "object",
                        "nullable": True,
                        "properties": {
                            "x_min": {"type": "number"},
                            "y_min": {"type": "number"},
                            "x_max": {"type": "number"},
                            "y_max": {"type": "number"}
                        }
                    },
                    "confidence": {"type": "number"},
                    "suggested_action": {"type": "string", "nullable": True},
                    "visible_alternatives": {"type": "array", "items": {"type": "string"}},
                    "typical_location": {"type": "string", "nullable": True},
                    "reasoning": {"type": "string"}
                },
                "required": ["target", "status", "spatial_description", "confidence"]
            }
        }
    },
    "required": ["results"]
}

SPATIAL_SINGLE_SCHEMA = {
    "type": "object",
    "properties": {
        "component_name": {"type": "string"},
        "component_visible": {"type": "boolean"},
        "visibility_status": {"type": "string"},
        "visibility_reason": {"type": "string"},
        "spatial_description": {"type": "string"},
        "landmark_description": {"type": "string"},
        "bounding_box": {
            "type": "object",
            "nullable": True,
            "properties": {
                "x_min": {"type": "number"},
                "y_min": {"type": "number"},
                "x_max": {"type": "number"},
                "y_max": {"type": "number"}
            }
        },
        "confidence": {"type": "number"},
        "suggested_action": {"type": "string", "nullable": True},
        "visible_alternatives": {"type": "array", "items": {"type": "string"}},
        "typical_location": {"type": "string", "nullable": True},
        "disambiguation_needed": {"type": "boolean"},
        "ambiguity_note": {"type": "string", "nullable": True}
    },
    "required": ["component_name", "component_visible", "spatial_description", "confidence"]
}


class SpatialMapper:
    """
    Locates specific components in device images.
    Uses multi-stage reasoning and provides helpful alternatives when localization fails.
    Supports multi-target queries with per-target status (found, not_visible, not_present, ambiguous).
    """

    # Minimum confidence to provide bounding box (lowered to be more permissive)
    LOCALIZATION_THRESHOLD = 0.4

    def __init__(self):
        pass

    def locate_multiple_components(
        self,
        image: Image.Image,
        target_components: List[str],
        image_dims: Tuple[int, int],
        device_context: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Locate multiple components in a single API call.
        Returns per-target status with evidence-based reasoning.

        Args:
            image: PIL Image
            target_components: List of component names to locate
            image_dims: (width, height) tuple
            device_context: Optional device detection context

        Returns:
            List of localization result dicts, one per target.
        """
        if not target_components:
            return []

        # Special case: if asked to find "all major visible components", detect first then localize
        if (len(target_components) == 1 and 
            any(keyword in target_components[0].lower() for keyword in ["all", "major", "visible components"])):
            logger.info("🔍 Generic component detection requested, identifying visible components first...")
            detected = self._detect_all_visible_components(image, image_dims, device_context)
            if detected and len(detected) > 0:
                logger.info(f"✅ Auto-detected {len(detected)} components: {detected}")
                target_components = detected
            else:
                logger.warning("⚠️ No components auto-detected, proceeding with generic query")
        
                        # QUOTA OPTIMIZATION: Disable auto-detection for specific component queries
        # If user asks "Where is SST?" or "Locate the capacitor", they want that specific component
        # No need to waste API calls detecting all components first
        # Only auto-detect for generic queries like "help me with this device"
        elif len(target_components) <= 2:
            # Check if targets look like specific component names (not generic)
            is_specific_query = all(
                len(t.split()) <= 4 and  # Specific names are usually short
                not any(generic in t.lower() for generic in ["all", "major", "everything", "device", "help", "troubleshoot"])
                for t in target_components
            )
            
            if is_specific_query:
                logger.info(f"💡 Specific component query detected: {target_components} - Skipping auto-detection to save quota")
            else:
                logger.warning(f"⚠️ Only {len(target_components)} target(s) provided: {target_components}")
                logger.info("🔍 Attempting comprehensive component auto-detection...")
                detected = self._detect_all_visible_components(image, image_dims, device_context)
                if detected and len(detected) >= len(target_components):
                    logger.info(f"✅ Auto-detection found {len(detected)} components (more than {len(target_components)}), using auto-detected list: {detected}")
                    target_components = detected
                else:
                    logger.info(f"ℹ️ Auto-detection found {len(detected) if detected else 0} components, keeping original targets")

        # If only one target, delegate to single-component method
        if len(target_components) == 1:
            result = self.locate_component(
                image, target_components[0], image_dims, device_context
            )
            return [self._single_to_multi_format(result)]

        width, height = image_dims

        device_str = ""
        if device_context:
            device_type = device_context.get("device_type", "")
            if device_type and device_type not in ["Unknown", "not_a_device"]:
                device_str = f"This device was identified as: {device_type}"
                components = device_context.get("components", [])
                if components:
                    device_str += f"\nAlready detected components: {', '.join(components[:8])}"

        targets_str = ", ".join(f'"{t}"' for t in target_components)
        
        # Quota optimization: Show component count to help user understand API usage
        logger.info(f"🎯 Localizing {len(target_components)} component(s): {targets_str[:100]}...")

        prompt = [
            f"""You are a spatial reasoning system for FixIt AI.

This image is exactly {width} x {height} pixels.

Your task: Locate ALL of these components in this image: {targets_str}
{device_str}

🔥 CRITICAL INSTRUCTION - READ CAREFULLY:
If you can see a component in ANY way (even partially, at an angle, blurry, or behind something transparent), you MUST:
1. Set status="found" 
2. Set component_visible=true
3. Provide a bounding box with pixel coordinates
4. Set confidence >= 0.4

DO NOT mark components as "not_visible" if they are ANYWHERE in the image.

ONLY use status="not_visible" if:
❌ The component is on the BACK SIDE of the device (camera facing wrong side)
❌ The component is COMPLETELY inside a sealed case/cover
❌ The camera is pointed at the WRONG side of the device entirely

Examples where you SHOULD use status="found":
✅ Component at an angle → status="found" + provide bbox
✅ Component partially visible → status="found" + provide bbox of visible part
✅ Component with something on top → status="found" + locate the visible part
✅ Component at edge of frame → status="found" + provide bbox
✅ Blurry or low quality view → status="found" + confidence=0.4-0.6
✅ Component name in query doesn't perfectly match what you see → status="found" + use closest match

For EACH target component:
- Return bounding box in **0-1 NORMALIZED COORDINATES** (fractional values between 0.0 and 1.0)
- X coordinates: 0.0 = left edge, 1.0 = right edge  
- Y coordinates: 0.0 = top edge, 1.0 = bottom edge
- Example: Component in top-left quarter:
  {{"x_min": 0.05, "y_min": 0.05, "x_max": 0.45, "y_max": 0.45}}
- Example: Component in center-right:
  {{"x_min": 0.6, "y_min": 0.4, "x_max": 0.9, "y_max": 0.7}}
- All values MUST be decimals between 0.0 and 1.0
- Even if uncertain, provide your best estimate (minimum confidence: 0.4)

⚠️ CRITICAL COORDINATE FORMAT:
- ✅ CORRECT: {{"x_min": 0.15, "y_min": 0.36, "x_max": 0.33, "y_max": 0.50}}  (0-1 decimals)
- ❌ WRONG: {{"x_min": 150, "y_min": 360, "x_max": 330, "y_max": 500}}  (pixels - don't use!)
- ❌ WRONG: {{"x_min": 15, "y_min": 36, "x_max": 33, "y_max": 50}}  (percentages - don't use!)

IMPORTANT BOUNDING BOX RULES:
- The bounding box will be drawn on the image for the user to see.
- It MUST accurately surround the component, not just point near it.
- Be conservative: a slightly larger box is better than missing the component.
- Landmark description: explain position relative to nearby visible features.
- For multi-target: each bbox must be independent. Prevent overlapping boxes unless components physically overlap.
- ENSURE x_min < x_max and y_min < y_max (boxes must have non-zero area)
- Minimum dimensions: 0.04 in each direction (4% of image)

Return JSON:
{{
    "results": [
        {{
            "target": "EXACT component name from the list above (e.g., 'CPU socket', '2x RAM slots')",
            "status": "found",  ← USE THIS if component is visible anywhere in image
            "component_visible": true,  ← SET TO TRUE if you can see it
            "spatial_description": "natural language location",
            "landmark_description": "nearby landmark reference like 'Next to power connector'",
            "bounding_box": {{"x_min": 0.15, "y_min": 0.36, "x_max": 0.33, "y_max": 0.50}},  ← 0-1 normalized coordinates
            "confidence": 0.4 to 1.0,  ← Minimum 0.4 for visible components
            "reasoning": "Brief 1-2 sentence explanation (KEEP SHORT to avoid truncation)",
            "suggested_action": null,
            "disambiguation_needed": false,
            "ambiguity_note": null
        }}
    ]
}}

🔥 REMEMBER: If you can see the component → status="found" + provide bbox + component_visible=true
Only use status="not_visible" if the component is on the back side or completely hidden.

⚠️ CRITICAL: The "target" field MUST contain the EXACT component name from the targets list.
- Do NOT use generic names like "unknown", "component", etc.
- Copy the exact target string (e.g., "CPU socket", "2x RAM slots")
- Return one result object for EACH target in the same order

CRITICAL COORDINATE VALIDATION:
- All bounding boxes MUST satisfy: x_min < x_max AND y_min < y_max
- All values MUST be between 0.0 and 1.0 (normalized coordinates)
- Box width (x_max - x_min) should be >= 0.04 (4% of image width)
- Box height (y_max - y_min) should be >= 0.04 (4% of image height)
- Example VALID box: {{"x_min": 0.15, "y_min": 0.36, "x_max": 0.33, "y_max": 0.50}} (18% x 14% box)
- Example INVALID box: {{"x_min": 0.5, "y_min": 0.5, "x_max": 0.5, "y_max": 0.5}} (0% x 0% - WRONG!)

CRITICAL RULES:
- Return one entry for EACH requested target
- Bounding box coordinates MUST be 0-1 normalized (decimals between 0.0 and 1.0)
- x_min < x_max and y_min < y_max ALWAYS
- ALWAYS provide bounding_box when status="found" (even if confidence is low like 0.4)
- If you can see the component, provide a bbox - don't worry about perfect accuracy
- KEEP "reasoning" BRIEF (1-2 sentences max) to prevent JSON truncation
""",
            image,
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=SPATIAL_MULTI_SCHEMA,
                temperature=0.2,
                max_output_tokens=16000  # Increased for very verbose models like gemini-3-flash-preview
            )

            if isinstance(response, dict):
                raw_results = response.get("results", [])
                if isinstance(raw_results, list):
                    # Log raw response for debugging
                    logger.info(f"📥 Received {len(raw_results)} raw results from Gemini")
                    for idx, r in enumerate(raw_results[:3]):  # Log first 3 for debugging
                        logger.info(f"  [{idx}] target='{r.get('target')}', status='{r.get('status')}', has_bbox={r.get('bounding_box') is not None}")
                    
                    # QUOTA OPTIMIZATION: Remove expensive fallback retry
                    # If 0 results returned, just return empty instead of making 6 more API calls
                    if len(raw_results) == 0:
                        logger.error(f"❌ Received 0 results (likely quota exhausted or JSON truncation)")
                        logger.warning(f"⚠️ Skipping fallback retry to conserve quota (would use 6+ more API calls)")
                        return []  # Return empty instead of triggering expensive fallback
                    
                    processed_results = []
                    for idx, r in enumerate(raw_results):
                        processed = self._process_multi_result(r, width, height)
                        
                        # Defensive: If target is "unknown" or empty, map it to the requested target by index
                        if processed.get("target") in ["unknown", "", None] and idx < len(target_components):
                            original_target = target_components[idx]
                            logger.warning(f"⚠️ Target field missing/unknown at index {idx}, mapping to requested target: '{original_target}'")
                            processed["target"] = original_target
                        
                        processed_results.append(processed)
                    
                    return processed_results

            # Fallback: locate individually
            logger.warning("Multi-target response invalid, falling back to individual localization")
            return self._fallback_individual_locate(
                image, target_components, image_dims, device_context
            )

        except Exception as e:
            logger.error(f"Multi-target spatial mapping failed: {e}")
            return [
                self._create_not_found_result(t, str(e))
                for t in target_components
            ]

    def locate_component(
        self,
        image: Image.Image,
        component_name: str,
        image_dims: Tuple[int, int],
        device_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Locates a specific component in the image using multi-stage reasoning.

        Stage 1: Can I see the component at all?
        Stage 2: Can I determine its rough location?
        Stage 3: Can I provide precise coordinates?
        """
        width, height = image_dims

        device_str = ""
        if device_context:
            device_type = device_context.get("device_type", "")
            if device_type and device_type not in ["Unknown", "not_a_device"]:
                device_str = f"This device was identified as: {device_type}"
                components = device_context.get("components", [])
                if components:
                    device_str += f"\nAlready detected components: {', '.join(components[:5])}"

        prompt = [
            f"""You are a spatial reasoning system for FixIt AI.

This image is exactly {width} x {height} pixels.

Your task: Locate "{component_name}" in this image.
{device_str}

Use MULTI-STAGE REASONING:

STAGE 1 - VISIBILITY CHECK:
- Is the component visible at all in this image?
- Could the component exist on this device type?
- Is the image quality good enough to see it?

STAGE 2 - ROUGH LOCATION (only if Stage 1 passes):
- Where in the image is it? (top, bottom, left, right, center)
- What is it near or adjacent to? Provide a LANDMARK reference.

STAGE 3 - PRECISE LOCATION (only if Stage 2 passes):
- Return bounding box in ABSOLUTE PIXEL COORDINATES (not normalized 0-1 values).
- The image is {width}x{height} pixels. Your coordinates must be within these bounds.
- CRITICAL: The bounding box MUST form a proper rectangle with area > 0
  - x_min must be LESS THAN x_max (not equal!)
  - y_min must be LESS THAN y_max (not equal!)
  - All coordinates must be positive integers within image bounds
- Example: For a {width}x{height} image, if component is at top-left quarter:
  {{"x_min": 50, "y_min": 40, "x_max": {width // 4}, "y_max": {height // 4}}}
  These are actual pixel positions, NOT percentages or 0-1000 scaled values.
- Make boxes slightly LARGER rather than smaller - better to include extra space than miss the component
- Minimum box size: at least 50x50 pixels
- Only if confidence >= 0.6

IMPORTANT BOUNDING BOX RULES:
- The bounding box will be drawn on the image for the user to see.
- It MUST accurately surround the component, not just point near it.
- Be conservative: a slightly larger box is better than missing the component.
- Landmark description: explain position relative to nearby visible features.
- ENSURE x_min < x_max and y_min < y_max (boxes must have non-zero area)
- Minimum dimensions: 50x50 pixels (don't create tiny point-like boxes)
- All coordinates must be within 0 to {width} (for x) and 0 to {height} (for y)

BE HONEST:
- If you can't see it, say "not_visible" and explain with evidence
- If image is unclear, say "too_blurry"
- If component doesn't exist on this device type, say "not_applicable"
- If you're unsure, set low confidence

Return JSON:
{{
    "component_visible": true/false,
    "component_name": "{component_name}",
    "visibility_status": "visible" | "not_visible" | "partially_visible" | "too_blurry" | "not_applicable" | "wrong_angle",
    "visibility_reason": "explain why component is or isn't visible with evidence",
    "spatial_description": "natural language location like 'bottom right corner, next to the power port' OR reason not visible",
    "landmark_description": "nearby landmark reference like 'Near the USB port cluster' or 'Below the CPU socket'",
    "bounding_box": null OR {{
        "x_min": absolute_pixel_int,
        "y_min": absolute_pixel_int,
        "x_max": absolute_pixel_int,
        "y_max": absolute_pixel_int
    }},
    "confidence": 0.0 to 1.0,
    "suggested_action": "what user should do if component not found",
    "visible_alternatives": ["list of components that ARE visible in this image"],
    "typical_location": "where this component is typically found on this type of device",
    "disambiguation_needed": false,
    "ambiguity_note": null
}}

Coordinates MUST be absolute pixel values: x in 0..{width}, y in 0..{height}.
x_min < x_max and y_min < y_max ALWAYS.
Only provide bounding_box if confidence >= 0.6 and you can CLEARLY see the component.
""",
            image,
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=SPATIAL_SINGLE_SCHEMA,
                temperature=0.2,
                max_output_tokens=4000  # Increased for verbose models
            )

            if isinstance(response, dict):
                return self._process_spatial_response(
                    response, width, height, component_name
                )

            return self._create_not_found_response(component_name)

        except Exception as e:
            logger.error(f"Spatial mapping failed: {e}")
            return self._create_error_response(component_name, str(e))

    def _validate_and_clamp_bbox(self, bbox: Dict[str, Any], width: int, height: int) -> Optional[Dict[str, int]]:
        """Validate bounding box coordinates and clamp to image bounds.
        Handles both absolute pixel coords and 0-1000 scaled coords (legacy).
        Returns pixel coords dict or None if invalid."""
        try:
            # Try reading absolute pixel coords first (new format)
            x_min = float(bbox.get("x_min", bbox.get("xmin", 0)))
            y_min = float(bbox.get("y_min", bbox.get("ymin", 0)))
            x_max = float(bbox.get("x_max", bbox.get("xmax", 0)))
            y_max = float(bbox.get("y_max", bbox.get("ymax", 0)))

            # Log original coordinates for debugging
            logger.info(f"🔍 Raw bbox from Gemini: x=({x_min:.3f}, {x_max:.3f}), y=({y_min:.3f}, {y_max:.3f}) | Image: {width}x{height}px")

            # Primary path: Expect 0-1 normalized coordinates (as per updated prompt)
            if x_max <= 1.0 and y_max <= 1.0 and x_min >= 0.0 and y_min >= 0.0:
                logger.info("✅ Received 0-1 normalized coordinates, scaling to pixels")
                
                # Scale to image dimensions
                x_min = x_min * width
                y_min = y_min * height
                x_max = x_max * width
                y_max = y_max * height
                
                logger.info(f"📐 Scaled to pixels: x=({x_min:.1f}, {x_max:.1f}), y=({y_min:.1f}, {y_max:.1f})")
            
            # Legacy fallback: 0-1000 scale (from older model versions)
            elif x_max <= 1000 and y_max <= 1000 and x_max > 1.0:
                logger.warning(f"⚠️ Detected legacy 0-1000 scale, converting to 0-1 then pixels")
                # Convert to 0-1 first
                x_min = x_min / 1000.0
                y_min = y_min / 1000.0
                x_max = x_max / 1000.0
                y_max = y_max / 1000.0
                # Then scale to pixels
                x_min = x_min * width
                y_min = y_min * height
                x_max = x_max * width
                y_max = y_max * height
                
                logger.info(f"📐 Converted from 0-1000: x=({x_min:.1f}, {x_max:.1f}), y=({y_min:.1f}, {y_max:.1f})")

            # Validate: x_min < x_max, y_min < y_max BEFORE clamping
            if x_min >= x_max or y_min >= y_max:
                logger.error(f"❌ Invalid bbox BEFORE clamping: x_min({x_min:.1f}) >= x_max({x_max:.1f}) or y_min({y_min:.1f}) >= y_max({y_max:.1f})")
                
                # Try to salvage by adding minimum size
                if x_min >= x_max:
                    width_fix = max(width * 0.05, 50)  # At least 5% of image width or 50px
                    x_max = x_min + width_fix
                    logger.warning(f"🔧 Fixed collapsed width: added {width_fix}px")
                    
                if y_min >= y_max:
                    height_fix = max(height * 0.05, 50)  # At least 5% of image height or 50px
                    y_max = y_min + height_fix
                    logger.warning(f"🔧 Fixed collapsed height: added {height_fix}px")

            # Clamp to image bounds
            x_min = max(0, min(int(x_min), width - 1))
            y_min = max(0, min(int(y_min), height - 1))
            x_max = max(0, min(int(x_max), width))
            y_max = max(0, min(int(y_max), height))

            # Ensure minimum box size after clamping (at least 10px)
            if x_max - x_min < 10:
                x_max = min(x_min + 10, width)
            if y_max - y_min < 10:
                y_max = min(y_min + 10, height)

            # Final check after clamping
            if x_min >= x_max or y_min >= y_max:
                logger.error(f"❌ Bbox collapsed AFTER clamping: ({x_min},{y_min})-({x_max},{y_max})")
                return None

            final_bbox = {"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max}
            logger.info(f"✅ Final validated bbox: ({x_min},{y_min})-({x_max},{y_max}) | Size: {x_max-x_min}x{y_max-y_min}px")
            
            return final_bbox

        except (TypeError, ValueError) as e:
            logger.error(f"❌ Failed to parse bounding box: {e}")
            return None

    def _process_multi_result(
        self, result: Dict[str, Any], width: int, height: int
    ) -> Dict[str, Any]:
        """Process a single result from multi-target localization."""
        target = result.get("target", "unknown")
        status = result.get("status", "not_visible")
        confidence = float(result.get("confidence", 0.0))
        component_visible = result.get("component_visible", status == "found")
        bbox = result.get("bounding_box")
        
        # 🔥 AGGRESSIVE DEFENSIVE CORRECTION 🔥
        # If Gemini provided a bounding box, the component MUST be visible
        if bbox and isinstance(bbox, dict):
            if bbox.get("x_min") is not None and bbox.get("x_max") is not None:
                logger.warning(f"⚠️ '{target}': Gemini provided bbox but status='{status}' → FORCING status='found'")
                status = "found"
                component_visible = True
                # Boost confidence if too low
                if confidence < self.LOCALIZATION_THRESHOLD:
                    logger.warning(f"⚠️ '{target}': Boosting confidence from {confidence:.2f} to {self.LOCALIZATION_THRESHOLD}")
                    confidence = self.LOCALIZATION_THRESHOLD
        
        # Defensive: if component_visible=true but status is not "found", correct it
        if component_visible and status not in ["found", "ambiguous"]:
            logger.warning(f"⚠️ Correcting mismatch for '{target}': component_visible=true but status='{status}', changing to 'found'")
            status = "found"
        
        # Defensive: if status="found" but component_visible=false, correct it
        if status == "found" and not component_visible:
            logger.warning(f"⚠️ Correcting mismatch for '{target}': status='found' but component_visible=false, setting to true")
            component_visible = True

        entry = {
            "target": target,
            "status": status if status in ("found", "not_visible", "not_present", "ambiguous") else "not_visible",
            "bounding_box": None,
            "pixel_coords": None,
            "spatial_description": result.get("spatial_description", ""),
            "landmark_description": result.get("landmark_description", ""),
            "reasoning": result.get("reasoning", ""),
            "suggested_action": result.get("suggested_action", ""),
            "confidence": confidence,
            "disambiguation_needed": result.get("disambiguation_needed", False),
            "ambiguity_note": result.get("ambiguity_note"),
            "component_visible": component_visible,
        }

        # Parse and validate bounding box if found
        
        # Log detailed status for debugging
        logger.info(f"🔍 Component '{target}': status={status}, visible={component_visible}, confidence={confidence:.2f}, has_bbox={bbox is not None}")
        
        if bbox and component_visible and confidence >= self.LOCALIZATION_THRESHOLD:
            logger.info(f"🎯 Processing bbox for '{target}' (confidence: {confidence:.2f})")
            pixel_coords = self._validate_and_clamp_bbox(bbox, width, height)
            if pixel_coords:
                entry["bounding_box"] = bbox
                entry["pixel_coords"] = pixel_coords
                logger.info(f"✅ Successfully processed bbox for '{target}'")
            else:
                logger.error(f"❌ Bounding box validation failed for '{target}', discarding bbox")
        elif not bbox:
            logger.warning(f"⚠️ No bounding_box returned for '{target}' (status={status})")
        elif not component_visible:
            logger.warning(f"⚠️ Component '{target}' marked as NOT VISIBLE by Gemini (status={status})")
        elif confidence < self.LOCALIZATION_THRESHOLD:
            logger.warning(f"⚠️ Confidence {confidence:.2f} < {self.LOCALIZATION_THRESHOLD} for '{target}', skipping bbox")

        return entry

    def _single_to_multi_format(self, single_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert single locate_component result to multi-target format."""
        component_visible = single_result.get("component_visible", False)
        visibility_status = single_result.get("visibility_status", "not_visible")

        # Map visibility_status to multi-target status
        if component_visible:
            status = "found"
        elif visibility_status == "not_applicable":
            status = "not_present"
        else:
            status = "not_visible"

        return {
            "target": single_result.get("component_name", "unknown"),
            "status": status,
            "bounding_box": single_result.get("bounding_box"),
            "pixel_coords": single_result.get("pixel_coords"),
            "spatial_description": single_result.get("spatial_description", ""),
            "landmark_description": single_result.get("landmark_description", ""),
            "reasoning": single_result.get("visibility_reason", ""),
            "suggested_action": single_result.get("suggested_action", ""),
            "confidence": single_result.get("confidence", 0.0),
            "disambiguation_needed": single_result.get("disambiguation_needed", False),
            "ambiguity_note": single_result.get("ambiguity_note"),
            "component_visible": component_visible,
            "visible_alternatives": single_result.get("visible_alternatives", []),
            "typical_location": single_result.get("typical_location", ""),
        }

    def _fallback_individual_locate(
        self,
        image: Image.Image,
        targets: List[str],
        image_dims: Tuple[int, int],
        device_context: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Fallback: locate each component individually."""
        results = []
        for target in targets:
            try:
                single = self.locate_component(
                    image, target, image_dims, device_context
                )
                results.append(self._single_to_multi_format(single))
            except Exception as e:
                logger.error(f"Individual locate failed for {target}: {e}")
                results.append(self._create_not_found_result(target, str(e)))
        return results

    def _process_spatial_response(
        self,
        response: Dict[str, Any],
        width: int,
        height: int,
        component_name: str,
    ) -> Dict[str, Any]:
        """Process and normalize the spatial response."""
        component_visible = response.get("component_visible", False)
        confidence = float(response.get("confidence", 0.0))
        visibility_status = response.get("visibility_status", "not_visible")

        result = {
            "component_visible": component_visible,
            "component_name": component_name,
            "visibility_status": visibility_status,
            "visibility_reason": response.get("visibility_reason", ""),
            "spatial_description": response.get(
                "spatial_description", "Location not identified"
            ),
            "landmark_description": response.get("landmark_description", ""),
            "confidence": confidence,
            "suggested_action": response.get("suggested_action", ""),
            "visible_alternatives": response.get("visible_alternatives", []),
            "typical_location": response.get("typical_location", ""),
            "disambiguation_needed": response.get("disambiguation_needed", False),
            "ambiguity_note": response.get("ambiguity_note"),
        }

        # Only include bounding box if visible and confident
        bbox = response.get("bounding_box")
        if (
            bbox
            and component_visible
            and confidence >= self.LOCALIZATION_THRESHOLD
        ):
            pixel_coords = self._validate_and_clamp_bbox(bbox, width, height)
            if pixel_coords:
                result["bounding_box"] = bbox
                result["pixel_coords"] = pixel_coords
            else:
                logger.warning(f"Bounding box validation failed for {component_name}, discarding bbox")
                result["bounding_box"] = None
                result["pixel_coords"] = None
        else:
            result["bounding_box"] = None
            result["pixel_coords"] = None

        return result

    def _create_not_found_response(self, component_name: str) -> Dict[str, Any]:
        """Create a response when component localization fails."""
        return {
            "component_visible": False,
            "component_name": component_name,
            "visibility_status": "not_visible",
            "visibility_reason": "Could not analyze the image for component location",
            "spatial_description": f"Unable to locate {component_name}",
            "landmark_description": "",
            "bounding_box": None,
            "pixel_coords": None,
            "confidence": 0.0,
            "suggested_action": "Please try taking a clearer photo or describe what you're looking for",
            "visible_alternatives": [],
            "typical_location": "",
            "disambiguation_needed": False,
            "ambiguity_note": None,
        }

    def _create_not_found_result(
        self, target: str, reason: str = ""
    ) -> Dict[str, Any]:
        """Create a not-found result in multi-target format."""
        return {
            "target": target,
            "status": "not_visible",
            "bounding_box": None,
            "pixel_coords": None,
            "spatial_description": f"Unable to locate {target}",
            "landmark_description": "",
            "reasoning": reason or "Could not analyze the image for this component",
            "suggested_action": "Please try taking a clearer photo or different angle",
            "confidence": 0.0,
            "disambiguation_needed": False,
            "ambiguity_note": None,
            "component_visible": False,
        }

    def _create_error_response(
        self, component_name: str, error: str
    ) -> Dict[str, Any]:
        """Create a response when an error occurs."""
        return {
            "component_visible": False,
            "component_name": component_name,
            "visibility_status": "error",
            "visibility_reason": f"Error during localization: {error}",
            "spatial_description": "Error locating component",
            "landmark_description": "",
            "bounding_box": None,
            "pixel_coords": None,
            "confidence": 0.0,
            "suggested_action": "Please try again",
            "visible_alternatives": [],
            "typical_location": "",
            "disambiguation_needed": False,
            "ambiguity_note": None,
            "error": error,
        }

    def should_attempt_localization(
        self,
        device_info: Dict[str, Any],
        query_info: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Determine if we should attempt spatial localization.

        Returns:
            Tuple of (should_attempt: bool, reason: str)
        """
        # Don't attempt if device wasn't identified with reasonable confidence
        device_confidence = device_info.get("device_confidence", 0.0)
        if device_confidence < 0.3:
            return (
                False,
                "Device identification confidence too low for spatial localization",
            )

        # Don't attempt for non-devices
        device_type = device_info.get("device_type", "Unknown")
        if device_type in ["Unknown", "not_a_device"]:
            return (
                False,
                "Cannot localize components on unidentified or non-device images",
            )

        # Check answer_type - skip localization for types that don't need it
        answer_type = query_info.get("answer_type", "")
        if answer_type in [
            "ask_clarifying_questions",
            "reject_invalid_image",
            "ask_for_better_input",
            "safety_warning_only",
        ]:
            return False, f"Localization not needed for answer_type={answer_type}"

        # For explain_only and identify_only, localization is optional but helpful for AR visualization
        # So we'll allow it but with lower priority
        
        # DEFAULT BEHAVIOR: Always attempt localization for valid devices
        # This provides comprehensive AR visualization even when not explicitly requested
        logger.info("✅ Localization enabled - device is valid and identifiable")
        return True, "Localization appropriate for AR visualization"

    def get_component_from_query(
        self, query: str, device_components: List[str] = None
    ) -> Optional[str]:
        """
        Extract the target component from a user query.
        """
        query_lower = query.lower()

        component_keywords = {
            "reset button": ["reset", "reset button"],
            "power button": ["power button", "power switch", "on/off"],
            "power port": ["power", "power port", "power jack", "power socket"],
            "ethernet port": ["ethernet", "lan port", "network port"],
            "usb port": ["usb", "usb port"],
            "hdmi port": ["hdmi"],
            "led indicator": ["light", "led", "indicator", "blinking"],
            "screen": ["screen", "display", "monitor"],
            "speaker": ["speaker", "audio"],
            "microphone": ["microphone", "mic"],
            "camera": ["camera", "webcam"],
            "antenna": ["antenna", "wifi antenna"],
            "SSD": ["ssd", "solid state", "m.2"],
            "RAM": ["ram", "memory", "dimm"],
            "cooling fan": ["fan", "cooling", "cooler", "heatsink fan"],
            "CPU": ["cpu", "processor"],
            "GPU": ["gpu", "graphics card", "video card"],
            "battery": ["battery"],
        }

        for component, patterns in component_keywords.items():
            if any(pattern in query_lower for pattern in patterns):
                return component

        # Check against detected components
        if device_components:
            for comp in device_components:
                if comp.lower() in query_lower:
                    return comp

        return None

    def get_multiple_components_from_query(
        self, query: str, device_components: List[str] = None
    ) -> List[str]:
        """
        Extract multiple target components from a user query.
        Handles queries like "locate SSD & cooling fan" or "find RAM, CPU, and GPU".
        """
        query_lower = query.lower()
        found = []

        component_keywords = {
            "reset button": ["reset button"],
            "power button": ["power button", "power switch"],
            "power port": ["power port", "power jack"],
            "ethernet port": ["ethernet port", "lan port", "network port"],
            "usb port": ["usb port", "usb"],
            "hdmi port": ["hdmi port", "hdmi"],
            "led indicator": ["led indicator", "led", "indicator light"],
            "screen": ["screen", "display"],
            "speaker": ["speaker"],
            "SSD": ["ssd", "solid state drive", "m.2 drive", "m.2 slot"],
            "RAM": ["ram", "memory module", "dimm"],
            "cooling fan": ["cooling fan", "fan", "cooler"],
            "CPU": ["cpu", "processor"],
            "GPU": ["gpu", "graphics card", "video card"],
            "battery": ["battery"],
            "heatsink": ["heatsink", "heat sink"],
            "motherboard": ["motherboard", "mainboard"],
            "power supply": ["power supply", "psu"],
        }

        for component, patterns in component_keywords.items():
            for pattern in patterns:
                if pattern in query_lower:
                    if component not in found:
                        found.append(component)
                    break

        # Also check device components
        if device_components:
            for comp in device_components:
                if comp.lower() in query_lower and comp not in found:
                    found.append(comp)

        return found

    def _detect_all_visible_components(
        self,
        image: Image.Image,
        image_dims: Tuple[int, int],
        device_context: Dict[str, Any] = None,
    ) -> List[str]:
        """
        Detect all major visible components in an image before localization.
        Used when user doesn't specify which components they want located.
        
        Returns:
            List of component names detected in the image.
        """
        width, height = image_dims
        device_str = ""
        if device_context:
            device_type = device_context.get("device_type", "")
            if device_type and device_type not in ["Unknown", "not_a_device"]:
                device_str = f"This is a {device_type}."

        detection_schema = {
            "type": "object",
            "properties": {
                "visible_components": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "description": "List of all major visible components (MINIMUM 3 required)"
                },
                "reasoning": {"type": "string"}
            },
            "required": ["visible_components"]
        }

        prompt = [
            f"""You are analyzing an electronic device image to identify ALL major visible components.

{device_str}

🎯 CRITICAL REQUIREMENT: You MUST list at LEAST 5-10 distinct components!
❌ DO NOT return just 1-2 components - that is unacceptable!

Your task: Systematically scan the ENTIRE image and identify EVERY visible part.

Scan Strategy:
1. Start at top-left, move to top-right
2. Scan middle-left to middle-right  
3. Scan bottom-left to bottom-right
4. List EVERYTHING you see at each position

Be EXHAUSTIVE - include:
✓ Major components (boards, modules, drives)
✓ Connectors and ports (USB, power, HDMI, etc)
✓ Mechanical parts (fans, wheels, chassis)
✓ Storage and slots (RAM slots, card slots)
✓ Cables and wires (if prominent)
✓ Power components (batteries, power supplies)
✓ Input/output devices (buttons, LEDs, displays)

Device-Specific Examples:

📱 MOTHERBOARD → List: CPU socket, RAM slots (count them!), PCIe slots, SATA ports, M.2 slots, power connectors (24-pin, 8-pin), chipset heatsink, CMOS battery, audio jacks, USB headers, VRM heatsinks, I/O shield area

💻 LAPTOP (internal) → List: RAM module(s), SSD/HDD, cooling fan, battery pack, heat pipes, WiFi card, keyboard connector, display cable, touchpad connector, speaker, webcam, ports (USB, HDMI, charging), hinges, antenna cables

🖨️ PRINTER → List: paper input tray, output tray, paper jam door, ink/toner cartridges, printhead, control panel, LCD screen, paper feed rollers, paper width guides, power button, USB port, Ethernet port, scanner bed cover

🤖 ARDUINO/ROBOTICS → List: microcontroller board (specify type), GPIO pins, motor driver module, DC motors, servo motors, wheels, chassis/frame, battery pack, battery holder, USB programming port, power jack, barrel connector, voltage regulator, LED indicators, push buttons, sensors (ultrasonic/IR/etc), breadboard, jumper wires, resistors (if visible), capacitors (if large)

🌐 ROUTER → List: Ethernet LAN ports (count them), WAN port, power port, USB ports, antennas (external), LED status indicators (power/internet/WiFi/LAN), reset pinhole button, WPS button, ventilation slots, mounting holes, label/serial number area

Formatting Rules:
- Be specific: "RAM slot 1", "RAM slot 2" (not just "RAM")
- Use quantities: "4x Ethernet LAN ports", "2x RAM modules"
- Describe location: "cooling fan (center)", "battery (bottom-right)"
- Name by function: "USB Type-C charging port", "HDMI output port"

Return JSON:
{{
    "visible_components": [
        "component1 with specifics",
        "component2 with location", 
        "component3 with count",
        ... (MINIMUM 5-10 items)
    ],
    "reasoning": "I systematically scanned the image and identified X major components including..."
}}

🎯 TARGET: 8-15 components per image
⚠️ MINIMUM: 5 components (anything less is incomplete)
❌ NEVER: 1-2 components (that's lazy scanning)
""",
            image
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=detection_schema,
                temperature=0.2,
                max_output_tokens=4000  # Increased for component detection
            )

            if isinstance(response, dict):
                components = response.get("visible_components", [])
                if isinstance(components, list) and len(components) > 0:
                    # Limit to avoid quota issues
                    return components[:12]  # Max 12 components
                    
            logger.warning("Component detection returned no components")
            return []

        except Exception as e:
            logger.error(f"Component detection failed: {e}")
            return []


# Singleton instance
spatial_mapper = SpatialMapper()
