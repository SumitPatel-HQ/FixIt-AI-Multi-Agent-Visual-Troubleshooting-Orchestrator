"""
Response Builder Utility
Builds scenario-specific responses based on pipeline results.
Handles different status types and confidence levels.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# Response status types
class ResponseStatus:
    SUCCESS = "success"
    INVALID_IMAGE = "invalid_image"
    LOW_CONFIDENCE = "low_confidence"
    COMPONENT_NOT_FOUND = "component_not_located"
    NEEDS_CLARIFICATION = "needs_clarification"
    ERROR = "error"


def build_troubleshoot_response(
    device_info: Dict[str, Any],
    spatial_info: Dict[str, Any],
    step_info: Dict[str, Any],
    image_dims: tuple,
    validation_info: Dict[str, Any] = None,
    query_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Combines outputs from all agents into a structured response.
    Creates scenario-specific responses based on confidence and results.
    
    Args:
        device_info: Device detection results
        spatial_info: Spatial mapping results
        step_info: Step generation results
        image_dims: (width, height) tuple
        validation_info: Image validation results (optional)
        query_info: Query parsing results (optional)
        
    Returns:
        Structured response matching the API model
    """
    
    # 1. Device Info
    device_identified = device_info.get("device_type", "Unknown Device")
    device_confidence = device_info.get("device_confidence", 0.0)
    confidence_level = device_info.get("confidence_level", "low")
    
    # 2. Spatial Info
    component = spatial_info.get("component_name")
    if not component:
        component = spatial_info.get("component")
    
    spatial_description = spatial_info.get("spatial_description", "Location not identified.")
    component_visible = spatial_info.get("component_visible", False)
    
    # Handle Bounding Box
    bbox = None
    if component_visible and spatial_info.get("pixel_coords"):
        bbox = spatial_info.get("pixel_coords")
        if bbox:
            width, height = image_dims
            bbox["x_min"] = max(0, min(bbox.get("x_min", 0), width))
            bbox["y_min"] = max(0, min(bbox.get("y_min", 0), height))
            bbox["x_max"] = max(0, min(bbox.get("x_max", 0), width))
            bbox["y_max"] = max(0, min(bbox.get("y_max", 0), height))
    
    # 3. Steps
    steps = step_info.get("troubleshooting_steps", [])
    issue_diagnosis = step_info.get("issue_diagnosis", "Diagnosis unavailable.")
    audio = step_info.get("audio_instructions", "")
    
    # 4. Determine response status
    status = _determine_status(device_info, spatial_info, step_info)
    
    # 5. Build base response
    response = {
        "status": status,
        "device_identified": device_identified,
        "device_confidence": device_confidence,
        "confidence_level": confidence_level,
        "component": component,
        "spatial_description": spatial_description,
        "bounding_box": bbox,
        "issue_diagnosis": issue_diagnosis,
        "troubleshooting_steps": steps,
        "audio_instructions": audio
    }
    
    # 6. Add scenario-specific fields
    response = _add_scenario_fields(response, device_info, spatial_info, step_info, query_info)
    
    return response


