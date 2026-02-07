"""
Image Validator Agent
Pre-validates images before proceeding with device troubleshooting.
Acts as GATE 1 in the pipeline.
"""

from typing import Dict, Any
from PIL import Image
import logging
from backend.utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

# Response schema for structured output
IMAGE_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "image_category": {"type": "string"},
        "is_physical_device": {"type": "boolean"},
        "confidence": {"type": "number"},
        "what_i_see": {"type": "string"},
        "rejection_reason": {"type": ["string", "null"]}
    },
    "required": ["image_category", "is_physical_device", "confidence", "what_i_see"]
}


class ImageValidator:
    """
    Validates whether an uploaded image is appropriate for device troubleshooting.
    Rejects software screenshots, people, documents, artwork, etc.
    """
    
    # Confidence threshold for accepting the image classification
    CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.6
    
    # Valid categories that can proceed to troubleshooting
    VALID_CATEGORIES = ["device", "electronic_component", "circuit_board", "appliance"]
    
    # Categories that should be rejected with specific messages
    REJECTION_MESSAGES = {
        "software_screenshot": "This appears to be a software screenshot or game screen, not a physical device. FixIt AI helps troubleshoot electronic devices like routers, printers, and appliances.",
        "person": "This image appears to show a person. FixIt AI is designed to help with electronic device troubleshooting only.",
        "document": "This appears to be a document or text. FixIt AI needs a photo of the actual device you need help with.",
        "artwork": "This appears to be artwork or an illustration. Please upload a photo of a real electronic device.",
        "nature": "This appears to be a nature or landscape image. FixIt AI helps troubleshoot electronic devices.",
        "food": "This appears to be a food image. FixIt AI is designed for electronic device troubleshooting.",
        "unclear": "The image is too blurry or unclear to identify. Please take a clearer photo of the device.",
        "other": "This doesn't appear to be an electronic device. FixIt AI helps troubleshoot devices like routers, printers, laptops, and appliances."
    }
    
    # Devices we can help with
    SUPPORTED_DEVICES = [
        "WiFi Routers & Modems",
        "Printers & Scanners", 
        "Laptops & Computers",
        "Smart Home Devices",
        "Kitchen Appliances",
        "Washing Machines & Dryers",
        "TVs & Monitors",
        "Audio Equipment",
        "Arduino & Circuit Boards",
        "Gaming Consoles",
        "Smartphones & Tablets"
    ]

    def __init__(self):
        pass

    def validate_image(self, image: Image.Image, user_query: str = "") -> Dict[str, Any]:
        """
        Validates if the image is suitable for device troubleshooting.
        
        Returns:
            Dict with:
            - is_valid: bool - Whether to proceed with troubleshooting
            - image_category: str - What type of image this is
            - rejection_reason: str - Why it was rejected (if applicable)
            - confidence: float - How confident we are in the classification
            - suggestion: str - What the user should do next
            - supported_devices: list - List of device types we support
        """
        
        prompt = [
            """You are a STRICT image classifier for a device troubleshooting system called FixIt AI.

Your job is to determine if an image shows a PHYSICAL ELECTRONIC DEVICE that can be troubleshot.

ANALYZE this image and classify it into ONE of these categories:

VALID for troubleshooting:
- "device" → Physical electronic device (router, printer, laptop, TV, appliance)
- "electronic_component" → Circuit board, Arduino, Raspberry Pi, electronic parts
- "circuit_board" → PCB, motherboard, visible electronics
- "appliance" → Home appliance (washing machine, microwave, refrigerator)

INVALID for troubleshooting:
- "software_screenshot" → Any screen capture, game screenshot, UI, desktop screenshot
- "person" → Photo of a person or living being
- "document" → Document, text, book, paper
- "artwork" → Drawing, painting, 3D render, illustration, meme
- "nature" → Landscape, plants, animals, outdoor scene
- "food" → Food items or beverages
- "unclear" → Too blurry, too dark, cannot determine content
- "other" → Anything else that doesn't fit above categories

BE VERY STRICT:
- Game screenshots are NOT devices (even if showing virtual objects)
- Software UIs are NOT devices
- Photos OF screens are different from screenshots - a photo of a laptop showing a game IS valid
- Stock photos or renders of devices should be marked as "artwork"

""",
            f"User's question about this image: {user_query}" if user_query else "",
            """
Return a JSON object with exactly these fields:
{
    "image_category": "one of the categories above",
    "is_physical_device": true/false,
    "confidence": 0.0 to 1.0,
    "what_i_see": "brief description of what you see in the image",
    "rejection_reason": "if not a valid device, explain why, else null"
}

Be HONEST about what you see. If it's clearly not a device, say so.
""",
            image
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=IMAGE_VALIDATION_SCHEMA,
                temperature=0.1  # Low temperature for more consistent classification
            )
            
            if isinstance(response, dict):
                return self._process_validation_response(response)
            
            # Fallback if parsing failed
            logger.warning("Image validation returned unexpected format")
            return self._create_unclear_response()

        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            # On error, allow the image to proceed but flag uncertainty
            return {
                "is_valid": True,  # Don't block on errors
                "image_category": "unknown",
                "confidence": 0.0,
                "rejection_reason": None,
                "suggestion": "Image validation encountered an error. Proceeding with caution.",
                "supported_devices": self.SUPPORTED_DEVICES,
                "error": str(e)
            }

    def _process_validation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize the validation response."""
        
        category = response.get("image_category", "other").lower().replace(" ", "_")
        is_physical = response.get("is_physical_device", False)
        confidence = float(response.get("confidence", 0.0))
        what_i_see = response.get("what_i_see", "")
        rejection_reason = response.get("rejection_reason")
        
        # Determine if valid based on category and physical device flag
        is_valid = (
            category in self.VALID_CATEGORIES or 
            (is_physical and confidence >= self.CLASSIFICATION_CONFIDENCE_THRESHOLD)
        )
        
        # Build response
        result = {
            "is_valid": is_valid,
            "image_category": category,
            "confidence": confidence,
            "what_i_see": what_i_see,
            "supported_devices": self.SUPPORTED_DEVICES
        }
        
        if is_valid:
            result["rejection_reason"] = None
            result["suggestion"] = None
        else:
            # Get specific rejection message for this category
            result["rejection_reason"] = self.REJECTION_MESSAGES.get(
                category, 
                rejection_reason or self.REJECTION_MESSAGES["other"]
            )
            result["suggestion"] = self._get_suggestion_for_category(category)
        
        return result
    
    def _get_suggestion_for_category(self, category: str) -> str:
        """Get a helpful suggestion based on the rejected category."""
        
        suggestions = {
            "software_screenshot": "Please take a photo of the physical device (not the screen contents) that you need help with.",
            "person": "Please upload a photo of the electronic device you need assistance with.",
            "document": "Please take a photo of the actual device you want to troubleshoot.",
            "artwork": "Please upload a real photograph of your device, not an illustration or render.",
            "nature": "FixIt AI troubleshoots electronic devices. Please upload a device photo.",
            "food": "Please upload a photo of an electronic device you need help with.",
            "unclear": "Please take a clearer, well-lit photo of the device from a good angle.",
            "other": "Upload a clear photo of your electronic device (router, printer, laptop, appliance, etc.)"
        }
        
        return suggestions.get(category, suggestions["other"])
    
    def _create_unclear_response(self) -> Dict[str, Any]:
        """Create a response for unclear/unparseable situations."""
        return {
            "is_valid": False,
            "image_category": "unclear",
            "confidence": 0.0,
            "rejection_reason": self.REJECTION_MESSAGES["unclear"],
            "suggestion": "Please upload a clearer photo of the device you need help with.",
            "supported_devices": self.SUPPORTED_DEVICES,
            "what_i_see": "Could not clearly identify the image contents"
        }


# Singleton instance
image_validator = ImageValidator()
