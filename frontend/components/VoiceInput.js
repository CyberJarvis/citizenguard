'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Mic,
  StopCircle,
  Loader2,
  Languages,
  CheckCircle,
  X,
  AlertCircle,
  Volume2
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '@/lib/api';

// Supported languages for IndicConformer
const INDIAN_LANGUAGES = [
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'ur', name: 'Urdu', nativeName: 'اردو' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം' },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'as', name: 'Assamese', nativeName: 'অসমীয়া' },
  { code: 'mai', name: 'Maithili', nativeName: 'मैथिली' },
  { code: 'brx', name: 'Bodo', nativeName: 'बड़ो' },
  { code: 'sat', name: 'Santali', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ' },
  { code: 'kok', name: 'Konkani', nativeName: 'कोंकणी' },
  { code: 'doi', name: 'Dogri', nativeName: 'डोगरी' },
  { code: 'ks', name: 'Kashmiri', nativeName: 'कॉशुर' },
  { code: 'ne', name: 'Nepali', nativeName: 'नेपाली' },
  { code: 'sd', name: 'Sindhi', nativeName: 'سنڌي' },
  { code: 'mni', name: 'Manipuri', nativeName: 'মৈতৈলোন্' },
  { code: 'sa', name: 'Sanskrit', nativeName: 'संस्कृतम्' },
  { code: 'en', name: 'English', nativeName: 'English' }
];

// Popular coastal languages at the top
const POPULAR_COASTAL_LANGUAGES = ['hi', 'bn', 'te', 'ta', 'ml', 'mr', 'gu', 'kn', 'or'];

export default function VoiceInput({
  onTranscription,
  description = '',
  onDescriptionChange,
  disabled = false
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('hi'); // Default to Hindi
  const [showLanguageSelector, setShowLanguageSelector] = useState(false);
  const [recordedAudio, setRecordedAudio] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [transcriptionResult, setTranscriptionResult] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      stopRecording();
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Handle data available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Handle recording stop
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(audioBlob);

        setRecordedAudio(audioBlob);
        setAudioURL(url);

        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }

        // Clear timer
        if (recordingTimerRef.current) {
          clearInterval(recordingTimerRef.current);
          recordingTimerRef.current = null;
        }

        // Auto-transcribe
        transcribeAudio(audioBlob);
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingDuration(0);

      // Start duration timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

      toast.success(`Recording in ${INDIAN_LANGUAGES.find(l => l.code === selectedLanguage)?.name}...`);
    } catch (error) {
      console.error('Recording error:', error);

      let errorMessage = 'Failed to access microphone';
      if (error.name === 'NotAllowedError') {
        errorMessage = 'Microphone permission denied. Please allow access.';
      } else if (error.name === 'NotFoundError') {
        errorMessage = 'No microphone found on this device.';
      }

      toast.error(errorMessage);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (audioBlob) => {
    setIsTranscribing(true);

    try {
      // Prepare form data
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', selectedLanguage);
      formData.append('decode_strategy', 'ctc'); // Use CTC for faster transcription

      // Send to backend
      const response = await api.post('/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const { transcription, language, language_code } = response.data;

      if (transcription && transcription !== '[No speech detected]') {
        // Update description with transcription
        const newDescription = description
          ? `${description}\n\n${transcription}`
          : transcription;

        onDescriptionChange(newDescription);

        setTranscriptionResult({
          text: transcription,
          language,
          languageCode: language_code
        });

        // Notify parent
        if (onTranscription) {
          onTranscription(transcription, language_code);
        }

        toast.success(`Transcribed successfully in ${language}!`);
      } else {
        toast.error('No speech detected. Please try again.');
      }
    } catch (error) {
      console.error('Transcription error:', error);

      const errorMessage = error.response?.data?.detail
        || error.message
        || 'Failed to transcribe audio. Please try again.';

      toast.error(errorMessage);
    } finally {
      setIsTranscribing(false);
    }
  };

  const retryTranscription = () => {
    if (recordedAudio) {
      transcribeAudio(recordedAudio);
    }
  };

  const clearRecording = () => {
    setRecordedAudio(null);
    setAudioURL(null);
    setTranscriptionResult(null);
    setRecordingDuration(0);

    if (audioURL) {
      URL.revokeObjectURL(audioURL);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getLanguageName = (code) => {
    const lang = INDIAN_LANGUAGES.find(l => l.code === code);
    return lang ? `${lang.name} (${lang.nativeName})` : code;
  };

  // Sort languages: popular coastal languages first, then alphabetically
  const sortedLanguages = [
    ...INDIAN_LANGUAGES.filter(l => POPULAR_COASTAL_LANGUAGES.includes(l.code)),
    ...INDIAN_LANGUAGES.filter(l => !POPULAR_COASTAL_LANGUAGES.includes(l.code))
  ];

  return (
    <div className="space-y-4">
      {/* Language Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Languages className="w-4 h-4 inline mr-1" />
          Select Language
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowLanguageSelector(!showLanguageSelector)}
            disabled={disabled || isRecording}
            className="w-full bg-white rounded-xl border border-gray-300 px-4 py-3 flex items-center justify-between hover:border-blue-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="font-medium text-gray-900">
              {getLanguageName(selectedLanguage)}
            </span>
            <Languages className="w-5 h-5 text-gray-400" />
          </button>

          {showLanguageSelector && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-200 z-50 max-h-80 overflow-y-auto">
              {/* Popular Coastal Languages */}
              <div className="p-2">
                <div className="px-3 py-2 text-xs font-bold text-blue-600 uppercase tracking-wide bg-blue-50 rounded-lg mb-1">
                  Popular Coastal Languages
                </div>
                {sortedLanguages.slice(0, POPULAR_COASTAL_LANGUAGES.length).map((lang) => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => {
                      setSelectedLanguage(lang.code);
                      setShowLanguageSelector(false);
                      toast.success(`Language set to ${lang.name}`);
                    }}
                    className={`w-full text-left px-3 py-3 rounded-lg hover:bg-blue-50 transition-colors ${
                      selectedLanguage === lang.code
                        ? 'bg-blue-100 text-blue-700 font-semibold'
                        : 'text-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{lang.name}</div>
                        <div className="text-sm text-gray-500">{lang.nativeName}</div>
                      </div>
                      {selectedLanguage === lang.code && (
                        <CheckCircle className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                  </button>
                ))}
              </div>

              {/* All Other Languages */}
              <div className="border-t border-gray-100 p-2">
                <div className="px-3 py-2 text-xs font-bold text-gray-500 uppercase tracking-wide">
                  All Languages
                </div>
                {sortedLanguages.slice(POPULAR_COASTAL_LANGUAGES.length).map((lang) => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => {
                      setSelectedLanguage(lang.code);
                      setShowLanguageSelector(false);
                      toast.success(`Language set to ${lang.name}`);
                    }}
                    className={`w-full text-left px-3 py-3 rounded-lg hover:bg-blue-50 transition-colors ${
                      selectedLanguage === lang.code
                        ? 'bg-blue-100 text-blue-700 font-semibold'
                        : 'text-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{lang.name}</div>
                        <div className="text-sm text-gray-500">{lang.nativeName}</div>
                      </div>
                      {selectedLanguage === lang.code && (
                        <CheckCircle className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recording Controls */}
      {!recordedAudio ? (
        <div>
          {!isRecording ? (
            <button
              type="button"
              onClick={startRecording}
              disabled={disabled}
              className="w-full bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-6 py-4 rounded-xl flex items-center justify-center space-x-3 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Mic className="w-6 h-6" />
              <span className="font-semibold">Start Voice Recording</span>
            </button>
          ) : (
            <div className="space-y-3">
              <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse"></div>
                    <span className="font-semibold text-red-700">Recording...</span>
                  </div>
                  <span className="text-red-700 font-mono font-bold text-lg">
                    {formatDuration(recordingDuration)}
                  </span>
                </div>
                <div className="text-sm text-red-600 mb-3">
                  Speaking in {INDIAN_LANGUAGES.find(l => l.code === selectedLanguage)?.name}
                </div>
              </div>

              <button
                type="button"
                onClick={stopRecording}
                className="w-full bg-gray-900 hover:bg-gray-800 text-white px-6 py-4 rounded-xl flex items-center justify-center space-x-3 transition-all"
              >
                <StopCircle className="w-6 h-6" />
                <span className="font-semibold">Stop Recording</span>
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Audio Player */}
          <div className="bg-white rounded-xl border border-gray-300 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Volume2 className="w-5 h-5 text-blue-600" />
                <span className="font-medium text-gray-700">Recorded Audio</span>
                <span className="text-sm text-gray-500">({formatDuration(recordingDuration)})</span>
              </div>
              <button
                type="button"
                onClick={clearRecording}
                className="text-red-600 hover:text-red-700 transition-colors"
                title="Delete recording"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <audio controls className="w-full" src={audioURL}>
              Your browser does not support the audio element.
            </audio>
          </div>

          {/* Transcription Status */}
          {isTranscribing && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center space-x-3">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              <div>
                <div className="font-medium text-blue-900">Transcribing audio...</div>
                <div className="text-sm text-blue-700">
                  Using IndicConformer for {INDIAN_LANGUAGES.find(l => l.code === selectedLanguage)?.name}
                </div>
              </div>
            </div>
          )}

          {/* Transcription Result */}
          {transcriptionResult && !isTranscribing && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <div className="flex items-start space-x-3">
                <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium text-green-900 mb-1">
                    Transcription Complete ({transcriptionResult.language})
                  </div>
                  <div className="text-sm text-green-800 bg-white rounded-lg p-3 border border-green-200">
                    {transcriptionResult.text}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Retry Button */}
          {!isTranscribing && (
            <button
              type="button"
              onClick={retryTranscription}
              className="w-full bg-white border-2 border-blue-600 text-blue-600 hover:bg-blue-50 px-6 py-3 rounded-xl flex items-center justify-center space-x-2 transition-all font-medium"
            >
              <Loader2 className="w-5 h-5" />
              <span>Retry Transcription</span>
            </button>
          )}
        </div>
      )}

      {/* Help Text */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 flex items-start space-x-2">
        <AlertCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-blue-800">
          <strong>Tip:</strong> Select your regional language above, then record your voice.
          The audio will be automatically transcribed and added to the description field.
          Supports 22 Indian languages powered by IndicConformer AI.
        </div>
      </div>
    </div>
  );
}
