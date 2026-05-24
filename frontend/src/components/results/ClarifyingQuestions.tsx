"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { HelpCircle, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ClarifyingQuestionsProps {
   questions: string[];
   mainMessage?: string;
   onSubmit: (answer: string) => void;
   isLoading?: boolean;
}

export function ClarifyingQuestions({
   questions,
   mainMessage,
   onSubmit,
   isLoading,
}: ClarifyingQuestionsProps) {
   const [answer, setAnswer] = useState("");

   const handleSubmit = () => {
      if (answer.trim()) {
         onSubmit(answer);
      }
   };

   return (
      <motion.div
         initial={{ opacity: 0, scale: 0.95 }}
         animate={{ opacity: 1, scale: 1 }}
         className="flex items-center justify-center min-h-[400px]"
      >
         <Card className="max-w-lg w-full border-amber-500/30 bg-amber-950/10">
            <CardHeader className="text-center pb-4">
               <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center mx-auto mb-4">
                  <HelpCircle className="w-8 h-8 text-amber-400" />
               </div>
               <CardTitle className="text-xl text-white">
                  I Need More Information
               </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
               {/* Main Message */}
               {mainMessage && (
                  <p className="text-center text-white/70">{mainMessage}</p>
               )}

               {/* Questions */}
               <div className="space-y-3">
                  {questions.map((q, i) => (
                     <div key={i} className="bg-white/5 border border-white/10 p-4 rounded-xl text-white/90 leading-relaxed text-sm">
                        {q}
                     </div>
                  ))}
               </div>

               {/* Input field */}
               <div className="space-y-2">
                   <textarea
                       className="w-full bg-black/50 border border-white/20 rounded-xl p-3 text-white placeholder:text-white/30 resize-none focus:outline-none focus:ring-2 focus:ring-accent"
                       rows={3}
                       placeholder="Type your answer here..."
                       value={answer}
                       onChange={(e) => setAnswer(e.target.value)}
                       onKeyDown={(e) => {
                           if (e.key === "Enter" && !e.shiftKey) {
                               e.preventDefault();
                               handleSubmit();
                           }
                       }}
                   />
               </div>

               {/* Submit Button */}
               <Button
                  variant="default"
                  size="lg"
                  className="w-full"
                  onClick={handleSubmit}
                  disabled={!answer.trim() || isLoading}
               >
                  {isLoading ? (
                     <span className="flex items-center gap-2">
                        <motion.span
                           animate={{ rotate: 360 }}
                           transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                           className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                        />
                        Processing...
                     </span>
                  ) : (
                     <span className="flex items-center gap-2">
                        <Send className="w-4 h-4" />
                        Submit Answer
                     </span>
                  )}
               </Button>
            </CardContent>
         </Card>
      </motion.div>
   );
}
