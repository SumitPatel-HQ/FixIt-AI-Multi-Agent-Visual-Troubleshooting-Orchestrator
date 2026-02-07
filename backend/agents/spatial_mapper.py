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
                    "status": {"type": "string", "enum": ["found", "not_visible", "not_present", "ambiguous"]},
                    "spatial_description": {"type": "string"},
                    "bounding_box": {
                        "type": ["object", "null"],
                        "properties": {
                            "x_min": {"type": "number"},
                            "y_min": {"type": "number"},
                            "x_max": {"type": "number"},
                            "y_max": {"type": "number"}
                        }
                    },
                    "confidence": {"type": "number"},
                    "suggested_action": {"type": ["string", "null"]},
                    "visible_alternatives": {"type": "array", "items": {"type": "string"}},
                    "typical_location": {"type": ["string", "null"]},
                    "reasoning": {"type": "string"}
                },
                "required": ["component_name", "status", "spatial_description", "confidence"]
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
        "spatial_description": {"type": "string"},
        "bounding_box": {
            "type": ["object", "null"],
            "properties": {
                "x_min": {"type": "number"},
                "y_min": {"type": "number"},
                "x_max": {"type": "number"},
                "y_max": {"type": "number"}
            }
        },
        "confidence": {"type": "number"},
        "suggested_action": {"type": ["string", "null"]},
        "visible_alternatives": {"type": "array", "items": {"type": "string"}},
        "typical_location": {"type": ["string", "null"]},
        "disambiguation_needed": {"type": "boolean"},
        "ambiguity_note": {"type": ["string", "null"]}
    },
    "required": ["component_name", "component_visible", "spatial_description", "confidence"]
}


class SpatialMapper:
    """
    Locates specific components in device images.
    Uses multi-stage reasoning and provides helpful alternatives when localization fails.
    Supports multi-target queries with per-target status (found, not_visible, not_present, ambiguous).
    """

    # Minimum confidence to provide bounding box
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

        prompt = [
            f"""You are a spatial reasoning system for FixIt AI.

Your task: Locate ALL of these components in this image: {targets_str}
{device_str}

For EACH target component, use MULTI-STAGE REASONING:

STAGE 1 - VISIBILITY CHECK:
- Is the component visible at all in this image?
- Could the component exist on this device type?
- If not visible, explain WHY with evidence:
  - "not_visible": Component typically exists but is not in current camera view (wrong angle, covered, out of frame)
  - "not_present": Component does not exist on this type of device (explain what alternative is used)
  - "ambiguous": Multiple similar components visible, need user to clarify which one

STAGE 2 - ROUGH LOCATION (only if visible):
- Where in the image is it? (top, bottom, left, right, center)
- What nearby LANDMARK helps identify it? (e.g., "near USB port cluster", "below CPU socket")

STAGE 3 - PRECISE LOCATION (only if Stage 2 passes):
- Provide a bounding box with coordinates scaled 0-1000
- Only if confidence > 0.4

Return JSON:
{{
    "results": [
        {{
            "target": "component name",
            "status": "found" | "not_visible" | "not_present" | "ambiguous",
            "component_visible": true/false,
            "spatial_description": "natural language location",
            "landmark_description": "nearby landmark reference like 'Next to power connector'",
            "bounding_box": null OR {{"ymin": 0, "xmin": 0, "ymax": 0, "xmax": 0}},
            "confidence": 0.0 to 1.0,
            "reasoning": "evidence-based explanation for this status",
            "suggested_action": "what user should do if not found",
            "disambiguation_needed": false,
            "ambiguity_note": null
        }}
    ]
}}

CRITICAL RULES:
- Return one entry for EACH requested target
- For "not_visible": Evidence must explain what's blocking view (wrong angle, a cover/shield, out of frame)
  Action: Suggest specific angle or side to photograph
- For "not_present": Evidence must explain why (no mounting points, device type doesn't use this, integrated differently)
  Action: Suggest where to check or what alternative exists
- For "ambiguous": List all matching components with brief location descriptions
  Action: Ask user to specify which one
- Only provide bounding_box when status is "found" and confidence > 0.4
""",
            image,
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=SPATIAL_MULTI_SCHEMA,
                temperature=0.2
            )

            if isinstance(response, dict):
                raw_results = response.get("results", [])
                if isinstance(raw_results, list):
                    return [
                        self._process_multi_result(r, width, height)
                        for r in raw_results
                    ]

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
- Can you provide a bounding box?
- Only provide coordinates if you can CLEARLY see the component

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
        "ymin": 0-1000 scaled,
        "xmin": 0-1000 scaled,
        "ymax": 0-1000 scaled,
        "xmax": 0-1000 scaled
    }},
    "confidence": 0.0 to 1.0,
    "suggested_action": "what user should do if component not found",
    "visible_alternatives": ["list of components that ARE visible in this image"],
    "typical_location": "where this component is typically found on this type of device",
    "disambiguation_needed": false,
    "ambiguity_note": null
}}

