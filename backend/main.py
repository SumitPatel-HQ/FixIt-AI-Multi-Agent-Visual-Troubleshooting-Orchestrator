"""
FixIt AI Backend - Main API
Implements gate-based routing for robust device troubleshooting.

Pipeline:
GATE 1: Image Type Validation
GATE 2: Device Detection (with confidence routing)
GATE 3: Query Understanding
GATE 4: Component Localization (conditional)
GATE 5: Response Generation (confidence-matched)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any, Union
import logging
import time
import os

# Utilities
from backend.utils.image_processor import process_image_for_gemini
from backend.utils.gemini_client import gemini_client, get_quota_status, reset_circuit_breaker
from backend.utils.response_builder import (
    build_troubleshoot_response, 
    build_rejection_response,
    build_low_confidence_response,
    build_component_not_found_response,
    ResponseStatus
)

# Agents
from backend.agents.image_validator import image_validator
from backend.agents.device_detector import device_detector
from backend.agents.query_parser import query_parser
from backend.agents.spatial_mapper import spatial_mapper
from backend.agents.rag_engine import rag_engine
from backend.agents.step_generator import step_generator

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FixIt AI Backend",
    description="AI-powered device troubleshooting with visual understanding",
    version="0.2.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Response Models ---

class BoundingBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int

class TroubleshootingStep(BaseModel):
    step_number: int
    instruction: str
    visual_cue: Optional[str] = None
    estimated_time: Optional[str] = None
    safety_note: Optional[str] = None
    caveat: Optional[str] = None

class TroubleshootResponse(BaseModel):
    """Extended response model with status and scenario-specific fields."""
    status: str = "success"
    device_identified: Optional[str] = None
    device_confidence: float = 0.0
    confidence_level: Optional[str] = None
    component: Optional[str] = None
    spatial_description: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None
    issue_diagnosis: str
    troubleshooting_steps: List[TroubleshootingStep]
    audio_instructions: str
    
    # Scenario-specific fields
    message: Optional[str] = None
    clarifying_questions: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    supported_devices: Optional[List[str]] = None
    visible_alternatives: Optional[List[str]] = None
    typical_location: Optional[str] = None
    detected_components: Optional[List[str]] = None
    reasoning: Optional[str] = None
    warnings: Optional[List[str]] = None
    when_to_seek_help: Optional[str] = None
    general_safety_tip: Optional[str] = None
    what_i_see: Optional[str] = None

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.6
MEDIUM_CONFIDENCE_THRESHOLD = 0.3

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.2.0", "pipeline": "gate-based"}

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
    Implements gate-based routing for robust handling of all scenarios.
    
    Gates:
    1. Image Type Validation - Reject non-device images
    2. Device Detection - Confidence-based routing
    3. Query Understanding - Parse user intent
    4. Component Localization - Only when needed
    5. Response Generation - Match quality to confidence
    """
    start_time = time.time()
    logger.info(f"Received troubleshoot request: '{query}'")
    
    try:
        # ===========================================
        # STEP 0: Image Processing
        # ===========================================
        logger.info("Step 0: Processing Image...")
        try:
            image = process_image_for_gemini(image_base64)
            current_width, current_height = image.size
            if not image_width or not image_height:
                image_width, image_height = current_width, current_height
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

        # ===========================================
        # GATES 1-3: Combined Analysis (1 call)
        # ===========================================
        logger.info("GATES 1-3: Combined validation + detection + query parsing...")
        combined_result = gemini_client.generate_combined_analysis(
            image=image,
            query=query,
            device_hint=device_hint
        )

        if combined_result.get("error"):
            logger.error("Combined analysis failed (quota or provider error).")
            return {
                "status": ResponseStatus.ERROR,
                "message": combined_result.get("error"),
                "retry_after": combined_result.get("retry_after", "tomorrow")
            }

        validation_info = combined_result.get("validation", {})
        device_info = combined_result.get("device", {})
        query_info = combined_result.get("query", {})

        if not validation_info.get("is_valid", False):
            logger.info(f"GATE 1 REJECTED: {validation_info.get('image_category')} - {validation_info.get('rejection_reason')}")
            response = build_rejection_response(validation_info, query)
            logger.info(f"Request completed in {time.time() - start_time:.2f}s (rejected at Gate 1)")
            return response

        device_type = device_info.get("device_type", "Unknown")
        device_confidence = device_info.get("device_confidence", 0.0)
        confidence_level = device_info.get("confidence_level")
        if not confidence_level:
            if device_confidence >= HIGH_CONFIDENCE_THRESHOLD:
                confidence_level = "high"
            elif device_confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            device_info["confidence_level"] = confidence_level

        logger.info(f"Detected: {device_type} (Confidence: {device_confidence:.2f}, Level: {confidence_level})")

        if device_type == "not_a_device":
            logger.info("GATE 2 REJECTED: Not a device")
            response = build_rejection_response({
                "rejection_reason": device_info.get("reasoning", "This does not appear to be an electronic device."),
                "what_i_see": validation_info.get("what_i_see", ""),
                "suggestion": validation_info.get("suggestion", "Please upload a photo of an electronic device you need help with."),
                "image_category": "not_a_device"
            }, query)
            logger.info(f"Request completed in {time.time() - start_time:.2f}s (rejected at Gate 2)")
            return response

        if confidence_level == "low" or device_confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            logger.info("GATE 2 LOW CONFIDENCE: Generating clarification response")
            response = build_low_confidence_response(device_info, query)
            logger.info(f"Request completed in {time.time() - start_time:.2f}s (low confidence)")
            return response
        
        query_type = query_info.get("query_type", "unclear")
        target_component = query_info.get("target_component")
        needs_localization = query_info.get("needs_localization", False)
        needs_steps = query_info.get("needs_steps", True)
        
        logger.info(f"Query type: {query_type}, Target: {target_component}, Localization: {needs_localization}")
        
        # Handle unclear queries
        if query_type == "unclear" and query_info.get("clarification_needed"):
            logger.info("GATE 3: Query unclear, generating clarification response")
            clarification_response = query_parser.generate_clarifying_response(query_info, device_info)
            # Continue with limited pipeline but add clarifying questions to response later

        # ===========================================
        # Step 3.5: RAG Retrieval (if applicable)
        # ===========================================
        logger.info("Step 3.5: Retrieving Manual Context...")
        manual_context = []
        if device_type and device_type not in ["Unknown", "not_a_device"]:
            search_query = f"{device_type} {query}"
            manual_context = rag_engine.retrieve(search_query, device_filter=device_type)
            logger.info(f"Retrieved {len(manual_context)} manual chunks.")

        # ===========================================
        # GATE 4: Spatial Localization (Conditional)
        # ===========================================
        spatial_info = {"component_visible": False, "spatial_description": "Not applicable"}
        
        # Determine if we should attempt localization
        should_localize, reason = spatial_mapper.should_attempt_localization(device_info, query_info)
        
        if should_localize:
            logger.info(f"GATE 4: Attempting Spatial Localization...")
            
            # Determine what to locate
            target_for_spatial = target_component
            if not target_for_spatial:
                target_for_spatial = spatial_mapper.get_component_from_query(query, device_info.get("components", []))
            if not target_for_spatial:
                target_for_spatial = f"component relevant to: {query}"
            
            logger.info(f"Locating: '{target_for_spatial}'")
            spatial_info = spatial_mapper.locate_component(
                image, 
                target_for_spatial, 
                (image_width, image_height),
                device_context=device_info
            )
            
            # Check if component was found
            if not spatial_info.get("component_visible", False):
                logger.info(f"GATE 4: Component not visible - {spatial_info.get('visibility_reason', 'unknown')}")
                
                # For locate-type queries, return component not found response
                if query_type == "locate":
                    response = build_component_not_found_response(
                        device_info, 
                        spatial_info, 
                        target_for_spatial
                    )
                    logger.info(f"Request completed in {time.time() - start_time:.2f}s (component not found)")
                    return response
            else:
                logger.info(f"GATE 4 PASSED: Component located at {spatial_info.get('spatial_description', 'location found')}")
        else:
            logger.info(f"GATE 4 SKIPPED: {reason}")

        # ===========================================
        # GATE 5: Step Generation (conditional)
        # ===========================================
        logger.info("GATE 5: Generating Response...")
        
        # Build spatial context
        spatial_context = {
            "component": spatial_info.get("component_name", target_component) if spatial_info else None,
            "component_name": spatial_info.get("component_name", target_component) if spatial_info else None,
            "spatial_description": spatial_info.get("spatial_description") if spatial_info else None,
            "component_visible": spatial_info.get("component_visible", False) if spatial_info else False,
            "visible_alternatives": spatial_info.get("visible_alternatives", []) if spatial_info else [],
            "typical_location": spatial_info.get("typical_location", "") if spatial_info else ""
        }
        
        # Copy pixel_coords if available
        if spatial_info and spatial_info.get("pixel_coords"):
            spatial_context["pixel_coords"] = spatial_info["pixel_coords"]
        
        # Determine if we should skip step generation
        # Only skip when ALL conditions are met:
        # 1. Query type is "locate" (just finding location)
        # 2. AI determined steps are NOT needed (needs_steps=False)
        # 3. Action is NOT an action verb (remove, replace, etc.)
        should_skip_steps = (
            query_type == "locate" and 
            query_info.get("needs_steps", True) == False and
            query_info.get("action_requested", "").lower() not in ["remove", "replace", "install", "repair", "fix"]
        )
        
        if should_skip_steps:
            logger.info("GATE 5 SKIPPED: Steps not required for simple locate query")
            step_info = {
                "issue_diagnosis": "Location identified.",
                "troubleshooting_steps": [],
                "audio_instructions": ""
            }
        else:
            logger.info("GATE 5: Generating troubleshooting steps...")
            step_info = step_generator.generate_steps(
                query=query,
                device_info=device_info,
                spatial_info=spatial_context,
                manual_context=manual_context,
                query_info=query_info
            )

        # ===========================================
        # STEP 6: Response Building
        # ===========================================
        logger.info("Step 6: Building Final Response...")
        final_response = build_troubleshoot_response(
            device_info=device_info,
            spatial_info=spatial_context,
            step_info=step_info,
            image_dims=(image_width, image_height),
            validation_info=validation_info,
            query_info=query_info
        )
        
        logger.info(f"Request completed in {time.time() - start_time:.2f}s (success)")
        return final_response

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate-image")
async def validate_image_endpoint(
    image_base64: str = Form(...),
):
    """
    Standalone endpoint to validate if an image is suitable for troubleshooting.
    Useful for pre-validation before the full troubleshoot call.
    """
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
    """
    Standalone endpoint for device identification.
    Returns device info without full troubleshooting pipeline.
    """
    try:
        image = process_image_for_gemini(image_base64)
        
        # First validate
        validation_info = image_validator.validate_image(image, query)
        if not validation_info.get("is_valid", False):
            return {
                "success": False,
                "reason": validation_info.get("rejection_reason"),
                "suggestion": validation_info.get("suggestion")
            }
        
        # Then detect
        device_info = device_detector.detect_device(image, query)
        device_info["success"] = True
        return device_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/quota-status")
async def quota_status_endpoint():
    """
    Check current Gemini API quota status and circuit breaker state.
    """
    return get_quota_status()


@app.post("/api/reset-quota")
async def reset_quota_endpoint(admin_key: str = Form(...)):
    """
    Reset the circuit breaker (emergency admin endpoint).
    Requires admin key for safety.
    """
    # Simple admin key check (in production, use proper auth)
    expected_key = os.getenv("ADMIN_KEY", "fixit-admin-2026")
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    reset_circuit_breaker()
    return {"message": "Circuit breaker reset", "status": get_quota_status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
