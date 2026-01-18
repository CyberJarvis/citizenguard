'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, AlertCircle, ChevronDown, Globe } from 'lucide-react';
import toast from 'react-hot-toast';

/**
 * InlineVoiceInput Component
 * Live speech-to-text with Indian language support
 */

const SUPPORTED_LANGUAGES = [
  { code: 'en-IN', name: 'English' },
  { code: 'hi-IN', name: 'Hindi' },
  { code: 'ta-IN', name: 'Tamil' },
  { code: 'bn-IN', name: 'Bengali' },
  { code: 'te-IN', name: 'Telugu' },
  { code: 'mr-IN', name: 'Marathi' },
  { code: 'gu-IN', name: 'Gujarati' },
  { code: 'kn-IN', name: 'Kannada' },
  { code: 'ml-IN', name: 'Malayalam' },
  { code: 'pa-IN', name: 'Punjabi' },
  { code: 'or-IN', name: 'Odia' }
];

export function InlineVoiceInput({ value, onChange, disabled = false, onListeningChange, onTranscriptChange }) {
  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [browserSupported, setBrowserSupported] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState('en-IN');
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);

  const recognitionRef = useRef(null);
  const valueRef = useRef(value);
  const dropdownRef = useRef(null);

  // Keep value ref updated
  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  // Notify parent of listening state changes
  useEffect(() => {
    onListeningChange?.(isListening);
  }, [isListening, onListeningChange]);

  // Notify parent of transcript changes
  useEffect(() => {
    onTranscriptChange?.(interimTranscript);
  }, [interimTranscript, onTranscriptChange]);

  // Check browser support on mount
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setBrowserSupported(false);
    }
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowLanguageDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, []);

  const startListening = useCallback(async () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      toast.error('Speech recognition not supported');
      return;
    }

    // First, check if microphone is available and request permission
    try {
      // Check available devices first
      const devices = await navigator.mediaDevices.enumerateDevices();
      const hasMic = devices.some(device => device.kind === 'audioinput');

      if (!hasMic) {
        toast.error('No microphone found. Please connect a microphone and try again.', { duration: 4000 });
        return;
      }

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Stop the stream immediately - we just needed permission
      stream.getTracks().forEach(track => track.stop());
    } catch (err) {
      console.error('Microphone error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        toast.error('Microphone access denied. Please allow microphone in browser settings.', { duration: 4000 });
      } else if (err.name === 'NotFoundError') {
        toast.error('No microphone detected. Please connect a microphone.', { duration: 4000 });
      } else if (err.name === 'NotReadableError') {
        toast.error('Microphone is in use by another app. Please close other apps using the mic.', { duration: 4000 });
      } else {
        toast.error('Microphone error: ' + err.message, { duration: 4000 });
      }
      return;
    }

    // Stop existing if any
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = selectedLanguage;

    recognition.onresult = (event) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript + ' ';
        } else {
          interim += transcript;
        }
      }

      // Show interim transcript
      setInterimTranscript(interim);

      // Add final text to textarea immediately
      if (final.trim()) {
        const currentValue = valueRef.current || '';
        const newValue = currentValue
          ? `${currentValue} ${final.trim()}`
          : final.trim();
        onChange(newValue);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === 'aborted') return;

      if (event.error === 'not-allowed') {
        toast.error('Microphone access denied. Please allow in browser settings.');
      } else if (event.error !== 'no-speech') {
        toast.error('Voice input error: ' + event.error);
      }

      setIsListening(false);
      setInterimTranscript('');
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimTranscript('');
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
      setIsListening(true);
      const lang = SUPPORTED_LANGUAGES.find(l => l.code === selectedLanguage);
      toast.success(`Listening in ${lang?.name}...`, { duration: 2000 });
    } catch (error) {
      toast.error('Failed to start voice input');
      setIsListening(false);
    }
  }, [selectedLanguage, onChange]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  const getCurrentLanguageName = () => {
    return SUPPORTED_LANGUAGES.find(l => l.code === selectedLanguage)?.name || 'English';
  };

  if (!browserSupported) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
        <p className="text-sm text-amber-800">Voice input requires Chrome, Edge, or Safari</p>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {/* Mic Button */}
      <button
        type="button"
        onClick={isListening ? stopListening : startListening}
        disabled={disabled}
        className={`p-2.5 rounded-full transition-all active:scale-95 disabled:opacity-50 ${
          isListening
            ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
            : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
        }`}
        title={isListening ? 'Stop recording' : 'Start voice input'}
      >
        {isListening ? <Square className="w-4 h-4 fill-current" /> : <Mic className="w-4 h-4" />}
      </button>

      {/* Language Selector */}
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => !isListening && setShowLanguageDropdown(!showLanguageDropdown)}
          disabled={isListening}
          className="flex items-center gap-1 px-2 py-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-50"
        >
          <Globe className="w-3 h-3" />
          <span>{getCurrentLanguageName()}</span>
          <ChevronDown className={`w-3 h-3 transition-transform ${showLanguageDropdown ? 'rotate-180' : ''}`} />
        </button>

        {showLanguageDropdown && (
          <div className="absolute top-full right-0 mt-1 w-36 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50 max-h-48 overflow-y-auto">
            {SUPPORTED_LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                type="button"
                onClick={() => {
                  setSelectedLanguage(lang.code);
                  setShowLanguageDropdown(false);
                }}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 transition-colors ${
                  selectedLanguage === lang.code ? 'bg-slate-100 text-slate-900 font-medium' : 'text-slate-600'
                }`}
              >
                {lang.name}
              </button>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
