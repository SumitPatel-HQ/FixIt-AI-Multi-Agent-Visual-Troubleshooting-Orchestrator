import os
import google.genai as genai
from dotenv import load_dotenv
import time
import json
import logging
from fastapi import HTTPException
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("Warning: GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=api_key)

# Default model (Updated for "Gemini 3" context - likely 1.5 Pro or 2.0 Flash)
DEFAULT_MODEL = os.getenv("GEMINI_MODEL_NAME")

# Task 2: Global quota circuit breaker
GEMINI_DISABLED = False

# Task 3: In-memory rate limiter (sliding window)
rate_limit_calls = []  # List of timestamps
MAX_CALLS_PER_MINUTE = 5

# Task 4: In-memory prompt cache
prompt_cache: Dict[str, Dict[str, Any]] = {}  # {hash: {response, timestamp}}
CACHE_TTL_SECONDS = 300  # 5 minutes

# API call tracking
api_call_count = 0

# RPD tracking (Gemini 3 Flash: ~5 RPD per call)
RPD_PER_CALL = 5
rpd_consumed_today = 0
MAX_RPD_DAILY = 20  # Free tier limit 

class GeminiClient:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        logger.info(f"Initialized GeminiClient with model: {model_name}")

    def _get_prompt_hash(self, prompt: list, response_schema: Any, temperature: float, max_output_tokens: int) -> str:
        """Generate hash for prompt deduplication."""
        # Handle prompts with images - convert non-serializable parts to placeholders
        hashable_prompt = []
        for item in prompt:
            if hasattr(item, 'size'):  # PIL Image object
                # Use image dimensions as proxy for cache key
                hashable_prompt.append(f"<IMAGE:{item.size}>")
            else:
                hashable_prompt.append(item)
        
        prompt_str = json.dumps(hashable_prompt, sort_keys=True)
        schema_str = json.dumps(response_schema, sort_keys=True) if response_schema else ""
        key = f"{prompt_str}|{schema_str}|{temperature}|{max_output_tokens}"
        return hashlib.sha256(key.encode()).hexdigest()

    def _check_cache(self, prompt_hash: str) -> Optional[dict]:
        """Check if response is cached and not expired."""
        if prompt_hash in prompt_cache:
            cached = prompt_cache[prompt_hash]
            age = (datetime.now() - cached["timestamp"]).total_seconds()
            if age < CACHE_TTL_SECONDS:
                logger.info("Cache hit - returning cached response")
                return cached["response"]
            else:
                # Expired - remove from cache
                del prompt_cache[prompt_hash]
        return None

    def _store_cache(self, prompt_hash: str, response: dict):
        """Store response in cache."""
        prompt_cache[prompt_hash] = {
            "response": response,
            "timestamp": datetime.now()
        }
        logger.info("Response cached")

    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded. Returns True if OK, False if exceeded."""
        global rate_limit_calls
        now = datetime.now()
        
        # Remove timestamps older than 60 seconds
        rate_limit_calls = [ts for ts in rate_limit_calls if (now - ts).total_seconds() < 60]
        
        if len(rate_limit_calls) >= MAX_CALLS_PER_MINUTE:
            logger.warning(f"Local rate limit exceeded: {len(rate_limit_calls)}/{MAX_CALLS_PER_MINUTE} calls in last minute")
            return False
        
        return True

    def _record_api_call(self):
        """Record a new API call timestamp."""
        global rate_limit_calls, api_call_count, rpd_consumed_today
        rate_limit_calls.append(datetime.now())
        api_call_count += 1
        rpd_consumed_today += RPD_PER_CALL
        rpd_remaining = MAX_RPD_DAILY - rpd_consumed_today
        logger.info(f"📊 API Call #{api_call_count} | Rate: {len(rate_limit_calls)}/5 per min | RPD: {rpd_consumed_today}/{MAX_RPD_DAILY} ({rpd_remaining} remaining)")
        
        if rpd_remaining <= 5:
            logger.warning(f"⚠️ Low RPD budget! Only {rpd_remaining} RPD remaining today")

    def _is_quota_error(self, error: Exception) -> bool:
        """Check if error is a quota/auth error that should not be retried."""
        error_str = str(error).lower()
        quota_indicators = ["429", "resource_exhausted", "quota"]
        return any(indicator in error_str for indicator in quota_indicators)

    def _is_transient_error(self, error: Exception) -> bool:
        """Check if error is transient and can be retried."""
        error_str = str(error).lower()
        transient_indicators = ["timeout", "500", "502", "503", "504"]
        return any(indicator in error_str for indicator in transient_indicators)

    def _quota_exhausted_response(self) -> dict:
        """Return structured quota exhausted response."""
        return {
            "error": "AI temporarily unavailable (free tier quota reached)",
            "retry_after": "tomorrow"
        }

    def generate_combined_analysis(
        self,
        image,
        query: str,
        device_hint: Optional[str] = None,
        temperature: float = 0.2
    ) -> dict:
        """
        Single-call combined analysis: validation + detection + query parsing.
        Reduces 3 Gemini calls into 1.
        """
        device_hint_text = f"\nDevice hint from user: {device_hint}" if device_hint else ""

        prompt_text = f"""You are FixIt AI's multi-stage analysis system.

User Query: "{query}"{device_hint_text}

Perform THREE analyses in one response:

1. IMAGE VALIDATION
   - Is this a physical electronic device? (yes or no)
   - What do you see in the image?
   - If not a valid device, provide rejection reason and suggestion

2. DEVICE DETECTION (if valid device)
   - Identify the exact device type (be specific - Router, Laser Printer, Gaming Laptop, Microwave, etc.)
   - Brand and model if visible
   - Your confidence level (0.0 to 1.0)
   - Classify confidence as: "high" (0.6+), "medium" (0.3-0.6), or "low" (<0.3)
   - List ALL visible components you can identify
   - Brief reasoning for your identification

3. QUERY UNDERSTANDING
   - What is the user trying to do? (identify/locate/troubleshoot/procedure/general_info/unclear)
   - Which specific component are they asking about? (null if none)
   - What action do they want to take?
   - Do they need you to find the exact location of something in the image?
   - Do they need step-by-step instructions?
   - Is the query unclear and needs clarification?

IMPORTANT QUERY CLASSIFICATION:
- If user wants to REMOVE, REPLACE, INSTALL, REPAIR, or FIX something → they NEED steps (needs_steps: true)
- If user asks "where is X" without wanting to do anything → they may not need steps (needs_steps: false)
- If user reports a PROBLEM or asks HOW TO do something → they NEED steps (needs_steps: true)
- Default to needs_steps: true unless you're confident they only want location information

Return ONLY valid JSON with this structure:
{{
  "validation": {{
    "is_valid": true,
    "image_category": "the device category you identified",
    "what_i_see": "what you actually see in this image",
    "rejection_reason": null,
    "suggestion": null
  }},
  "device": {{
    "device_type": "the specific device type",
    "brand": "brand name if visible",
    "model": "model if visible",
    "device_confidence": 0.85,
    "confidence_level": "high",
    "components": ["component1", "component2", "component3"],
    "reasoning": "why you identified it this way"
  }},
  "query": {{
    "query_type": "locate",
    "target_component": "the component they're asking about",
    "action_requested": "what they want to do",
    "needs_localization": true,
    "needs_steps": false,
    "clarification_needed": false,
    "clarifying_questions": [],
    "confidence": 0.9
  }}
}}

IMPORTANT: Identify the ACTUAL device type you see, not from a predefined list. Be specific and accurate."""

        prompt = [prompt_text, image]

        return self.generate_response(
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=2500
        )

    def generate_response(
        self, 
        prompt: list, 
        response_schema: any = None,
        temperature: float = 0.2, 
        max_output_tokens: int = 2000
    ) -> dict:
        """
        Sends a prompt to Gemini and parses the JSON response.
        Implements quota protection, rate limiting, and caching.
        """
        global GEMINI_DISABLED
        
        # Task 2: Circuit breaker check
        if GEMINI_DISABLED:
            logger.error("🚫 CIRCUIT BREAKER ACTIVE - Gemini disabled due to quota exhaustion")
            return self._quota_exhausted_response()

        # Task 4: Check cache first
        prompt_hash = self._get_prompt_hash(prompt, response_schema, temperature, max_output_tokens)
        cached_response = self._check_cache(prompt_hash)
        if cached_response is not None:
            return cached_response

        # Task 3: Rate limiter check
        if not self._check_rate_limit():
            raise HTTPException(
                status_code=429, 
                detail="Local rate limit exceeded (max 5 requests per minute)"
            )

        # Record this API call
        self._record_api_call()

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        if response_schema:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = response_schema

        # Task 1 & 6: Single call with smart retry
        max_retries = 1  # Only 1 retry for transient errors
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sending request to Gemini (Attempt {attempt+1}/{max_retries+1})...")
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=generation_config
                )
                
                # Parse JSON if schema provided or expected
                if response_schema or (isinstance(prompt, list) and "JSON" in str(prompt)):
                    try:
                        result = json.loads(response.text)
                    except json.JSONDecodeError:
                        # Fallback simple cleaning if response isn't perfect JSON
                        logger.warning("JSON Decode Failed, attempting to clean response text.")
                        text = response.text.replace("```json", "").replace("```", "").strip()
                        result = json.loads(text)
                else:
                    result = {"text": response.text}

                # Cache successful response
                self._store_cache(prompt_hash, result)
                return result

            except Exception as e:
                logger.error(f"Gemini API error (attempt {attempt+1}/{max_retries+1}): {e}")
                
                # Task 1: Check for quota errors - never retry
                if self._is_quota_error(e):
                    logger.critical("❌ QUOTA EXHAUSTED - Activating circuit breaker. Gemini disabled globally.")
                    logger.critical(f"Total API calls made this session: {api_call_count}")
                    GEMINI_DISABLED = True
                    return self._quota_exhausted_response()
                
                # Task 1: Only retry transient errors
                if attempt < max_retries and self._is_transient_error(e):
                    logger.info("Transient error detected - will retry once")
                    time.sleep(2)  # Simple backoff
                    continue
                
                # Non-transient error or max retries reached
                logger.error("Non-retryable error or max retries reached")
                raise HTTPException(
                    status_code=503, 
                    detail=f"Gemini API unavailable: {str(e)}"
                )
        
        return {}

def get_quota_status() -> dict:
    """Get current quota protection status."""
    global GEMINI_DISABLED, api_call_count, rate_limit_calls, rpd_consumed_today
    
    # Clean old rate limit timestamps
    now = datetime.now()
    active_calls = [ts for ts in rate_limit_calls if (now - ts).total_seconds() < 60]
    
    return {
        "circuit_breaker_active": GEMINI_DISABLED,
        "total_calls_this_session": api_call_count,
        "calls_in_last_minute": len(active_calls),
        "rate_limit_remaining": max(0, MAX_CALLS_PER_MINUTE - len(active_calls)),
        "rpd_consumed": rpd_consumed_today,
        "rpd_remaining": max(0, MAX_RPD_DAILY - rpd_consumed_today),
        "rpd_budget_percent": int((rpd_consumed_today / MAX_RPD_DAILY) * 100) if MAX_RPD_DAILY > 0 else 0,
        "cache_size": len(prompt_cache),
        "status": "disabled" if GEMINI_DISABLED else "active"
    }

def reset_circuit_breaker():
    """Reset the circuit breaker (admin/debug only)."""
    global GEMINI_DISABLED
    GEMINI_DISABLED = False
    logger.warning("\u26a0\ufe0f Circuit breaker manually reset - Gemini re-enabled")

# Singleton instance
gemini_client = GeminiClient()
