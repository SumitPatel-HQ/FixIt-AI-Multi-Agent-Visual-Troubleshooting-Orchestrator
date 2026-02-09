// ═══════════════════════════════════════════════════════════════
// FixIt AI API Service
// Handles all communication with the FastAPI backend
// ═══════════════════════════════════════════════════════════════

import { APIResponse, SessionData } from "@/types/api-response";

// Configuration - IMPORTANT: Restart frontend dev server if you change .env.local
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REQUEST_TIMEOUT = 120000; // 120 seconds for AI processing (increased for slower models like gemini-3-flash-preview)

// Log the configuration on module load
console.log("[API] Configuration - Backend URL:", API_BASE_URL);

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

export interface TroubleshootRequest {
   image: File;
   query: string;
   deviceHint?: {
      type?: string;
      brand?: string;
      model?: string;
   };
}

export interface TroubleshootResponse {
   success: boolean;
   sessionId: string;
   response: APIResponse;
   imageUrl: string;
   originalQuery: string;
   error?: string;
}

export interface HealthCheckResponse {
   status: string;
   version: string;
   pipeline: string;
}

export interface APIError {
   message: string;
   statusCode?: number;
   retryAfter?: number;
   isNetworkError?: boolean;
   isTimeout?: boolean;
}

// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Convert File to base64 string
 */
async function fileToBase64(file: File): Promise<string> {
   return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
         const result = reader.result as string;
         // Remove data URL prefix (e.g., "data:image/jpeg;base64,")
         const base64 = result.split(",")[1];
         resolve(base64);
      };
      reader.onerror = () => reject(new Error("Failed to read file"));
      reader.readAsDataURL(file);
   });
}

/**
 * Create object URL for image preview
 */
function createImageUrl(file: File): string {
   return URL.createObjectURL(file);
}

/**
 * Generate unique session ID
 */
function generateSessionId(): string {
   return `session-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Fetch with timeout
 */
async function fetchWithTimeout(
   url: string,
   options: RequestInit,
   timeout: number = REQUEST_TIMEOUT
): Promise<Response> {
   const controller = new AbortController();
   const timeoutId = setTimeout(() => controller.abort(), timeout);

   try {
      console.log("[API] Fetching:", url);
      const response = await fetch(url, {
         ...options,
         signal: controller.signal,
         mode: "cors",
      });
      console.log("[API] Response status:", response.status);
      return response;
   } catch (error) {
      console.error("[API] Fetch error:", error);
      throw error;
   } finally {
      clearTimeout(timeoutId);
   }
}

/**
 * Handle API errors consistently
 */
function handleAPIError(error: unknown): APIError {
   if (error instanceof Error) {
      if (error.name === "AbortError") {
         return {
            message: "Request timed out. The server may be busy - please try again.",
            isTimeout: true,
         };
      }
      if (error.message.includes("fetch") || error.message.includes("network")) {
         return {
            message: "Unable to connect to the server. Please check your connection.",
            isNetworkError: true,
         };
      }
      return { message: error.message };
   }
   return { message: "An unexpected error occurred. Please try again." };
}

// ═══════════════════════════════════════════════════════════════
// API Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthCheckResponse | null> {
   try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/health`, {
         method: "GET",
      }, 5000);

      if (!response.ok) {
         console.warn("Health check failed:", response.status);
         return null;
      }

      return await response.json();
   } catch (error) {
      console.warn("Health check error:", error);
      return null;
   }
}

/**
 * Main troubleshooting endpoint
 * Sends image and query to backend for AI analysis
 */
export async function troubleshoot(
   request: TroubleshootRequest
): Promise<TroubleshootResponse> {
   const sessionId = generateSessionId();
   const imageUrl = createImageUrl(request.image);

   try {
      // Convert image to base64
      console.log("[API] Converting image to base64...");
      const imageBase64 = await fileToBase64(request.image);

      // Get image dimensions
      const imageDimensions = await getImageDimensions(request.image);

      // Prepare form data (FastAPI expects Form data, not JSON)
      const formData = new FormData();
      formData.append("image_base64", imageBase64);
      formData.append("query", request.query);

      if (request.deviceHint) {
         // Backend expects device_hint as a string (will be parsed internally)
         const hintParts = [];
         if (request.deviceHint.type) hintParts.push(request.deviceHint.type);
         if (request.deviceHint.brand) hintParts.push(request.deviceHint.brand);
         if (request.deviceHint.model) hintParts.push(request.deviceHint.model);
         if (hintParts.length > 0) {
            formData.append("device_hint", hintParts.join(" "));
         }
      }

      formData.append("image_width", String(imageDimensions.width));
      formData.append("image_height", String(imageDimensions.height));

      console.log("[API] Sending request to backend...", {
         endpoint: `${API_BASE_URL}/api/troubleshoot`,
         query: request.query,
         imageSize: request.image.size,
         dimensions: imageDimensions,
      });

      // Make API request
      const response = await fetchWithTimeout(
         `${API_BASE_URL}/api/troubleshoot`,
         {
            method: "POST",
            body: formData,
         }
      );

      // Handle error responses
      if (!response.ok) {
         const errorData = await response.json().catch(() => ({}));
         console.error("[API] Error response:", response.status, errorData);

         throw new Error(
            errorData.detail || errorData.message || `Server error: ${response.status}`
         );
      }

      // Parse successful response
      const apiResponse: APIResponse = await response.json();
      console.log("[API] Received response:", {
         answerType: apiResponse.answer_type,
         deviceType: apiResponse.device_info?.device_type,
         hasSteps: !!apiResponse.troubleshooting_steps?.length,
      });

      return {
         success: true,
         sessionId,
         response: apiResponse,
         imageUrl,
         originalQuery: request.query,
      };
   } catch (error) {
      console.error("[API] Troubleshoot error:", error);
      const apiError = handleAPIError(error);

      // Revoke the object URL since we failed
      URL.revokeObjectURL(imageUrl);

      return {
         success: false,
         sessionId,
         response: createErrorResponse(apiError.message),
         imageUrl: "",
         originalQuery: request.query,
         error: apiError.message,
      };
   }
}

