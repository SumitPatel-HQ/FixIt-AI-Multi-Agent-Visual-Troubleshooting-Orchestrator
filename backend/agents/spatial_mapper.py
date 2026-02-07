"""
Spatial Mapper Agent
Locates components in device images with multi-stage reasoning.
Only activates when appropriate and provides useful alternatives when localization fails.
"""

from typing import Dict, Any, List, Tuple, Optional
from PIL import Image
import json
import logging
from backend.utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)


class SpatialMapper:
    """
    Locates specific components in device images.
    Uses multi-stage reasoning and provides helpful alternatives when localization fails.
    """
    
    # Minimum confidence to provide bounding box
    LOCALIZATION_THRESHOLD = 0.4

    def __init__(self):
        pass

    def locate_component(
        self, 
        image: Image.Image, 
        component_name: str, 
        image_dims: Tuple[int, int],
        device_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Locates a specific component in the image using multi-stage reasoning.
        
        Stage 1: Can I see the component at all?
        Stage 2: Can I determine its rough location?
        Stage 3: Can I provide precise coordinates?
        
        Only proceeds to next stage if previous stage succeeds.
        
        Args:
            image: PIL Image
            component_name: Component to locate
            image_dims: (width, height) tuple
            device_context: Optional device detection context
            
        Returns:
            Dict with:
            - component_visible: bool
            - component_name: str - What we were looking for
            - spatial_description: str - Natural language location
            - bounding_box: dict or None - Pixel coordinates if found
            - confidence: float
            - visibility_reason: str - Why visible/not visible
            - suggested_action: str - What user should do
            - alternatives: list - If not found, what IS visible
        """
        width, height = image_dims
        
        # Build context string
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
- What is it near or adjacent to?

STAGE 3 - PRECISE LOCATION (only if Stage 2 passes):
- Can you provide a bounding box?
- Only provide coordinates if you can CLEARLY see the component

BE HONEST:
- If you can't see it, say "not_visible"
- If image is unclear, say "too_blurry"
- If component doesn't exist on this device type, say "not_applicable"
- If you're unsure, set low confidence

Return JSON:
{{
    "component_visible": true/false,
    "component_name": "{component_name}",
    "visibility_status": "visible" | "not_visible" | "partially_visible" | "too_blurry" | "not_applicable" | "wrong_angle",
    "visibility_reason": "explain why component is or isn't visible",
    "spatial_description": "natural language location like 'bottom right corner, next to the power port' OR reason not visible",
    "bounding_box": null OR {{
        "ymin": 0-1000 scaled,
        "xmin": 0-1000 scaled,
        "ymax": 0-1000 scaled,
        "xmax": 0-1000 scaled
    }},
    "confidence": 0.0 to 1.0,
    "suggested_action": "what user should do if component not found",
    "visible_alternatives": ["list of components that ARE visible in this image"],
    "typical_location": "where this component is typically found on this type of device"
}}

Only provide bounding_box if confidence > 0.4 and you can CLEARLY see the component.
""",
            image
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                temperature=0.2
            )
            
            if isinstance(response, dict):
                return self._process_spatial_response(response, width, height, component_name)
            
            return self._create_not_found_response(component_name)

        except Exception as e:
            logger.error(f"Spatial mapping failed: {e}")
            return self._create_error_response(component_name, str(e))

    def _process_spatial_response(
        self, 
        response: Dict[str, Any], 
        width: int, 
        height: int, 
        component_name: str
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
            "spatial_description": response.get("spatial_description", "Location not identified"),
            "confidence": confidence,
            "suggested_action": response.get("suggested_action", ""),
            "visible_alternatives": response.get("visible_alternatives", []),
            "typical_location": response.get("typical_location", "")
        }
        
        # Only include bounding box if visible and confident
        bbox = response.get("bounding_box")
        if bbox and component_visible and confidence >= self.LOCALIZATION_THRESHOLD:
            # Scale from 1000-scale to actual pixels
            try:
                y_min_norm = float(bbox.get("ymin", 0)) / 1000.0
                x_min_norm = float(bbox.get("xmin", 0)) / 1000.0
                y_max_norm = float(bbox.get("ymax", 0)) / 1000.0
                x_max_norm = float(bbox.get("xmax", 0)) / 1000.0
                
                result["bounding_box"] = bbox  # Keep original normalized
                result["pixel_coords"] = {
                    "x_min": int(x_min_norm * width),
                    "y_min": int(y_min_norm * height),
                    "x_max": int(x_max_norm * width),
                    "y_max": int(y_max_norm * height)
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
            "bounding_box": None,
            "pixel_coords": None,
            "confidence": 0.0,
            "suggested_action": "Please try taking a clearer photo or describe what you're looking for",
            "visible_alternatives": [],
            "typical_location": ""
        }

    def _create_error_response(self, component_name: str, error: str) -> Dict[str, Any]:
        """Create a response when an error occurs."""
        return {
            "component_visible": False,
            "component_name": component_name,
            "visibility_status": "error",
            "visibility_reason": f"Error during localization: {error}",
            "spatial_description": "Error locating component",
            "bounding_box": None,
            "pixel_coords": None,
            "confidence": 0.0,
            "suggested_action": "Please try again",
            "visible_alternatives": [],
            "typical_location": "",
            "error": error
        }

    def should_attempt_localization(
        self, 
        device_info: Dict[str, Any],
        query_info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Determine if we should attempt spatial localization.
        
        Returns:
            Tuple of (should_attempt: bool, reason: str)
        """
        # Don't attempt if device wasn't identified
        device_confidence = device_info.get("device_confidence", 0.0)
        if device_confidence < 0.3:
            return False, "Device identification confidence too low for spatial localization"
        
        # Don't attempt for non-devices
        device_type = device_info.get("device_type", "Unknown")
        if device_type in ["Unknown", "not_a_device"]:
            return False, "Cannot localize components on unidentified or non-device images"
        
        # Only attempt if query needs it
        needs_localization = query_info.get("needs_localization", False)
        target_component = query_info.get("target_component")
        
        if not needs_localization and not target_component:
            return False, "Query does not require component localization"
        
        return True, "Localization appropriate"

    def get_component_from_query(self, query: str, device_components: List[str] = None) -> Optional[str]:
        """
        Extract the target component from a user query.
        
        Args:
            query: User's question
            device_components: List of components detected on the device
            
        Returns:
            Component name or None
        """
        query_lower = query.lower()
        
        # Common component patterns
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
            "antenna": ["antenna", "wifi antenna"]
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


# Singleton instance
spatial_mapper = SpatialMapper()
