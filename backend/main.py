"""
FixIt AI Backend - Main API
Implements enhanced gate-based routing with answer_type enforcement.

Pipeline:
GATE 0: Image Processing
GATE 1-3: Combined Analysis (validation + detection + query parsing + safety + intent)
GATE 4: Component Localization (conditional, multi-target)
GATE 5: Web Grounding with Gemini Native Google Search (conditional)
GATE 6: Response Generation (answer_type-aware, enriched with web results)
GATE 7: Response Assembly + Audio Generation + Schema Validation

Note: RAG engine removed - using Gemini native grounding exclusively for knowledge retrieval.
"""

from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging
import time
import os

# Utilities
from backend.utils.image_processor import process_image_for_gemini
from backend.utils.gemini_client import gemini_client, get_quota_status, reset_circuit_breaker
from backend.utils.response_builder import (
    build_enhanced_response,
    build_rejection_response,
    build_low_confidence_response,
    build_component_not_found_response,
    ResponseStatus,
)
from backend.utils.schema_validator import validate_response
from backend.utils.audio_generator import generate_audio_script

# Agents
from backend.agents.image_validator import image_validator
from backend.agents.device_detector import device_detector
from backend.agents.spatial_mapper import spatial_mapper
# RAG engine removed - using Gemini native grounding instead
from backend.agents.step_generator import step_generator

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FixIt AI Backend",
    description="AI-powered device troubleshooting with visual understanding",
    version="0.3.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.6
MEDIUM_CONFIDENCE_THRESHOLD = 0.3

# Safety keywords that force safety_warning_only
SAFETY_KEYWORDS = [
    "burning", "smoke", "melting", "swelling battery", "swollen battery",
    "electric shock", "exposed mains", "sparking", "fire", "disconnect power",
    "electrocution", "short circuit", "overheating", "burning smell",
]

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.3.0", "pipeline": "enhanced-gate-based"}


