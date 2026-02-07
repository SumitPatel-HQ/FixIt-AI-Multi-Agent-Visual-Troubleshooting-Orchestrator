"""
Query Parser Agent
Understands user intent before processing to enable smarter routing.
Acts as GATE 3 in the pipeline.
"""

from typing import Dict, Any, List
import logging
from backend.utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

# Response schema for structured output
QUERY_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "query_type": {
            "type": "string",
            "enum": ["identify", "locate", "troubleshoot", "procedure", "general_info", "unclear"]
        },
        "target_component": {"type": ["string", "null"]},
        "action_requested": {"type": "string"},
        "needs_localization": {"type": "boolean"},
        "needs_steps": {"type": "boolean"},
        "clarification_needed": {"type": "boolean"},
        "clarifying_questions": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"}
    },
    "required": ["query_type", "action_requested", "needs_localization", "needs_steps", "clarification_needed", "clarifying_questions", "confidence"]
}


class QueryParser:
    """
    Parses user queries to understand intent and extract target components.
    Enables smarter routing through the troubleshooting pipeline.
    """
    
    # Query type definitions
    QUERY_TYPES = {
        "identify": "User wants to identify what something is",
        "locate": "User wants to find where something is located",
        "troubleshoot": "User wants to fix a problem",
        "procedure": "User wants step-by-step instructions",
        "general_info": "User wants general information about device",
        "unclear": "Query intent is not clear"
    }
    
    # Common component keywords for quick extraction
    COMPONENT_KEYWORDS = {
        "button": ["button", "btn", "switch", "toggle"],
        "light": ["light", "led", "indicator", "lamp", "blinking"],
        "port": ["port", "socket", "jack", "connector", "usb", "hdmi", "ethernet"],
        "cable": ["cable", "wire", "cord", "connection"],
        "screen": ["screen", "display", "monitor", "lcd"],
        "power": ["power", "battery", "charger", "outlet"],
        "reset": ["reset", "restart", "reboot"]
    }

    def __init__(self):
        pass

    def parse_query(self, query: str, device_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parses the user query to understand intent and extract components.
        
        Args:
            query: The user's question/request
            device_context: Optional context about detected device
            
        Returns:
            Dict with:
            - query_type: str - Type of query (identify, locate, troubleshoot, etc.)
            - target_component: str or None - Specific component mentioned
            - action_requested: str - What user wants to do
            - needs_localization: bool - Whether spatial mapping is needed
            - needs_steps: bool - Whether step generation is needed
            - clarification_needed: bool - Whether we need more info
            - clarifying_questions: list - Questions to ask if needed
            - keywords_found: list - Relevant keywords found in query
        """
        
        # First, do quick keyword extraction
        keywords = self._extract_keywords(query)
        
        # Build context string for Gemini
        device_str = ""
        if device_context:
            device_str = f"Detected device: {device_context.get('device_type', 'Unknown')}"
            if device_context.get('components'):
                device_str += f"\nVisible components: {', '.join(device_context['components'][:5])}"
        
        prompt = [
            f"""You are a query understanding system for FixIt AI, a device troubleshooting assistant.

Analyze this user query and determine their intent.

User Query: "{query}"
{device_str}

Determine:
1. What TYPE of question is this?
   - "identify" → Asking what something is ("what component is this", "what is this device")
   - "locate" → Asking where something is ("where is the reset button")
   - "troubleshoot" → Reporting a problem ("not working", "won't turn on", "making noise")
   - "procedure" → Asking how to do something ("how to connect", "how to reset")
   - "general_info" → Asking about features or capabilities
   - "unclear" → Cannot determine intent

2. Is there a SPECIFIC COMPONENT mentioned?
   - Extract any specific part, button, port, or feature mentioned
   - Return null if no specific component is mentioned

3. What ACTION does the user want to take?
   - Summarize what outcome the user is seeking

4. Do we need to LOCALIZE a component in the image?
   - true if user asks "where is X" or needs to find something
   - false for general troubleshooting

5. Do we need to generate STEP-BY-STEP instructions?
   - true for troubleshooting or procedure questions
   - false for simple identification questions

Return a JSON object:
{{
    "query_type": "identify" | "locate" | "troubleshoot" | "procedure" | "general_info" | "unclear",
    "target_component": "specific component name or null",
    "action_requested": "what user wants to accomplish",
    "needs_localization": true/false,
    "needs_steps": true/false,
    "clarification_needed": true/false,
    "clarifying_questions": ["list of questions if clarification needed else empty array"],
    "confidence": 0.0 to 1.0
}}
"""
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=QUERY_PARSE_SCHEMA,
                temperature=0.2
            )
            
            if isinstance(response, dict):
                result = self._process_parse_response(response, keywords)
                return result
            
            return self._create_fallback_response(query, keywords)

        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            return self._create_fallback_response(query, keywords)

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract relevant keywords from query using simple pattern matching."""
        query_lower = query.lower()
        found_keywords = []
        
        for component, patterns in self.COMPONENT_KEYWORDS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    found_keywords.append(component)
                    break
        
        return list(set(found_keywords))

    def _process_parse_response(self, response: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
        """Process and normalize the parse response."""
        
        return {
            "query_type": response.get("query_type", "unclear"),
            "target_component": response.get("target_component"),
            "action_requested": response.get("action_requested", ""),
            "needs_localization": response.get("needs_localization", False),
            "needs_steps": response.get("needs_steps", True),  # Default to true for safety
            "clarification_needed": response.get("clarification_needed", False),
            "clarifying_questions": response.get("clarifying_questions", []),
            "keywords_found": keywords,
            "confidence": response.get("confidence", 0.5)
        }

    def _create_fallback_response(self, query: str, keywords: List[str]) -> Dict[str, Any]:
        """Create a fallback response based on basic analysis."""
        
        query_lower = query.lower()
        
        # Simple heuristics for query type
        query_type = "unclear"
        needs_localization = False
        needs_steps = True
        
        if any(w in query_lower for w in ["what is", "what's", "identify", "what component"]):
            query_type = "identify"
            needs_steps = False
        elif any(w in query_lower for w in ["where is", "where's", "locate", "find"]):
            query_type = "locate"
            needs_localization = True
            needs_steps = False
        elif any(w in query_lower for w in ["how to", "how do", "steps", "guide"]):
            query_type = "procedure"
            needs_steps = True
        elif any(w in query_lower for w in ["not working", "broken", "won't", "doesn't", "problem", "issue", "error"]):
            query_type = "troubleshoot"
            needs_steps = True
        
        # Extract target component from keywords
        target_component = keywords[0] if keywords else None
        
        return {
            "query_type": query_type,
            "target_component": target_component,
            "action_requested": query,
            "needs_localization": needs_localization,
            "needs_steps": needs_steps,
            "clarification_needed": query_type == "unclear",
            "clarifying_questions": [
                "Could you describe what issue you're experiencing?",
                "What would you like help with specifically?"
            ] if query_type == "unclear" else [],
            "keywords_found": keywords,
            "confidence": 0.3
        }

    def generate_clarifying_response(self, query_info: Dict[str, Any], device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a clarifying response when the query is unclear.
        """
        questions = query_info.get("clarifying_questions", [])
        
        device_type = device_info.get("device_type", "your device")
        components = device_info.get("components", [])
        
        response = {
            "status": "clarification_needed",
            "message": f"I can see this appears to be a {device_type}, but I need a bit more information to help you.",
            "questions": questions if questions else [
                "What specific issue are you experiencing?",
                "Which part of the device are you asking about?"
            ],
            "available_help": [
                "Identifying components",
                "Locating specific parts",
                "Troubleshooting issues",
                "Step-by-step repair guidance"
            ]
        }
        
        if components:
            response["visible_components"] = components[:5]
            response["hint"] = f"I can see these components: {', '.join(components[:5])}. Are you asking about any of these?"
        
        return response


# Singleton instance
query_parser = QueryParser()
