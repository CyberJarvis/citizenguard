"""
Certificates API Router
Endpoints for certificate generation, download, and verification
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_database
from app.middleware.rbac import get_current_user
from app.services.certificate_service import CertificateService
from app.services.email import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["Certificates"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class CertificateResponse(BaseModel):
    success: bool
    message: str
    certificate_id: Optional[str] = None
    certificate_url: Optional[str] = None


class CertificateListResponse(BaseModel):
    success: bool
    certificates: List[dict]
    total: int
    skip: int
    limit: int


class VerificationResponse(BaseModel):
    valid: bool
    message: str
    certificate: Optional[dict] = None


# ============================================================================
# CERTIFICATE ENDPOINTS
# ============================================================================

@router.post("/events/{event_id}/generate", response_model=CertificateResponse)
async def generate_certificate(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate certificate for current user's event attendance

    - User must have attended the event (registration_status = 'attended')
    - Certificate can only be generated once per event per user
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    success, message, certificate_data = await CertificateService.generate_certificate(
        db=db,
        event_id=event_id,
        user_id=user_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return CertificateResponse(
        success=True,
        message=message,
        certificate_id=certificate_data.get("certificate_id"),
        certificate_url=certificate_data.get("certificate_url")
    )


@router.get("/events/{event_id}/download")
async def download_event_certificate(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Download certificate for current user's event attendance
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    # Get registration with certificate
    registration = await db.event_registrations.find_one({
        "event_id": event_id,
        "user_id": user_id
    })

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    if not registration.get("certificate_generated") or not registration.get("certificate_url"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found. Please generate it first."
        )

    # Get file path
    certificate_url = registration.get("certificate_url")
    file_path = certificate_url.lstrip("/")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found"
        )

    # Get event for filename
    event = await db.events.find_one({"event_id": event_id})
    event_title = event.get("title", "Certificate") if event else "Certificate"
    filename = f"Certificate_{event_title.replace(' ', '_')[:30]}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.post("/events/{event_id}/email", response_model=CertificateResponse)
async def email_certificate(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Email certificate to current user

    - Certificate must be generated first
    - Sends email with download link
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    # Get registration
    registration = await db.event_registrations.find_one({
        "event_id": event_id,
        "user_id": user_id
    })

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )

    if not registration.get("certificate_generated"):
        # Generate certificate first
        success, message, certificate_data = await CertificateService.generate_certificate(
            db=db,
            event_id=event_id,
            user_id=user_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
    else:
        certificate_data = {
            "certificate_id": registration.get("certificate_id"),
            "certificate_url": registration.get("certificate_url")
        }

    # Get event details
    event = await db.events.find_one({"event_id": event_id})
    event_title = event.get("title", "Volunteer Event") if event else "Volunteer Event"

    # Get user email
    user = await db.users.find_one({"user_id": user_id})
    user_email = user.get("email") if user else registration.get("user_email")
    user_name = user.get("name") if user else registration.get("user_name", "Volunteer")

    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email not found"
        )

    # Send email
    email_sent = await EmailService.send_certificate_email(
        to_email=user_email,
        user_name=user_name,
        event_title=event_title,
        certificate_url=certificate_data.get("certificate_url"),
        certificate_id=certificate_data.get("certificate_id")
    )

    if email_sent:
        # Mark as emailed
        await CertificateService.mark_certificate_emailed(
            db=db,
            certificate_id=certificate_data.get("certificate_id")
        )

        return CertificateResponse(
            success=True,
            message="Certificate sent to your email",
            certificate_id=certificate_data.get("certificate_id"),
            certificate_url=certificate_data.get("certificate_url")
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again later."
        )


@router.get("/my", response_model=CertificateListResponse)
async def get_my_certificates(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all certificates for current user
    """
    user_id = current_user.get("user_id") or current_user.get("sub")

    success, message, certificates, total = await CertificateService.get_user_certificates(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit
    )

    return CertificateListResponse(
        success=success,
        certificates=certificates,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{certificate_id}/verify", response_model=VerificationResponse)
async def verify_certificate(
    certificate_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify a certificate (public endpoint)

    - No authentication required
    - Returns certificate details if valid
    """
    valid, message, verification_data = await CertificateService.verify_certificate(
        db=db,
        certificate_id=certificate_id
    )

    if not valid:
        return VerificationResponse(
            valid=False,
            message=message,
            certificate=None
        )

    return VerificationResponse(
        valid=True,
        message="Certificate is valid",
        certificate=verification_data
    )


@router.get("/{certificate_id}/download")
async def download_certificate_by_id(
    certificate_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Download certificate by ID (public for verification purposes)
    """
    success, message, certificate = await CertificateService.get_certificate(
        db=db,
        certificate_id=certificate_id
    )

    if not success or not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    certificate_url = certificate.get("certificate_url")
    if not certificate_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found"
        )

    file_path = certificate_url.lstrip("/")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found on server"
        )

    event_title = certificate.get("event_title", "Certificate")
    filename = f"Certificate_{event_title.replace(' ', '_')[:30]}.pdf"

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )
