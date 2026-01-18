"""
Voice Transcription Service
Handles multilingual speech-to-text using OpenAI Whisper for Indian languages
"""

import logging
import os
import tempfile
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported languages - Whisper supports all these and more!
SUPPORTED_LANGUAGES = {
    'as': 'Assamese',
    'bn': 'Bengali',
    'brx': 'Bodo',
    'doi': 'Dogri',
    'gu': 'Gujarati',
    'hi': 'Hindi',
    'kn': 'Kannada',
    'kok': 'Konkani',
    'ks': 'Kashmiri',
    'mai': 'Maithili',
    'ml': 'Malayalam',
    'mni': 'Manipuri',
    'mr': 'Marathi',
    'ne': 'Nepali',
    'or': 'Odia',
    'pa': 'Punjabi',
    'sa': 'Sanskrit',
    'sat': 'Santali',
    'sd': 'Sindhi',
    'ta': 'Tamil',
    'te': 'Telugu',
    'ur': 'Urdu',
    'en': 'English'
}

# Language code mapping for Whisper (some codes are different)
WHISPER_LANGUAGE_MAP = {
    'as': 'as',
    'bn': 'bn',
    'brx': 'hi',  # Bodo -> fallback to Hindi
    'doi': 'hi',  # Dogri -> fallback to Hindi
    'gu': 'gu',
    'hi': 'hi',
    'kn': 'kn',
    'kok': 'hi',  # Konkani -> fallback to Hindi
    'ks': 'ur',   # Kashmiri -> fallback to Urdu
    'mai': 'hi',  # Maithili -> fallback to Hindi
    'ml': 'ml',
    'mni': 'hi',  # Manipuri -> fallback to Hindi
    'mr': 'mr',
    'ne': 'ne',
    'or': 'or',
    'pa': 'pa',
    'sa': 'sa',
    'sat': 'hi',  # Santali -> fallback to Hindi
    'sd': 'sd',
    'ta': 'ta',
    'te': 'te',
    'ur': 'ur',
    'en': 'en'
}


class VoiceTranscriptionService:
    """
    Service for transcribing audio using OpenAI Whisper
    Supports all major Indian languages
    """

    def __init__(self):
        """Initialize the transcription service"""
        self.model = None
        self.model_loaded = False
        self.model_loading_error = None
        self.model_size = "base"  # Options: tiny, base, small, medium, large

    def _load_model(self):
        """
        Lazy load the Whisper model
        Only loads when first transcription is requested
        """
        if self.model_loaded:
            return

        if self.model_loading_error:
            raise self.model_loading_error

        try:
            logger.info(f"Loading Whisper {self.model_size} model...")

            # Import here to avoid loading if not needed
            import whisper
            import torch

            # Load Whisper model
            # 'base' is a good balance between speed and accuracy (~150MB)
            # Options: tiny (~40MB), base (~150MB), small (~500MB), medium (~1.5GB), large (~3GB)
            self.model = whisper.load_model(self.model_size)

            # Check if using GPU
            if torch.cuda.is_available():
                logger.info(f"Whisper {self.model_size} model loaded on GPU")
            else:
                logger.info(f"Whisper {self.model_size} model loaded on CPU")

            self.model_loaded = True
            logger.info("Whisper model loaded successfully")

        except Exception as e:
            error_msg = f"Failed to load Whisper model: {str(e)}"
            logger.error(error_msg)
            self.model_loading_error = RuntimeError(error_msg)
            raise self.model_loading_error

    async def transcribe(
        self,
        audio_file_path: str,
        language_code: str = 'hi',
        decode_strategy: str = 'ctc'
    ) -> Tuple[str, str]:
        """
        Transcribe audio file to text using Whisper

        Args:
            audio_file_path: Path to audio file (WAV, MP3, WebM, etc.)
            language_code: Language code (e.g., 'hi' for Hindi, 'ta' for Tamil)
            decode_strategy: Not used for Whisper (kept for API compatibility)

        Returns:
            Tuple of (transcribed_text, detected_language)

        Raises:
            ValueError: If language not supported or audio file invalid
            RuntimeError: If model fails to load or transcribe
        """
        try:
            # Validate language
            if language_code not in SUPPORTED_LANGUAGES:
                logger.warning(f"Unsupported language: {language_code}, falling back to Hindi")
                language_code = 'hi'

            # Load model if not already loaded
            self._load_model()

            # Map to Whisper language code
            whisper_lang = WHISPER_LANGUAGE_MAP.get(language_code, 'hi')

            # Transcribe using Whisper
            logger.info(f"Transcribing audio in {SUPPORTED_LANGUAGES[language_code]}")

            result = self.model.transcribe(
                audio_file_path,
                language=whisper_lang,
                fp16=False  # Use fp32 for CPU compatibility
            )

            # Extract transcription
            transcription = result['text'].strip()

            logger.info(f"Transcription successful: {len(transcription)} characters")

            return transcription, SUPPORTED_LANGUAGES[language_code]

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    async def transcribe_from_bytes(
        self,
        audio_bytes: bytes,
        language_code: str = 'hi',
        decode_strategy: str = 'ctc',
        file_extension: str = 'wav'
    ) -> Tuple[str, str]:
        """
        Transcribe audio from bytes

        Args:
            audio_bytes: Audio file content as bytes
            language_code: Language code
            decode_strategy: Decoding strategy
            file_extension: File extension (wav, mp3, webm, etc.)

        Returns:
            Tuple of (transcribed_text, detected_language)
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f'.{file_extension}'
        ) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            # Transcribe from temp file
            transcription, language = await self.transcribe(
                temp_path,
                language_code,
                decode_strategy
            )
            return transcription, language

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

    def get_supported_languages(self):
        """Get list of supported languages"""
        return SUPPORTED_LANGUAGES

    def detect_language_from_audio(self, audio_file_path: str) -> str:
        """
        Attempt to detect language from audio
        This is a placeholder - actual implementation would use a language identification model

        For now, returns 'hi' (Hindi) as default
        """
        # TODO: Implement actual language detection using a language ID model
        # For now, we'll rely on user selection
        logger.info("Language detection not implemented, defaulting to Hindi")
        return 'hi'


# Global instance
_transcription_service = None


def get_transcription_service() -> VoiceTranscriptionService:
    """
    Get or create the global transcription service instance
    Uses singleton pattern to avoid loading model multiple times
    """
    global _transcription_service

    if _transcription_service is None:
        _transcription_service = VoiceTranscriptionService()

    return _transcription_service
