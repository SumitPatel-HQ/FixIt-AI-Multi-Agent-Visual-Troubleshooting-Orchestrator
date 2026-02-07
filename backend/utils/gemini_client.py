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

# RPD tracking (Gemini 2.5 Flash: 1 request per call, 20 requests per day free tier)
RPD_PER_CALL = 1
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
            logger.warning(f"⚠️ Low RPD budget! Only {rpd_remaining} requests remaining today")

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
        Single-call combined analysis: validation + detection + query parsing + intent routing.
        Now includes answer_type classification, safety detection, image quality assessment,
        multi-target extraction, and smart brand/model recognition.
        """
        device_hint_text = f"\nDevice hint from user: {device_hint}" if device_hint else ""

        prompt_text = f"""You are FixIt AI's multi-stage analysis system.

User Query: "{query}"{device_hint_text}

Perform FIVE analyses in one response:

1. IMAGE VALIDATION & QUALITY
   - Is this a physical electronic device? (yes or no)
   - What do you see in the image?
   - Image quality assessment: is it blurry, too dark, or too far away?
   - Are there MULTIPLE devices visible? If so, list them.
   - If not a valid device (game screenshot, UI, person, food, artwork), provide rejection reason

2. DEVICE DETECTION (if valid device)
   - Identify the exact device type (be specific - Router, Laser Printer, Gaming Laptop, Microwave, etc.)
   - Brand and model ONLY IF clearly visible (logos, labels readable)
   - If brand/model NOT visible: set brand to "unknown", model to "not visible"
   - Add brand_model_guidance: instructions on where to find brand/model on this device type
   - Your confidence level (0.0 to 1.0)
   - Classify confidence as: "high" (0.6+), "medium" (0.3-0.6), or "low" (<0.3)
   - List ALL visible components you can identify
   - Brief reasoning for your identification

   BRAND/MODEL RULES:
   - For generic devices (Arduino, breadboard, generic cables): skip brand detection entirely, set brand to "generic"
   - For locate_only or identify_only intents: skip brand/model detection
   - NEVER guess brand from visual similarity - only report if text/logo is readable
   - If not visible: brand_model_guidance should say where to look (e.g., "Check label on back panel")

3. QUERY UNDERSTANDING & INTENT CLASSIFICATION
   Classify the user's PRIMARY intent:
   - "identify" → User wants to identify/name what something is
   - "locate" → User wants to find where something is physically
   - "explain" → User wants to understand how something works, architecture, function
   - "troubleshoot" → User wants to diagnose issues and get repair guidance
   - "compare" → User wants to compare options (future)
   - "unclear" → Cannot determine intent

   Determine the answer_type (controls what content to generate):
   - "locate_only" → Only show component location info
   - "identify_only" → Only show detected components list
   - "explain_only" → Only show how-it-works explanation
   - "troubleshoot_steps" → Show full repair workflow
   - "mixed" → ONLY when user explicitly uses "and" to ask 2+ clear questions
   - "ask_clarifying_questions" → Show only questions, no other content
   - "reject_invalid_image" → Image is not a device
   - "ask_for_better_input" → Image is too blurry/dark/unclear
   - "safety_warning_only" → Dangerous situation detected

4. SAFETY DETECTION
   Check for ANY safety-critical indicators:
   - In the QUERY: "burning", "smoke", "melting", "swelling battery", "electric shock", "exposed mains", "sparking", "fire", "disconnect power"
   - In the IMAGE: visible damage, melting, burn marks, swollen batteries, exposed wires
   - If ANY safety risk found: set safety_detected to true and override answer_type to "safety_warning_only"
   - safety_message should contain specific safety instructions

5. MULTI-TARGET EXTRACTION
   - Does the query mention MULTIPLE components? (look for "&", "and", commas between components)
   - Extract ALL target components as a list
   - Example: "locate SSD & cooling fan" → target_components: ["SSD", "cooling fan"]
   - Example: "where is the reset button" → target_components: ["reset button"]

CRITICAL RULES:
- If answer_type is "locate_only", do NOT suggest generating troubleshooting steps
- If answer_type is "explain_only", do NOT suggest generating repair steps
- If answer_type is "identify_only", do NOT suggest localization or steps
- "mixed" is ONLY allowed when user explicitly asks 2+ distinct questions using "and"
- If image quality is too poor (blurry/dark): override answer_type to "ask_for_better_input"
- If safety risk detected: override answer_type to "safety_warning_only"
- If multiple devices visible and query is ambiguous: set clarification_needed to true

QUERY CLASSIFICATION DETAILS:
- "what is this" / "what component" / "identify" → identify intent → identify_only
- "where is" / "locate" / "find" → locate intent → locate_only
- "how does it work" / "explain" / "architecture" → explain intent → explain_only
- "not working" / "fix" / "repair" / "replace" / "remove" / "install" → troubleshoot intent → troubleshoot_steps
- "how to" + action verb → troubleshoot intent → troubleshoot_steps
- Vague: "help with this" / "this thing" → unclear → ask_clarifying_questions
- "Don't give steps, just diagnose" → diagnose_only

Return ONLY valid JSON with this structure:
{{
  "validation": {{
    "is_valid": true,
    "image_category": "the device category you identified",
    "what_i_see": "what you actually see in this image",
    "image_quality": "good" | "blurry" | "dark" | "too_far" | "partial",
    "multiple_devices": false,
    "device_list": [],
    "rejection_reason": null,
    "suggestion": null
  }},
  "device": {{
    "device_type": "the specific device type",
    "device_category": "broader category (networking, computing, appliance, etc.)",
    "brand": "brand name if clearly visible, else 'unknown'",
    "model": "model if clearly visible, else 'not visible'",
    "brand_model_guidance": "where to find brand/model on this device type, or null",
    "device_confidence": 0.85,
    "confidence_level": "high",
    "components": ["component1", "component2", "component3"],
    "reasoning": "why you identified it this way"
  }},
  "query": {{
    "query_type": "locate",
    "answer_type": "locate_only",
    "target_component": "primary component they're asking about (or null)",
    "target_components": ["list", "of", "all", "targets"],
    "action_requested": "what they want to do",
    "needs_localization": true,
    "needs_steps": false,
    "needs_explanation": false,
    "clarification_needed": false,
    "clarifying_questions": [],
    "confidence": 0.9
  }},
  "safety": {{
    "safety_detected": false,
    "safety_keywords_found": [],
    "safety_message": null,
    "override_answer_type": false
  }}
}}

IMPORTANT: Identify the ACTUAL device type you see, not from a predefined list. Be specific and accurate. Be HONEST about uncertainty."""

        prompt = [prompt_text, image]

        return self.generate_response(
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=3000
        )

    def generate_grounded_response(
        self,
        query: str,
        device_info: Dict[str, Any],
        context: str = "",
        temperature: float = 0.3
    ) -> dict:
        """
        Generate a response using Gemini's NATIVE Grounding with Google Search tool.
        This uses the built-in google_search tool that triggers real web searches
        and returns grounding_metadata with actual source URIs and support chunks.

        Args:
            query: User's question
            device_info: Device detection results
            context: Any existing manual context
            temperature: Generation temperature

        Returns:
            Dict with grounded response text, source URIs, and rendered chunks
        """
        global GEMINI_DISABLED

        if GEMINI_DISABLED:
            return {"error": "Gemini disabled", "grounded": False}

        device_type = device_info.get("device_type", "device")
        brand = device_info.get("brand", "")
        model_name = device_info.get("model", "")

        device_str = device_type
        if brand and brand.lower() not in ["unknown", "", "generic"]:
            device_str = f"{brand} {device_type}"
        if model_name and model_name.lower() not in ["not visible", ""]:
            device_str = f"{device_str} {model_name}"

        prompt_text = f"""You are FixIt AI's troubleshooting expert.

Device: {device_str}
User Query: "{query}"
{f'Existing manual context: {context[:500]}' if context else 'No manual context available - rely on web search.'}

Using the web search results, provide accurate troubleshooting guidance for this specific device.
Focus on:
1. Official manufacturer troubleshooting procedures
2. Common community-verified solutions
3. Safety precautions specific to this device
4. Model-specific quirks or known issues

