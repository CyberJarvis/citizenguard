"""
Upload API Endpoints
Handles S3 presigned URL generation for direct browser uploads
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.security import get_current_user
from app.models.user import User
from app.services.s3_service import s3_service
from app.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


# ==================== Request/Response Models ====================

class PresignedUrlRequest(BaseModel):
    """Request model for generating presigned URL"""
    upload_type: str = Field(
        ...,
        description="Type of upload: 'hazard_image', 'hazard_voice', 'profile', 'event'"
    )
    content_type: str = Field(
        ...,
        description="MIME type of the file (e.g., 'image/jpeg', 'audio/webm')"
    )
    filename: str = Field(
        ...,
        description="Original filename with extension"
    )
    file_size: Optional[int] = Field(
        None,
        description="File size in bytes (for validation)"
    )
    event_id: Optional[str] = Field(
        None,
        description="Event ID (required for event uploads)"
    )


class PresignedUrlResponse(BaseModel):
    """Response model with presigned URL details"""
    presigned_url: str = Field(..., description="Presigned URL for PUT upload")
    s3_key: str = Field(..., description="S3 object key (path)")
    public_url: str = Field(..., description="Public URL after upload completes")
    expires_in: int = Field(..., description="URL expiry time in seconds")
    max_size: int = Field(..., description="Maximum allowed file size in bytes")
    content_type: str = Field(..., description="Expected content type")


class StorageStatusResponse(BaseModel):
    """Response model for storage status"""
    s3_enabled: bool
    storage_type: str
    bucket_name: Optional[str] = None
    region: Optional[str] = None


# ==================== Endpoints ====================

@router.get("/status", response_model=StorageStatusResponse)
async def get_storage_status():
    """
    Get current storage configuration status

    Returns whether S3 is enabled and basic configuration info
    """
    if settings.S3_ENABLED:
        return StorageStatusResponse(
            s3_enabled=True,
            storage_type="s3",
            bucket_name=settings.S3_BUCKET_NAME,
            region=settings.AWS_REGION
        )
    else:
        return StorageStatusResponse(
            s3_enabled=False,
            storage_type="local",
            bucket_name=None,
            region=None
        )


import logging

logger = logging.getLogger(__name__)


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: PresignedUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a presigned URL for direct S3 upload

    This endpoint returns a presigned URL that the frontend can use to upload
    files directly to S3, bypassing the backend for large file transfers.

    **Upload Types:**
    - `hazard_image`: Hazard report photos (max 10MB, image/jpeg, image/png, image/webp)
    - `hazard_voice`: Voice notes for hazard reports (max 5MB, audio/webm, audio/mp3, audio/wav)
    - `profile`: User profile pictures (max 5MB, image/jpeg, image/png, image/webp)
    - `event`: Event photos (max 10MB, image/jpeg, image/png, image/webp)

    **Usage:**
    1. Call this endpoint to get a presigned URL
    2. Use the presigned URL to PUT the file directly to S3
    3. Use the `public_url` as the file reference in subsequent API calls
    """
    logger.info(f"Presigned URL request: type={request.upload_type}, content_type={request.content_type}, filename={request.filename}, size={request.file_size}")

    # Check if S3 is enabled
    if not s3_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 storage is not enabled. Please use local upload endpoints."
        )

    # Determine user_id parameter based on upload type
    user_id = None
    if request.upload_type == 'profile':
        user_id = str(current_user.id)
    elif request.upload_type == 'event':
        if not request.event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="event_id is required for event uploads"
            )
        user_id = request.event_id

    try:
        result = s3_service.generate_presigned_url(
            upload_type=request.upload_type,
            content_type=request.content_type,
            filename=request.filename,
            user_id=user_id,
            file_size=request.file_size
        )

        return PresignedUrlResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )


@router.delete("/file")
async def delete_uploaded_file(
    s3_key: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an uploaded file from S3

    **Note:** This endpoint should be used carefully. In most cases,
    file deletion should be handled by the respective resource endpoints
    (e.g., deleting a hazard report should also delete its associated files).
    """
    if not s3_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 storage is not enabled"
        )

    # Security check: Only allow deletion of files in allowed folders
    allowed_prefixes = ['hazards/', 'profiles/', 'events/', 'voice-notes/']
    if not any(s3_key.startswith(prefix) for prefix in allowed_prefixes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete files outside allowed folders"
        )

    # For profile pictures, ensure user can only delete their own
    if s3_key.startswith('profiles/'):
        user_folder = f"profiles/{current_user.id}/"
        if not s3_key.startswith(user_folder):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete other users' profile pictures"
            )

    success = s3_service.delete_file(s3_key)

    if success:
        return {"message": "File deleted successfully", "s3_key": s3_key}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )
