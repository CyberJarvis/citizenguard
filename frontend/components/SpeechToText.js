'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Mic,
  Square,
  Globe,
  ChevronDown,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';

/**
 * Speech-to-Text Component with Multi-Indian Language Support
 *
 * LIVE TRANSCRIPTION using Web Speech API
 * - Real-time speech-to-text as you speak
 * - Supports 15+ Indian regional languages
 * - Automatic language detection from browser settings
 * - Shows interim results while speaking
 */

// Supported Indian languages with Web Speech API codes
const INDIAN_LANGUAGES = [
  { code: 'en-IN', name: 'English', nativeName: 'English' },
  { code: 'hi-IN', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'bn-IN', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'te-IN', name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'mr-IN', name: 'Marathi', nativeName: 'मराठी' },
  { code: 'ta-IN', name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'gu-IN', name: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'kn-IN', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'ml-IN', name: 'Malayalam', nativeName: 'മലയാളം' },
  { code: 'pa-IN', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'or-IN', name: 'Odia', nativeName: 'ଓଡ଼ିଆ' },
  { code: 'as-IN', name: 'Assamese', nativeName: 'অসমীয়া' },
  { code: 'ur-IN', name: 'Urdu', nativeName: 'اردو' },
  { code: 'ne-NP', name: 'Nepali', nativeName: 'नेपाली' },
  { code: 'sa-IN', name: 'Sanskrit', nativeName: 'संस्कृतम्' },
];

// Priority languages for coastal areas (shown first)
const PRIORITY_LANGUAGES = ['en-IN', 'hi-IN', 'ta-IN', 'te-IN', 'ml-IN', 'mr-IN', 'gu-IN', 'bn-IN', 'kn-IN', 'or-IN'];

// Detect best language match from browser
const detectBrowserLanguage = () => {
  if (typeof window === 'undefined') return 'en-IN';

  const browserLang = navigator.language || navigator.userLanguage || 'en-IN';
  const shortCode = browserLang.split('-')[0].toLowerCase();

  // Try to find exact match first
  let match = INDIAN_LANGUAGES.find(lang =>
    lang.code.toLowerCase() === browserLang.toLowerCase()
  );

  // Try short code match
  if (!match) {
    match = INDIAN_LANGUAGES.find(lang =>
      lang.code.split('-')[0].toLowerCase() === shortCode
    );
  }

  return match?.code || 'en-IN';
};

