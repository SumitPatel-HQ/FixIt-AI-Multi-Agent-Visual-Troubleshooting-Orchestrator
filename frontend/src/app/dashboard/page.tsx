'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { CameraCapture } from '@/components/input-hub/CameraCapture';
import { FileUpload } from '@/components/input-hub/FileUpload';
import { VoiceInput } from '@/components/input-hub/VoiceInput';
import { InvalidQueryModal } from '@/components/ui/InvalidQueryModal';
import { QuotaExhaustedModal } from '@/components/ui/QuotaExhaustedModal';
import { useDashboard } from './dashboard-context';
import { troubleshoot, storeSession, checkHealth, cleanupExpiredSessions } from '@/lib/api';

type InputMode = 'camera' | 'upload';
type QueryMode = 'voice' | 'text';

interface DeviceHint {
   type: string;
   brand: string;
   model: string;
}

const EXAMPLE_QUERIES = [
   'Where is the RAM?',
   'How to fix paper jam?',
   'What are these LED lights?',
   'Locate the reset button',
];

const DEVICE_TYPES = [
   'Router',
   'Printer',
   'Laptop',
   'Arduino',
   'Desktop PC',
   'Smartphone',
   'Tablet',
   'Other',
];

export default function InputHubPage() {
   const router = useRouter();
   const { isMobileMenuOpen } = useDashboard();

   // Visual input state
   const [inputMode, setInputMode] = useState<InputMode>('upload');
   const [selectedFile, setSelectedFile] = useState<File | null>(null);
   const [showCamera, setShowCamera] = useState(false);

   // Query input state
   const [queryMode, setQueryMode] = useState<QueryMode>('text');
   const [queryText, setQueryText] = useState('');

   // Device hint state
   const [showDeviceHint, setShowDeviceHint] = useState(false);
   const [deviceHint, setDeviceHint] = useState<DeviceHint>({
      type: '',
      brand: '',
      model: '',
   });

   // Form state
   const [errors, setErrors] = useState<{ image?: string; query?: string }>({});
   const [isSubmitting, setIsSubmitting] = useState(false);
   const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
   
   // Invalid query modal state
   const [showInvalidQueryModal, setShowInvalidQueryModal] = useState(false);
   const [invalidQueryData, setInvalidQueryData] = useState<{
      query: string;
      deviceType: string;
      isMismatch: boolean;
      suggestions: string[];
   } | null>(null);

   // Quota exhausted modal state
   const [showQuotaModal, setShowQuotaModal] = useState(false);
   const [quotaRetryAfter, setQuotaRetryAfter] = useState<string>('tomorrow');

   // Check backend health on mount and cleanup expired sessions
   useEffect(() => {
      const checkBackend = async () => {
         const health = await checkHealth();
         setBackendStatus(health ? 'online' : 'offline');
         if (health) {
            console.log('[FixIt] Backend connected:', health);
         } else {
            console.warn('[FixIt] Backend offline - will use fallback mode');
         }
      };

      checkBackend();
      cleanupExpiredSessions();
   }, []);

   // Handlers
   const handleCameraCapture = (file: File) => {
      setSelectedFile(file);
      setShowCamera(false);
      setInputMode('upload');
      setErrors({ ...errors, image: undefined });
   };

   const handleFileSelect = (file: File) => {
      setSelectedFile(file);
      setErrors({ ...errors, image: undefined });
   };

   const handleFileRemove = () => {
      setSelectedFile(null);
   };

   const handleVoiceTranscript = (text: string) => {
      setQueryText(text);
      setErrors({ ...errors, query: undefined });
   };

   const handleExampleClick = (example: string) => {
      setQueryText(example);
      setQueryMode('text');
      setErrors({ ...errors, query: undefined });
   };

   const validateForm = (): boolean => {
      const newErrors: { image?: string; query?: string } = {};

      if (!selectedFile) {
         newErrors.image = 'Please upload an image of your device';
      }

      if (!queryText.trim()) {
         newErrors.query = 'Please describe the issue or ask a question';
      }

      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
   };

   const handleSubmit = async () => {
      if (!validateForm()) {
         return;
      }

      // Warn if backend is offline
      if (backendStatus === 'offline') {
         setErrors({
            ...errors,
            query: 'Backend server is offline. Please ensure the backend is running on port 8000.'
         });
         return;
      }

      setIsSubmitting(true);
      setErrors({});

      try {
         // Call the real backend API
         const result = await troubleshoot({
            image: selectedFile!,
            query: queryText,
            deviceHint: (deviceHint.type || deviceHint.brand || deviceHint.model)
               ? deviceHint
               : undefined,
         });

         console.log('[Dashboard] Troubleshoot result:', {
            success: result.success,
            hasResponse: !!result.response,
            responseStatus: result.response?.status,
            responseError: result.response?.error,
            responseMessage: result.response?.message,
            resultError: result.error,
         });

         if (!result.success) {
            // Check if it's a quota error
            if (result.error?.includes('quota') || 
                result.error?.includes('temporarily unavailable') ||
                result.error?.includes('free tier')) {
               console.log('[Dashboard] Quota error detected in result.error');
               setQuotaRetryAfter(result.error.includes('tomorrow') ? 'tomorrow' : 'later');
               setShowQuotaModal(true);
               return;
            }
            throw new Error(result.error || 'Failed to analyze device');
         }

         // Check if response indicates quota exhaustion (check status, message, and error fields)
         const responseStatus = result.response?.status;
         const errorMessage = result.response?.error || result.response?.message || '';
         
         console.log('[Dashboard] Checking quota in response:', { responseStatus, errorMessage });
         
         if ((responseStatus === 'error' && errorMessage.includes('quota')) ||
             errorMessage.includes('temporarily unavailable') ||
             errorMessage.includes('free tier')) {
            console.log('[Dashboard] Quota error detected in response');
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const retryAfter = (result.response as any).retry_after as string | undefined;
            setQuotaRetryAfter(retryAfter || 'tomorrow');
            setShowQuotaModal(true);
            return;
         }

         // Check if response indicates invalid query
         if (result.response?.status === 'invalid_query' || result.response?.error === 'invalid_query') {
            setInvalidQueryData({
               query: result.response.query || queryText,
               deviceType: result.response.device_type || 'device',
               isMismatch: result.response.is_mismatch || false,
               suggestions: result.response.suggestions || [],
            });
            setShowInvalidQueryModal(true);
            return;
         }

         // Store session data for the results page
         storeSession({
            sessionId: result.sessionId,
            imageUrl: result.imageUrl,
            originalQuery: result.originalQuery,
            timestamp: new Date().toISOString(),
            response: result.response,
         });

         // Navigate to results page
         router.push(`/dashboard/results?session=${result.sessionId}`);
      } catch (error) {
         console.error('Submission error:', error);
         const errorMessage = error instanceof Error
            ? error.message
            : 'Failed to submit request. Please try again.';
         
         // Check if error message indicates quota exhaustion
         if (errorMessage.includes('quota') || 
             errorMessage.includes('temporarily unavailable') ||
             errorMessage.includes('free tier')) {
            setQuotaRetryAfter('tomorrow');
            setShowQuotaModal(true);
            return;
         }
         
         setErrors({ ...errors, query: errorMessage });
      } finally {
         setIsSubmitting(false);
      }
   };

   const handleRetryQuery = () => {
      setShowInvalidQueryModal(false);
      setInvalidQueryData(null);
      setQueryText('');
      setErrors({});
      // Focus on the query input
      setTimeout(() => {
         const textarea = document.querySelector('textarea');
         if (textarea) {
            textarea.focus();
         }
      }, 100);
   };

   const handleCloseQuotaModal = () => {
      setShowQuotaModal(false);
      setErrors({});
   };

   return (
      <div className="space-y-8 max-w-8xl mx-auto">
         {/* Page Header */}
         <div className="space-y-2">
            <h1 className="text-4xl font-display font-bold text-foreground">
               Device Troubleshooting
            </h1>
            <p className="text-muted-foreground text-lg">
               Upload an image and describe your issue to get instant AI-powered assistance
            </p>
         </div>

         {/* Grid for Inputs */}
         <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Visual Input Section */}
            <div className="bg-secondary/20 backdrop-blur-sm border border-border/50 rounded-2xl p-6 flex flex-col">
               <div className="flex flex-col gap-4 mb-6">
                  <div className="flex items-center justify-between">
                     <h2 className="text-xl font-display font-semibold text-foreground">
                        Upload Device Image
                     </h2>
                     {/* Mode Toggle */}
                     <div className="flex gap-1 p-1 bg-secondary/50 rounded-lg">
                        <button
                           onClick={() => {
                              setInputMode('camera');
                              setShowCamera(true);
                           }}
                           className={`
                              px-4 py-2 rounded-md text-sm font-medium transition-all
                              ${inputMode === 'camera' && showCamera
                                 ? 'text-primary bg-primary/10 shadow-lg shadow-primary/5 border border-primary/10'
                                 : 'text-muted-foreground hover:text-primary hover:bg-primary/10'
                              }
                           `}
                        >
                           📸 Capture Live
                        </button>
                        <button
                           onClick={() => {
                              setInputMode('upload');
                              setShowCamera(false);
                           }}
                           className={`
                              px-4 py-2 rounded-md text-sm font-medium transition-all
                              ${inputMode === 'upload' && !showCamera
                                 ? 'text-primary bg-primary/10 shadow-lg shadow-primary/5 border border-primary/10'
                                 : 'text-muted-foreground hover:text-primary hover:bg-primary/10'
                              }
                           `}
                        >
                           📁 Upload File
                        </button>
                     </div>
                  </div>
               </div>

               <div className="flex-1 min-h-[300px] flex flex-col justify-center">
                  {/* Camera or Upload Component */}
                  {showCamera ? (
                     <CameraCapture
                        onCapture={handleCameraCapture}
                        onCancel={() => {
                           setShowCamera(false);
                           setInputMode('upload');
                        }}
                     />
                  ) : (
                     <FileUpload
                        onFileSelect={handleFileSelect}
                        selectedFile={selectedFile}
                        onRemove={handleFileRemove}
                     />
                  )}
               </div>

               {/* Error Message */}
               {errors.image && (
                  <p className="mt-4 text-sm text-red-400 flex items-center gap-2">
                     <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                     </svg>
                     {errors.image}
                  </p>
               )}
            </div>

            {/* Query Input Section */}
            <div className="bg-secondary/20 backdrop-blur-sm border border-border/50 rounded-2xl p-6 flex flex-col">
               <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xl font-display font-semibold text-foreground">
                     What&apos;s the issue?
                  </h2>
               </div>

               {/* Query Mode Tabs - Restored Original Style */}
               <div className="flex gap-2 border-b border-border mb-6">
                  <button
                     onClick={() => setQueryMode('voice')}
                     className={`
                        px-4 py-2 font-medium transition-all relative text-sm
                        ${queryMode === 'voice'
                           ? 'text-primary'
                           : 'text-muted-foreground hover:text-primary'
                        }
                     `}
                  >
                     Voice Input
                     {queryMode === 'voice' && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary/70" />
                     )}
                  </button>
                  <button
                     onClick={() => setQueryMode('text')}
                     className={`
                        px-4 py-2 font-medium transition-all relative text-sm
                        ${queryMode === 'text'
                           ? 'text-primary '
                           : 'text-muted-foreground hover:text-primary'
                        }
                     `}
                  >
                     Text Input
                     {queryMode === 'text' && (
                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary/70 rounded-full" />
                     )}
                  </button>
               </div>

               <div className="flex-1 flex flex-col h-full">
                  {/* Query Input Content */}
                  {queryMode === 'voice' ? (
                     <div className="flex-1 flex items-center justify-center">
                        <VoiceInput onTranscript={handleVoiceTranscript} currentText={queryText} />
                     </div>
                  ) : (
                     <div className="space-y-4 flex-1 flex flex-col">
                        <textarea
                           value={queryText}
                           onChange={(e) => {
                              setQueryText(e.target.value);
                              setErrors({ ...errors, query: undefined });
                           }}
                           placeholder="Describe the problem or ask a question..."
                           className="flex-1 w-full min-h-10 p-4 bg-secondary/30 border border-border/50 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent/50 resize-none transition-all"
                           maxLength={500}
                        />



                        {/* Example Queries */}
                        <div className="space-y-3 mt-auto">
                           <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest">Suggestions</p>
                           <div className="flex flex-wrap gap-2">
                              {EXAMPLE_QUERIES.map((example) => (
                                 <button
                                    key={example}
                                    onClick={() => handleExampleClick(example)}
                                    className="px-3 py-1.5 bg-secondary/40 border border-border/40 rounded-lg text-sm text-foreground hover:bg-accent/10 hover:border-accent/40 transition-all text-left"
                                 >
                                    {example}
                                 </button>
                              ))}
                           </div>
                        </div>
                     </div>
                  )}
               </div>

               {/* Error Message */}
               {errors.query && (
                  <p className="mt-4 text-sm text-red-400 flex items-center gap-2">
                     <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                     </svg>
                     {errors.query}
                  </p>
               )}
            </div>
         </div>


         {/* Optional Device Hint Section */}
         <div className="bg-secondary/10 backdrop-blur-sm border border-border/40 rounded-xl overflow-hidden">
            <button
               onClick={() => setShowDeviceHint(!showDeviceHint)}
               className="w-full px-6 py-3 flex items-center justify-between hover:bg-secondary/20 transition-colors"
            >
               <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                  </svg>
                  <span className="text-sm font-medium text-foreground">Advanced Options (Optional)</span>
               </div>
               <svg
                  className={`w-4 h-4 text-muted-foreground transition-transform ${showDeviceHint ? 'rotate-180' : ''
                     }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
               >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
               </svg>
            </button>

            {showDeviceHint && (
               <div className="px-6 pb-6 pt-2 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                     {/* Device Type */}
                     <div className="space-y-1.5">
                        <label className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground">
                           Device Type
                        </label>
                        <select
                           value={deviceHint.type}
                           onChange={(e) => setDeviceHint({ ...deviceHint, type: e.target.value })}
                           className="w-full px-3 py-2 bg-secondary/30 border border-border/50 rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-accent/50"
                        >
                           <option value="">Select type</option>
                           {DEVICE_TYPES.map((type) => (
                              <option key={type} value={type.toLowerCase()}>
                                 {type}
                              </option>
                           ))}
                        </select>
                     </div>

                     {/* Brand */}
                     <div className="space-y-1.5">
                        <label className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground">
                           Brand
                        </label>
                        <input
                           type="text"
                           value={deviceHint.brand}
                           onChange={(e) => setDeviceHint({ ...deviceHint, brand: e.target.value })}
                           placeholder="e.g., HP, Cisco"
                           className="w-full px-3 py-2 bg-secondary/30 border border-border/50 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent/50"
                        />
                     </div>

                     {/* Model */}
                     <div className="space-y-1.5">
                        <label className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground">
                           Model
                        </label>
                        <input
                           type="text"
                           value={deviceHint.model}
                           onChange={(e) => setDeviceHint({ ...deviceHint, model: e.target.value })}
                           placeholder="e.g., XPS 15"
                           className="w-full px-3 py-2 bg-secondary/30 border border-border/50 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent/50"
                        />
                     </div>
                  </div>
               </div>
            )}
         </div>

         {/* Submit Button */}
         <div className={cn(
            "fixed bottom-6 left-6 right-6 z-50 md:static md:p-0 md:m-0",
            isMobileMenuOpen ? "hidden md:block" : "block"
         )}>
            <Button
               onClick={handleSubmit}
               disabled={isSubmitting || !selectedFile || !queryText.trim()}
               size="lg"
               className="w-full h-14 text-base font-semibold rounded-full text-primary bg-primary/10 shadow-lg shadow-primary/5 border border-primary/10 transition-all  active:scale-95 disabled:bg-[#111111] disabled:text-muted-foreground cursor-pointer disabled:shadow-none disabled:opacity-90 hover:text-primary hover:bg-primary/10 "
            >
               {isSubmitting ? (
                  <>
                     <svg className="w-5 h-5 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                     </svg>
                     Analyzing your device...
                  </>
               ) : !selectedFile || !queryText.trim() ? (
                  'Select image and enter query'
               ) : (
                  <>
                     <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                     </svg>
                     Analyze & Troubleshoot
                  </>
               )}
            </Button>
         </div>

         {/* Invalid Query Modal */}
         {showInvalidQueryModal && invalidQueryData && (
            <InvalidQueryModal
               query={invalidQueryData.query}
               deviceType={invalidQueryData.deviceType}
               isMismatch={invalidQueryData.isMismatch}
               suggestions={invalidQueryData.suggestions}
               onRetry={handleRetryQuery}
            />
         )}

         {/* Quota Exhausted Modal */}
         {showQuotaModal && (
            <QuotaExhaustedModal
               onClose={handleCloseQuotaModal}
               retryAfter={quotaRetryAfter}
            />
         )}

      </div>
   );
}

