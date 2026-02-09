// this is search box in result page

// "use client";

// import { useState, useRef, useEffect } from "react";
// import { motion, AnimatePresence } from "framer-motion";
// import {
//    Mic,
//    MapPin,
//    Camera,
//    BookOpen,
//    Save,
//    Loader2,
//    ArrowUp,
//    Paperclip,
//    X,
// } from "lucide-react";
// import { Button } from "@/components/ui/button";
// import { CameraCapture } from "@/components/input-hub/CameraCapture";

// interface FollowUpInputProps {
//    isLoading?: boolean;
//    onSubmit: (query: string) => void;
//    sessionId: string;
// }

// const QUICK_ACTIONS = [
//    { icon: <MapPin className="w-4 h-4" />, label: "Locate another part", query: "Can you locate another component?" },
//    { icon: <Camera className="w-4 h-4" />, label: "Different angle", query: "What other angles would help with this diagnosis?" },
//    { icon: <BookOpen className="w-4 h-4" />, label: "Explain more", query: "Can you explain this in more detail?" },
//    { icon: <Save className="w-4 h-4" />, label: "Save guide", query: "Save this troubleshooting guide" },
// ];

// export function FollowUpInput({ isLoading, onSubmit, sessionId }: FollowUpInputProps) {
//    const [inputValue, setInputValue] = useState("");
//    const [isRecording, setIsRecording] = useState(false);
//    const [isListening, setIsListening] = useState(false);
//    const inputRef = useRef<HTMLInputElement>(null);
//    // eslint-disable-next-line @typescript-eslint/no-explicit-any
//    const recognitionRef = useRef<any>(null);

//    const [showCamera, setShowCamera] = useState(false);
//    const [attachment, setAttachment] = useState<string | null>(null);
//    const fileInputRef = useRef<HTMLInputElement>(null);

//    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
//       const file = e.target.files?.[0];
//       if (file) {
//          const url = URL.createObjectURL(file);
//          setAttachment(url);
//       }
//    };

//    const handleCameraCapture = (file: File) => {
//       const url = URL.createObjectURL(file);
//       setAttachment(url);
//       setShowCamera(false);
//    };

//    const handleRemoveAttachment = () => {
//       setAttachment(null);
//       if (fileInputRef.current) fileInputRef.current.value = '';
//    };

//    // Initialize Speech Recognition
//    useEffect(() => {
//       if (typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)) {
//          // eslint-disable-next-line @typescript-eslint/no-explicit-any
//          const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
//          recognitionRef.current = new SpeechRecognitionAPI();
//          recognitionRef.current.continuous = false;
//          recognitionRef.current.interimResults = true;
//          recognitionRef.current.lang = "en-US";

//          // eslint-disable-next-line @typescript-eslint/no-explicit-any
//          recognitionRef.current.onresult = (event: any) => {
//             const transcript = Array.from(event.results)
//                // eslint-disable-next-line @typescript-eslint/no-explicit-any
//                .map((result: any) => result[0].transcript)
//                .join("");
//             setInputValue(transcript);
//          };

//          recognitionRef.current.onend = () => {
//             setIsRecording(false);
//             setIsListening(false);
//          };

//          recognitionRef.current.onerror = () => {
//             setIsRecording(false);
//             setIsListening(false);
//          };
//       }

//       return () => {
//          if (recognitionRef.current) {
//             recognitionRef.current.stop();
//          }
//       };
//    }, []);

//    const handleVoiceInput = () => {
//       if (!recognitionRef.current) return;

//       if (isRecording) {
//          recognitionRef.current.stop();
//          setIsRecording(false);
//          setIsListening(false);
//       } else {
//          recognitionRef.current.start();
//          setIsRecording(true);
//          setIsListening(true);
//       }
//    };

//    const handleSubmit = () => {
//       if ((!inputValue.trim() && !attachment) || isLoading) return;
//       onSubmit(inputValue.trim()); // You might want to pass the attachment here too
//       setInputValue("");
//       setAttachment(null); // Clear attachment after submission
//       if (fileInputRef.current) fileInputRef.current.value = '';
//    };

//    const handleKeyDown = (e: React.KeyboardEvent) => {
//       if (e.key === "Enter" && !e.shiftKey) {
//          e.preventDefault();
//          handleSubmit();
//       }
//    };

