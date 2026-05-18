// Thin API client used by the dashboard for single-file and batch referral uploads.

import axios from 'axios';
import { ApiResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadFiles = async (
  files: FileList,
  onProgress?: (progress: number) => void
): Promise<ApiResponse> => {
  // The backend expects repeated "files" keys for batch uploads.
  const formData = new FormData();
  
  Array.from(files).forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post<ApiResponse>('/referrals/analyze-batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
};

export const uploadSingleFile = async (file: File): Promise<ApiResponse> => {
  // Kept for compatibility even though the current UI uses the batch path.
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/referrals/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