Be specific to the device brand/model when possible.
Include step numbers if providing a procedure.
Always mention when to seek professional help."""

        prompt = [prompt_text]

        try:
            from google.genai import types

            # Configure the native Google Search grounding tool
            # Using dynamic_retrieval_config to let Gemini decide when to search
            google_search_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Rate limit check
            if not self._check_rate_limit():
                return {"error": "Rate limited", "grounded": False}
            self._record_api_call()

            logger.info(f"Sending grounded request for: {device_str} - {query[:50]}...")

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[google_search_tool],
                    temperature=temperature,
                    max_output_tokens=3000,
                )
            )

            # Extract the main text response
            response_text = response.text if response.text else ""

            # Extract grounding metadata from the response
            grounding_sources = []
            search_entry_point_html = None
            grounding_chunks = []

            # The grounding_metadata lives on the response candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]

                # Extract grounding_metadata
                grounding_meta = getattr(candidate, 'grounding_metadata', None)
                if grounding_meta:
                    logger.info("Grounding metadata found in response")

                    # Extract search entry point (rendered HTML snippet)
                    search_ep = getattr(grounding_meta, 'search_entry_point', None)
                    if search_ep:
                        search_entry_point_html = getattr(search_ep, 'rendered_content', None)

                    # Extract grounding chunks (source URIs + text)
                    chunks = getattr(grounding_meta, 'grounding_chunks', None)
                    if chunks:
                        for chunk in chunks:
                            web_chunk = getattr(chunk, 'web', None)
                            if web_chunk:
                                grounding_chunks.append({
                                    "uri": getattr(web_chunk, 'uri', ''),
                                    "title": getattr(web_chunk, 'title', ''),
                                })

                    # Extract grounding supports (text segments mapped to sources)
                    supports = getattr(grounding_meta, 'grounding_supports', None)
                    if supports:
                        for support in supports:
                            segment = getattr(support, 'segment', None)
                            indices = getattr(support, 'grounding_chunk_indices', [])
                            conf_scores = getattr(support, 'confidence_scores', [])

                            support_entry = {
                                "text": getattr(segment, 'text', '') if segment else '',
                                "source_indices": list(indices) if indices else [],
                                "confidence_scores": list(conf_scores) if conf_scores else [],
                            }
                            grounding_sources.append(support_entry)

                    # Extract web_search_queries used
                    search_queries = getattr(grounding_meta, 'web_search_queries', None)
                    if search_queries:
                        logger.info(f"Grounding search queries: {search_queries}")

            # Build source URIs list for display
            source_uris = []
            for chunk in grounding_chunks:
                uri = chunk.get("uri", "")
                title = chunk.get("title", "")
                if uri:
                    source_uris.append({
                        "url": uri,
                        "title": title or uri,
                    })

            has_grounding = bool(grounding_chunks or grounding_sources)

            result = {
                "grounded": has_grounding or bool(response_text),
                "grounded_guidance": response_text,
                "sources": source_uris,
                "sources_summary": self._summarize_sources(source_uris),
                "grounding_chunks": grounding_chunks,
                "grounding_supports": grounding_sources,
                "search_entry_point_html": search_entry_point_html,
                "confidence": 0.8 if has_grounding else 0.5,
                "disclaimer": "This information was retrieved from web sources. Always verify with official documentation." if has_grounding else None,
            }

            logger.info(f"Grounding complete: {len(source_uris)} sources, {len(grounding_sources)} supports")
            return result

        except ImportError:
            logger.warning("Google Search grounding tool not available - check google-genai SDK version")
            return {"error": "Grounding not available - update google-genai package", "grounded": False}
        except Exception as e:
            logger.warning(f"Grounded response failed: {e}")
            if self._is_quota_error(e):
                GEMINI_DISABLED = True
                return self._quota_exhausted_response()
            return {"error": str(e), "grounded": False}

    def _summarize_sources(self, source_uris: list) -> str:
        """Create a human-readable summary of grounding sources."""
        if not source_uris:
            return "Google Search"

        titles = [s.get("title", s.get("url", "")) for s in source_uris[:5]]
        # Extract domain names as fallback
        summaries = []
        for s in source_uris[:5]:
            title = s.get("title", "")
            url = s.get("url", "")
            if title:
                summaries.append(title)
            elif url:
                # Extract domain
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    summaries.append(domain)
                except Exception:
                    summaries.append(url[:50])

        return "; ".join(summaries) if summaries else "Google Search"

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
                    except json.JSONDecodeError as json_err:
                        # Fallback: clean response and try to extract valid JSON
                        logger.warning(f"JSON Decode Failed: {json_err}, attempting to clean response text.")
                        
                        try:
                            # Remove markdown code fences
                            text = response.text.replace("```json", "").replace("```", "").strip()
                            
                            # Try parsing the cleaned text
                            result = json.loads(text)
                            logger.info("Successfully parsed JSON after cleaning markdown")
                        except json.JSONDecodeError as clean_err:
                            # If still failing, try to extract just the first complete JSON object
                            logger.info(f"Extracting first JSON object (Extra data detected)")
                            
                            try:
                                # Find the first '{' and try to parse from there
                                start_idx = text.find('{')
                                if start_idx != -1:
                                    # Use a JSON decoder to parse and stop at the first complete object
                                    decoder = json.JSONDecoder()
                                    result, end_idx = decoder.raw_decode(text[start_idx:])
                                    extra_content = text[start_idx + end_idx:].strip()
                                    if extra_content:
                                        logger.debug(f"Ignored extra content after JSON ({len(extra_content)} chars)")
                                    logger.info("Successfully extracted JSON object")
                                else:
                                    raise ValueError("No JSON object found in response")
                            except Exception as final_err:
                                logger.error(f"Failed all JSON extraction attempts: {final_err}")
                                logger.error(f"Response preview: {response.text[:500]}...")
                                raise HTTPException(
                                    status_code=500,
                                    detail=f"Gemini returned invalid JSON format. Error: {final_err}"
                                )
                else:
                    result = {"text": response.text}

                # Cache successful response
                self._store_cache(prompt_hash, result)
                return result

            except HTTPException:
                # Re-raise HTTPExceptions directly (like invalid JSON format)
                raise
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
