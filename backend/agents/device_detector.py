"""
Device Detector Agent
Identifies electronic devices with honest uncertainty reporting.
Acts as GATE 2 in the pipeline.
"""

from typing import Dict, Any, Optional
from PIL import Image
import json
import logging
from backend.utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

# Response schema for structured output
DEVICE_DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "device_type": {"type": "string"},
        "brand": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "components": {"type": "array", "items": {"type": "string"}},
        "device_confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "is_identifiable": {"type": "boolean"},
        "what_i_see": {"type": "string"},
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "clarifying_questions": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["device_type", "device_confidence", "reasoning", "is_identifiable", "what_i_see", "components"]
}


class DeviceDetector:
    """
    Identifies electronic devices in images with honest confidence reporting.
    Key principle: Be honest about uncertainty rather than guessing.
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.6   # Proceed with full pipeline
    MEDIUM_CONFIDENCE_THRESHOLD = 0.3  # Limited help with caveats
    # Below 0.3 = Early exit, ask for clarification
    
    # Device categories we can help with
    KNOWN_DEVICE_CATEGORIES = [
        "WiFi Router", "Modem", "Network Switch",
        "Printer", "Scanner", "Multifunction Printer",
        "Laptop", "Desktop Computer", "Monitor",
        "TV", "Smart TV", "Streaming Device",
        "Smartphone", "Tablet",
        "Arduino", "Raspberry Pi", "Circuit Board", "Microcontroller",
        "Gaming Console", "Gaming PC",
        "Washing Machine", "Dryer", "Dishwasher",
        "Microwave", "Oven", "Refrigerator",
        "Air Conditioner", "Heater", "Fan",
        "Speaker", "Headphones", "Audio Receiver",
        "Camera", "Webcam", "Security Camera",
        "Smart Home Hub", "Thermostat", "Smart Light"
    ]

    def __init__(self):
        pass

    def detect_device(self, image: Image.Image, query: str = "") -> Dict[str, Any]:
        """
        Analyzes the image to identify the device, brand, model, and visible components.
        
        Key behaviors:
        - Returns honest confidence scores
        - Sets device_type to "not_a_device" if clearly not a device
        - Sets device_type to "Unknown" with low confidence if unsure
        - Provides clear reasoning for identification
        
        Returns:
            Dict with:
            - device_type: str - Device category or "Unknown" or "not_a_device"
            - brand: str or None
            - model: str or None
            - components: list - Visible components
            - device_confidence: float - 0.0 to 1.0
            - reasoning: str - Explanation of identification
            - is_identifiable: bool - Whether we could identify it
            - suggestions: list - Suggestions if identification failed
        """
        
        prompt = [
            """You are an expert electronic device identifier for FixIt AI.

IMPORTANT: Be COMPLETELY HONEST about uncertainty. 
- If you cannot identify the device, say so with LOW confidence
- If this is NOT a device at all, say "not_a_device" 
- Do NOT guess or make up device types
- Do NOT force identification when you're unsure

Analyze this image and identify the electronic device shown.
""",
            f"User's context/question: {query}" if query else "",
            """
Known device categories you can identify:
- Networking: WiFi Router, Modem, Network Switch
- Computing: Laptop, Desktop, Monitor, Tablet, Smartphone
- Printing: Printer, Scanner, Multifunction Printer
- Entertainment: TV, Gaming Console, Streaming Device
- Audio: Speaker, Headphones, Audio Receiver
- Electronics: Arduino, Raspberry Pi, Circuit Board
- Appliances: Washing Machine, Microwave, Refrigerator, AC
- Smart Home: Smart Hub, Thermostat, Smart Light, Camera

Return a JSON object with HONEST assessments:
{
    "device_type": "specific device type OR 'Unknown' OR 'not_a_device'",
    "brand": "brand name if visible, else null",
    "model": "model number if visible, else null",
    "components": ["list", "of", "visible", "components"],
    "device_confidence": 0.0 to 1.0,
    "reasoning": "explain HOW you identified this OR WHY you couldn't",
    "is_identifiable": true/false,
    "what_i_see": "describe what you actually see in the image",
    "suggestions": ["if identification failed, suggest what might help"] 
}

CONFIDENCE GUIDELINES:
- 0.8-1.0: Clear view, recognizable brand/model, certain identification
- 0.6-0.8: Good view, confident in device type but unsure of brand/model
- 0.3-0.6: Partial view or unclear, making educated guess
- 0.1-0.3: Very unsure, might be wrong
- 0.0-0.1: Cannot identify at all or not a device

If confidence < 0.3, ALSO include:
- "clarifying_questions": ["questions to ask user for better identification"]

Be honest! Low confidence is better than wrong identification.
""",
            image
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=DEVICE_DETECTION_SCHEMA,
                temperature=0.2
            )
            
            if isinstance(response, dict):
                return self._process_detection_response(response)
            
            # If response parsing failed, return unknown
            return self._create_unknown_response("Response parsing failed")

        except Exception as e:
            logger.error(f"Device detection failed: {e}")
            return self._create_error_response(str(e))

    def _process_detection_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize the detection response."""
        
        device_type = response.get("device_type", "Unknown")
        confidence = float(response.get("device_confidence", 0.0))
        is_identifiable = response.get("is_identifiable", confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD)
        
        # Ensure components is always a list
        components = response.get("components", [])
        if not isinstance(components, list):
            components = []
        
        # Build the result
        result = {
            "device_type": device_type,
            "brand": response.get("brand"),
            "model": response.get("model"),
            "components": components,
            "device_confidence": confidence,
            "reasoning": response.get("reasoning", ""),
            "is_identifiable": is_identifiable,
            "what_i_see": response.get("what_i_see", ""),
            "suggestions": response.get("suggestions", [])
        }
        
        # Add clarifying questions for low confidence
        if confidence < self.MEDIUM_CONFIDENCE_THRESHOLD:
            result["clarifying_questions"] = response.get("clarifying_questions", [
                "What type of device is this? (router, printer, laptop, etc.)",
                "Can you take a photo from a different angle?",
                "Are there any visible brand names or labels?"
            ])
            result["needs_clarification"] = True
        else:
            result["needs_clarification"] = False
        
        # Determine confidence level for routing
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            result["confidence_level"] = "high"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            result["confidence_level"] = "medium"
        else:
            result["confidence_level"] = "low"
        
        return result

    def _create_unknown_response(self, reason: str) -> Dict[str, Any]:
        """Create a response for unknown/unidentifiable devices."""
        return {
            "device_type": "Unknown",
            "brand": None,
            "model": None,
            "components": [],
            "device_confidence": 0.0,
            "reasoning": reason,
            "is_identifiable": False,
            "what_i_see": "Could not analyze the image",
            "suggestions": [
                "Please ensure the device is clearly visible",
                "Try taking a photo from a different angle",
                "Include any visible brand names or labels"
            ],
            "clarifying_questions": [
                "What type of device is this?",
                "What brand is it?"
            ],
            "needs_clarification": True,
            "confidence_level": "low"
        }

    def _create_error_response(self, error: str) -> Dict[str, Any]:
        """Create a response when an error occurs."""
        return {
            "device_type": "Unknown",
            "brand": None,
            "model": None,
            "components": [],
            "device_confidence": 0.0,
            "reasoning": f"Error during detection: {error}",
            "is_identifiable": False,
            "what_i_see": "Error analyzing image",
            "suggestions": ["Please try again with a different image"],
            "error": error,
            "needs_clarification": True,
            "confidence_level": "low"
        }

    def get_confidence_explanation(self, device_info: Dict[str, Any]) -> str:
        """
        Generate a user-friendly explanation of the confidence level.
        """
        confidence = device_info.get("device_confidence", 0.0)
        device_type = device_info.get("device_type", "Unknown")
        
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return f"I'm confident this is a {device_type}."
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return f"I think this might be a {device_type}, but I'm not entirely certain."
        else:
            return "I'm having trouble identifying this device clearly."


# Singleton instance
device_detector = DeviceDetector()
