"""
Response Builder Utility
Builds the enhanced response schema based on answer_type and pipeline results.
Maps all agent outputs to the unified JSON structure.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# Answer type to UI title mapping
ANSWER_TYPE_TITLES = {
    "locate_only": "Component Location",
    "identify_only": "Detected Components",
    "explain_only": "How It Works",
    "troubleshoot_steps": "Troubleshooting Steps",
    "diagnose_only": "Diagnosis",
    "mixed": "Device Overview",
    "ask_clarifying_questions": "I need more information",
    "reject_invalid_image": "Image Not Suitable",
    "ask_for_better_input": "Better Image Needed",
    "safety_warning_only": "Safety Alert",
}

# Legacy status mapping for backwards compatibility
class ResponseStatus:
    SUCCESS = "success"
    INVALID_IMAGE = "invalid_image"
    LOW_CONFIDENCE = "low_confidence"
    COMPONENT_NOT_FOUND = "component_not_located"
    NEEDS_CLARIFICATION = "needs_clarification"
    ERROR = "error"


def build_enhanced_response(
    answer_type: str,
    device_info: Dict[str, Any],
    query_info: Dict[str, Any],
    validation_info: Dict[str, Any] = None,
    safety_info: Dict[str, Any] = None,
    localization_results: List[Dict[str, Any]] = None,
    step_info: Dict[str, Any] = None,
    image_dims: tuple = None,
    grounding_info: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Build the unified enhanced response conforming to the new schema.

    Every response includes:
    - answer_type, needs_clarification, cannot_comply_reason
    - device_info (always)
    - audio_instructions (always, generated later by audio_generator)
    - Conditional sections based on answer_type
    """
    response = {
        "answer_type": answer_type,
        "needs_clarification": False,
        "cannot_comply_reason": None,
    }

    # --- Device Info ---
    response["device_info"] = _build_device_info(device_info)

    # --- Set cannot_comply_reason based on context ---
    if answer_type == "reject_invalid_image":
        response["cannot_comply_reason"] = "invalid_image"
    elif answer_type == "ask_for_better_input":
        device_confidence = device_info.get("device_confidence", 0.0)
        image_quality = (validation_info or {}).get("image_quality", "good")
        if image_quality in ("blurry", "dark", "too_far"):
            response["cannot_comply_reason"] = "low_confidence"
        elif device_confidence < 0.3:
            response["cannot_comply_reason"] = "low_confidence"
    elif answer_type == "safety_warning_only":
        response["cannot_comply_reason"] = "safety_risk"

    # --- Needs Clarification ---
    if answer_type == "ask_clarifying_questions":
        response["needs_clarification"] = True
    elif query_info.get("clarification_needed"):
        response["needs_clarification"] = True

    # --- Message (for UI display) ---
    response["message"] = _get_message_for_type(
        answer_type, device_info, validation_info, safety_info, query_info
    )

    # --- Section Title (for dynamic UI) ---
    response["section_title"] = ANSWER_TYPE_TITLES.get(answer_type, "Analysis Results")

    # --- Localization Results ---
    if answer_type in ("locate_only", "troubleshoot_steps", "mixed"):
        response["localization_results"] = localization_results or []
    else:
        response["localization_results"] = None

    # --- Explanation ---
    if answer_type in ("explain_only", "mixed"):
        if step_info and isinstance(step_info, dict):
            response["explanation"] = step_info.get("explanation")
        else:
            response["explanation"] = None
    else:
        response["explanation"] = None

    # --- Diagnosis ---
    if answer_type in ("troubleshoot_steps", "diagnose_only", "mixed", "safety_warning_only"):
        response["diagnosis"] = _build_diagnosis(step_info, safety_info)
    else:
        response["diagnosis"] = None

    # --- Troubleshooting Steps ---
    if answer_type in ("troubleshoot_steps", "mixed"):
        response["troubleshooting_steps"] = _build_steps(step_info)
    else:
        response["troubleshooting_steps"] = None

    # --- Clarifying Questions ---
    if response["needs_clarification"]:
        questions = query_info.get("clarifying_questions", [])
        if not questions and device_info.get("clarifying_questions"):
            questions = device_info["clarifying_questions"]
        if not questions:
            questions = [
                "What specific issue are you experiencing?",
                "Which part of the device are you asking about?",
            ]
        response["clarifying_questions"] = questions
    else:
        response["clarifying_questions"] = None

    # --- Visualizations ---
    response["visualizations"] = _build_visualizations(
        localization_results, image_dims
    )

    # --- Audio instructions placeholder (filled by audio_generator) ---
    response["audio_instructions"] = ""
    # Preserve any audio already generated by step_generator
    if step_info and isinstance(step_info, dict):
        audio = step_info.get("audio_instructions", "")
        if audio:
            response["audio_instructions"] = audio

    # --- Web Grounding ---
    response["web_grounding_used"] = bool(
        grounding_info and grounding_info.get("grounded")
    )
    if response["web_grounding_used"]:
        # Include actual source URIs from grounding metadata
        sources = grounding_info.get("sources", [])
        if sources and isinstance(sources, list):
            response["grounding_sources"] = sources  # [{url, title}, ...]
        else:
            response["grounding_sources"] = [{"url": "", "title": grounding_info.get("sources_summary", "Google Search")}]
        response["grounding_sources_summary"] = grounding_info.get("sources_summary", "Google Search")
        response["grounding_disclaimer"] = grounding_info.get("disclaimer")
        # Include search entry point HTML if available (for rich rendering)
        if grounding_info.get("search_entry_point_html"):
            response["search_entry_point_html"] = grounding_info["search_entry_point_html"]
    else:
        response["grounding_sources"] = None
        response["grounding_sources_summary"] = None

    # --- Legacy compatibility fields ---
    response["status"] = _answer_type_to_status(answer_type)
    response["device_identified"] = device_info.get("device_type", "Unknown")
    response["device_confidence"] = device_info.get("device_confidence", 0.0)
    response["confidence_level"] = device_info.get("confidence_level", "low")

    # Legacy fields from step_info
    if step_info and isinstance(step_info, dict):
        response["issue_diagnosis"] = step_info.get("issue_diagnosis", "")
        response["warnings"] = step_info.get("warnings")
        response["when_to_seek_help"] = step_info.get("when_to_seek_help")
    else:
        response["issue_diagnosis"] = response.get("message", "")

    # Detected components
    if device_info.get("components"):
        response["detected_components"] = device_info["components"]

    # Safety info
    if safety_info and safety_info.get("safety_detected"):
        response["safety"] = safety_info

    # Rejection-specific fields
    if answer_type == "reject_invalid_image":
        image_category = (validation_info or {}).get("image_category", "unknown")
        response["image_category"] = image_category
        response["what_was_detected"] = (validation_info or {}).get("what_i_see", "")
        response["suggestion"] = (validation_info or {}).get("suggestion", "Please upload a photo of an electronic device.")
        response["supported_devices"] = (validation_info or {}).get("supported_devices", [
            "WiFi Routers & Modems", "Printers & Scanners",
            "Laptops & Computers", "Smart Home Devices",
            "Home Appliances", "Circuit Boards & Arduino",
        ])
        # Generate contextual rejection message based on what was detected
        response["message"] = _get_contextual_rejection_message(
            image_category,
            (validation_info or {}).get("what_i_see", ""),
            (validation_info or {}).get("rejection_reason", ""),
        )

    # Low confidence specific fields
    if answer_type == "ask_for_better_input":
        response["what_i_see"] = device_info.get("what_i_see", "")
        response["reasoning"] = device_info.get("reasoning", "")
        response["suggestions"] = device_info.get("suggestions", [
            "Ensure the entire device is visible in the photo",
            "Take the photo in good lighting",
            "Include any visible brand names or model numbers",
        ])

    return response


