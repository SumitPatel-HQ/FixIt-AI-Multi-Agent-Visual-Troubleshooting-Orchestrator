import base64
import io
from PIL import Image
import logging

# Configure Logging
logger = logging.getLogger(__name__)

def decode_image(base64_string: str) -> Image.Image:
    """Decodes a base64 string into a PIL Image."""
    try:
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        logger.error(f"Failed to decode image: {e}")
        raise ValueError("Invalid image data")

def validate_image(image: Image.Image, min_size: int = 50, max_size: int = 4096) -> bool:
    """Checks if image dimensions are within reasonable bounds."""
    width, height = image.size
    if width < min_size or height < min_size:
        return False
    # Max size check is soft, we will resize
    return True

def resize_image_if_needed(image: Image.Image, max_dimension: int = 1024) -> Image.Image:
    """Resizes image if it exceeds max dimension, maintaining aspect ratio."""
    width, height = image.size
    if width <= max_dimension and height <= max_dimension:
        return image
    
    if width > height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))
        
    logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def process_image_for_gemini(base64_string: str) -> Image.Image:
    """
    Full pipeline: decode -> validate -> resize -> return PIL Image
    """
    image = decode_image(base64_string)
    if not validate_image(image):
        raise ValueError("Image too small")
    
    image = resize_image_if_needed(image)
    return image
