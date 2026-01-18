'use client';

import { useState, useRef, useEffect } from 'react';
import {
  X,
  Image as ImageIcon,
  Loader2,
  Send,
  Calendar,
  Megaphone,
  FileText,
  Plus,
  Trash2
} from 'lucide-react';
import { createCommunityPost, getCommunityEvents } from '@/lib/api';
import toast from 'react-hot-toast';

export default function CreatePostModal({
  isOpen,
  onClose,
  communityId,
  isOrganizer = false,
  onPostCreated
}) {
  const [content, setContent] = useState('');
  const [postType, setPostType] = useState('general');
  const [relatedEventId, setRelatedEventId] = useState('');
  const [photos, setPhotos] = useState([]);
  const [photoPreview, setPhotoPreview] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [events, setEvents] = useState([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    if (isOpen && postType === 'event_recap' && events.length === 0) {
      loadEvents();
    }
  }, [isOpen, postType]);

  const loadEvents = async () => {
    try {
      setIsLoadingEvents(true);
      const response = await getCommunityEvents(communityId, 0, 50, 'completed');
      if (response.success) {
        setEvents(response.events || []);
      }
    } catch (error) {
      console.error('Error loading events:', error);
    } finally {
      setIsLoadingEvents(false);
    }
  };

  const handlePhotoSelect = (e) => {
    const files = Array.from(e.target.files || []);

    if (photos.length + files.length > 5) {
      toast.error('Maximum 5 photos allowed');
      return;
    }

    const validFiles = files.filter(file => {
      if (!file.type.startsWith('image/')) {
        toast.error(`${file.name} is not an image`);
        return false;
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error(`${file.name} is too large (max 5MB)`);
        return false;
      }
      return true;
    });

    setPhotos(prev => [...prev, ...validFiles]);

    // Create previews
    validFiles.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removePhoto = (index) => {
    setPhotos(prev => prev.filter((_, i) => i !== index));
    setPhotoPreview(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!content.trim() || content.length < 10) {
      toast.error('Post content must be at least 10 characters');
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await createCommunityPost(
        communityId,
        content,
        postType,
        relatedEventId || null,
        photos
      );

      if (response.success) {
        toast.success('Post created!');
        resetForm();
        onClose();
        if (onPostCreated) onPostCreated();
      } else {
        toast.error(response.message || 'Failed to create post');
      }
    } catch (error) {
      console.error('Error creating post:', error);
      toast.error(error.response?.data?.detail || 'Failed to create post');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setContent('');
    setPostType('general');
    setRelatedEventId('');
    setPhotos([]);
    setPhotoPreview([]);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <h3 className="font-bold text-lg text-gray-900">Create Post</h3>
          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* Post Type Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Post Type</label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setPostType('general')}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  postType === 'general'
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <FileText className="w-4 h-4" />
                General
              </button>

              {isOrganizer && (
                <button
                  onClick={() => setPostType('announcement')}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition ${
                    postType === 'announcement'
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                  }`}
                >
                  <Megaphone className="w-4 h-4" />
                  Announcement
                </button>
              )}

              <button
                onClick={() => setPostType('event_recap')}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  postType === 'event_recap'
                    ? 'bg-green-600 text-white'
                    : 'bg-green-50 text-green-700 hover:bg-green-100'
                }`}
              >
                <Calendar className="w-4 h-4" />
                Event Recap
              </button>
            </div>
          </div>

          {/* Event Selection for Event Recap */}
          {postType === 'event_recap' && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Related Event</label>
              {isLoadingEvents ? (
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading events...
                </div>
              ) : events.length === 0 ? (
                <p className="text-sm text-gray-500">No completed events found</p>
              ) : (
                <select
                  value={relatedEventId}
                  onChange={(e) => setRelatedEventId(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Select an event</option>
                  {events.map(event => (
                    <option key={event.event_id} value={event.event_id}>
                      {event.title}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* Content */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What's on your mind?"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={5}
              maxLength={5000}
            />
            <div className="flex justify-between items-center mt-1">
              <p className="text-xs text-gray-500">Minimum 10 characters</p>
              <p className="text-xs text-gray-500">{content.length}/5000</p>
            </div>
          </div>

          {/* Photo Upload */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Photos (max 5)
            </label>

            {/* Preview Grid */}
            {photoPreview.length > 0 && (
              <div className="grid grid-cols-3 gap-2 mb-3">
                {photoPreview.map((preview, index) => (
                  <div key={index} className="relative aspect-square rounded-lg overflow-hidden">
                    <img
                      src={preview}
                      alt={`Preview ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                    <button
                      onClick={() => removePhoto(index)}
                      className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add Photo Button */}
            {photos.length < 5 && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={handlePhotoSelect}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-blue-400 hover:text-blue-600 transition w-full justify-center"
                >
                  <ImageIcon className="w-5 h-5" />
                  Add Photos
                </button>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-200 flex gap-3 flex-shrink-0">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || content.length < 10}
            className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Posting...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Post
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