@app.post("/api/troubleshoot")
async def troubleshoot(
    image_base64: str = Form(...),
    query: str = Form(...),
    device_hint: Optional[str] = Form(None),
    image_width: Optional[int] = Form(None),
    image_height: Optional[int] = Form(None),
):
    """
    Main endpoint for visual troubleshooting.
    Implements enhanced gate-based routing with answer_type enforcement.

    Gates:
    0. Image Processing
    1-3. Combined Analysis (validation + detection + intent + safety)
    4. Component Localization (conditional, multi-target)
    5. Response Generation (answer_type-aware)
    6. Web Grounding (conditional)
    7. Response Assembly + Audio + Schema Validation
    """
    start_time = time.time()
    logger.info(f"Received troubleshoot request: '{query}'")

    try:
        # ===========================================
        # GATE 0: Image Processing
        # ===========================================
        logger.info("GATE 0: Processing Image...")
        try:
            image = process_image_for_gemini(image_base64)
            current_width, current_height = image.size
            if not image_width or not image_height:
                image_width, image_height = current_width, current_height
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

        # ===========================================
        # GATES 1-3: Combined Analysis (1 API call)
        # Intent + Validation + Detection + Safety
        # ===========================================
        logger.info("GATES 1-3: Combined analysis...")
        try:
            combined_result = gemini_client.generate_combined_analysis(
                image=image,
                query=query,
                device_hint=device_hint,
            )
        except Exception as e:
            logger.error(f"Combined analysis failed: {e}")
            combined_result = {"error": str(e)}

        if combined_result.get("error"):
            logger.error(f"Combined analysis error: {combined_result.get('error')}")
            return _build_error_response(combined_result)

        # Extract sub-results
        validation_info = combined_result.get("validation", {})
        device_info = combined_result.get("device", {})
        query_info = combined_result.get("query", {})
        safety_info = combined_result.get("safety", {})

        # ===========================================
        # DECISION GATE: Image Validity
        # ===========================================
        if not validation_info.get("is_valid", False):
            logger.info(f"GATE 1 REJECTED: {validation_info.get('image_category')}")
            response = build_rejection_response(validation_info, query)
            response["audio_instructions"] = generate_audio_script(response)
            response = validate_response(response)
            logger.info(f"Completed in {time.time() - start_time:.2f}s (rejected)")
            return response

        # ===========================================
        # DECISION GATE: Image Quality
        # ===========================================
        image_quality = validation_info.get("image_quality", "good")
        if image_quality in ("blurry", "dark", "too_far"):
            logger.info(f"GATE 1b: Image quality issue: {image_quality}")
            query_info["answer_type"] = "ask_for_better_input"

        # ===========================================
        # DECISION GATE: Safety Override
        # ===========================================
        safety_detected = safety_info.get("safety_detected", False)
        if not safety_detected:
            # Also check query text for safety keywords
            query_lower = query.lower()
            for keyword in SAFETY_KEYWORDS:
                if keyword in query_lower:
                    safety_detected = True
                    safety_info["safety_detected"] = True
                    safety_info["safety_keywords_found"] = [keyword]
                    safety_info["safety_message"] = (
                        "STOP. This situation may require professional help. "
                        "Do NOT attempt DIY repair. Contact a qualified professional."
                    )
                    safety_info["override_answer_type"] = True
                    break

        if safety_detected and safety_info.get("override_answer_type", False):
            logger.info("SAFETY OVERRIDE: Forcing safety_warning_only")
            query_info["answer_type"] = "safety_warning_only"

        # ===========================================
        # DECISION GATE: Device Detection Confidence
        # ===========================================
        device_type = device_info.get("device_type", "Unknown")
        device_confidence = device_info.get("device_confidence", 0.0)

        # Compute confidence_level if not provided
        confidence_level = device_info.get("confidence_level")
        if not confidence_level:
            if device_confidence >= HIGH_CONFIDENCE_THRESHOLD:
                confidence_level = "high"
            elif device_confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            device_info["confidence_level"] = confidence_level

        logger.info(f"Device: {device_type} ({device_confidence:.2f}, {confidence_level})")

        if device_type == "not_a_device":
            logger.info("GATE 2 REJECTED: Not a device")
            response = build_rejection_response(
                {
                    "rejection_reason": device_info.get("reasoning", "Not an electronic device."),
                    "what_i_see": validation_info.get("what_i_see", ""),
                    "suggestion": "Please upload a photo of an electronic device.",
                    "image_category": "not_a_device",
                },
                query,
            )
            response["audio_instructions"] = generate_audio_script(response)
            response = validate_response(response)
            logger.info(f"Completed in {time.time() - start_time:.2f}s (not a device)")
            return response

        if confidence_level == "low" and device_confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            # Override answer_type unless safety took priority
            current_answer_type = query_info.get("answer_type", "")
            if current_answer_type != "safety_warning_only":
                logger.info("GATE 2: Low confidence, asking for better input")
                response = build_low_confidence_response(device_info, query)
                response["audio_instructions"] = generate_audio_script(response)
                response = validate_response(response)
                logger.info(f"Completed in {time.time() - start_time:.2f}s (low confidence)")
                return response

        # ===========================================
        # DECISION GATE: Multiple Devices
        # ===========================================
        if validation_info.get("multiple_devices", False):
            device_list = validation_info.get("device_list", [])
            if len(device_list) > 1 and query_info.get("answer_type") not in ("safety_warning_only",):
                logger.info(f"Multiple devices detected: {device_list}")
                query_info["answer_type"] = "ask_clarifying_questions"
                query_info["clarification_needed"] = True
                query_info["clarifying_questions"] = [
                    f"I see multiple devices: {', '.join(device_list)}. Which one do you need help with?"
                ]

        # ===========================================
        # Determine final answer_type
        # ===========================================
        answer_type = query_info.get("answer_type", "troubleshoot_steps")
        query_type = query_info.get("query_type", "unclear")
        target_component = query_info.get("target_component")
        target_components = query_info.get("target_components", [])
        needs_localization = query_info.get("needs_localization", False)

        logger.info(f"Answer type: {answer_type}, Query type: {query_type}")
        logger.info(f"Targets: {target_components or [target_component]}")

        # ===========================================
        # GATE 3.5: RAG Retrieval - REMOVED
        # Now using Gemini native grounding with Google Search instead
        # ===========================================
        manual_context = []  # Empty - relying on web grounding

        # =============================================
        # GATE 4: Component Localization (conditional)
        # ===========================================
        localization_results = []

        should_localize, localize_reason = spatial_mapper.should_attempt_localization(
            device_info, query_info
        )

        if should_localize:
            logger.info("GATE 4: Attempting localization...")

            # Determine targets
            targets = []
            if target_components:
                targets = target_components
            elif target_component:
                targets = [target_component]
            else:
                # Try extracting from query
                extracted = spatial_mapper.get_multiple_components_from_query(
                    query, device_info.get("components", [])
                )
                if extracted:
                    targets = extracted
                else:
                    single = spatial_mapper.get_component_from_query(
                        query, device_info.get("components", [])
                    )
                    if single:
                        targets = [single]
                    else:
                        targets = [f"component relevant to: {query}"]

            logger.info(f"Locating targets: {targets}")

            try:
                localization_results = spatial_mapper.locate_multiple_components(
                    image,
                    targets,
                    (image_width, image_height),
                    device_context=device_info,
                )
            except Exception as e:
                logger.error(f"Localization failed: {e}")
                localization_results = [
                    {
                        "target": t,
                        "status": "not_visible",
                        "reasoning": f"Localization error: {str(e)}",
                        "suggested_action": "Please try again.",
                        "confidence": 0.0,
                        "bounding_box": None,
                        "pixel_coords": None,
                        "spatial_description": "",
                        "landmark_description": "",
                        "disambiguation_needed": False,
                        "ambiguity_note": None,
                        "component_visible": False,
                    }
                    for t in targets
                ]

            # Check results
            found_count = sum(1 for r in localization_results if r.get("status") == "found")
            total_count = len(localization_results)
            logger.info(f"GATE 4: Found {found_count}/{total_count} targets")

            # If locate-only and ALL targets not found
            if answer_type == "locate_only" and found_count == 0 and total_count > 0:
                logger.info("GATE 4: No targets found, but returning locate results with status")
                # Don't early-return; let the response builder handle it with per-target status
        else:
            logger.info(f"GATE 4 SKIPPED: {localize_reason}")

        # ===========================================
        # GATE 5: Web Grounding (BEFORE step generation)
        # Grounded content enriches the step generator
        # ===========================================
        grounding_info = None
        should_ground = _should_trigger_web_grounding(
            answer_type, device_info, manual_context, query
        )

        if should_ground:
            logger.info("GATE 5: Attempting native Google Search grounding...")
            try:
                context_str = "\n\n".join(manual_context) if manual_context else ""
                grounding_info = gemini_client.generate_grounded_response(
                    query=query,
                    device_info=device_info,
                    context=context_str,
                )
                if grounding_info and grounding_info.get("grounded"):
                    logger.info(f"GATE 5: Web grounding successful - {len(grounding_info.get('sources', []))} sources")
                    # Inject grounded guidance into manual_context so step generator uses it
                    grounded_text = grounding_info.get("grounded_guidance", "")
                    if grounded_text:
                        manual_context.append(f"[Web Search Results]\n{grounded_text}")
                else:
                    logger.info("GATE 5: Web grounding returned no results")
                    grounding_info = None
            except Exception as e:
                logger.warning(f"Web grounding failed (non-fatal): {e}")
                grounding_info = None
        else:
            logger.info("GATE 5 SKIPPED: Web grounding not needed")

        # ===========================================
        # GATE 6: Response Generation (answer_type-aware)
        # Now enriched with grounded web context if available
        # ===========================================
        step_info = None

        # Only generate content for types that need it
        if answer_type in ("troubleshoot_steps", "explain_only", "diagnose_only", "mixed"):
            logger.info(f"GATE 6: Generating content for {answer_type}...")

            # Build spatial context for step generator
            spatial_context = {}
            if localization_results:
                found = [r for r in localization_results if r.get("status") == "found"]
                if found:
                    first = found[0]
                    spatial_context = {
                        "component": first.get("target"),
                        "component_name": first.get("target"),
                        "spatial_description": first.get("spatial_description"),
                        "component_visible": True,
                        "visible_alternatives": [],
                        "typical_location": "",
                    }
                    if first.get("pixel_coords"):
                        spatial_context["pixel_coords"] = first["pixel_coords"]

            try:
                step_info = step_generator.generate(
                    query=query,
                    device_info=device_info,
                    spatial_info=spatial_context,
                    manual_context=manual_context,
                    query_info=query_info,
                    answer_type=answer_type,
                )
            except Exception as e:
                logger.error(f"Step generation failed: {e}")
                step_info = {
                    "issue_diagnosis": "An error occurred during analysis.",
                    "troubleshooting_steps": [],
                    "audio_instructions": "I encountered an error generating the response. Please try again.",
                }

            if step_info and step_info.get("skipped"):
                step_info = None
        else:
            logger.info(f"GATE 6 SKIPPED: Not needed for {answer_type}")

        # ===========================================
        # GATE 7: Response Assembly
        # ===========================================
        logger.info("GATE 7: Building response...")

        final_response = build_enhanced_response(
            answer_type=answer_type,
            device_info=device_info,
            query_info=query_info,
            validation_info=validation_info,
            safety_info=safety_info if safety_detected else None,
            localization_results=localization_results if localization_results else None,
            step_info=step_info,
            image_dims=(image_width, image_height),
            grounding_info=grounding_info,
        )

        # Generate audio script if not already present
        if not final_response.get("audio_instructions"):
            final_response["audio_instructions"] = generate_audio_script(final_response)
        elif len(final_response["audio_instructions"]) < 10:
            # Replace very short/empty audio
            final_response["audio_instructions"] = generate_audio_script(final_response)

        # Schema validation
        final_response = validate_response(final_response)

        logger.info(f"Completed in {time.time() - start_time:.2f}s ({answer_type})")
        return final_response

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        # Return a structured error instead of raising 500
        error_response = {
            "answer_type": "troubleshoot_steps",
            "status": ResponseStatus.ERROR,
            "needs_clarification": False,
            "cannot_comply_reason": None,
            "message": f"An error occurred: {str(e)}",
            "device_info": {
                "device_category": "unknown",
                "device_type": "Unknown",
                "brand": "unknown",
                "model": "not visible",
                "brand_model_guidance": None,
                "confidence": 0.0,
                "components": [],
            },
            "localization_results": None,
            "explanation": None,
            "diagnosis": None,
            "troubleshooting_steps": None,
            "clarifying_questions": None,
            "visualizations": [],
            "audio_instructions": "I encountered an error during analysis. Please try again.",
            "web_grounding_used": False,
            "grounding_sources": None,
            "issue_diagnosis": f"Error: {str(e)}",
            "device_identified": "Unknown",
            "device_confidence": 0.0,
            "confidence_level": "low",
            "section_title": "Error",
        }
        return error_response


