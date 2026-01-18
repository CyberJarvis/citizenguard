"""
Organizer API Endpoints
Handles organizer applications, verification, and admin review workflows.
"""

import logging
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

from app.database import get_database
from app.models.user import User
from app.models.community import (
    OrganizerApplication,
    OrganizerApplicationCreate,
    OrganizerApplicationReview,
    ApplicationStatus,
    INDIAN_COASTAL_ZONES,
    INDIAN_COASTAL_STATES,
)
from app.middleware.rbac import get_current_user, require_admin
from app.services.organizer_service import get_organizer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizer", tags=["organizer"])


# ============================================================================
# Response Models
# ============================================================================

class EligibilityResponse(BaseModel):
    """Response model for eligibility check"""
    eligible: bool
    reason: Optional[str] = None
    message: str
    credibility_score: int
    required_score: int
    existing_application: Optional[dict] = None
    can_reapply: Optional[bool] = None
    cooldown_ends: Optional[str] = None


class ApplicationResponse(BaseModel):
    """Response model for application submission"""
    success: bool
    message: str
    application: Optional[dict] = None


class ApplicationListResponse(BaseModel):
    """Response model for application list"""
    success: bool
    applications: list
    total: int
    skip: int
    limit: int


# ============================================================================
# Public Endpoints (Authenticated Users)
# ============================================================================

