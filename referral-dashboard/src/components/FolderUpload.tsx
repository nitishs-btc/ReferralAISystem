// Upload surface that supports drag-drop, folder selection, and file selection for referral batches.

import { useRef, useState } from 'react';
import { Upload, FolderOpen, Loader2 } from 'lucide-react';

interface FolderUploadProps {
  onUpload: (files: FileList) => void;
  isUploading: boolean;
  progress: number;
}

export default function FolderUpload({ onUpload, isUploading, progress }: FolderUploadProps) {
  const folderInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFolderSelect = () => {
    folderInputRef.current?.click();
  };

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  return (
    <div className="w-full">
      <input
        ref={folderInputRef}
        type="file"
        // Folder upload is Chrome/WebKit-specific but very convenient for medical packet drops.
        // @ts-expect-error webkitdirectory is not in types
        webkitdirectory=""
        multiple
        onChange={handleChange}
        className="hidden"
        disabled={isUploading}
      />
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.jpg,.jpeg,.png,.gif,.bmp,.tiff,.doc,.docx,.zip,.tar,.tar.gz"
        onChange={handleChange}
        className="hidden"
        disabled={isUploading}
      />

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-400 hover:bg-blue-50'}
        `}
      >
        {isUploading ? (
          <div className="space-y-4">
            <Loader2 className="w-12 h-12 mx-auto text-blue-500 animate-spin" />
            <div>
              <p className="text-lg font-medium text-gray-700">Processing Documents...</p>
              <p className="text-sm text-gray-500 mt-1">{progress}% complete</p>
            </div>
            <div className="w-full max-w-xs mx-auto bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-center gap-4">
              <FolderOpen className="w-12 h-12 text-blue-500" />
              <Upload className="w-12 h-12 text-gray-400" />
            </div>
            <div>
              <p className="text-lg font-medium text-gray-700">
                Drag & Drop files or folders here
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Supports PDF, Images, Word docs, ZIP/TAR archives
              </p>
            </div>
            <div className="flex justify-center gap-3">
              <button
                onClick={handleFolderSelect}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
              >
                <FolderOpen className="w-4 h-4" />
                Select Folder
              </button>
              <button
                onClick={handleFileSelect}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Select Files
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
