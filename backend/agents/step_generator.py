"""
Step Generator Agent
Generates context-aware troubleshooting steps based on confidence and available information.
Enhanced with answer_type-aware generation: explanation mode, diagnosis-only, and mixed support.
"""

from typing import Dict, Any, List, Optional
import json
import logging
from backend.utils.gemini_client import gemini_client

logger = logging.getLogger(__name__)

# Response schemas for structured output
TROUBLESHOOT_SCHEMA = {
    "type": "object",
    "properties": {
        "issue_diagnosis": {"type": "string"},
        "diagnosis": {
            "type": "object",
            "properties": {
                "issue": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "safety_warning": {"type": ["string", "null"]},
                "possible_causes": {"type": "array", "items": {"type": "string"}},
                "indicators": {"type": "array", "items": {"type": "string"}},
                "professional_needed": {"type": "boolean"}
            },
            "required": ["issue", "severity", "possible_causes", "indicators", "professional_needed"]
        },
        "troubleshooting_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_number": {"type": "integer"},
                    "instruction": {"type": "string"},
                    "visual_cue": {"type": "string"},
                    "estimated_time": {"type": "string"},
                    "safety_note": {"type": ["string", "null"]}
                },
                "required": ["step_number", "instruction", "visual_cue", "estimated_time"]
            }
        },
        "audio_instructions": {"type": "string"},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "when_to_seek_help": {"type": "string"}
    },
    "required": ["issue_diagnosis", "diagnosis", "troubleshooting_steps", "audio_instructions"]
}

DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnosis": {
            "type": "object",
            "properties": {
                "issue": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "safety_warning": {"type": ["string", "null"]},
                "possible_causes": {"type": "array", "items": {"type": "string"}},
                "indicators": {"type": "array", "items": {"type": "string"}},
                "professional_needed": {"type": "boolean"}
            },
            "required": ["issue", "severity", "possible_causes", "indicators", "professional_needed"]
        },
        "audio_instructions": {"type": "string"}
    },
    "required": ["diagnosis", "audio_instructions"]
}

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {
            "type": "object",
            "properties": {
                "overview": {"type": "string"},
                "key_components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "function": {"type": "string"},
                            "location": {"type": "string"}
                        },
                        "required": ["name", "function"]
                    }
                },
                "how_it_works": {"type": "string"},
                "common_issues": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["overview", "how_it_works"]
        },
        "audio_instructions": {"type": "string"}
    },
    "required": ["explanation", "audio_instructions"]
}