@router.get("/eligibility", response_model=EligibilityResponse)
async def check_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Check if the current user is eligible to apply as a verified organizer.

    Requirements:
    - Credibility score >= 80
    - No pending application
    - Not already a verified organizer
    - Not in cooldown period after rejection
    """
    try:
        service = get_organizer_service(db)
        result = await service.check_eligibility(current_user)
        return EligibilityResponse(**result)
    except Exception as e:
        logger.error(f"Error checking eligibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check eligibility"
        )


@router.get("/zones")
async def get_coastal_zones():
    """Get list of valid Indian coastal zones for the application form."""
    return {
        "success": True,
        "coastal_zones": INDIAN_COASTAL_ZONES,
        "states": INDIAN_COASTAL_STATES
    }


@router.post("/apply", response_model=ApplicationResponse)
async def submit_application(
    name: str = Form(..., min_length=2, max_length=100),
    email: EmailStr = Form(...),
    phone: str = Form(..., pattern=r"^\+?[1-9]\d{9,14}$"),
    coastal_zone: str = Form(...),
    state: str = Form(...),
    aadhaar_document: UploadFile = File(..., description="Aadhaar document (PDF, JPEG, PNG, max 5MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Submit an organizer application with Aadhaar document.

    Requirements:
    - Credibility score >= 80
    - Valid Aadhaar document (PDF/Image, max 5MB)
    - Valid coastal zone and state
    """
    try:
        service = get_organizer_service(db)

        # Create application data
        application_data = OrganizerApplicationCreate(
            name=name,
            email=email,
            phone=phone,
            coastal_zone=coastal_zone,
            state=state
        )

        success, message, application = await service.submit_application(
            current_user,
            application_data,
            aadhaar_document
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return ApplicationResponse(
            success=True,
            message=message,
            application={
                "application_id": application.application_id,
                "status": application.status.value,
                "applied_at": application.applied_at.isoformat()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application"
        )


@router.get("/application-status")
async def get_application_status(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get the current user's organizer application status.
    Returns null if no application exists.
    """
    try:
        service = get_organizer_service(db)
        application = await service.get_application_status(current_user.user_id)

        if not application:
            return {
                "success": True,
                "has_application": False,
                "application": None
            }

        return {
            "success": True,
            "has_application": True,
            "application": {
                "application_id": application.application_id,
                "name": application.name,
                "email": application.email,
                "phone": application.phone,
                "coastal_zone": application.coastal_zone,
                "state": application.state,
                "credibility_at_application": application.credibility_at_application,
                "status": application.status.value,
                "applied_at": application.applied_at.isoformat(),
                "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None,
                "rejection_reason": application.rejection_reason
            }
        }

    except Exception as e:
        logger.error(f"Error getting application status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application status"
        )


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/applications", response_model=ApplicationListResponse)
async def list_applications(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin Only - List all organizer applications with optional status filter.
    """
    try:
        service = get_organizer_service(db)

        # Parse status filter
        app_status = None
        if status_filter:
            try:
                app_status = ApplicationStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: pending, approved, rejected"
                )

        applications, total = await service.get_all_applications(
            status=app_status,
            skip=skip,
            limit=limit
        )

        # Convert to response format
        app_list = []
        for app in applications:
            app_list.append({
                "application_id": app.application_id,
                "user_id": app.user_id,
                "name": app.name,
                "email": app.email,
                "phone": app.phone,
                "coastal_zone": app.coastal_zone,
                "state": app.state,
                "credibility_at_application": app.credibility_at_application,
                "status": app.status.value,
                "applied_at": app.applied_at.isoformat(),
                "reviewed_by_name": app.reviewed_by_name,
                "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
                "rejection_reason": app.rejection_reason
            })

        return ApplicationListResponse(
            success=True,
            applications=app_list,
            total=total,
            skip=skip,
            limit=limit
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list applications"
        )


@router.get("/admin/applications/{application_id}")
async def get_application_detail(
    application_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin Only - Get detailed information about a specific application.
    """
    try:
        service = get_organizer_service(db)
        application = await service.get_application_by_id(application_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        return {
            "success": True,
            "application": {
                "application_id": application.application_id,
                "user_id": application.user_id,
                "name": application.name,
                "email": application.email,
                "phone": application.phone,
                "coastal_zone": application.coastal_zone,
                "state": application.state,
                "aadhaar_document_url": application.aadhaar_document_url,
                "credibility_at_application": application.credibility_at_application,
                "status": application.status.value,
                "applied_at": application.applied_at.isoformat(),
                "reviewed_by_id": application.reviewed_by_id,
                "reviewed_by_name": application.reviewed_by_name,
                "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None,
                "rejection_reason": application.rejection_reason
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application details"
        )


@router.get("/admin/applications/{application_id}/aadhaar")
async def get_aadhaar_document(
    application_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin Only - Get the Aadhaar document for an application.
    Returns the file for viewing.
    """
    try:
        service = get_organizer_service(db)
        file_path = await service.get_aadhaar_document_path(application_id)

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application or document not found"
            )

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )

        # Determine media type
        extension = file_path.split(".")[-1].lower()
        media_type_map = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png"
        }
        media_type = media_type_map.get(extension, "application/octet-stream")

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=f"aadhaar_{application_id}.{extension}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Aadhaar document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document"
        )


@router.post("/admin/applications/{application_id}/approve")
async def approve_application(
    application_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin Only - Approve an organizer application.
    This will upgrade the user's role to VERIFIED_ORGANIZER.
    """
    try:
        service = get_organizer_service(db)
        success, message, application = await service.approve_application(
            application_id,
            current_user
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "application": {
                "application_id": application.application_id,
                "status": application.status.value,
                "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve application"
        )


class RejectRequest(BaseModel):
    """Request body for rejecting an application"""
    rejection_reason: str


@router.post("/admin/applications/{application_id}/reject")
async def reject_application(
    application_id: str,
    request: RejectRequest,
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin Only - Reject an organizer application with a reason.
    """
    try:
        service = get_organizer_service(db)
        success, message, application = await service.reject_application(
            application_id,
            current_user,
            request.rejection_reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        return {
            "success": True,
            "message": message,
            "application": {
                "application_id": application.application_id,
                "status": application.status.value,
                "rejection_reason": application.rejection_reason,
                "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject application"
        )


@router.get("/admin/statistics")
async def get_organizer_statistics(
    current_user: User = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Admin Only - Get organizer application statistics for dashboard.
    """
    try:
        service = get_organizer_service(db)
        stats = await service.get_statistics()

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )
