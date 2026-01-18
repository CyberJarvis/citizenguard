'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import PageHeader from '@/components/PageHeader';
import { useNotesStore, useAnalystStore } from '@/stores/analystStore';
import {
  getAnalystNotes,
  createAnalystNote,
  updateAnalystNote,
  deleteAnalystNote
} from '@/lib/api';
import {
  FileText,
  Plus,
  Search,
  Tag,
  Pin,
  PinOff,
  Edit3,
  Trash2,
  X,
  Save,
  RefreshCw,
  ChevronDown,
  Loader2,
  Calendar,
  Clock,
  Link2,
  Filter
} from 'lucide-react';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';

const noteColors = {
  default: { bg: 'bg-white', border: 'border-gray-200', hover: 'hover:border-gray-300' },
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', hover: 'hover:border-blue-300' },
  green: { bg: 'bg-green-50', border: 'border-green-200', hover: 'hover:border-green-300' },
  amber: { bg: 'bg-amber-50', border: 'border-amber-200', hover: 'hover:border-amber-300' },
  red: { bg: 'bg-red-50', border: 'border-red-200', hover: 'hover:border-red-300' },
  purple: { bg: 'bg-purple-50', border: 'border-purple-200', hover: 'hover:border-purple-300' }
};

function NotesPageContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { addRecentNote } = useAnalystStore();
  const {
    notes,
    setNotes,
    totalNotes,
    selectedNote,
    setSelectedNote,
    isEditing,
    setEditing,
    tagFilter,
    setTagFilter,
    searchQuery,
    setSearchQuery,
    availableTags,
    setAvailableTags
  } = useNotesStore();

  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [showNewNote, setShowNewNote] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // New/Edit note form state
  const [noteForm, setNoteForm] = useState({
    title: '',
    content: '',
    tags: [],
    color: 'default',
    is_pinned: false,
    reference_type: null,
    reference_id: null
  });
  const [tagInput, setTagInput] = useState('');

  // Check authorization
  useEffect(() => {
    if (user && !['analyst', 'authority_admin'].includes(user.role)) {
      router.push('/dashboard');
    }
  }, [user, router]);

  // Fetch notes
  const fetchNotes = async () => {
    setLoading(true);
    try {
      const response = await getAnalystNotes({
        page,
        limit: pageSize,
        search: searchQuery || undefined,
        tags: tagFilter.length > 0 ? tagFilter : undefined
      });

      if (response.success) {
        setNotes(response.data.notes, response.data.total);
        setAvailableTags(response.data.available_tags || []);
      }
    } catch (error) {
      console.error('Error fetching notes:', error);
      toast.error('Failed to load notes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
  }, [page, searchQuery, tagFilter]);

  // Handle create note
  const handleCreateNote = async () => {
    if (!noteForm.title.trim()) {
      toast.error('Title is required');
      return;
    }

    try {
      const response = await createAnalystNote({
        title: noteForm.title,
        content: noteForm.content,
        tags: noteForm.tags,
        color: noteForm.color,
        is_pinned: noteForm.is_pinned,
        reference_type: noteForm.reference_type,
        reference_id: noteForm.reference_id
      });

      if (response.success) {
        toast.success('Note created successfully');
        setShowNewNote(false);
        resetForm();
        fetchNotes();
        addRecentNote(response.data);
      }
    } catch (error) {
      console.error('Error creating note:', error);
      toast.error('Failed to create note');
    }
  };

  // Handle update note
  const handleUpdateNote = async () => {
    if (!selectedNote || !noteForm.title.trim()) return;

    try {
      const response = await updateAnalystNote(selectedNote.note_id, {
        title: noteForm.title,
        content: noteForm.content,
        tags: noteForm.tags,
        color: noteForm.color,
        is_pinned: noteForm.is_pinned
      });

      if (response.success) {
        toast.success('Note updated successfully');
        setEditing(false);
        fetchNotes();
      }
    } catch (error) {
      console.error('Error updating note:', error);
      toast.error('Failed to update note');
    }
  };

  // Handle delete note
  const handleDeleteNote = async (noteId) => {
    if (!confirm('Are you sure you want to delete this note?')) return;

    try {
      const response = await deleteAnalystNote(noteId);
      if (response.success) {
        toast.success('Note deleted successfully');
        if (selectedNote?.note_id === noteId) {
          setSelectedNote(null);
        }
        fetchNotes();
      }
    } catch (error) {
      console.error('Error deleting note:', error);
      toast.error('Failed to delete note');
    }
  };

  // Handle toggle pin
  const handleTogglePin = async (note) => {
    try {
      const response = await updateAnalystNote(note.note_id, {
        is_pinned: !note.is_pinned
      });

      if (response.success) {
        fetchNotes();
      }
    } catch (error) {
      console.error('Error toggling pin:', error);
      toast.error('Failed to update note');
    }
  };

  // Edit note
  const startEditNote = (note) => {
    setSelectedNote(note);
    setNoteForm({
      title: note.title,
      content: note.content,
      tags: note.tags || [],
      color: note.color || 'default',
      is_pinned: note.is_pinned,
      reference_type: note.reference_type,
      reference_id: note.reference_id
    });
    setEditing(true);
  };

  // Reset form
  const resetForm = () => {
    setNoteForm({
      title: '',
      content: '',
      tags: [],
      color: 'default',
      is_pinned: false,
      reference_type: null,
      reference_id: null
    });
    setTagInput('');
  };

  // Add tag
  const addTag = () => {
    if (tagInput.trim() && !noteForm.tags.includes(tagInput.trim())) {
      setNoteForm({
        ...noteForm,
        tags: [...noteForm.tags, tagInput.trim()]
      });
      setTagInput('');
    }
  };

  // Remove tag
  const removeTag = (tag) => {
    setNoteForm({
      ...noteForm,
      tags: noteForm.tags.filter(t => t !== tag)
    });
  };

  // Group notes by pinned status
  const pinnedNotes = notes.filter(n => n.is_pinned);
  const regularNotes = notes.filter(n => !n.is_pinned);

  if (loading && notes.length === 0) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-[#0d4a6f] animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading notes...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6 space-y-6">
        {/* Page Header - Desktop Only */}
        <PageHeader />

        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d4a6f] to-[#083a57] rounded-2xl shadow-lg p-6 text-white relative overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 opacity-10">
            <svg viewBox="0 0 1440 120" className="w-full h-12">
              <path fill="white" d="M0,32L48,37.3C96,43,192,53,288,58.7C384,64,480,64,576,58.7C672,53,768,43,864,42.7C960,43,1056,53,1152,58.7C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z"></path>
            </svg>
          </div>
          <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <FileText className="w-6 h-6 text-white" />
                </div>
                My Notes
              </h1>
              <p className="text-[#9ecbec] mt-1">
                {totalNotes} notes total
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  resetForm();
                  setShowNewNote(true);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 rounded-xl hover:bg-white/20 transition-colors text-white"
              >
                <Plus className="w-4 h-4" />
                New Note
              </button>
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
              />
            </div>

            {/* Filter toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <Filter className="w-4 h-4" />
              <span className="text-sm">Tags</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>

            <button
              onClick={fetchNotes}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Tags filter */}
          {showFilters && availableTags.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-sm font-medium text-gray-700 mb-2">Filter by tags:</p>
              <div className="flex flex-wrap gap-2">
                {availableTags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => {
                      if (tagFilter.includes(tag)) {
                        setTagFilter(tagFilter.filter(t => t !== tag));
                      } else {
                        setTagFilter([...tagFilter, tag]);
                      }
                    }}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                      tagFilter.includes(tag)
                        ? 'bg-[#e8f4fc] border-[#c5e1f5] text-[#0d4a6f]'
                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
                {tagFilter.length > 0 && (
                  <button
                    onClick={() => setTagFilter([])}
                    className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-full"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Notes Grid */}
        <div className="space-y-6">
          {/* Pinned Notes */}
          {pinnedNotes.length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Pin className="w-4 h-4" />
                Pinned
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {pinnedNotes.map((note) => (
                  <NoteCard
                    key={note.note_id}
                    note={note}
                    onSelect={() => setSelectedNote(note)}
                    onEdit={() => startEditNote(note)}
                    onDelete={() => handleDeleteNote(note.note_id)}
                    onTogglePin={() => handleTogglePin(note)}
                    isSelected={selectedNote?.note_id === note.note_id}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Regular Notes */}
          {regularNotes.length > 0 && (
            <div>
              {pinnedNotes.length > 0 && (
                <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
                  All Notes
                </h2>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {regularNotes.map((note) => (
                  <NoteCard
                    key={note.note_id}
                    note={note}
                    onSelect={() => setSelectedNote(note)}
                    onEdit={() => startEditNote(note)}
                    onDelete={() => handleDeleteNote(note.note_id)}
                    onTogglePin={() => handleTogglePin(note)}
                    isSelected={selectedNote?.note_id === note.note_id}
                  />
                ))}
              </div>
            </div>
          )}

          {notes.length === 0 && !loading && (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No notes yet</h3>
              <p className="text-gray-600 mb-4">Create your first note to get started</p>
              <button
                onClick={() => {
                  resetForm();
                  setShowNewNote(true);
                }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57]"
              >
                <Plus className="w-4 h-4" />
                Create Note
              </button>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalNotes > pageSize && (
          <div className="flex justify-center gap-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-gray-600">
              Page {page} of {Math.ceil(totalNotes / pageSize)}
            </span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page >= Math.ceil(totalNotes / pageSize)}
              className="px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}

        {/* New Note Modal */}
        {showNewNote && (
          <NoteModal
            title="Create New Note"
            noteForm={noteForm}
            setNoteForm={setNoteForm}
            tagInput={tagInput}
            setTagInput={setTagInput}
            addTag={addTag}
            removeTag={removeTag}
            onSave={handleCreateNote}
            onClose={() => {
              setShowNewNote(false);
              resetForm();
            }}
          />
        )}

        {/* Edit Note Modal */}
        {isEditing && selectedNote && (
          <NoteModal
            title="Edit Note"
            noteForm={noteForm}
            setNoteForm={setNoteForm}
            tagInput={tagInput}
            setTagInput={setTagInput}
            addTag={addTag}
            removeTag={removeTag}
            onSave={handleUpdateNote}
            onClose={() => {
              setEditing(false);
              setSelectedNote(null);
              resetForm();
            }}
          />
        )}

        {/* Note Preview Modal */}
        {selectedNote && !isEditing && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className={`bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden ${noteColors[selectedNote.color || 'default'].bg}`}>
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-gray-900">{selectedNote.title}</h2>
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {new Date(selectedNote.created_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {new Date(selectedNote.updated_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedNote(null)}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
                {selectedNote.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {selectedNote.tags.map((tag) => (
                      <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="p-6 overflow-y-auto max-h-[50vh]">
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{selectedNote.content || 'No content'}</ReactMarkdown>
                </div>
              </div>
              <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
                <button
                  onClick={() => startEditNote(selectedNote)}
                  className="flex items-center gap-2 px-4 py-2 text-[#0d4a6f] hover:bg-[#e8f4fc] rounded-xl"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteNote(selectedNote.note_id)}
                  className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

// Note Card Component
function NoteCard({ note, onSelect, onEdit, onDelete, onTogglePin, isSelected }) {
  const colors = noteColors[note.color || 'default'];

  return (
    <div
      onClick={onSelect}
      className={`${colors.bg} ${colors.border} ${colors.hover} border rounded-xl p-4 cursor-pointer transition-all ${
        isSelected ? 'ring-2 ring-[#1a6b9a]' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-gray-900 line-clamp-1">{note.title}</h3>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onTogglePin();
          }}
          className="p-1 hover:bg-gray-200 rounded"
        >
          {note.is_pinned ? (
            <PinOff className="w-4 h-4 text-[#0d4a6f]" />
          ) : (
            <Pin className="w-4 h-4 text-gray-400" />
          )}
        </button>
      </div>

      <p className="text-sm text-gray-600 line-clamp-3 mb-3">
        {note.content || 'No content'}
      </p>

      {note.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {note.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="px-2 py-0.5 bg-white/50 text-gray-600 text-xs rounded-full">
              {tag}
            </span>
          ))}
          {note.tags.length > 3 && (
            <span className="px-2 py-0.5 text-gray-500 text-xs">
              +{note.tags.length - 3} more
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{new Date(note.updated_at).toLocaleDateString()}</span>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1 hover:bg-gray-200 rounded"
          >
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 hover:bg-red-100 rounded text-red-500"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Note Modal Component
function NoteModal({ title, noteForm, setNoteForm, tagInput, setTagInput, addTag, removeTag, onSave, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">{title}</h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={noteForm.title}
              onChange={(e) => setNoteForm({ ...noteForm, title: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
              placeholder="Note title..."
            />
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Content <span className="text-gray-400 font-normal">(Markdown supported)</span>
            </label>
            <textarea
              value={noteForm.content}
              onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
              rows={8}
              className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a] font-mono text-sm"
              placeholder="Write your note here... (Markdown supported)"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1a6b9a] focus:border-[#1a6b9a]"
                placeholder="Add a tag..."
              />
              <button
                onClick={addTag}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Add
              </button>
            </div>
            {noteForm.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {noteForm.tags.map((tag) => (
                  <span key={tag} className="inline-flex items-center gap-1 px-3 py-1 bg-[#e8f4fc] text-[#0d4a6f] text-sm rounded-full">
                    {tag}
                    <button onClick={() => removeTag(tag)} className="hover:text-[#083a57]">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Color */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
            <div className="flex gap-2">
              {Object.entries(noteColors).map(([color, styles]) => (
                <button
                  key={color}
                  onClick={() => setNoteForm({ ...noteForm, color })}
                  className={`w-8 h-8 rounded-full ${styles.bg} ${styles.border} border-2 ${
                    noteForm.color === color ? 'ring-2 ring-[#1a6b9a] ring-offset-2' : ''
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Pin option */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={noteForm.is_pinned}
              onChange={(e) => setNoteForm({ ...noteForm, is_pinned: e.target.checked })}
              className="w-4 h-4 text-[#0d4a6f] rounded focus:ring-[#1a6b9a]"
            />
            <span className="text-sm text-gray-700">Pin this note</span>
          </label>
        </div>

        <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            className="flex items-center gap-2 px-4 py-2 bg-[#0d4a6f] text-white rounded-xl hover:bg-[#083a57]"
          >
            <Save className="w-4 h-4" />
            Save Note
          </button>
        </div>
      </div>
    </div>
  );
}

export default function NotesPage() {
  return <NotesPageContent />;
}
