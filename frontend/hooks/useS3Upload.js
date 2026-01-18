/**
 * useS3Upload Hook
 *
 * A React hook for uploading files directly to S3 using presigned URLs.
 * This bypasses the backend for file transfer, reducing server load.
 *
 * Usage:
 * const { uploadFile, uploading, progress, error } = useS3Upload();
 * const result = await uploadFile(file, 'hazard_image');
 * // result = { s3Key, publicUrl }
 */

import { useState, useCallback } from 'react';
import api from '@/lib/api';

// Upload types supported by the backend
export const UPLOAD_TYPES = {
  HAZARD_IMAGE: 'hazard_image',
  HAZARD_VOICE: 'hazard_voice',
  PROFILE: 'profile',
  EVENT: 'event',
};

// File type validations (matching backend)
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/avif', 'image/heic', 'image/heif'];
const ALLOWED_VOICE_TYPES = ['audio/webm', 'audio/mpeg', 'audio/wav', 'audio/mp4'];

const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_VOICE_SIZE = 5 * 1024 * 1024;  // 5MB
const MAX_PROFILE_SIZE = 5 * 1024 * 1024; // 5MB

/**
 * Check if S3 storage is enabled on the backend
 */
export async function checkS3Status() {
  try {
    const response = await api.get('/uploads/status');
    return response.data;
  } catch (error) {
    console.error('Failed to check S3 status:', error);
    return { s3_enabled: false, storage_type: 'local' };
  }
}

/**
 * Custom hook for S3 file uploads
 */
export function useS3Upload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  /**
   * Validate file before upload
   */
  const validateFile = useCallback((file, uploadType) => {
    // Check if file exists
    if (!file) {
      throw new Error('No file provided');
    }

    // Determine allowed types and max size based on upload type
    let allowedTypes;
    let maxSize;

    if (uploadType === UPLOAD_TYPES.HAZARD_VOICE) {
      allowedTypes = ALLOWED_VOICE_TYPES;
      maxSize = MAX_VOICE_SIZE;
    } else if (uploadType === UPLOAD_TYPES.PROFILE) {
      allowedTypes = ALLOWED_IMAGE_TYPES;
      maxSize = MAX_PROFILE_SIZE;
    } else {
      allowedTypes = ALLOWED_IMAGE_TYPES;
      maxSize = MAX_IMAGE_SIZE;
    }

    // Validate file type
    if (!allowedTypes.includes(file.type)) {
      throw new Error(`Invalid file type: ${file.type}. Allowed: ${allowedTypes.join(', ')}`);
    }

    // Validate file size
    if (file.size > maxSize) {
      throw new Error(`File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB. Maximum: ${maxSize / 1024 / 1024}MB`);
    }

    return true;
  }, []);

  /**
   * Get presigned URL from backend
   */
  const getPresignedUrl = useCallback(async (file, uploadType, eventId = null) => {
    const payload = {
      upload_type: uploadType,
      content_type: file.type,
      filename: file.name,
      file_size: file.size,
    };

    if (eventId) {
      payload.event_id = eventId;
    }

    const response = await api.post('/uploads/presigned-url', payload);
    return response.data;
  }, []);

  /**
   * Upload file to S3 using presigned URL
   */
  const uploadToS3 = useCallback(async (presignedUrl, file, contentType) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          setProgress(percentComplete);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(true);
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload aborted'));
      });

      xhr.open('PUT', presignedUrl);
      xhr.setRequestHeader('Content-Type', contentType);
      xhr.send(file);
    });
  }, []);

  /**
   * Main upload function
   *
   * @param {File} file - The file to upload
   * @param {string} uploadType - Type of upload (from UPLOAD_TYPES)
   * @param {string} eventId - Optional event ID for event photo uploads
   * @returns {Promise<{s3Key: string, publicUrl: string}>}
   */
  const uploadFile = useCallback(async (file, uploadType, eventId = null) => {
    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      // Validate file
      validateFile(file, uploadType);

      // Get presigned URL from backend
      const presignedData = await getPresignedUrl(file, uploadType, eventId);

      // Upload to S3
      await uploadToS3(presignedData.presigned_url, file, presignedData.content_type);

      setProgress(100);

      return {
        s3Key: presignedData.s3_key,
        publicUrl: presignedData.public_url,
      };
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setUploading(false);
    }
  }, [validateFile, getPresignedUrl, uploadToS3]);

  /**
   * Upload multiple files
   *
   * @param {File[]} files - Array of files to upload
   * @param {string} uploadType - Type of upload
   * @param {string} eventId - Optional event ID
   * @returns {Promise<Array<{s3Key: string, publicUrl: string}>>}
   */
  const uploadMultiple = useCallback(async (files, uploadType, eventId = null) => {
    setUploading(true);
    setProgress(0);
    setError(null);

    const results = [];
    const totalFiles = files.length;

    try {
      for (let i = 0; i < totalFiles; i++) {
        const file = files[i];

        // Validate
        validateFile(file, uploadType);

        // Get presigned URL
        const presignedData = await getPresignedUrl(file, uploadType, eventId);

        // Upload
        await uploadToS3(presignedData.presigned_url, file, presignedData.content_type);

        results.push({
          s3Key: presignedData.s3_key,
          publicUrl: presignedData.public_url,
          filename: file.name,
        });

        // Update overall progress
        setProgress(Math.round(((i + 1) / totalFiles) * 100));
      }

      return results;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setUploading(false);
    }
  }, [validateFile, getPresignedUrl, uploadToS3]);

  /**
   * Reset the hook state
   */
  const reset = useCallback(() => {
    setUploading(false);
    setProgress(0);
    setError(null);
  }, []);

  return {
    uploadFile,
    uploadMultiple,
    uploading,
    progress,
    error,
    reset,
    UPLOAD_TYPES,
  };
}

export default useS3Upload;