def _should_trigger_web_grounding(
    answer_type: str,
    device_info: dict,
    manual_context: list,
    query: str,
) -> bool:
    """
    Determine if Gemini's native Google Search grounding should be triggered.

    This uses Gemini's built-in google_search tool which performs real web searches
    and returns grounding_metadata with source URIs and cited text segments.

    Trigger when:
    1. Any troubleshoot/explain/diagnose query (primary knowledge source)
    2. Brand/model is identified (model-specific guidance is most valuable)
    3. User explicitly asks for official/latest/manufacturer info
    4. Query mentions firmware, driver, update, specs, compatibility

    Do NOT trigger when:
    - answer_type is locate_only, identify_only, or non-content types
    - Device is generic hobby board (Arduino, breadboard - community docs are better)
    - Safety situation (use conservative general guidance, don't search)
    
    Note: manual_context is always empty now (RAG removed), relying fully on web grounding.
    """
    # Never ground for these types
    if answer_type in (
        "locate_only", "identify_only", "ask_clarifying_questions",
        "reject_invalid_image", "ask_for_better_input", "safety_warning_only",
    ):
        return False

    # Skip for generic hobby/dev boards
    device_type = (device_info.get("device_type", "") or "").lower()
    generic_devices = ["arduino", "breadboard", "generic", "usb cable", "prototype board"]
    if any(g in device_type for g in generic_devices):
        return False

    query_lower = query.lower()

    # Always ground for explicit web-info requests
    explicit_triggers = [
        "latest", "official", "manufacturer", "firmware", "driver",
        "update", "specs", "specification", "compatibility", "recall",
        "warranty", "manual", "documentation", "download", "support page",
        "error code", "model number", "part number",
    ]
    if any(phrase in query_lower for phrase in explicit_triggers):
        return True

    # Ground when brand/model is known (model-specific results are high value)
    brand = (device_info.get("brand", "") or "").lower()
    model = (device_info.get("model", "") or "").lower()
    has_brand = brand and brand not in ("unknown", "generic", "")
    has_model = model and model not in ("not visible", "")

    if has_brand and has_model:
        # Known brand + model = always worth grounding for troubleshoot/explain
        return True

    if has_brand and answer_type in ("troubleshoot_steps", "diagnose_only"):
        # Known brand + troubleshoot intent = ground for brand-specific guidance
        return True

    # For any content-generation mode without specific brand info, use grounding as primary knowledge source
    if answer_type in ("troubleshoot_steps", "explain_only", "mixed", "diagnose_only"):
        return True

    return False


