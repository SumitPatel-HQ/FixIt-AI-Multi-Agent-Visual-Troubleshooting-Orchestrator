// ═══════════════════════════════════════════════════════════════
// FixIt AI API Response Types
// ═══════════════════════════════════════════════════════════════

export type AnswerType =
   | "locate_only"
   | "identify_only"
   | "explain_only"
   | "troubleshoot_steps"
   | "mixed"
   | "ask_clarifying_questions"
   | "reject_invalid_image"
   | "ask_for_better_input"
   | "safety_warning_only";

export type CannotComplyReason =
   | "not_visible"
   | "not_present"
   | "low_confidence"
   | "invalid_image"
   | "safety_risk"
   | null;

export type ComponentStatus = "found" | "not_visible" | "not_present" | "ambiguous";

export type Severity = "low" | "medium" | "high" | "critical";

export interface BoundingBox {
   x_min: number;
   y_min: number;
   x_max: number;
   y_max: number;
}

export interface ArrowHint {
   from: { x: number; y: number };
   to: { x: number; y: number };
}

export interface DeviceInfo {
   device_category: string;
   device_type: string;
   brand: string;
   model: string;
   brand_model_guidance: string | null;
   confidence: number; // 0.0 - 1.0
}

export interface LocalizationResult {
   target: string;
   status: ComponentStatus;
   bounding_box: BoundingBox | null;
   spatial_description: string;
   landmark_description: string;
   reasoning: string;
   suggested_action: string;
   confidence: number;
   disambiguation_needed: boolean;
}

export interface Diagnosis {
   issue: string;
   severity: Severity;
   safety_warning: string | null;
   possible_causes?: string[];
   indicators?: string[];
}

export interface TroubleshootingStep {
   step: number;
   instruction: string;
   visual_cue: string;
   estimated_time: string;
   overlay_reference: string | null;
   safety_note?: string;
}

export interface ComponentFunction {
   name: string;
   description: string;
}

export interface Explanation {
   overview: string;
   component_functions: ComponentFunction[];
   data_flow: string;
}

export interface Visualization {
   target: string;
   bounding_box: BoundingBox;
   arrow_hint: ArrowHint | null;
   label: string;
   landmark_description: string;
   confidence: number;
   overlay_id: string;
   disambiguation_needed: boolean;
   ambiguity_note: string | null;
   // Additional fields for detail panel
   spatial_description?: string;
   reasoning?: string;
   suggested_action?: string;
}

export interface GroundingSource {
   id: string;
   type: "manual" | "web" | "knowledge_base" | "forum" | "video" | "pdf";
   title: string;
   url: string;
   domain: string;
   excerpt: string;
   full_text?: string;
   relevance: "high" | "medium" | "low";
   referenced_in_steps: number[];
   published_date?: string;
   author?: string;
   favicon_url?: string;
}

export interface APIResponse {
   answer_type: AnswerType;
   needs_clarification: boolean;
   cannot_comply_reason: CannotComplyReason;

   device_info: DeviceInfo;
   localization_results: LocalizationResult[];

   diagnosis?: Diagnosis;
   troubleshooting_steps?: TroubleshootingStep[];
   explanation?: Explanation;
   visualizations: Visualization[];

   audio_instructions: string;
   clarifying_questions?: string[];

   web_grounding_used?: boolean;
   grounding_sources?: GroundingSource[];

   // Error fields for invalid query handling
   status?: string;
   error?: string;
   query?: string;
   device_type?: string;
   is_mismatch?: boolean;
   message?: string;
   suggestions?: string[];
}

// Session data that includes the original image and query
export interface SessionData {
   sessionId: string;
   imageUrl: string;
   originalQuery: string;
   timestamp: string;
   response: APIResponse;
   conversationHistory?: ConversationEntry[];
}

export interface ConversationEntry {
   query: string;
   response: APIResponse;
   timestamp: string;
}

// Loading stages for progressive loading
export type LoadingStage =
   | "device_recognition"
   | "visual_analysis"
   | "diagnosis"
   | "action_steps"
   | "complete";

export const LOADING_STAGE_CONFIG: Record<LoadingStage, {
   progress: number;
   message: string;
   icon: string
}> = {
   device_recognition: { progress: 25, message: "Analyzing device...", icon: "🔍" },
   visual_analysis: { progress: 50, message: "Identifying components...", icon: "🎯" },
   diagnosis: { progress: 75, message: "Generating diagnosis...", icon: "🩺" },
   action_steps: { progress: 90, message: "Preparing guidance...", icon: "🔧" },
   complete: { progress: 100, message: "Analysis complete", icon: "✅" },
};
