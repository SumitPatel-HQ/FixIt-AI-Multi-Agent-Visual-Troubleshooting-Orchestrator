"""
Schema Validator Utility
Enforces output schema compliance based on answer_type.
Validates that responses contain required fields and omit irrelevant ones.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Valid answer_type values
VALID_ANSWER_TYPES = {
    "locate_only",
    "identify_only",
    "explain_only",
    "troubleshoot_steps",
    "diagnose_only",
    "mixed",
    "ask_clarifying_questions",
    "reject_invalid_image",
    "ask_for_better_input",
    "safety_warning_only",
}

# Valid cannot_comply_reason values
VALID_CANNOT_COMPLY_REASONS = {
    "not_visible",
    "not_present",
    "low_confidence",
    "invalid_image",
    "safety_risk",
    None,
}

# Valid localization status values
VALID_LOCALIZATION_STATUS = {"found", "not_visible", "not_present", "ambiguous"}

# Fields that must ALWAYS be present
ALWAYS_REQUIRED_FIELDS = {
    "answer_type",
    "needs_clarification",
    "cannot_comply_reason",
    "audio_instructions",
    "device_info",
}

# Fields that must be null/absent for specific answer_types
FORBIDDEN_FIELDS_BY_TYPE = {
    "locate_only": {"troubleshooting_steps", "explanation"},
    "identify_only": {"troubleshooting_steps", "explanation", "localization_results"},
    "explain_only": {"troubleshooting_steps", "localization_results"},
    "ask_clarifying_questions": {"troubleshooting_steps", "explanation", "localization_results"},
    "reject_invalid_image": {"troubleshooting_steps", "explanation", "localization_results"},
    "ask_for_better_input": {"troubleshooting_steps", "explanation", "localization_results"},
    "safety_warning_only": {"troubleshooting_steps", "explanation"},
}

# Fields that are conditionally required
REQUIRED_FIELDS_BY_TYPE = {
    "locate_only": {"localization_results"},
    "identify_only": {"device_info"},
    "explain_only": {"explanation"},
    "troubleshoot_steps": {"diagnosis", "troubleshooting_steps"},
    "diagnose_only": {"diagnosis"},
    "mixed": set(),  # Flexible
    "ask_clarifying_questions": {"clarifying_questions"},
    "reject_invalid_image": set(),
    "ask_for_better_input": set(),
    "safety_warning_only": {"diagnosis"},
}


def validate_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and enforce schema compliance on a response.
    Fixes minor issues and logs warnings for significant ones.

    Returns the validated (and possibly corrected) response.
    """
    if not isinstance(response, dict):
        logger.error("Response is not a dict, returning safe fallback")
        return _create_fallback_response()

    answer_type = response.get("answer_type", "troubleshoot_steps")

    # Validate answer_type
    if answer_type not in VALID_ANSWER_TYPES:
        logger.warning(f"Invalid answer_type '{answer_type}', defaulting to 'troubleshoot_steps'")
        answer_type = "troubleshoot_steps"
        response["answer_type"] = answer_type

    # Ensure always-required fields exist
    if "needs_clarification" not in response:
        response["needs_clarification"] = False

    if "cannot_comply_reason" not in response:
        response["cannot_comply_reason"] = None
    elif response["cannot_comply_reason"] not in VALID_CANNOT_COMPLY_REASONS:
        logger.warning(f"Invalid cannot_comply_reason: {response['cannot_comply_reason']}")
        response["cannot_comply_reason"] = None

    if "audio_instructions" not in response or not response["audio_instructions"]:
        logger.warning("Missing audio_instructions, will be generated")
        response["audio_instructions"] = ""

    if "device_info" not in response:
        response["device_info"] = {
            "device_category": "unknown",
            "device_type": "Unknown",
            "brand": "unknown",
            "model": "not visible",
            "brand_model_guidance": None,
            "confidence": 0.0,
        }

    # Nullify forbidden fields for this answer_type
    forbidden = FORBIDDEN_FIELDS_BY_TYPE.get(answer_type, set())
    for field in forbidden:
        if field in response and response[field] is not None:
            if field == "troubleshooting_steps" and response[field]:
                logger.info(f"Removing {field} for answer_type={answer_type}")
            response[field] = None

    # Validate localization_results structure
    if "localization_results" in response and response["localization_results"]:
        response["localization_results"] = _validate_localization_results(
            response["localization_results"]
        )

    # Validate troubleshooting_steps structure
    if "troubleshooting_steps" in response and response["troubleshooting_steps"]:
        response["troubleshooting_steps"] = _validate_steps(
            response["troubleshooting_steps"]
        )

    # Validate visualizations structure
    if "visualizations" in response and response["visualizations"]:
        response["visualizations"] = _validate_visualizations(
            response["visualizations"]
        )

    # Ensure web_grounding fields
    if "web_grounding_used" not in response:
        response["web_grounding_used"] = False
    if "grounding_sources" not in response:
        response["grounding_sources"] = None

    return response