export default function SpeechToText({
  value = '',
  onChange,
  disabled = false,
  compact = false
}) {
  // State
  const [isListening, setIsListening] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('en-IN');
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);

  // Refs
  const recognitionRef = useRef(null);
  const dropdownRef = useRef(null);
  const valueRef = useRef(value);
  const isListeningRef = useRef(false);

  // Keep refs in sync
  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  // Auto-detect language on mount
  useEffect(() => {
    const detectedLang = detectBrowserLanguage();
    setSelectedLanguage(detectedLang);

    // Check if Web Speech API is supported
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
    }
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
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

  // Start listening
  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      toast.error('Speech recognition not supported. Use Chrome or Edge.');
      return;
    }

    // Create new recognition instance each time
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = selectedLanguage;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setInterimTranscript('');
    };

    recognition.onresult = (event) => {
      let interim = '';
      let finalText = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += transcript + ' ';
        } else {
          interim += transcript;
        }
      }

      // Update interim transcript for live display
      setInterimTranscript(interim);

      // Append final transcript to value immediately
      if (finalText.trim()) {
        const currentValue = valueRef.current;
        const newValue = currentValue
          ? `${currentValue} ${finalText.trim()}`
          : finalText.trim();
        onChange(newValue);
      }
    };

    recognition.onerror = (event) => {
      // 'aborted' is normal when user stops - ignore it
      if (event.error === 'aborted') return;

      const errorMessages = {
        'no-speech': 'No speech detected. Try speaking louder.',
        'audio-capture': 'No microphone found. Check your device.',
        'not-allowed': 'Microphone access denied. Please allow access in browser settings.',
        'network': 'Network error. Check your internet connection.',
        'service-not-allowed': 'Speech service not available. Try Chrome or Edge browser.',
      };

      if (event.error !== 'no-speech') {
        toast.error(errorMessages[event.error] || 'Voice input error');
        setIsListening(false);
        setInterimTranscript('');
      }
    };

    recognition.onend = () => {
      // Auto-restart if user hasn't stopped it
      if (isListeningRef.current) {
        try {
          recognition.start();
        } catch (e) {
          setIsListening(false);
          setInterimTranscript('');
        }
      } else {
        setInterimTranscript('');
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
      setIsListening(true);

      const lang = INDIAN_LANGUAGES.find(l => l.code === selectedLanguage);
      toast.success(`Listening in ${lang?.name}...`, { icon: '🎤', duration: 2000 });
    } catch (error) {
      console.error('Failed to start recognition:', error);
      toast.error('Failed to start voice input. Please try again.');
    }
  };

  // Stop listening
  const stopListening = () => {
    setIsListening(false);
    isListeningRef.current = false;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }

    setInterimTranscript('');

    if (valueRef.current) {
      toast.success('Voice input captured!', { icon: '✓', duration: 2000 });
    }
  };

  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // Get current language
  const getCurrentLanguage = () => {
    return INDIAN_LANGUAGES.find(l => l.code === selectedLanguage);
  };

  // Sort languages: priority first
  const sortedLanguages = [
    ...INDIAN_LANGUAGES.filter(l => PRIORITY_LANGUAGES.includes(l.code)),
    ...INDIAN_LANGUAGES.filter(l => !PRIORITY_LANGUAGES.includes(l.code))
  ];

  // If not supported, show message
  if (!speechSupported) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
        <p className="text-sm text-amber-800">
          Live voice input requires Chrome, Edge, or Safari browser.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Controls Row */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Voice Button */}
        <button
          type="button"
          onClick={toggleListening}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed ${
            isListening
              ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 animate-pulse'
              : 'bg-[#0d4a6f] hover:bg-[#083a57] text-white shadow-lg shadow-[#0d4a6f]/20'
          }`}
        >
          {isListening ? (
            <>
              <Square className="w-4 h-4 fill-current" />
              <span>Stop</span>
            </>
          ) : (
            <>
              <Mic className="w-4 h-4" />
              <span>{compact ? '' : 'Voice'}</span>
            </>
          )}
        </button>

        {/* Language Selector */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setShowLanguageDropdown(!showLanguageDropdown)}
            disabled={isListening}
            className="flex items-center gap-2 px-3 py-2.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-sm font-medium text-slate-700 transition-all disabled:opacity-50"
          >
            <Globe className="w-4 h-4 text-slate-500" />
            <span className="hidden sm:inline">{getCurrentLanguage()?.name}</span>
            <span className="sm:hidden">{getCurrentLanguage()?.code.split('-')[0].toUpperCase()}</span>
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showLanguageDropdown ? 'rotate-180' : ''}`} />
          </button>

          {showLanguageDropdown && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-1 z-50 max-h-72 overflow-y-auto">
              {/* Priority Languages */}
              <div className="px-3 py-2 text-xs font-semibold text-[#0d4a6f] uppercase tracking-wide bg-[#e8f4fc] border-b border-slate-100">
                Coastal Languages
              </div>
              {sortedLanguages.slice(0, PRIORITY_LANGUAGES.length).map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => {
                    setSelectedLanguage(lang.code);
                    setShowLanguageDropdown(false);
                    toast.success(`Language: ${lang.name}`, { duration: 1500 });
                  }}
                  className={`w-full text-left px-3 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center justify-between ${
                    selectedLanguage === lang.code ? 'bg-[#e8f4fc] text-[#0d4a6f]' : 'text-slate-700'
                  }`}
                >
                  <div>
                    <span className="font-medium">{lang.name}</span>
                    <span className="text-slate-400 ml-2">{lang.nativeName}</span>
                  </div>
                  {selectedLanguage === lang.code && (
                    <CheckCircle className="w-4 h-4 text-[#0d4a6f]" />
                  )}
                </button>
              ))}

              {/* Other Languages */}
              <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wide border-t border-slate-100 mt-1">
                More Languages
              </div>
              {sortedLanguages.slice(PRIORITY_LANGUAGES.length).map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => {
                    setSelectedLanguage(lang.code);
                    setShowLanguageDropdown(false);
                    toast.success(`Language: ${lang.name}`, { duration: 1500 });
                  }}
                  className={`w-full text-left px-3 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center justify-between ${
                    selectedLanguage === lang.code ? 'bg-[#e8f4fc] text-[#0d4a6f]' : 'text-slate-700'
                  }`}
                >
                  <div>
                    <span className="font-medium">{lang.name}</span>
                    <span className="text-slate-400 ml-2">{lang.nativeName}</span>
                  </div>
                  {selectedLanguage === lang.code && (
                    <CheckCircle className="w-4 h-4 text-[#0d4a6f]" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Live Transcription Display */}
      {isListening && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3">
          <div className="flex items-center gap-3">
            <div className="relative flex-shrink-0">
              <div className="absolute inset-0 bg-red-400 rounded-full animate-ping opacity-30" />
              <div className="relative w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <Mic className="w-4 h-4 text-red-600" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-sm font-medium text-red-800">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span>Listening in {getCurrentLanguage()?.name}...</span>
              </div>
              {interimTranscript ? (
                <p className="text-sm text-slate-700 mt-1 italic bg-white/50 rounded px-2 py-1">
                  "{interimTranscript}"
                </p>
              ) : (
                <p className="text-xs text-red-600 mt-1">Speak now - your words appear in real-time</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Help text when not listening */}
      {!isListening && !compact && (
        <p className="text-xs text-slate-400">
          Live transcription in: English, Hindi, Tamil, Telugu, Bengali, Marathi, Malayalam, Gujarati, Kannada & more
        </p>
      )}
    </div>
  );
}