/**
 * Follow-up query within an existing session
 */
export async function followUpQuery(
   sessionData: SessionData,
   newQuery: string,
   newImage?: File
): Promise<TroubleshootResponse> {
   // If there's a new image, treat it as a new troubleshooting request
   if (newImage) {
      return troubleshoot({
         image: newImage,
         query: newQuery,
      });
   }

   // Otherwise, we need to re-send with the original image context
   // For now, we'll need to handle this differently since we don't store the original file
   // This is a limitation that may need session storage on the backend
   console.warn("[API] Follow-up without new image - feature requires backend session support");

   return {
      success: false,
      sessionId: sessionData.sessionId,
      response: createErrorResponse("Follow-up queries without a new image require the original image to be re-uploaded."),
      imageUrl: sessionData.imageUrl,
      originalQuery: newQuery,
      error: "Please upload the image again for follow-up queries.",
   };
}

// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Get image dimensions
 */
async function getImageDimensions(file: File): Promise<{ width: number; height: number }> {
   return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
         resolve({ width: img.width, height: img.height });
         URL.revokeObjectURL(img.src);
      };
      img.onerror = () => {
         resolve({ width: 800, height: 600 }); // Default fallback
      };
      img.src = URL.createObjectURL(file);
   });
}

/**
 * Create a structured error response
 */
function createErrorResponse(message: string): APIResponse {
   return {
      answer_type: "troubleshoot_steps",
      needs_clarification: false,
      cannot_comply_reason: null,
      device_info: {
         device_category: "unknown",
         device_type: "Unknown",
         brand: "unknown",
         model: "not visible",
         brand_model_guidance: null,
         confidence: 0,
      },
      localization_results: [],
      visualizations: [],
      audio_instructions: message,
      diagnosis: {
         issue: message,
         severity: "low",
         safety_warning: null,
      },
   };
}

// ═══════════════════════════════════════════════════════════════
// Session Storage (Client-side caching)
// ═══════════════════════════════════════════════════════════════

const SESSION_STORAGE_KEY = "fixit_sessions";
const SESSION_EXPIRY_MS = 30 * 60 * 1000; // 30 minutes

/**
 * Store session data in localStorage
 */
export function storeSession(sessionData: SessionData): void {
   try {
      const sessions = getStoredSessions();
      sessions[sessionData.sessionId] = {
         ...sessionData,
         expiresAt: Date.now() + SESSION_EXPIRY_MS,
      };
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
   } catch (error) {
      console.warn("[Session] Failed to store session:", error);
   }
}

/**
 * Retrieve session data from localStorage
 */
export function getSession(sessionId: string): SessionData | null {
   try {
      const sessions = getStoredSessions();
      const session = sessions[sessionId];

      if (!session) return null;

      // Check expiry
      if (session.expiresAt && session.expiresAt < Date.now()) {
         deleteSession(sessionId);
         return null;
      }

      return session;
   } catch (error) {
      console.warn("[Session] Failed to get session:", error);
      return null;
   }
}

/**
 * Delete a session from localStorage
 */
export function deleteSession(sessionId: string): void {
   try {
      const sessions = getStoredSessions();
      delete sessions[sessionId];
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
   } catch (error) {
      console.warn("[Session] Failed to delete session:", error);
   }
}

/**
 * Get all stored sessions
 */
function getStoredSessions(): Record<string, SessionData & { expiresAt?: number }> {
   try {
      const raw = localStorage.getItem(SESSION_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
   } catch {
      return {};
   }
}

/**
 * Clean up expired sessions
 */
export function cleanupExpiredSessions(): void {
   try {
      const sessions = getStoredSessions();
      const now = Date.now();
      let modified = false;

      for (const sessionId of Object.keys(sessions)) {
         if (sessions[sessionId].expiresAt && sessions[sessionId].expiresAt < now) {
            delete sessions[sessionId];
            modified = true;
         }
      }

      if (modified) {
         localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
      }
   } catch (error) {
      console.warn("[Session] Failed to cleanup sessions:", error);
   }
}