def _validate_localization_results(results: Any) -> List[Dict[str, Any]]:
    """Validate and normalize localization results."""
    if not isinstance(results, list):
        return []

    validated = []
    for item in results:
        if not isinstance(item, dict):
            continue
        entry = {
            "target": item.get("target", "unknown"),
            "status": item.get("status", "not_visible"),
            "bounding_box": item.get("bounding_box"),
            "spatial_description": item.get("spatial_description", ""),
            "landmark_description": item.get("landmark_description", ""),
            "reasoning": item.get("reasoning", ""),
            "suggested_action": item.get("suggested_action", ""),
            "confidence": float(item.get("confidence", 0.0)),
            "disambiguation_needed": item.get("disambiguation_needed", False),
        }
        if entry["status"] not in VALID_LOCALIZATION_STATUS:
            entry["status"] = "not_visible"
        validated.append(entry)

    return validated


def _validate_steps(steps: Any) -> List[Dict[str, Any]]:
    """Validate and normalize troubleshooting steps."""
    if not isinstance(steps, list):
        return []

    validated = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        validated.append({
            "step": step.get("step", step.get("step_number", i + 1)),
            "instruction": step.get("instruction", "No instruction"),
            "visual_cue": step.get("visual_cue", ""),
            "estimated_time": step.get("estimated_time", ""),
            "safety_note": step.get("safety_note"),
            "overlay_reference": step.get("overlay_reference"),
        })

    return validated


def _validate_visualizations(visualizations: Any) -> List[Dict[str, Any]]:
    """Validate and normalize visualization entries."""
    if not isinstance(visualizations, list):
        return []

    validated = []
    for i, viz in enumerate(visualizations):
        if not isinstance(viz, dict):
            continue
        entry = {
            "target": viz.get("target", "unknown"),
            "bounding_box": viz.get("bounding_box"),
            "arrow_hint": viz.get("arrow_hint"),
            "label": viz.get("label", viz.get("target", "unknown")),
            "landmark_description": viz.get("landmark_description", ""),
            "confidence": float(viz.get("confidence", 0.0)),
            "overlay_id": viz.get("overlay_id", f"viz_{i + 1}"),
            "disambiguation_needed": viz.get("disambiguation_needed", False),
            "ambiguity_note": viz.get("ambiguity_note"),
        }
        # Normalize bounding_box to expected format
        if entry["bounding_box"] and isinstance(entry["bounding_box"], dict):
            bbox = entry["bounding_box"]
            entry["bounding_box"] = {
                "x_min": int(bbox.get("x_min", 0)),
                "y_min": int(bbox.get("y_min", 0)),
                "x_max": int(bbox.get("x_max", 0)),
                "y_max": int(bbox.get("y_max", 0)),
            }
        validated.append(entry)

    return validated


def _create_fallback_response() -> Dict[str, Any]:
    """Create a safe fallback response when validation completely fails."""
    return {
        "answer_type": "troubleshoot_steps",
        "needs_clarification": False,
        "cannot_comply_reason": None,
        "device_info": {
            "device_category": "unknown",
            "device_type": "Unknown",
            "brand": "unknown",
            "model": "not visible",
            "brand_model_guidance": None,
            "confidence": 0.0,
        },
        "localization_results": None,
        "explanation": None,
        "diagnosis": {
            "issue": "An error occurred during analysis. Please try again.",
            "severity": "medium",
            "safety_warning": None,
        },
        "troubleshooting_steps": [
            {
                "step": 1,
                "instruction": "Please try submitting your request again.",
                "visual_cue": "",
                "estimated_time": "",
            }
        ],
        "clarifying_questions": None,
        "visualizations": None,
        "audio_instructions": "I encountered an error during analysis. Please try again.",
        "web_grounding_used": False,
        "grounding_sources": None,
    }