//    const handleActionClick = (query: string) => {
//       setInputValue(query);
//       inputRef.current?.focus();
//    };

//    const hasVoiceSupport =
//       typeof window !== "undefined" &&
//       ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

//    return (
//       <div className={`sticky bottom-0 bg-gradient-to-t from-background via-background/80 to-transparent pt-6 pb-4 px-4 ${showCamera ? "z-[100]" : "z-40"}`}>
//          {/* Live Camera Modal */}
//          <AnimatePresence>
//             {showCamera && (
//                <motion.div
//                   initial={{ opacity: 0 }}
//                   animate={{ opacity: 1 }}
//                   exit={{ opacity: 0 }}
//                   className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
//                >
//                   <motion.div
//                      initial={{ scale: 0.9, y: 20 }}
//                      animate={{ scale: 1, y: 0 }}
//                      exit={{ scale: 0.9, y: 20 }}
//                      className="w-full max-w-2xl bg-[#1a1a1a] rounded-3xl border border-white/10 p-6 shadow-2xl"
//                   >
//                      <div className="flex items-center justify-between mb-6">
//                         <h2 className="text-xl font-semibold text-white">Capture Photo</h2>
//                         <button
//                            onClick={() => setShowCamera(false)}
//                            className="p-2 hover:bg-white/10 rounded-full transition-colors"
//                         >
//                            <X className="w-5 h-5 text-white/60" />
//                         </button>
//                      </div>
//                      <CameraCapture
//                         onCapture={handleCameraCapture}
//                         onCancel={() => setShowCamera(false)}
//                      />
//                   </motion.div>
//                </motion.div>
//             )}
//          </AnimatePresence>

//          <motion.div
//             initial={{ opacity: 0, y: 20 }}
//             animate={{ opacity: 1, y: 0 }}
//             transition={{ delay: 0.2 }}
//             className="max-w-xl mx-auto w-full"
//          >
//             <div className="relative group plus-menu-container">
//                {/* Hidden File Input */}
//                <input
//                   type="file"
//                   ref={fileInputRef}
//                   className="hidden"
//                   accept="image/*"
//                   onChange={handleFileSelect}
//                />

//                {/* Main Input Container */}
//                <div className={`
//                    relative flex transition-all duration-300
//                    bg-[#1a1a1a]/80 backdrop-blur-xl border border-white/10
//                    shadow-2xl shadow-black/50 p-1.5
//                    ${attachment ? "rounded-[2rem] flex-col pt-4" : "rounded-full items-center pl-2"}
//                    ${isRecording ? "border-red-500/30 ring-1 ring-red-500/20" : "hover:border-white/20 hover:bg-[#202020]/90"}
//                    group-focus-within:border-accent/50 group-focus-within:ring-1 group-focus-within:ring-accent/20
//                 `}>
//                   {/* Attachment Row */}
//                   {attachment && (
//                      <div className="px-2.5 mb-3">
//                         <div className="relative group/image inline-block">
//                            <div className="relative w-16 h-16 rounded-xl overflow-hidden border border-white/10 shadow-lg bg-black/20">
//                               <img src={attachment} alt="Preview" className="w-full h-full object-cover" />
//                            </div>
//                            <button
//                               onClick={handleRemoveAttachment}
//                               className="absolute -top-2 -right-2 w-5 h-5 bg-white text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform z-10"
//                            >
//                               <X className="w-3 h-3" strokeWidth={3} />
//                            </button>
//                         </div>
//                      </div>
//                   )}

//                   {/* Main Action Row */}
//                   <div className="flex items-center w-full gap-1 pl-1">
//                      {/* Left Actions */}
//                      <div className="flex items-center gap-0.5">
//                         <button
//                            onClick={() => setShowCamera(true)}
//                            className="p-2 rounded-full text-white/40 hover:text-white hover:bg-white/10 transition-all"
//                            title="Take Photo"
//                         >
//                            <Camera className="w-4 h-4" />
//                         </button>
//                         <button
//                            onClick={() => fileInputRef.current?.click()}
//                            className="p-2 rounded-full text-white/40 hover:text-white hover:bg-white/10 transition-all"
//                            title="Upload Image"
//                         >
//                            <Paperclip className="w-4 h-4" />
//                         </button>
//                      </div>