def build_rejection_response(
    validation_info: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Build a rejection response for invalid images.
    
    This is called when the image validation gate rejects the image.
    """
    
    return {
        "status": ResponseStatus.INVALID_IMAGE,
        "device_identified": None,
        "device_confidence": 0.0,
        "message": validation_info.get("rejection_reason", "This image is not suitable for device troubleshooting."),
        "image_category": validation_info.get("image_category", "unknown"),
        "what_was_detected": validation_info.get("what_i_see", ""),
        "suggestion": validation_info.get("suggestion", "Please upload a photo of an electronic device."),
        "supported_devices": validation_info.get("supported_devices", [
            "WiFi Routers & Modems",
            "Printers & Scanners",
            "Laptops & Computers",
            "Smart Home Devices",
            "Home Appliances",
            "Circuit Boards & Arduino"
        ]),
        "troubleshooting_steps": [],
        "audio_instructions": f"I'm sorry, but {validation_info.get('rejection_reason', 'this image does not appear to show an electronic device')}. FixIt AI helps troubleshoot electronic devices like routers, printers, and appliances. Please upload a photo of the actual device you need help with.",
        "issue_diagnosis": "Image not suitable for device troubleshooting."
    }


def build_low_confidence_response(
    device_info: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Build a response when device confidence is too low to proceed.
    """
    
    clarifying_questions = device_info.get("clarifying_questions", [
        "What type of device is this? (router, printer, laptop, etc.)",
        "Can you take a photo from a different angle?",
        "Are there any visible brand names or labels?"
    ])
    
    suggestions = device_info.get("suggestions", [
        "Ensure the entire device is visible in the photo",
        "Take the photo in good lighting",
        "Include any visible brand names or model numbers"
    ])
    
    return {
        "status": ResponseStatus.LOW_CONFIDENCE,
        "device_identified": device_info.get("device_type", "Unknown"),
        "device_confidence": device_info.get("device_confidence", 0.0),
        "message": "I'm having trouble identifying this device clearly.",
        "what_i_see": device_info.get("what_i_see", ""),
        "reasoning": device_info.get("reasoning", ""),
        "clarifying_questions": clarifying_questions,
        "suggestions": suggestions,
        "troubleshooting_steps": [{
            "step_number": 1,
            "instruction": "Please answer the questions above or provide a clearer image",
            "visual_cue": "Look for brand names, model numbers, or distinctive features",
            "estimated_time": "1 minute"
        }],
        "audio_instructions": "I'm having trouble identifying this device. Could you tell me what type of device this is, or try taking a clearer photo? Look for any visible brand names or model numbers that might help.",
        "issue_diagnosis": "Device identification uncertain - need more information.",
        "general_safety_tip": "Before working on any electronic device, always disconnect power first."
    }


def build_component_not_found_response(
    device_info: Dict[str, Any],
    spatial_info: Dict[str, Any],
    component_name: str
) -> Dict[str, Any]:
    """
    Build a response when component localization fails but device is known.
    """
    
    device_type = device_info.get("device_type", "device")
    visible_alternatives = spatial_info.get("visible_alternatives", [])
    typical_location = spatial_info.get("typical_location", "")
    suggested_action = spatial_info.get("suggested_action", "")
    
    message = f"I can see this is a {device_type}, but I couldn't locate the {component_name}."
    if spatial_info.get("visibility_reason"):
        message += f" {spatial_info.get('visibility_reason')}"
    
    steps = []
    
    if typical_location:
        steps.append({
            "step_number": 1,
            "instruction": f"The {component_name} is typically located {typical_location}",
            "visual_cue": f"Look for the {component_name} in that area",
            "estimated_time": "30 seconds"
        })
    
    if suggested_action:
        steps.append({
            "step_number": len(steps) + 1,
            "instruction": suggested_action,
            "visual_cue": "This should reveal the component",
            "estimated_time": "1 minute"
        })
    
    if not steps:
        steps.append({
            "step_number": 1,
            "instruction": f"Try taking a photo from a different angle to show the {component_name}",
            "visual_cue": f"Make sure the area containing the {component_name} is visible",
            "estimated_time": "30 seconds"
        })
    
    return {
        "status": ResponseStatus.COMPONENT_NOT_FOUND,
        "device_identified": device_type,
        "device_confidence": device_info.get("device_confidence", 0.0),
        "component": component_name,
        "component_searched": component_name,
        "message": message,
        "spatial_description": spatial_info.get("spatial_description", ""),
        "visible_components": visible_alternatives,
        "typical_location": typical_location,
        "suggestion": suggested_action,
        "troubleshooting_steps": steps,
        "audio_instructions": f"I can see your {device_type}, but the {component_name} isn't visible from this angle. {typical_location if typical_location else 'Try taking a photo from a different angle.'}"
    }


def _determine_status(
    device_info: Dict[str, Any],
    spatial_info: Dict[str, Any],
    step_info: Dict[str, Any]
) -> str:
    """Determine the response status based on results."""
    
    # Check for quota exhaustion (special case - not an error, just limited)
    if step_info.get("quota_info"):
        return ResponseStatus.SUCCESS  # Detection succeeded, just no detailed steps
    
    # Check for errors (but not quota exhaustion)
    if device_info.get("error") or step_info.get("error"):
        return ResponseStatus.ERROR
    
    # Check for low confidence
    device_confidence = device_info.get("device_confidence", 0.0)
    if device_confidence < 0.3 or device_info.get("needs_clarification"):
        return ResponseStatus.LOW_CONFIDENCE
    
    # Check if device wasn't identified
    device_type = device_info.get("device_type", "Unknown")
    if device_type in ["Unknown", "not_a_device"]:
        return ResponseStatus.INVALID_IMAGE
    
    # Check if clarification is needed
    if step_info.get("needs_clarification"):
        return ResponseStatus.NEEDS_CLARIFICATION
    
    # Check component visibility
    if spatial_info.get("component_name") and not spatial_info.get("component_visible", True):
        return ResponseStatus.COMPONENT_NOT_FOUND
    
    return ResponseStatus.SUCCESS


def _add_scenario_fields(
    response: Dict[str, Any],
    device_info: Dict[str, Any],
    spatial_info: Dict[str, Any],
    step_info: Dict[str, Any],
    query_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Add scenario-specific fields to the response."""
    
    status = response.get("status", ResponseStatus.SUCCESS)
    
    # For low confidence, add clarifying questions
    if status == ResponseStatus.LOW_CONFIDENCE:
        response["clarifying_questions"] = device_info.get("clarifying_questions", [])
        response["suggestions"] = device_info.get("suggestions", [])
        response["general_safety_tip"] = "Before working on any electronic device, always disconnect power first."
    
    # For component not found, add alternatives
    if status == ResponseStatus.COMPONENT_NOT_FOUND:
        response["visible_alternatives"] = spatial_info.get("visible_alternatives", [])
        response["typical_location"] = spatial_info.get("typical_location", "")
    
    # Add device components if available
    if device_info.get("components"):
        response["detected_components"] = device_info.get("components")
    
    # Add reasoning for transparency
    if device_info.get("reasoning"):
        response["reasoning"] = device_info.get("reasoning")
    
    # Add quota info if present
    if step_info.get("quota_info"):
        response["quota_info"] = step_info.get("quota_info")
        response["message"] = "Device identified successfully. Detailed steps temporarily unavailable (AI quota reached)."
    
    # Add query understanding info if available
    if query_info:
        response["query_understood"] = {
            "type": query_info.get("query_type"),
            "target": query_info.get("target_component"),
            "action": query_info.get("action_requested")
        }
    
    # Add warnings from step generation
    if step_info.get("warnings"):
        response["warnings"] = step_info.get("warnings")
    
    # Add when to seek professional help
    if step_info.get("when_to_seek_help"):
        response["when_to_seek_help"] = step_info.get("when_to_seek_help")
    
    return response


def format_response_for_display(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the response for frontend display.
    Ensures consistent structure and user-friendly messages.
    """
    
    formatted = response.copy()
    
    # Ensure status has a display message
    status = formatted.get("status", ResponseStatus.SUCCESS)
    status_messages = {
        ResponseStatus.SUCCESS: "Analysis complete",
        ResponseStatus.INVALID_IMAGE: "Invalid image for troubleshooting",
        ResponseStatus.LOW_CONFIDENCE: "Need more information",
        ResponseStatus.COMPONENT_NOT_FOUND: "Component not visible",
        ResponseStatus.NEEDS_CLARIFICATION: "Clarification needed",
        ResponseStatus.ERROR: "An error occurred"
    }
    formatted["status_message"] = status_messages.get(status, "Unknown status")
    
    # Format confidence as percentage
    confidence = formatted.get("device_confidence", 0.0)
    formatted["confidence_percent"] = f"{int(confidence * 100)}%"
    
    # Add confidence badge
    if confidence >= 0.6:
        formatted["confidence_badge"] = "high"
    elif confidence >= 0.3:
        formatted["confidence_badge"] = "medium"
    else:
        formatted["confidence_badge"] = "low"
    
    return formatted
