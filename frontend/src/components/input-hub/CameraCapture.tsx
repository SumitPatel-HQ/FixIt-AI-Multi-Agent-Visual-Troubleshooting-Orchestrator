'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';

interface CameraCaptureProps {
   onCapture: (file: File) => void;
   onCancel: () => void;
}

export function CameraCapture({ onCapture, onCancel }: CameraCaptureProps) {
   const videoRef = useRef<HTMLVideoElement>(null);
   const canvasRef = useRef<HTMLCanvasElement>(null);
   const streamRef = useRef<MediaStream | null>(null);

   const [isStreaming, setIsStreaming] = useState(false);
   const [capturedImage, setCapturedImage] = useState<string | null>(null);
   const [error, setError] = useState<string | null>(null);
   const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');

   // Multi-call lock to prevent parallel initialization (fixes NotReadableError in Strict Mode)
   const startingRef = useRef(false);

   const startCamera = useCallback(async function startCameraFn(retryCount = 0): Promise<void> {
      // Don't start if we're already trying or already streaming
      if (startingRef.current) return;

      try {
         startingRef.current = true;
         setError(null);

         // Helper to try getting stream with fallback
         const getStream = async () => {
            // Try HD with specific facing mode first
            try {
               return await navigator.mediaDevices.getUserMedia({
                  video: {
                     facingMode,
                     width: { ideal: 1280 },
                     height: { ideal: 720 }
                  }
               });
            } catch (e) {
               console.warn('Constraint-based access failed, retrying generic video...', e);
               // Fallback: Just get any video stream
               return await navigator.mediaDevices.getUserMedia({ video: true });
            }
         };

         const stream = await getStream();

         // Check if we're still mounted and have a video ref
         if (videoRef.current) {
            videoRef.current.srcObject = stream;
            streamRef.current = stream;
            setIsStreaming(true);
            startingRef.current = false; // Successfully started
         } else {
            // Clean up immediately if component unmounted mid-stream initialization
            stream.getTracks().forEach(track => track.stop());
            startingRef.current = false;
         }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
         startingRef.current = false; // Release lock even on failure
         console.error('Camera access error:', err);

         // Retry logic: Wait longer if hardware is still locked
         if ((err?.name === 'NotReadableError' || err?.message?.includes('Could not start video source')) && retryCount < 2) {
            console.log(`Resource busy, retrying in 1.5s... (Attempt ${retryCount + 1})`);
            await new Promise(resolve => setTimeout(resolve, 1500));
            return startCameraFn(retryCount + 1);
         }

         let message = 'Camera access denied. Please enable camera permissions.';
         if (err?.name === 'NotReadableError' || err?.message?.includes('Could not start video source')) {
            message = 'Camera is busy. Please close other camera apps and refresh.';
         } else if (err?.name === 'NotAllowedError') {
            message = 'Camera permission was blocked.';
         } else if (err?.name === 'NotFoundError') {
            message = 'No camera found on this device.';
         }

         setError(message);
      }
   }, [facingMode]);

   const stopCamera = useCallback(() => {
      startingRef.current = false;
      if (streamRef.current) {
         streamRef.current.getTracks().forEach(track => {
            track.stop();
            console.log('Camera track stopped');
         });
         streamRef.current = null;
      }
      if (videoRef.current) {
         videoRef.current.srcObject = null;
      }
      setIsStreaming(false);
   }, []);

   const capturePhoto = useCallback(() => {
      if (videoRef.current && canvasRef.current) {
         const video = videoRef.current;
         const canvas = canvasRef.current;

         canvas.width = video.videoWidth;
         canvas.height = video.videoHeight;

         const ctx = canvas.getContext('2d');
         if (ctx) {
            ctx.drawImage(video, 0, 0);
            const imageData = canvas.toDataURL('image/jpeg', 0.9);
            setCapturedImage(imageData);
            stopCamera();
         }
      }
   }, [stopCamera]);

   const handleRetake = useCallback(() => {
      setCapturedImage(null);
      startCamera();
   }, [startCamera]);

   const handleUsePhoto = useCallback(() => {
      if (capturedImage && canvasRef.current) {
         canvasRef.current.toBlob((blob) => {
            if (blob) {
               const file = new File([blob], `camera-capture-${Date.now()}.jpg`, {
                  type: 'image/jpeg'
               });
               onCapture(file);
               stopCamera();
            }
         }, 'image/jpeg', 0.9);
      }
   }, [capturedImage, onCapture, stopCamera]);

   const switchCamera = useCallback(() => {
      stopCamera();
      setFacingMode(prev => prev === 'user' ? 'environment' : 'user');
   }, [stopCamera]);

   // Improved mount effect with strictly managed cleanup
   useEffect(() => {
      let isActive = true;
      const initialWait = setTimeout(() => {
         if (isActive) startCamera();
      }, 300);

      return () => {
         isActive = false;
         clearTimeout(initialWait);
         stopCamera();
      };
   }, [startCamera, stopCamera]);

   if (error) {
      return (
         <div className="space-y-4">
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
               <svg className="w-12 h-12 text-red-500 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
               </svg>
               <p className="text-red-400 font-medium">{error}</p>
            </div>
            <div className="flex gap-3">
               <Button onClick={() => startCamera(0)} variant="outline" className="flex-1">
                  Try Again
               </Button>
               <Button onClick={onCancel} variant="secondary" className="flex-1">
                  Cancel
               </Button>
            </div>
         </div>
      );
   }

   return (
      <div className="space-y-4">
         {/* Camera Preview / Captured Image */}
         <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
            {capturedImage ? (
               // eslint-disable-next-line @next/next/no-img-element
               <img src={capturedImage} alt="Captured" className="w-full h-full object-contain" />
            ) : (
               <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
               />
            )}

            {/* Camera Controls Overlay */}
            {isStreaming && !capturedImage && (
               <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 to-transparent">
                  <div className="flex items-center justify-between max-w-md mx-auto">
                     {/* Switch Camera Button */}
                     <button
                        onClick={switchCamera}
                        className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center hover:bg-white/30 transition-colors"
                        aria-label="Switch camera"
                     >
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                     </button>

                     {/* Capture Button */}
                     <button
                        onClick={capturePhoto}
                        className="w-20 h-20 rounded-full bg-white border-4 border-white/30 hover:scale-105 transition-transform active:scale-95 shutter-animation"
                        aria-label="Capture photo"
                     >
                        <div className="w-full h-full rounded-full bg-white" />
                     </button>

                     {/* Cancel Button */}
                     <button
                        onClick={onCancel}
                        className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center hover:bg-white/30 transition-colors"
                        aria-label="Cancel"
                     >
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                     </button>
                  </div>
               </div>
            )}
         </div>

         {/* Captured Image Actions */}
         {capturedImage && (
            <div className="flex gap-3">
               <Button onClick={handleRetake} variant="outline" className="flex-1">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Retake
               </Button>
               <Button onClick={handleUsePhoto} className="flex-1">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Use This Photo
               </Button>
            </div>
         )}

         {/* Hidden canvas for image capture */}
         <canvas ref={canvasRef} className="hidden" />

         <style jsx>{`
        @keyframes shutter {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(0.95); }
        }
        .shutter-animation:active {
          animation: shutter 0.3s ease;
        }
      `}</style>
      </div>
   );
}
