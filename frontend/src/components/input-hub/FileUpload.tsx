'use client';

import { useCallback, useState } from 'react';
import { Button } from '@/components/ui/button';

interface FileUploadProps {
   onFileSelect: (file: File) => void;
   selectedFile: File | null;
   onRemove: () => void;
}

export function FileUpload({ onFileSelect, selectedFile, onRemove }: FileUploadProps) {
   const [isDragging, setIsDragging] = useState(false);
   const [error, setError] = useState<string | null>(null);

   const validateFile = (file: File): boolean => {
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'video/mp4', 'video/quicktime'];
      const maxSize = 200 * 1024 * 1024; // 200MB

      if (!validTypes.includes(file.type)) {
         setError('Please upload a valid image (JPG, PNG) or video (MP4, MOV) file');
         return false;
      }

      if (file.size > maxSize) {
         setError('File size must be less than 200MB');
         return false;
      }

      setError(null);
      return true;
   };

   const handleFileChange = useCallback((file: File) => {
      if (validateFile(file)) {
         onFileSelect(file);
      }
   }, [onFileSelect]);

   const handleDrop = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) {
         handleFileChange(file);
      }
   }, [handleFileChange]);

   const handleDragOver = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
   }, []);

   const handleDragLeave = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
   }, []);

   const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
         handleFileChange(file);
      }
   }, [handleFileChange]);

   const formatFileSize = (bytes: number): string => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
   };

   if (selectedFile) {
      const isImage = selectedFile.type.startsWith('image/');
      const previewUrl = URL.createObjectURL(selectedFile);

      return (
         <div className="space-y-4">
            {/* File Preview */}
            <div className="relative bg-secondary/50 border border-border rounded-xl overflow-hidden">
               {isImage ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                     src={previewUrl}
                     alt="Preview"
                     className="w-full h-64 object-contain"
                  />
               ) : (
                  <video
                     src={previewUrl}
                     className="w-full h-64 object-contain"
                     controls={false}
                  />
               )}

               {/* Remove button overlay */}
               <button
                  onClick={onRemove}
                  className="absolute top-3 right-3 w-10 h-10 rounded-full bg-red-500/90 backdrop-blur-sm hover:bg-red-600 transition-colors flex items-center justify-center group"
                  aria-label="Remove file"
               >
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
               </button>
            </div>

            {/* File Info */}
            <div className="flex items-center gap-3 p-4 bg-secondary/30 border border-border rounded-xl">
               <div className="w-12 h-12 rounded-lg bg-accent/20 flex items-center justify-center flex-shrink-0">
                  {isImage ? (
                     <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                     </svg>
                  ) : (
                     <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                     </svg>
                  )}
               </div>
               <div className="flex-1 min-w-0">
                  <p className="font-medium text-foreground truncate">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">{formatFileSize(selectedFile.size)}</p>
               </div>
               <Button onClick={onRemove} variant="ghost" size="sm">
                  Change
               </Button>
            </div>
         </div>
      );
   }

   return (
      <div className="flex-1 flex flex-col h-full">
         {/* Drop Zone */}
         <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`
               relative border border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer flex-1 flex flex-col justify-center items-center
               ${isDragging
                  ? 'border-accent bg-accent/5'
                  : 'border-border/60 hover:border-accent/50 hover:bg-secondary/20'
               }
            `}
         >
            <input
               type="file"
               accept="image/jpeg,image/jpg,image/png,video/mp4,video/quicktime"
               onChange={handleInputChange}
               className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
               aria-label="Upload Image"
            />

            <div className="space-y-3 pointer-events-none">
               {/* Upload Icon */}
               <div className={`w-12 h-12 rounded-xl mx-auto flex items-center justify-center transition-colors ${isDragging ? 'bg-accent/20' : 'bg-secondary/40'
                  }`}>
                  <svg
                     className={`w-6 h-6 transition-colors ${isDragging ? 'text-accent' : 'text-muted-foreground'}`}
                     fill="none"
                     stroke="currentColor"
                     viewBox="0 0 24 24"
                  >
                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
               </div>

               {/* Upload Text */}
               <div>
                  <p className="font-medium text-foreground">
                     {isDragging ? 'Drop it here' : 'Click or drag image here'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                     Supports JPG, PNG, (Max 200MB)
                  </p>
               </div>
            </div>
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
      </div>
   );
}