//                      {/* Input Area */}
//                      <div className="flex-1 min-w-0">
//                         <input
//                            ref={inputRef}
//                            type="text"
//                            value={inputValue}
//                            onChange={(e) => setInputValue(e.target.value)}
//                            onKeyDown={handleKeyDown}
//                            placeholder={attachment ? "Describe the Problem..." : "Ask anything..."}
//                            disabled={isLoading}
//                            className="w-full bg-transparent border-none outline-none text-[14px] font-medium text-white placeholder-white/40 placeholder:font-normal h-9 px-1"
//                            autoComplete="off"
//                         />
//                      </div>

//                      {/* Right Actions */}
//                      <div className="flex items-center gap-1 pr-0.5">
//                         {/* Voice Input */}
//                         <AnimatePresence mode="wait">
//                            {isRecording ? (
//                               <motion.div
//                                  initial={{ opacity: 0, scale: 0.8 }}
//                                  animate={{ opacity: 1, scale: 1 }}
//                                  exit={{ opacity: 0, scale: 0.8 }}
//                                  className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20"
//                               >
//                                  <div className="flex gap-0.5">
//                                     {[1, 2, 3].map((i) => (
//                                        <motion.div
//                                           key={i}
//                                           animate={{ height: [4, 12, 4] }}
//                                           transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.1 }}
//                                           className="w-0.5 bg-red-500 rounded-full"
//                                        />
//                                     ))}
//                                  </div>
//                                  <button
//                                     onClick={handleVoiceInput}
//                                     className="text-xs font-semibold text-red-400 hover:text-red-300 transition-colors"
//                                  >
//                                     Stop
//                                  </button>
//                               </motion.div>
//                            ) : (
//                               hasVoiceSupport && (
//                                  <button
//                                     onClick={handleVoiceInput}
//                                     className="p-2 rounded-full text-white/40 hover:text-white hover:bg-white/10 transition-all"
//                                     title="Voice Input"
//                                  >
//                                     <Mic className="w-4 h-4" />
//                                  </button>
//                               )
//                            )}
//                         </AnimatePresence>

//                         {/* Send Button */}
//                         <button
//                            onClick={handleSubmit}
//                            disabled={(!inputValue.trim() && !attachment) || isLoading}
//                            className={`
//                                p-2 rounded-full flex items-center justify-center transition-all duration-200
//                                ${(inputValue.trim() || attachment) && !isLoading
//                                  ? "bg-white text-black hover:bg-white/90 scale-100 opacity-100 shadow-lg shadow-white/10"
//                                  : "bg-white/5 text-white/20 scale-95 opacity-50 cursor-not-allowed"
//                               }
//                             `}
//                         >
//                            {isLoading ? (
//                               <Loader2 className="w-4 h-4 animate-spin" />
//                            ) : (
//                               <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
//                            )}
//                         </button>
//                      </div>
//                   </div>
//                </div>
//             </div>

//             {/* Quick Actions - Floating Pills */}
//             <div className="flex items-center justify-center gap-2 mt-3 px-4 overflow-x-auto pb-1 scrollbar-hide mask-gradient">
//                {QUICK_ACTIONS.map((action, index) => (
//                   <motion.button
//                      key={action.label}
//                      initial={{ opacity: 0, y: 10 }}
//                      animate={{ opacity: 1, y: 0 }}
//                      transition={{ delay: 0.4 + index * 0.05 }}
//                      onClick={() => handleActionClick(action.query)}
//                      disabled={isLoading}
//                      className={`
//                         flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-full
//                         bg-white/5 border border-white/5 backdrop-blur-sm
//                         text-[12px] font-medium text-white/60
//                         hover:bg-white/10 hover:border-white/10 hover:text-white hover:scale-105
//                         active:scale-95 transition-all duration-200
//                         disabled:opacity-50 disabled:cursor-not-allowed
//                      `}
//                   >
//                      <span className="opacity-70">{action.icon}</span>
//                      <span>{action.label}</span>
//                   </motion.button>
//                ))}
//             </div>
//          </motion.div>
//       </div>
//    );
// }