def _build_error_response(combined_result: dict) -> dict:
    """Build a structured error response."""
    return {
        "answer_type": "troubleshoot_steps",
        "status": ResponseStatus.ERROR,
        "needs_clarification": False,
        "cannot_comply_reason": None,
        "message": combined_result.get("error", "An error occurred"),
        "retry_after": combined_result.get("retry_after", ""),
        "device_info": {
            "device_category": "unknown",
            "device_type": "Unknown",
            "brand": "unknown",
            "model": "not visible",
            "brand_model_guidance": None,
            "confidence": 0.0,
            "components": [],
        },
        "localization_results": None,
        "explanation": None,
        "diagnosis": None,
        "troubleshooting_steps": None,
        "clarifying_questions": None,
        "visualizations": [],
        "audio_instructions": "I'm temporarily unable to process your request. Please try again later.",
        "web_grounding_used": False,
        "grounding_sources": None,
        "issue_diagnosis": combined_result.get("error", ""),
        "device_identified": "Unknown",
        "device_confidence": 0.0,
        "confidence_level": "low",
        "section_title": "Error",
    }


# --- Additional Endpoints ---

@app.post("/api/validate-image")
async def validate_image_endpoint(
    image_base64: str = Form(...),
):
    """Standalone image validation endpoint."""
    try:
        image = process_image_for_gemini(image_base64)
        validation_info = image_validator.validate_image(image)
        return validation_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/identify-device")
async def identify_device_endpoint(
    image_base64: str = Form(...),
    query: Optional[str] = Form(""),
):
    """Standalone device identification endpoint."""
    try:
        image = process_image_for_gemini(image_base64)
        validation_info = image_validator.validate_image(image, query)
        if not validation_info.get("is_valid", False):
            return {
                "success": False,
                "reason": validation_info.get("rejection_reason"),
                "suggestion": validation_info.get("suggestion"),
            }
        device_info = device_detector.detect_device(image, query)
        device_info["success"] = True
        return device_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/quota-status")
async def quota_status_endpoint():
    """Check Gemini API quota status."""
    return get_quota_status()


@app.post("/api/reset-quota")
async def reset_quota_endpoint(admin_key: str = Form(...)):
    """Reset circuit breaker (admin only)."""
    expected_key = os.getenv("ADMIN_KEY", "fixit-admin-2026")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    reset_circuit_breaker()
    return {"message": "Circuit breaker reset", "status": get_quota_status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
