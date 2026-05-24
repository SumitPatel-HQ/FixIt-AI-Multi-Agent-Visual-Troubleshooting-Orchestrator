'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface VoiceInputProps {
   onTranscript: (text: string) => void;
   currentText: string;
}

export function VoiceInput({ onTranscript, currentText }: VoiceInputProps) {
   const [isRecording, setIsRecording] = useState(false);
   const [isProcessing, setIsProcessing] = useState(false);
   const [error, setError] = useState<string | null>(null);
   const [audioLevel, setAudioLevel] = useState(0);

   // eslint-disable-next-line @typescript-eslint/no-explicit-any
   const recognitionRef = useRef<any>(null);
   const audioContextRef = useRef<AudioContext | null>(null);
   const analyserRef = useRef<AnalyserNode | null>(null);
   const animationFrameRef = useRef<number>(null);
   const onTranscriptRef = useRef(onTranscript);
   const currentTextRef = useRef(currentText);

   // Sync refs with latest props
   useEffect(() => {
      onTranscriptRef.current = onTranscript;
      currentTextRef.current = currentText;
   }, [onTranscript, currentText]);

   // Initialize Speech Recognition once
   useEffect(() => {
      if (typeof window !== 'undefined') {
         // eslint-disable-next-line @typescript-eslint/no-explicit-any
         const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

         if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            recognition.onresult = (event: any) => {
               let finalTranscript = '';
               for (let i = event.resultIndex; i < event.results.length; i++) {
                  if (event.results[i].isFinal) {
                     finalTranscript += event.results[i][0].transcript + ' ';
                  }
               }

               if (finalTranscript) {
                  onTranscriptRef.current(currentTextRef.current + finalTranscript);
               }
            };

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            recognition.onerror = (event: any) => {
               console.error('Speech recognition error:', event.error);
               setError('Speech recognition failed. Please try again.');
               setIsRecording(false);
               setIsProcessing(false);
            };

            recognition.onend = () => {
               setIsRecording(false);
               setIsProcessing(false);
            };

            recognitionRef.current = recognition;
         }
      }

      return () => {
         if (recognitionRef.current) {
            recognitionRef.current.stop();
         }
         if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
         }
         // Safely close AudioContext
         if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close().catch(console.error);
         }
      };
   }, []); // Run only once

   // Audio visualization
   const visualizeAudio = useCallback(async () => {
      try {
         const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

         // Only create context if not already existing or closed
         if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
            audioContextRef.current = new AudioContext();
         }

         const audioContext = audioContextRef.current;
         const analyser = audioContext.createAnalyser();
         const microphone = audioContext.createMediaStreamSource(stream);

         analyser.fftSize = 256;
         microphone.connect(analyser);
         analyserRef.current = analyser;

         const dataArray = new Uint8Array(analyser.frequencyBinCount);

         const updateLevel = () => {
            if (analyserRef.current && audioContext.state !== 'closed') {
               analyserRef.current.getByteFrequencyData(dataArray);
               const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
               setAudioLevel(average / 255);
               animationFrameRef.current = requestAnimationFrame(updateLevel);
            }
         };

         updateLevel();
      } catch (err) {
         console.error('Microphone access error:', err);
      }
   }, []);

   const startRecording = useCallback(() => {
      if (!recognitionRef.current) {
         setError('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
         return;
      }

      setError(null);
      setIsRecording(true);
      setIsProcessing(false);

      try {
         recognitionRef.current.start();
         visualizeAudio();
      } catch (err) {
         console.error('Failed to start recording:', err);
         setError('Failed to start recording. Please try again.');
         setIsRecording(false);
      }
   }, [visualizeAudio]);

   const stopRecording = useCallback(() => {
      if (recognitionRef.current) {
         recognitionRef.current.stop();
      }

      if (animationFrameRef.current) {
         cancelAnimationFrame(animationFrameRef.current);
      }

      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
         audioContextRef.current.close().catch(console.error);
      }
      // audioContextRef.current = null; // Removed to allow state check in visualizeAudio

      setIsRecording(false);
      setIsProcessing(true);
      setAudioLevel(0);

      // Simulate processing delay
      setTimeout(() => setIsProcessing(false), 500);
   }, []);

   const handleToggleRecording = useCallback(() => {
      if (isRecording) {
         stopRecording();
      } else {
         startRecording();
      }
   }, [isRecording, startRecording, stopRecording]);

   return (
      <div className="space-y-6 w-full">
         {/* Microphone Button */}
         <div className="flex flex-col items-center gap-4">
            <button
               onClick={handleToggleRecording}
               disabled={isProcessing}
               className={`
            relative w-24 h-24 rounded-full transition-all duration-300
            ${isRecording
                     ? 'bg-red-500 hover:bg-red-600 scale-110'
                     : 'bg-muted hover:bg-primary/10'
                  }
            ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            disabled:opacity-50 disabled:cursor-not-allowed
            shadow-lg hover:shadow-xl
          `}
               aria-label={isRecording ? 'Stop recording' : 'Start recording'}
            >
               {/* Pulsing rings when recording */}
               {isRecording && (
                  <>
                     <div
                        className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75"
                        style={{ animationDuration: '1.5s' }}
                     />
                     <div
                        className="absolute inset-0 rounded-full bg-red-500"
                        style={{
                           transform: `scale(${1 + audioLevel * 0.3})`,
                           opacity: 0.3,
                           transition: 'transform 0.1s ease-out'
                        }}
                     />
                  </>
               )}

               {/* Icon */}
               <div className="relative z-10 flex items-center justify-center h-full">
                  {isProcessing ? (
                     <svg className="w-10 h-10 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                     </svg>
                  ) : isRecording ? (
                     <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" rx="2" />
                     </svg>
                  ) : (
                     <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                     </svg>
                  )}
               </div>
            </button>

            {/* Status Text */}
            <div className="text-center">
               <p className="text-sm font-medium text-foreground">
                  {isProcessing ? 'Transcribing...' : isRecording ? 'Recording...' : 'Tap to speak'}
               </p>
               {isRecording && (
                  <p className="text-xs text-muted-foreground mt-1">
                     Tap again to stop
                  </p>
               )}
            </div>

            {/* Waveform Visualization */}
            {isRecording && (
               <div className="flex items-center gap-1 h-12">
                  {[...Array(20)].map((_, i) => (
                     <div
                        key={i}
                        className="w-1 bg-accent rounded-full transition-all duration-100"
                        style={{
                           height: `${20 + Math.abs(Math.sin(i * 10)) * audioLevel * 60}%`,
                           opacity: 0.5 + audioLevel * 0.7
                        }}
                     />
                  ))}
               </div>
            )}
         </div>

         {/* Editable Text Area */}
         <div className="w-full">
            <textarea
               value={currentText}
               onChange={(e) => onTranscript(e.target.value)}
               placeholder="Start speaking or type here..."
               className="w-full min-h-5 p-4 bg-secondary/30 border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent/50 resize-none transition-all"
            />
         </div>

         {/* Error Message */}
         {error && (
            <div className="flex items-start gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
               <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
               </svg>
               <p className="text-sm text-red-400">{error}</p>
            </div>
         )}

         {/* Browser Support Note */}
         {/* {!recognitionRef.current && (
            <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
               <p className="text-sm text-yellow-400">
                  Voice input requires Chrome, Edge, or Safari browser.
               </p>
            </div>
         )} */}
      </div>
   );
}