class StepGenerator:
    """
    Generates troubleshooting steps, explanations, and diagnoses based on answer_type.
    Routes to appropriate generation mode based on intent classification.
    """

    def __init__(self):
        pass

    def generate(
        self,
        query: str,
        device_info: Dict[str, Any],
        spatial_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None,
        answer_type: str = "troubleshoot_steps"
    ) -> Dict[str, Any]:
        """
        Main entry point. Routes to appropriate generation mode based on answer_type.
        """
        # Route based on answer_type
        if answer_type == "explain_only":
            return self._generate_explanation(query, device_info, manual_context, query_info)
        elif answer_type == "diagnose_only":
            return self._generate_diagnosis_only(query, device_info, spatial_info, manual_context, query_info)
        elif answer_type == "mixed":
            return self._generate_mixed(query, device_info, spatial_info, manual_context, query_info)
        elif answer_type in ["locate_only", "identify_only"]:
            # These don't need step generation
            return {"skipped": True, "reason": f"No generation needed for {answer_type}"}
        elif answer_type in ["ask_clarifying_questions", "reject_invalid_image",
                             "ask_for_better_input", "safety_warning_only"]:
            return {"skipped": True, "reason": f"No generation needed for {answer_type}"}
        else:
            # Default: troubleshoot_steps
            return self.generate_steps(query, device_info, spatial_info, manual_context, query_info)

    def generate_steps(
        self,
        query: str,
        device_info: Dict[str, Any],
        spatial_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generates troubleshooting steps based on all available context.
        The response quality is matched to the confidence level.
        """
        device_confidence = device_info.get("device_confidence", 0.0)
        device_type = device_info.get("device_type", "Unknown")
        confidence_level = device_info.get("confidence_level", "low")

        if device_type in ["not_a_device", "Unknown"]:
            return self._generate_identification_help(query, device_info)
        elif confidence_level == "low" or device_confidence < 0.3:
            return self._generate_diagnostic_response(query, device_info, query_info)
        elif confidence_level == "medium" or device_confidence < 0.6:
            return self._generate_cautious_steps(query, device_info, spatial_info, manual_context, query_info)
        else:
            return self._generate_confident_steps(query, device_info, spatial_info, manual_context, query_info)

    def _generate_explanation(
        self,
        query: str,
        device_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a how-it-works explanation instead of repair steps."""
        device_type = device_info.get("device_type", "Unknown Device")
        components = device_info.get("components", [])
        context_str = "\n\n".join(manual_context) if manual_context else "No specific manual context."

        target_component = None
        if query_info:
            target_component = query_info.get("target_component")

        focus = f"specifically about the {target_component}" if target_component else "in general"

        prompt = [
            f"""You are an expert electronics educator for FixIt AI.

User Query: "{query}"
Device: {device_type}
Visible Components: {', '.join(components[:8]) if components else 'none detected'}
Focus: {focus}

Manual Context:
{context_str}

Generate an educational EXPLANATION (NOT repair steps) about how this device/component works.

Return JSON:
{{
    "explanation": {{
        "overview": "2-3 sentence overview of how the device/component works",
        "component_functions": [
            {{
                "name": "component name",
                "purpose": "what it does",
                "how_it_works": "brief technical explanation"
            }}
        ],
        "data_flow": "how data or energy flows through the device",
        "key_concepts": ["list of key technical concepts"],
        "common_misconceptions": ["common misunderstandings about this device"]
    }},
    "audio_instructions": "natural voice narration of the explanation"
}}

Be technically accurate but accessible. Explain like teaching someone curious.
"""
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=EXPLAIN_SCHEMA,
                temperature=0.3
            )
            if isinstance(response, dict) and not response.get("error"):
                return response
            return self._create_fallback_explanation(device_type, target_component)
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return self._create_fallback_explanation(device_type, target_component)

    def _generate_diagnosis_only(
        self,
        query: str,
        device_info: Dict[str, Any],
        spatial_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a diagnosis without repair steps."""
        device_type = device_info.get("device_type", "Unknown Device")
        context_str = "\n\n".join(manual_context) if manual_context else "No specific manual context."

        component = ""
        if spatial_info and spatial_info.get("component_name"):
            component = spatial_info["component_name"]

        prompt = [
            f"""You are a diagnostic expert for FixIt AI.

User Query: "{query}"
Device: {device_type}
Component of interest: {component or 'general device'}

Manual Context:
{context_str}

Provide a DIAGNOSIS ONLY - do NOT provide repair steps.
The user specifically wants to understand the problem, not fix it yet.

Return JSON:
{{
    "diagnosis": {{
        "issue": "clear explanation of the likely problem",
        "severity": "low" | "medium" | "high" | "critical",
        "safety_warning": "any safety concerns, or null",
        "possible_causes": ["list of possible causes", "in order of likelihood"],
        "indicators": ["what signs confirm this diagnosis"],
        "professional_needed": false
    }},
    "audio_instructions": "natural language summary of the diagnosis"
}}
"""
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=DIAGNOSIS_SCHEMA,
                temperature=0.3
            )
            if isinstance(response, dict) and not response.get("error"):
                return response
            return {
                "diagnosis": {
                    "issue": f"I detected a potential issue with your {device_type} but couldn't generate a detailed diagnosis.",
                    "severity": "medium",
                    "safety_warning": None,
                    "possible_causes": [],
                    "indicators": [],
                    "professional_needed": False,
                },
                "audio_instructions": f"I noticed an issue with your {device_type} but couldn't complete the full diagnosis. Please try again or consult a professional."
            }
        except Exception as e:
            logger.error(f"Diagnosis generation failed: {e}")
            return {
                "diagnosis": {
                    "issue": "Unable to generate diagnosis due to an error.",
                    "severity": "medium",
                    "safety_warning": None,
                    "possible_causes": [],
                    "indicators": [],
                    "professional_needed": False,
                },
                "audio_instructions": "I encountered an error generating the diagnosis. Please try again."
            }

    def _generate_mixed(
        self,
        query: str,
        device_info: Dict[str, Any],
        spatial_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a mixed response covering multiple intents."""
        # For mixed queries, generate both explanation and troubleshooting
        # Don't rely on sub_intents - always generate both for mixed
        result = {}

        # Generate explanation
        explain_result = self._generate_explanation(query, device_info, manual_context, query_info)
        if isinstance(explain_result, dict):
            result["explanation"] = explain_result.get("explanation")

        # Generate troubleshooting steps with diagnosis
        steps_result = self.generate_steps(query, device_info, spatial_info, manual_context, query_info)
        if isinstance(steps_result, dict):
            result["troubleshooting_steps"] = steps_result.get("troubleshooting_steps")
            result["issue_diagnosis"] = steps_result.get("issue_diagnosis", "")
            result["audio_instructions"] = steps_result.get("audio_instructions", "")
            result["warnings"] = steps_result.get("warnings")
            result["when_to_seek_help"] = steps_result.get("when_to_seek_help")
            
            # Build complete diagnosis object
            diag = steps_result.get("diagnosis")
            if isinstance(diag, dict):
                result["diagnosis"] = diag
            else:
                # Fallback: construct from issue_diagnosis
                result["diagnosis"] = {
                    "issue": steps_result.get("issue_diagnosis", ""),
                    "severity": "medium",
                    "safety_warning": None,
                    "possible_causes": [],
                    "indicators": [],
                    "professional_needed": False,
                }

        return result

    def _generate_confident_steps(
        self,
        query: str,
        device_info: Dict[str, Any],
        spatial_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate detailed steps when confidence is high."""
        context_str = "\n\n".join(manual_context) if manual_context else "No specific manual pages found."

        device_str = f"{device_info.get('device_type', 'Unknown Device')}"
        brand = device_info.get('brand', '')
        if brand and brand.lower() not in ['unknown', '']:
            device_str += f" ({brand}"
            model = device_info.get('model', '')
            if model and model.lower() not in ['not visible', '']:
                device_str += f" {model}"
            device_str += ")"

        component = spatial_info.get('component_name', 'Unknown') if spatial_info else 'Unknown'
        spatial_desc = spatial_info.get('spatial_description', 'location unknown') if spatial_info else 'location unknown'

        component_str = f"Target: {component}"
        if spatial_info and spatial_info.get('component_visible'):
            component_str += f" - Located at: {spatial_desc}"
        elif spatial_info and spatial_info.get('typical_location'):
            component_str += f" - Typically located: {spatial_info.get('typical_location')}"

        prompt = [
            f"""You are an expert repair technician AI for FixIt AI.

Generate SPECIFIC, ACTIONABLE troubleshooting steps for this issue.

User Query: {query}
Device: {device_str}
{component_str}

Manual Context:
{context_str}

{self._get_query_type_instructions(query_info)}

Return ONLY valid JSON with NO extra text before or after:
{{
    "issue_diagnosis": "concise explanation of what is likely happening",
    "diagnosis": {{
        "issue": "detailed explanation of the problem",
        "severity": "low" | "medium" | "high" | "critical",
        "safety_warning": null,
        "possible_causes": ["most likely cause", "second likely cause"],
        "indicators": ["sign 1 that confirms this", "sign 2"],
        "professional_needed": false
    }},
    "troubleshooting_steps": [
        {{
            "step_number": 1,
            "instruction": "clear action to take",
            "visual_cue": "what to look for",
            "estimated_time": "e.g., 30 seconds",
            "safety_note": "any safety precautions if needed"
        }}
    ],
    "audio_instructions": "friendly paragraph combining diagnosis and steps for TTS",
    "warnings": ["any important warnings"],
    "when_to_seek_help": "when should user consult a professional"
}}

Keep steps:
- Safe and beginner-friendly
- Specific to this device type
- Based on actual visible components
- In logical order
"""
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=TROUBLESHOOT_SCHEMA,
                temperature=0.3
            )

            if isinstance(response, dict) and response.get("error"):
                if "quota" in response.get("error", "").lower():
                    return self._create_quota_exhausted_response(device_info, spatial_info)

            if isinstance(response, dict):
                return self._validate_step_response(response)
            return self._create_fallback_steps_response(device_info)
        except Exception as e:
            logger.error(f"Step generation failed: {e}")
            if "quota" in str(e).lower() or "429" in str(e):
                return self._create_quota_exhausted_response(device_info, spatial_info)
            return self._create_error_response(str(e))

    def _generate_cautious_steps(
        self,
        query: str,
        device_info: Dict[str, Any],
        spatial_info: Dict[str, Any],
        manual_context: List[str],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate general guidance with uncertainty caveats."""
        device_type = device_info.get('device_type', 'Unknown')
        reasoning = device_info.get('reasoning', '')

        prompt = [
            f"""You are a helpful repair assistant for FixIt AI.

The user asked: "{query}"
I THINK this might be a {device_type}, but I'm not entirely certain.
My reasoning: {reasoning}

Because I'm not 100% sure about the device:
1. Provide GENERAL guidance that would apply to most {device_type}s
2. Include appropriate caveats about uncertainty
3. Suggest ways the user can verify the device type
4. Focus on safe, universal steps

Return ONLY valid JSON with NO extra text:
{{
    "issue_diagnosis": "based on my assessment (noting uncertainty)",
    "diagnosis": {{
        "issue": "general explanation with uncertainty noted",
        "severity": "medium",
        "safety_warning": null,
        "possible_causes": ["general cause 1", "general cause 2"],
        "indicators": [],
        "professional_needed": false
    }},
    "confidence_note": "explain your uncertainty to the user",
    "troubleshooting_steps": [
        {{
            "step_number": 1,
            "instruction": "general safe step",
            "visual_cue": "what to look for",
            "estimated_time": "time estimate",
            "caveat": "any uncertainty about this step"
        }}
    ],
    "audio_instructions": "friendly paragraph that acknowledges uncertainty",
    "verification_questions": ["questions to verify device type"],
    "general_safety_tips": ["universal safety tips"]
}}

Be honest about limitations while still being helpful.
"""
        ]

        try:
            response = gemini_client.generate_response(
                prompt=prompt,
                response_schema=TROUBLESHOOT_SCHEMA,
                temperature=0.3
            )

            if isinstance(response, dict) and response.get("error"):
                if "quota" in response.get("error", "").lower():
                    return self._create_quota_exhausted_response(device_info, spatial_info)

            if isinstance(response, dict):
                return self._validate_step_response(response)
            return self._create_cautious_fallback(device_type)
        except Exception as e:
            logger.error(f"Cautious step generation failed: {e}")
            if "quota" in str(e).lower() or "429" in str(e):
                return self._create_quota_exhausted_response(device_info, spatial_info)
            return self._create_cautious_fallback(device_type)

    def _generate_diagnostic_response(
        self,
        query: str,
        device_info: Dict[str, Any],
        query_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate diagnostic questions instead of potentially wrong steps."""
        what_i_see = device_info.get('what_i_see', 'Unable to clearly identify the device')
        clarifying_questions = device_info.get('clarifying_questions', [])
        suggestions = device_info.get('suggestions', [])

        return {
            "issue_diagnosis": f"I'm having trouble identifying this device clearly. {what_i_see}",
            "needs_clarification": True,
            "troubleshooting_steps": [{
                "step_number": 1,
                "instruction": "Please help me understand your device better by answering a few questions",
                "visual_cue": "Look at your device to answer these questions",
                "estimated_time": "1 minute"
            }],
            "clarifying_questions": clarifying_questions if clarifying_questions else [
                "What type of device is this? (e.g., router, printer, laptop)",
                "What brand is it? Are there any visible logos or labels?",
                "Can you describe the issue you're experiencing?"
            ],
            "suggestions": suggestions if suggestions else [
                "Try taking a photo from a different angle",
                "Make sure the device is well-lit",
                "Include any visible brand names or model numbers"
            ],
            "audio_instructions": "I need a bit more information to help you effectively. Could you tell me what type of device this is, and describe the issue you're experiencing?",
            "general_safety_tip": "While I gather more information, remember: always disconnect power before working on any electronic device."
        }

    def _generate_identification_help(
        self,
        query: str,
        device_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate helpful response when device couldn't be identified at all."""
        what_i_see = device_info.get('what_i_see', '')
        components = device_info.get('components', [])

        diagnosis = "I couldn't identify a troubleshootable device in this image."
        if what_i_see:
            diagnosis += f" {what_i_see}"

        steps = [{
            "step_number": 1,
            "instruction": "Upload a clear photo of the electronic device you need help with",
            "visual_cue": "Show the entire device with visible brand/labels if possible",
            "estimated_time": "30 seconds"
        }]

        if components:
            steps.append({
                "step_number": 2,
                "instruction": f"I can see some elements in the image: {', '.join(components[:3])}. If you're asking about these, please clarify.",
                "visual_cue": "Point to or describe the specific part you need help with",
                "estimated_time": "30 seconds"
            })

        return {
            "issue_diagnosis": diagnosis,
            "device_not_identified": True,
            "troubleshooting_steps": steps,
            "audio_instructions": "I couldn't identify a device to troubleshoot. Please upload a clear photo of the electronic device you need help with, making sure the whole device is visible.",
            "supported_devices": [
                "WiFi Routers & Modems",
                "Printers & Scanners",
                "Laptops & Computers",
                "Smart Home Devices",
                "Home Appliances",
                "Circuit Boards & Arduino"
            ],
            "tips_for_better_photos": [
                "Ensure the device is well-lit",
                "Show the front panel with controls/indicators",
                "Include any visible brand names or labels",
                "Step back to show the entire device"
            ]
        }

    def _get_query_type_instructions(self, query_info: Dict[str, Any] = None) -> str:
        """Get additional instructions based on query type."""
        if not query_info:
            return ""

        query_type = query_info.get("query_type", "unclear")

        if query_type == "identify":
            return """
Query Type: IDENTIFICATION
User wants to know what something is. Focus on:
- Explaining what the component/device is
- Its purpose and function
- How it relates to the device
"""
        elif query_type == "locate":
            return """
Query Type: LOCATION
User wants to find something. Focus on:
- Describing exact location
- Identifying nearby landmarks
- How to access it if hidden
"""
        elif query_type == "procedure":
            return """
Query Type: HOW-TO
User wants step-by-step instructions. Focus on:
- Clear sequential steps
- What tools might be needed
- Common pitfalls to avoid
"""
        elif query_type == "troubleshoot":
            return """
Query Type: TROUBLESHOOTING
User has a problem to fix. Focus on:
- Diagnosing the issue
- Step-by-step fix
- When to seek professional help
"""
        elif query_type == "explain":
            return """
Query Type: EXPLANATION
User wants to understand how something works. Focus on:
- How the device/component functions
- Key technical concepts
- How components interact
"""
        return ""

    def _validate_step_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize the step response."""
        if "troubleshooting_steps" not in response:
            response["troubleshooting_steps"] = []

        if "issue_diagnosis" not in response:
            response["issue_diagnosis"] = "Unable to determine specific diagnosis."

        if "audio_instructions" not in response:
            response["audio_instructions"] = ""

        for i, step in enumerate(response.get("troubleshooting_steps", [])):
            if "step_number" not in step:
                step["step_number"] = i + 1
            if "instruction" not in step:
                step["instruction"] = "No instruction available"
            if "visual_cue" not in step:
                step["visual_cue"] = ""
            if "estimated_time" not in step:
                step["estimated_time"] = "N/A"

        return response

    def _create_fallback_explanation(self, device_type: str, target_component: Optional[str] = None) -> Dict[str, Any]:
        """Create a fallback explanation when generation fails."""
        focus = target_component or device_type
        return {
            "explanation": {
                "overview": f"This is a {device_type}. {f'The {target_component} is a key component.' if target_component else ''}",
                "component_functions": [],
                "data_flow": "",
                "key_concepts": [],
                "common_misconceptions": [],
            },
            "audio_instructions": f"This appears to be a {device_type}. Unfortunately, I couldn't generate a detailed explanation. Please try again or consult the device manual for more information."
        }

    def _create_fallback_steps_response(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback response when step generation fails but device is known."""
        device_type = device_info.get("device_type", "device")

        return {
            "issue_diagnosis": f"I can see this is a {device_type}, but I couldn't generate specific troubleshooting steps.",
            "troubleshooting_steps": [{
                "step_number": 1,
                "instruction": f"For {device_type} issues, start by power cycling the device (unplug, wait 30 seconds, plug back in)",
                "visual_cue": "Wait for all lights to return to normal",
                "estimated_time": "2 minutes"
            }, {
                "step_number": 2,
                "instruction": "Check all cable connections are secure",
                "visual_cue": "Look for loose or damaged cables",
                "estimated_time": "1 minute"
            }, {
                "step_number": 3,
                "instruction": "If the issue persists, consult the device manual or manufacturer support",
                "visual_cue": "Look for model number for support lookup",
                "estimated_time": "5 minutes"
            }],
            "audio_instructions": f"For your {device_type}, try power cycling it first. Unplug the device, wait 30 seconds, then plug it back in. If that doesn't work, check all cable connections. If the issue continues, you may need to consult the manufacturer or a professional.",
            "note": "These are general troubleshooting steps. For device-specific help, please describe your issue in more detail."
        }

    def _create_cautious_fallback(self, device_type: str) -> Dict[str, Any]:
        """Create a cautious fallback when uncertain."""
        return {
            "issue_diagnosis": f"I think this might be a {device_type}, but I'm not entirely certain. Here's general guidance.",
            "confidence_note": "Please verify this matches your device before following these steps.",
            "troubleshooting_steps": [{
                "step_number": 1,
                "instruction": "First, verify this is the correct device type",
                "visual_cue": "Check for brand name and model number",
                "estimated_time": "30 seconds"
            }, {
                "step_number": 2,
                "instruction": "Safely disconnect power before any troubleshooting",
                "visual_cue": "Confirm all power indicators are off",
                "estimated_time": "30 seconds"
            }],
            "audio_instructions": f"I'm not entirely sure about the device type, so please verify before proceeding. If this is indeed a {device_type}, start by safely disconnecting the power.",
            "general_safety_tips": [
                "Always disconnect power before working on electronics",
                "Don't open sealed units unless qualified",
                "If unsure, consult a professional"
            ]
        }

    def _create_quota_exhausted_response(self, device_info: Dict[str, Any], spatial_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a response when AI quota is exhausted."""
        device_type = device_info.get('device_type', 'device')
        component = 'component'
        if spatial_info:
            component = spatial_info.get('component_name') or spatial_info.get('component') or 'component'

        return {
            "issue_diagnosis": f"I successfully identified your {device_type} and located the {component}, but I've reached my AI analysis limit for now.",
            "troubleshooting_steps": [{
                "step_number": 1,
                "instruction": f"The {component} is visible in the image at the location shown",
                "visual_cue": spatial_info.get('spatial_description', 'See bounding box for location') if spatial_info else 'N/A',
                "estimated_time": "N/A"
            }],
            "audio_instructions": f"I found your {device_type} and located the {component}, but I've reached my daily AI usage limit. Please try again tomorrow for detailed troubleshooting steps.",
            "quota_info": "AI analysis temporarily unavailable. Device and component detection successful."
        }

    def _create_error_response(self, error: str) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "issue_diagnosis": "I encountered an error while generating troubleshooting steps.",
            "troubleshooting_steps": [{
                "step_number": 1,
                "instruction": "Please try your request again",
                "visual_cue": "N/A",
                "estimated_time": "N/A"
            }],
            "audio_instructions": "I'm sorry, I encountered an error. Please try again.",
            "error": error
        }


# Singleton instance
step_generator = StepGenerator()