def _build_device_info(device_info: Dict[str, Any]) -> Dict[str, Any]:
    """Build the device_info section of the response."""
    brand = device_info.get("brand", "unknown")
    model = device_info.get("model", "not visible")
    
    # Only include brand_model_guidance if brand/model could NOT be identified
    brand_unknown = not brand or brand.lower() in ("unknown", "generic", "")
    model_unknown = not model or model.lower() in ("not visible", "")
    
    if brand_unknown or model_unknown:
        guidance = device_info.get("brand_model_guidance")
    else:
        # Brand and model successfully identified - no guidance needed
        guidance = None
    
    return {
        "device_category": device_info.get("device_category", "unknown"),
        "device_type": device_info.get("device_type", "Unknown"),
        "brand": brand or "unknown",
        "model": model or "not visible",
        "brand_model_guidance": guidance,
        "confidence": device_info.get("device_confidence", 0.0),
        "components": device_info.get("components", []),
    }


def _build_diagnosis(
    step_info: Dict[str, Any] = None,
    safety_info: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Build the diagnosis section."""
    diagnosis = {
        "issue": "",
        "severity": "medium",
        "safety_warning": None,
    }

    if step_info and isinstance(step_info, dict):
        # From step generator
        diag = step_info.get("diagnosis")
        if isinstance(diag, dict):
            diagnosis["issue"] = diag.get("issue", "")
            diagnosis["severity"] = diag.get("severity", "medium")
            diagnosis["safety_warning"] = diag.get("safety_warning")
            if diag.get("possible_causes"):
                diagnosis["possible_causes"] = diag["possible_causes"]
            if diag.get("indicators"):
                diagnosis["indicators"] = diag["indicators"]
            if diag.get("professional_needed"):
                diagnosis["professional_needed"] = True
        elif step_info.get("issue_diagnosis"):
            diagnosis["issue"] = step_info["issue_diagnosis"]

    if safety_info and safety_info.get("safety_detected"):
        diagnosis["safety_warning"] = safety_info.get(
            "safety_message", "This situation may require professional help."
        )
        diagnosis["severity"] = "critical"

    return diagnosis


def _build_steps(step_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Build the troubleshooting_steps section."""
    if not step_info or not isinstance(step_info, dict):
        return []

    raw_steps = step_info.get("troubleshooting_steps", [])
    if not isinstance(raw_steps, list):
        return []

    steps = []
    for i, s in enumerate(raw_steps):
        if not isinstance(s, dict):
            continue
        steps.append({
            "step": s.get("step", s.get("step_number", i + 1)),
            "instruction": s.get("instruction", ""),
            "visual_cue": s.get("visual_cue", ""),
            "estimated_time": s.get("estimated_time", ""),
            "safety_note": s.get("safety_note"),
            "overlay_reference": s.get("overlay_reference"),
        })

    return steps


def _build_visualizations(
    localization_results: List[Dict[str, Any]] = None,
    image_dims: tuple = None,
) -> List[Dict[str, Any]]:
    """Build the visualizations section from localization results.
    
    IMPORTANT: Returns normalized coordinates (0.0-1.0) for frontend rendering.
    The frontend ARImageCanvas expects coordinates in 0-1 range and converts to percentages.
    """
    if not localization_results:
        return []

    # Get image dimensions for normalization
    img_width = image_dims[0] if image_dims else 1
    img_height = image_dims[1] if image_dims else 1

    visualizations = []
    logger.info(f"📊 Building visualizations from {len(localization_results)} localization results (image: {img_width}x{img_height}px)")
    
    for i, result in enumerate(localization_results):
        if not isinstance(result, dict):
            logger.warning(f"⚠️ Skipping non-dict result at index {i}")
            continue
        
        target = result.get("target", "unknown")
        status = result.get("status", "unknown")
        
        if status != "found":
            logger.info(f"ℹ️ Skipping '{target}' with status '{status}' (not 'found')")
            continue

        pixel_coords = result.get("pixel_coords")
        bbox = None
        
        if not pixel_coords:
            logger.error(f"❌ Component '{target}' marked as 'found' but has no pixel_coords!")
            continue
            
        if not isinstance(pixel_coords, dict):
            logger.error(f"❌ Component '{target}' has invalid pixel_coords type: {type(pixel_coords)}")
            continue
        
        # Get pixel values
        x_min_px = pixel_coords.get("x_min", 0)
        y_min_px = pixel_coords.get("y_min", 0)
        x_max_px = pixel_coords.get("x_max", 0)
        y_max_px = pixel_coords.get("y_max", 0)
        
        logger.info(f"🎯 Processing '{target}': pixel_coords=({x_min_px},{y_min_px})-({x_max_px},{y_max_px})")
        
        # Clamp to image dimensions first
        x_min_px = max(0, min(x_min_px, img_width))
        y_min_px = max(0, min(y_min_px, img_height))
        x_max_px = max(0, min(x_max_px, img_width))
        y_max_px = max(0, min(y_max_px, img_height))
        
        # Validate box has area
        if x_min_px >= x_max_px or y_min_px >= y_max_px:
            logger.error(f"❌ Invalid box for '{target}' after clamping: ({x_min_px},{y_min_px})-({x_max_px},{y_max_px})")
            continue
        
        # Normalize to 0-1 range for frontend rendering
        bbox = {
            "x_min": x_min_px / img_width if img_width > 0 else 0,
            "y_min": y_min_px / img_height if img_height > 0 else 0,
            "x_max": x_max_px / img_width if img_width > 0 else 0,
            "y_max": y_max_px / img_height if img_height > 0 else 0,
        }
        
        # Final validation
        if bbox["x_min"] >= bbox["x_max"] or bbox["y_min"] >= bbox["y_max"]:
            logger.error(f"❌ Normalized bbox invalid for '{target}': {bbox}")
            continue
        
        # Log for debugging
        logger.info(f"✅ '{target}': pixel=({x_min_px},{y_min_px})-({x_max_px},{y_max_px}) -> normalized=({bbox['x_min']:.3f},{bbox['y_min']:.3f})-({bbox['x_max']:.3f},{bbox['y_max']:.3f})")

        target = result.get("target", "unknown")
        viz_entry = {
            "target": target,
            "bounding_box": bbox,
            "arrow_hint": None,
            "label": target.title(),
            "landmark_description": result.get("landmark_description", ""),
            "confidence": result.get("confidence", 0.0),
            "overlay_id": f"viz_{i + 1}",
            "disambiguation_needed": result.get("disambiguation_needed", False),
            "ambiguity_note": result.get("ambiguity_note"),
            # Include spatial description for detail panel
            "spatial_description": result.get("spatial_description", ""),
            "reasoning": result.get("reasoning", ""),
            "suggested_action": result.get("suggested_action", ""),
        }
        visualizations.append(viz_entry)
        logger.info(f"✅ Added visualization for '{target}' to response")

    logger.info(f"📊 Final visualization count: {len(visualizations)}")
    return visualizations


def _get_contextual_rejection_message(
    image_category: str,
    what_i_see: str,
    rejection_reason: str,
) -> str:
    """Generate a contextual rejection message based on what was actually detected in the image."""
    category = (image_category or "").lower().replace(" ", "_")
    
    contextual_messages = {
        "person": (
            f"This image shows people, not an electronic device. "
            f"FixIt AI helps troubleshoot electronic devices like routers, printers, and circuit boards. "
            f"Please upload a photo of the device you need help with."
        ),
        "software_screenshot": (
            f"This appears to be a software interface or screenshot. "
            f"FixIt AI troubleshoots physical electronic devices. "
            f"For software help, please consult the software's help documentation."
        ),
        "document": (
            f"This appears to be a document or text content. "
            f"FixIt AI needs a photo of the physical device you want to troubleshoot."
        ),
        "nature": (
            f"This appears to be a nature or outdoor scene. "
            f"FixIt AI is designed to help with electronic device troubleshooting. "
            f"Please upload a photo of the device you need assistance with."
        ),
        "food": (
            f"This appears to be a food or beverage image. "
            f"FixIt AI helps troubleshoot electronic devices. "
            f"Please upload a photo of the device you need help with."
        ),
        "artwork": (
            f"This appears to be artwork or an illustration. "
            f"FixIt AI needs a real photograph of a physical electronic device to provide troubleshooting help."
        ),
    }
    
    # Use contextual message if available, otherwise use what_i_see for a custom message
    if category in contextual_messages:
        return contextual_messages[category]
    
    if what_i_see:
        return (
            f"I can see {what_i_see}, but this doesn't appear to be an electronic device I can help troubleshoot. "
            f"FixIt AI helps with devices like routers, printers, laptops, and appliances. "
            f"Please upload a photo of the device you need help with."
        )
    
    return rejection_reason or "This image is not suitable for device troubleshooting. Please upload a photo of an electronic device."


def _get_message_for_type(
    answer_type: str,
    device_info: Dict[str, Any],
    validation_info: Dict[str, Any] = None,
    safety_info: Dict[str, Any] = None,
    query_info: Dict[str, Any] = None,
) -> str:
    """Generate appropriate message based on answer_type."""
    device_type = device_info.get("device_type", "device")

    messages = {
        "locate_only": f"Located components on your {device_type}.",
        "identify_only": f"I identified this as a {device_type}.",
        "explain_only": f"Here's how your {device_type} works.",
        "troubleshoot_steps": f"Here's how to troubleshoot your {device_type}.",
        "diagnose_only": f"Here's my diagnosis for your {device_type}.",
        "mixed": f"Here's a comprehensive analysis of your {device_type}.",
        "ask_clarifying_questions": "I need more information to help you effectively.",
        "ask_for_better_input": "I'm having trouble analyzing the image clearly.",
        "safety_warning_only": "This situation may require professional help. Please read the safety warning carefully.",
    }

    if answer_type == "reject_invalid_image":
        return (validation_info or {}).get(
            "rejection_reason",
            "This image is not suitable for device troubleshooting.",
        )

    return messages.get(answer_type, "Analysis complete.")


def _answer_type_to_status(answer_type: str) -> str:
    """Map answer_type to legacy status for backwards compatibility."""
    mapping = {
        "locate_only": ResponseStatus.SUCCESS,
        "identify_only": ResponseStatus.SUCCESS,
        "explain_only": ResponseStatus.SUCCESS,
        "troubleshoot_steps": ResponseStatus.SUCCESS,
        "diagnose_only": ResponseStatus.SUCCESS,
        "mixed": ResponseStatus.SUCCESS,
        "ask_clarifying_questions": ResponseStatus.NEEDS_CLARIFICATION,
        "reject_invalid_image": ResponseStatus.INVALID_IMAGE,
        "ask_for_better_input": ResponseStatus.LOW_CONFIDENCE,
        "safety_warning_only": ResponseStatus.SUCCESS,
    }
    return mapping.get(answer_type, ResponseStatus.SUCCESS)


# --- Legacy builders kept for backwards compatibility ---

def build_troubleshoot_response(
    device_info: Dict[str, Any],
    spatial_info: Dict[str, Any],
    step_info: Dict[str, Any],
    image_dims: tuple,
    validation_info: Dict[str, Any] = None,
    query_info: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Legacy builder - delegates to build_enhanced_response."""
    answer_type = (query_info or {}).get("answer_type", "troubleshoot_steps")

    # Convert single spatial_info to localization_results format
    localization_results = None
    if spatial_info and spatial_info.get("component_name"):
        component_visible = spatial_info.get("component_visible", False)
        status = "found" if component_visible else "not_visible"
        localization_results = [{
            "target": spatial_info.get("component_name", "unknown"),
            "status": status,
            "bounding_box": spatial_info.get("bounding_box"),
            "pixel_coords": spatial_info.get("pixel_coords"),
            "spatial_description": spatial_info.get("spatial_description", ""),
            "landmark_description": spatial_info.get("landmark_description", ""),
            "reasoning": spatial_info.get("visibility_reason", ""),
            "suggested_action": spatial_info.get("suggested_action", ""),
            "confidence": spatial_info.get("confidence", 0.0),
            "disambiguation_needed": spatial_info.get("disambiguation_needed", False),
            "ambiguity_note": spatial_info.get("ambiguity_note"),
        }]

    return build_enhanced_response(
        answer_type=answer_type,
        device_info=device_info,
        query_info=query_info or {},
        validation_info=validation_info,
        localization_results=localization_results,
        step_info=step_info,
        image_dims=image_dims,
    )


def build_rejection_response(
    validation_info: Dict[str, Any],
    query: str,
) -> Dict[str, Any]:
    """Build rejection response using enhanced builder."""
    return build_enhanced_response(
        answer_type="reject_invalid_image",
        device_info={"device_type": None, "device_confidence": 0.0},
        query_info={"query_type": "unclear", "answer_type": "reject_invalid_image"},
        validation_info=validation_info,
    )


def build_low_confidence_response(
    device_info: Dict[str, Any],
    query: str,
) -> Dict[str, Any]:
    """Build low confidence response using enhanced builder."""
    return build_enhanced_response(
        answer_type="ask_for_better_input",
        device_info=device_info,
        query_info={"query_type": "unclear", "answer_type": "ask_for_better_input",
                     "clarification_needed": True,
                     "clarifying_questions": device_info.get("clarifying_questions", [])},
    )


def build_component_not_found_response(
    device_info: Dict[str, Any],
    spatial_info: Dict[str, Any],
    component_name: str,
) -> Dict[str, Any]:
    """Build component not found response using enhanced builder."""
    localization_results = [{
        "target": component_name,
        "status": "not_visible",
        "bounding_box": None,
        "pixel_coords": None,
        "spatial_description": spatial_info.get("spatial_description", ""),
        "landmark_description": spatial_info.get("landmark_description", ""),
        "reasoning": spatial_info.get("visibility_reason", ""),
        "suggested_action": spatial_info.get("suggested_action", ""),
        "confidence": 0.0,
        "disambiguation_needed": False,
        "ambiguity_note": None,
        "visible_alternatives": spatial_info.get("visible_alternatives", []),
        "typical_location": spatial_info.get("typical_location", ""),
    }]

    return build_enhanced_response(
        answer_type="locate_only",
        device_info=device_info,
        query_info={"query_type": "locate", "answer_type": "locate_only"},
        localization_results=localization_results,
    )
