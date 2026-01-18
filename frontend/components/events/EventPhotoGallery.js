'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Camera,
  X,
  Upload,
  Loader2,
  Trash2,
  EyeOff,
  Eye,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
  ZoomIn
} from 'lucide-react';
import { uploadEventPhoto, getEventPhotos, deleteEventPhoto, togglePhotoVisibility } from '@/lib/api';
import toast from 'react-hot-toast';

export default function EventPhotoGallery({
  eventId,
  isOrganizer = false,
  canUpload = false,
  onPhotoCountChange
}) {
  const [photos, setPhotos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [uploadCaption, setUploadCaption] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const fileInputRef = useRef(null);

  const getBackendBaseUrl = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    return apiUrl.replace('/api/v1', '');
  };

  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith('http')) return path;
    return `${getBackendBaseUrl()}${path}`;
  };

  useEffect(() => {
    fetchPhotos(true);
  }, [eventId]);

  const fetchPhotos = async (reset = false) => {
    try {
      if (reset) setIsLoading(true);
      const currentPage = reset ? 0 : page;

      const response = await getEventPhotos(eventId, currentPage * 12, 12, isOrganizer);

      if (response.success) {
        const newPhotos = response.photos || [];
        if (reset) {
          setPhotos(newPhotos);
          setPage(1);
        } else {
          setPhotos(prev => [...prev, ...newPhotos]);
          setPage(prev => prev + 1);
        }
        setTotal(response.total);
        setHasMore(newPhotos.length === 12);

        if (onPhotoCountChange) {
          onPhotoCountChange(response.total);
        }
      }
    } catch (error) {
      console.error('Error fetching photos:', error);
      toast.error('Failed to load photos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image size must be less than 5MB');
      return;
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setShowUploadModal(true);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      const response = await uploadEventPhoto(eventId, selectedFile, uploadCaption);

      if (response.success) {
        toast.success('Photo uploaded successfully!');
        setShowUploadModal(false);
        setSelectedFile(null);
        setPreviewUrl(null);
        setUploadCaption('');
        fetchPhotos(true);
      } else {
        toast.error(response.message || 'Failed to upload photo');
      }
    } catch (error) {
      console.error('Error uploading photo:', error);
      toast.error(error.response?.data?.detail || 'Failed to upload photo');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (photoId) => {
    if (!confirm('Are you sure you want to delete this photo?')) return;

    try {
      const response = await deleteEventPhoto(eventId, photoId);
      if (response.success) {
        toast.success('Photo deleted');
        setPhotos(prev => prev.filter(p => p.photo_id !== photoId));
        setTotal(prev => prev - 1);
        setSelectedPhoto(null);
      }
    } catch (error) {
      console.error('Error deleting photo:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete photo');
    }
  };

  const handleToggleVisibility = async (photoId, currentlyHidden) => {
    try {
      const response = await togglePhotoVisibility(eventId, photoId, !currentlyHidden);
      if (response.success) {
        toast.success(currentlyHidden ? 'Photo is now visible' : 'Photo hidden');
        setPhotos(prev =>
          prev.map(p =>
            p.photo_id === photoId ? { ...p, is_hidden: !currentlyHidden } : p
          )
        );
      }
    } catch (error) {
      console.error('Error toggling visibility:', error);
      toast.error('Failed to update photo');
    }
  };

  const openLightbox = (photo, index) => {
    setSelectedPhoto(photo);
    setSelectedIndex(index);
  };

  const closeLightbox = () => {
    setSelectedPhoto(null);
  };

  const navigateLightbox = (direction) => {
    const newIndex = selectedIndex + direction;
    if (newIndex >= 0 && newIndex < photos.length) {
      setSelectedIndex(newIndex);
      setSelectedPhoto(photos[newIndex]);
    }
  };

  const cancelUpload = () => {
    setShowUploadModal(false);
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadCaption('');
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
        <p className="text-gray-600">Loading photos...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Camera className="w-5 h-5 text-blue-600" />
          <h3 className="font-bold text-gray-900">Event Photos</h3>
          <span className="text-sm text-gray-500">({total})</span>
        </div>

        {canUpload && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
            >
              <Upload className="w-4 h-4" />
              Upload Photo
            </button>
          </>
        )}
      </div>

      {/* Photo Grid */}
      {photos.length === 0 ? (
        <div className="p-8 text-center">
          <ImageIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h4 className="text-lg font-semibold text-gray-900 mb-2">No Photos Yet</h4>
          <p className="text-gray-600 mb-4">
            {canUpload
              ? 'Be the first to share a memory from this event!'
              : 'Photos will appear here once attendees start sharing.'}
          </p>
          {canUpload && (
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
            >
              <Camera className="w-4 h-4" />
              Add Photo
            </button>
          )}
        </div>
      ) : (
        <div className="p-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {photos.map((photo, index) => (
              <div
                key={photo.photo_id}
                className={`relative group aspect-square rounded-xl overflow-hidden cursor-pointer ${
                  photo.is_hidden ? 'opacity-50' : ''
                }`}
                onClick={() => openLightbox(photo, index)}
              >
                <img
                  src={getImageUrl(photo.photo_url)}
                  alt={photo.caption || 'Event photo'}
                  className="w-full h-full object-cover transition group-hover:scale-105"
                />

                {/* Overlay */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <ZoomIn className="w-8 h-8 text-white" />
                </div>

                {/* Hidden Badge */}
                {photo.is_hidden && (
                  <div className="absolute top-2 left-2 px-2 py-1 bg-red-500 text-white text-xs rounded-full flex items-center gap-1">
                    <EyeOff className="w-3 h-3" />
                    Hidden
                  </div>
                )}

                {/* User Badge */}
                <div className="absolute bottom-2 left-2 right-2">
                  <p className="text-xs text-white bg-black/50 px-2 py-1 rounded-full truncate">
                    {photo.user_name}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Load More */}
          {hasMore && (
            <button
              onClick={() => fetchPhotos()}
              className="w-full mt-4 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition font-medium"
            >
              Load More Photos
            </button>
          )}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-bold text-gray-900">Upload Photo</h3>
              <button
                onClick={cancelUpload}
                className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="p-5">
              {/* Preview */}
              {previewUrl && (
                <div className="relative aspect-video rounded-xl overflow-hidden mb-4 bg-gray-100">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-full object-contain"
                  />
                </div>
              )}

              {/* Caption */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Caption (optional)
                </label>
                <textarea
                  value={uploadCaption}
                  onChange={(e) => setUploadCaption(e.target.value)}
                  placeholder="Add a caption to your photo..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={3}
                  maxLength={500}
                />
                <p className="text-xs text-gray-500 mt-1 text-right">
                  {uploadCaption.length}/500
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={cancelUpload}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={isUploading}
                  className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Lightbox */}
      {selectedPhoto && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50">
          {/* Close Button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition"
          >
            <X className="w-6 h-6 text-white" />
          </button>

          {/* Navigation */}
          {selectedIndex > 0 && (
            <button
              onClick={() => navigateLightbox(-1)}
              className="absolute left-4 w-12 h-12 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition"
            >
              <ChevronLeft className="w-6 h-6 text-white" />
            </button>
          )}

          {selectedIndex < photos.length - 1 && (
            <button
              onClick={() => navigateLightbox(1)}
              className="absolute right-4 w-12 h-12 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition"
            >
              <ChevronRight className="w-6 h-6 text-white" />
            </button>
          )}

          {/* Image */}
          <div className="max-w-4xl max-h-[80vh] mx-4">
            <img
              src={getImageUrl(selectedPhoto.photo_url)}
              alt={selectedPhoto.caption || 'Event photo'}
              className="max-w-full max-h-[80vh] object-contain rounded-lg"
            />
          </div>

          {/* Info Bar */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-6">
            <div className="max-w-4xl mx-auto flex items-end justify-between">
              <div>
                <p className="text-white font-medium">{selectedPhoto.user_name}</p>
                {selectedPhoto.caption && (
                  <p className="text-white/80 text-sm mt-1">{selectedPhoto.caption}</p>
                )}
                <p className="text-white/60 text-xs mt-2">
                  {new Date(selectedPhoto.uploaded_at).toLocaleDateString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric'
                  })}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                {isOrganizer && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleVisibility(selectedPhoto.photo_id, selectedPhoto.is_hidden);
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm transition"
                  >
                    {selectedPhoto.is_hidden ? (
                      <>
                        <Eye className="w-4 h-4" />
                        Show
                      </>
                    ) : (
                      <>
                        <EyeOff className="w-4 h-4" />
                        Hide
                      </>
                    )}
                  </button>
                )}

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(selectedPhoto.photo_id);
                  }}
                  className="flex items-center gap-2 px-3 py-2 bg-red-500/80 hover:bg-red-500 text-white rounded-lg text-sm transition"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
