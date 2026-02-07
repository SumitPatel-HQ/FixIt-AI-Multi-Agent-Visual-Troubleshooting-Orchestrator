"""
Audio Generator Utility
Generates audio instruction scripts from structured response fields.
Ensures audio_instructions is ALWAYS present regardless of answer_type.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def generate_audio_script(response: Dict[str, Any]) -> str:
    """
    Generate a natural-language audio script from structured response fields.
    Called after response is built but before final validation.

    Rules:
    - Audio script must ALWAYS be generated from structured output fields.
    - Never return empty/null audio_instructions.
    - Adapt tone and content based on answer_type.

    Args:
        response: The structured response dict.

    Returns:
        A string suitable for text-to-speech narration.
    """
    answer_type = response.get("answer_type", "troubleshoot_steps")

    generators = {
        "locate_only": _audio_for_locate,
        "identify_only": _audio_for_identify,
        "explain_only": _audio_for_explain,
        "troubleshoot_steps": _audio_for_troubleshoot,
        "diagnose_only": _audio_for_diagnose,
        "mixed": _audio_for_mixed,
        "ask_clarifying_questions": _audio_for_clarification,
        "reject_invalid_image": _audio_for_rejection,
        "ask_for_better_input": _audio_for_better_input,
        "safety_warning_only": _audio_for_safety,
    }

    generator = generators.get(answer_type, _audio_for_troubleshoot)
    try:
        script = generator(response)
        if script and script.strip():
            return script.strip()
    except Exception as e:
        logger.warning(f"Audio generation failed for {answer_type}: {e}")

    # Fallback: always return something
    return _audio_fallback(response)


def _audio_for_locate(response: Dict[str, Any]) -> str:
    """Generate audio for locate_only responses."""
    parts = []
    results = response.get("localization_results") or []

    if not results:
        return "I wasn't able to locate the requested component. Please try a different angle or specify which component you're looking for."

    found = [r for r in results if r.get("status") == "found"]
    not_found = [r for r in results if r.get("status") != "found"]

    for r in found:
        target = r.get("target", "the component")
        desc = r.get("spatial_description") or r.get("landmark_description") or "in the image"
        parts.append(f"I found the {target} {desc}.")

    for r in not_found:
        target = r.get("target", "the component")
        status = r.get("status", "not_visible")
        if status == "not_visible":
            action = r.get("suggested_action", "Try photographing from a different angle.")
            parts.append(f"The {target} is not visible from this angle. {action}")
        elif status == "not_present":
            reasoning = r.get("reasoning", "It does not appear to be present on this device.")
            parts.append(f"The {target} does not appear to be present. {reasoning}")
        elif status == "ambiguous":
            note = r.get("reasoning", "I see multiple similar components.")
            parts.append(f"I'm not sure which {target} you mean. {note}")

    return " ".join(parts)


def _audio_for_identify(response: Dict[str, Any]) -> str:
    """Generate audio for identify_only responses."""
    device_info = response.get("device_info", {})
    device_type = device_info.get("device_type", "device")
    confidence = device_info.get("confidence", 0.0)
    components = device_info.get("components", [])

    parts = []
    if confidence >= 0.6:
        parts.append(f"This appears to be a {device_type}.")
    elif confidence >= 0.3:
        parts.append(f"I think this might be a {device_type}, but I'm not entirely certain.")
    else:
        parts.append("I'm having trouble identifying this device.")

    if components:
        comp_str = ", ".join(components[:5])
        parts.append(f"I can see the following components: {comp_str}.")

    brand = device_info.get("brand", "unknown")
    model = device_info.get("model", "not visible")
    if brand and brand.lower() not in ("unknown", "generic"):
        parts.append(f"The brand appears to be {brand}.")
        if model and model.lower() != "not visible":
            parts.append(f"The model is {model}.")

    return " ".join(parts)


def _audio_for_explain(response: Dict[str, Any]) -> str:
    """Generate audio for explain_only responses."""
    explanation = response.get("explanation")
    if not explanation:
        device_type = response.get("device_info", {}).get("device_type", "this device")
        return f"I'd like to explain how {device_type} works, but I couldn't generate a detailed explanation. Please try again."

    parts = []
    if isinstance(explanation, dict):
        overview = explanation.get("overview", "")
        if overview:
            parts.append(overview)

        comp_functions = explanation.get("component_functions", [])
        if comp_functions and isinstance(comp_functions, list):
            for cf in comp_functions[:3]:
                if isinstance(cf, dict):
                    name = cf.get("name", "")
                    purpose = cf.get("purpose", "")
                    if name and purpose:
                        parts.append(f"The {name} {purpose}.")

        data_flow = explanation.get("data_flow", "")
        if data_flow:
            parts.append(data_flow)
    elif isinstance(explanation, str):
        parts.append(explanation)

    return " ".join(parts) if parts else "Here's an explanation of how this device works."


def _audio_for_troubleshoot(response: Dict[str, Any]) -> str:
    """Generate audio for troubleshoot_steps responses."""
    parts = []

    diagnosis = response.get("diagnosis")
    if isinstance(diagnosis, dict):
        issue = diagnosis.get("issue", "")
        if issue:
            parts.append(issue)
        safety = diagnosis.get("safety_warning")
        if safety:
            parts.append(f"Safety warning: {safety}")
    elif response.get("issue_diagnosis"):
        parts.append(response["issue_diagnosis"])

    steps = response.get("troubleshooting_steps") or []
    if steps:
        parts.append(f"Here are {len(steps)} steps to help fix this.")
        for step in steps[:5]:
            if isinstance(step, dict):
                instruction = step.get("instruction", "")
                if instruction:
                    step_num = step.get("step", step.get("step_number", ""))
                    parts.append(f"Step {step_num}: {instruction}")

    when_to_seek = response.get("when_to_seek_help")
    if when_to_seek:
        parts.append(f"Seek professional help if: {when_to_seek}")

    return " ".join(parts) if parts else "I've prepared troubleshooting steps for you."


def _audio_for_diagnose(response: Dict[str, Any]) -> str:
    """Generate audio for diagnose_only responses."""
    diagnosis = response.get("diagnosis")
    if not diagnosis or not isinstance(diagnosis, dict):
        return "I attempted to diagnose the issue but couldn't complete the analysis. Please try again."

    parts = []
    issue = diagnosis.get("issue", "")
    if issue:
        parts.append(issue)

    severity = diagnosis.get("severity", "")
    if severity:
        parts.append(f"The severity appears to be {severity}.")

    safety = diagnosis.get("safety_warning")
    if safety:
        parts.append(f"Important safety note: {safety}")

    causes = diagnosis.get("possible_causes", [])
    if causes:
        parts.append("Possible causes include: " + ", ".join(causes[:3]) + ".")

    return " ".join(parts) if parts else "I've completed the diagnosis."


def _audio_for_mixed(response: Dict[str, Any]) -> str:
    """Generate audio for mixed responses combining multiple intents."""
    parts = []

    # Include explanation if present
    explanation = response.get("explanation")
    if explanation and isinstance(explanation, dict):
        overview = explanation.get("overview", "")
        if overview:
            parts.append(overview)

    # Include diagnosis if present
    diagnosis = response.get("diagnosis")
    if diagnosis and isinstance(diagnosis, dict):
        issue = diagnosis.get("issue", "")
        if issue:
            parts.append(issue)

    # Include steps summary
    steps = response.get("troubleshooting_steps") or []
    if steps:
        parts.append(f"I've prepared {len(steps)} steps to address this.")

    # Include localization if present
    results = response.get("localization_results") or []
    found = [r for r in results if r.get("status") == "found"]
    if found:
        targets = ", ".join(r.get("target", "") for r in found)
        parts.append(f"I located: {targets}.")

    return " ".join(parts) if parts else "Here's a combined analysis of your request."


def _audio_for_clarification(response: Dict[str, Any]) -> str:
    """Generate audio for clarification requests."""
    questions = response.get("clarifying_questions") or []
    if questions:
        q_text = " ".join(questions[:3])
        return f"I need more information to help you. {q_text}"
    return "I need a bit more information. Could you describe what you're looking for or what issue you're experiencing?"


def _audio_for_rejection(response: Dict[str, Any]) -> str:
    """Generate audio for rejected images."""
    message = response.get("message") or response.get("rejection_reason", "")
    if message:
        return f"{message} FixIt AI helps troubleshoot electronic devices like routers, printers, and appliances. Please upload a photo of the actual device you need help with."
    return "This image doesn't appear to show an electronic device. Please upload a photo of the device you need help troubleshooting."


def _audio_for_better_input(response: Dict[str, Any]) -> str:
    """Generate audio for better input requests."""
    reason = response.get("cannot_comply_reason", "")
    message = response.get("message", "")
    if message:
        return f"{message} Please retake the photo with better lighting, a steady camera, and focus on the device from about 6 to 12 inches away."
    if reason == "low_confidence":
        return "I'm having trouble identifying this device clearly. Could you take a clearer photo, perhaps from a different angle, with good lighting?"
    return "The image quality isn't sufficient for analysis. Please retake the photo with better lighting and make sure the device is clearly visible."


def _audio_for_safety(response: Dict[str, Any]) -> str:
    """Generate audio for safety warnings."""
    parts = ["Warning! This situation may require professional help."]

    safety = response.get("safety", {})
    if isinstance(safety, dict) and safety.get("safety_message"):
        parts.append(safety["safety_message"])

    diagnosis = response.get("diagnosis")
    if isinstance(diagnosis, dict):
        warning = diagnosis.get("safety_warning")
        if warning:
            parts.append(warning)

    parts.append("Do not attempt to repair this yourself. Contact a qualified professional or your device manufacturer for assistance.")
    return " ".join(parts)


def _audio_fallback(response: Dict[str, Any]) -> str:
    """Last-resort fallback audio generation."""
    device_type = "your device"
    device_info = response.get("device_info")
    if isinstance(device_info, dict):
        dt = device_info.get("device_type", "")
        if dt and dt not in ("Unknown", "not_a_device"):
            device_type = dt

    return f"I've completed the analysis of {device_type}. Please review the results on screen for detailed information."