Only provide bounding_box if confidence > 0.4 and you can CLEARLY see the component.
""",
            image,
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=SPATIAL_SINGLE_SCHEMA,
                temperature=0.2
            )

            if isinstance(response, dict):
                return self._process_spatial_response(
                    response, width, height, component_name
                )

            return self._create_not_found_response(component_name)

        except Exception as e:
            logger.error(f"Spatial mapping failed: {e}")
            return self._create_error_response(component_name, str(e))

    def _process_multi_result(
        self, result: Dict[str, Any], width: int, height: int
    ) -> Dict[str, Any]:
        """Process a single result from multi-target localization."""
        target = result.get("target", "unknown")
        status = result.get("status", "not_visible")
        confidence = float(result.get("confidence", 0.0))
        component_visible = result.get("component_visible", status == "found")

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

        # Parse bounding box if found
        bbox = result.get("bounding_box")
        if bbox and component_visible and confidence >= self.LOCALIZATION_THRESHOLD:
            try:
                y_min_norm = float(bbox.get("ymin", 0)) / 1000.0
                x_min_norm = float(bbox.get("xmin", 0)) / 1000.0
                y_max_norm = float(bbox.get("ymax", 0)) / 1000.0
                x_max_norm = float(bbox.get("xmax", 0)) / 1000.0

                entry["bounding_box"] = bbox
                entry["pixel_coords"] = {
                    "x_min": int(x_min_norm * width),
                    "y_min": int(y_min_norm * height),
                    "x_max": int(x_max_norm * width),
                    "y_max": int(y_max_norm * height),
                }
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to parse bounding box for {target}: {e}")

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
            try:
                y_min_norm = float(bbox.get("ymin", 0)) / 1000.0
                x_min_norm = float(bbox.get("xmin", 0)) / 1000.0
                y_max_norm = float(bbox.get("ymax", 0)) / 1000.0
                x_max_norm = float(bbox.get("xmax", 0)) / 1000.0

                result["bounding_box"] = bbox
                result["pixel_coords"] = {
                    "x_min": int(x_min_norm * width),
                    "y_min": int(y_min_norm * height),
                    "x_max": int(x_max_norm * width),
                    "y_max": int(y_max_norm * height),
                }
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to parse bounding box: {e}")
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
        # Don't attempt if device wasn't identified
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

        # Check answer_type - only localize for relevant types
        answer_type = query_info.get("answer_type", "")
        if answer_type in [
            "explain_only",
            "identify_only",
            "ask_clarifying_questions",
            "reject_invalid_image",
            "ask_for_better_input",
            "safety_warning_only",
        ]:
            return False, f"Localization not needed for answer_type={answer_type}"

        # Check if query needs it
        needs_localization = query_info.get("needs_localization", False)
        target_component = query_info.get("target_component")
        target_components = query_info.get("target_components", [])

        if not needs_localization and not target_component and not target_components:
            return False, "Query does not require component localization"

        return True, "Localization appropriate"

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


# Singleton instance
spatial_mapper = SpatialMapper()
