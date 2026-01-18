"""
Voice Transcription Endpoints
API endpoints for converting speech to text using OpenAI Whisper
"""

import logging
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    status
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.services.voice_transcription import (
    get_transcription_service,
    SUPPORTED_LANGUAGES
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["Voice Transcription"])

# Maximum audio file size (10MB)
MAX_AUDIO_SIZE = 10 * 1024 * 1024

# Allowed audio formats (base MIME types without codec info)
ALLOWED_AUDIO_TYPES = [
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "audio/x-m4a",
    "audio/mp4"
]


def is_valid_audio_type(content_type: str) -> bool:
    """Check if content type is valid, handling codec suffixes like audio/webm;codecs=opus"""
    if not content_type:
        return False
    # Extract base MIME type (before semicolon if present)
    base_type = content_type.split(';')[0].strip().lower()
    return base_type in ALLOWED_AUDIO_TYPES


class TranscriptionResponse(BaseModel):
    """Response model for transcription"""
    transcription: str
    language: str
    language_code: str
    decode_strategy: str
    success: bool = True


class LanguagesResponse(BaseModel):
    """Response model for supported languages"""
    languages: dict
    count: int


@router.post("", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form('hi', description="Language code (e.g., 'hi' for Hindi, 'ta' for Tamil)"),
    decode_strategy: str = Form('ctc', description="Decode strategy: 'ctc' (faster) or 'rnnt' (more accurate)")
):
    """
    Transcribe audio to text using OpenAI Whisper

    Supports 22 Indian languages + English:
    - Assamese (as), Bengali (bn), Bodo (brx), Dogri (doi)
    - Gujarati (gu), Hindi (hi), Kannada (kn), Konkani (kok)
    - Kashmiri (ks), Maithili (mai), Malayalam (ml), Manipuri (mni)
    - Marathi (mr), Nepali (ne), Odia (or), Punjabi (pa)
    - Sanskrit (sa), Santali (sat), Sindhi (sd), Tamil (ta)
    - Telugu (te), Urdu (ur), English (en)

    **File Requirements:**
    - Max size: 10MB
    - Formats: WAV, MP3, WebM, OGG, FLAC, M4A

    **Parameters:**
    - `audio`: Audio file to transcribe
    - `language`: Language code (default: 'hi' for Hindi)
    - `decode_strategy`: 'ctc' (faster, default) or 'rnnt' (more accurate)

    **Returns:**
    - `transcription`: Transcribed text
    - `language`: Full language name
    - `language_code`: Language code used
    - `decode_strategy`: Decode strategy used
    """
    try:
        # Validate file type (handles codec suffixes like audio/webm;codecs=opus)
        if not is_valid_audio_type(audio.content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid audio format '{audio.content_type}'. Allowed: {', '.join(ALLOWED_AUDIO_TYPES)}"
            )

        # Read audio content
        audio_content = await audio.read()

        # Validate file size
        if len(audio_content) > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio file too large. Maximum size: {MAX_AUDIO_SIZE / 1024 / 1024}MB"
            )

        # Validate language
        if language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language '{language}', falling back to Hindi")
            language = 'hi'

        # Validate decode strategy
        if decode_strategy not in ['ctc', 'rnnt']:
            logger.warning(f"Invalid decode strategy '{decode_strategy}', using CTC")
            decode_strategy = 'ctc'

        # Get file extension
        file_extension = audio.filename.split('.')[-1] if audio.filename else 'wav'

        # Get transcription service
        service = get_transcription_service()

        # Transcribe
        logger.info(f"Transcribing {len(audio_content)} bytes in {language} using {decode_strategy}")

        transcription, language_name = await service.transcribe_from_bytes(
            audio_bytes=audio_content,
            language_code=language,
            decode_strategy=decode_strategy,
            file_extension=file_extension
        )

        if not transcription:
            logger.warning("Transcription returned empty string")
            transcription = "[No speech detected]"

        logger.info(f"Transcription successful: {len(transcription)} characters")

        return TranscriptionResponse(
            transcription=transcription,
            language=language_name,
            language_code=language,
            decode_strategy=decode_strategy
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        # Model loading or transcription error
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transcribe audio. Please try again."
        )


@router.get("/languages", response_model=LanguagesResponse)
async def get_supported_languages():
    """
    Get list of supported languages for transcription

    Returns all 22 Indian languages supported by IndicConformer,
    plus English as a fallback option.

    **Returns:**
    - `languages`: Dictionary of language codes and names
    - `count`: Number of supported languages
    """
    return LanguagesResponse(
        languages=SUPPORTED_LANGUAGES,
        count=len(SUPPORTED_LANGUAGES)
    )


@router.get("/health")
async def transcription_health():
    """
    Health check for transcription service

    **Returns:**
    - Service status and model information
    """
    try:
        service = get_transcription_service()

        return JSONResponse(
            content={
                "status": "healthy",
                "model": "openai/whisper-base",
                "model_loaded": service.model_loaded,
                "supported_languages": len(SUPPORTED_LANGUAGES),
                "decode_strategies": ["ctc", "rnnt"]
            },
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e)
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
