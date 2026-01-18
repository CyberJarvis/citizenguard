"""
Authority API Endpoints
For authorities to verify reports, manage users, and access detailed information
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.user import User
from app.models.hazard import HazardReport, VerificationStatus, ApprovalSource
from app.models.verification import AIRecommendation
from app.models.rbac import Permission
from app.middleware.rbac import (
    require_authority,
    require_admin,
    require_permission,
    has_permission,
    filter_pii_fields,
    require_analyst_or_authority
)
from app.utils.audit import log_audit_event
from app.services.auto_ticket_service import get_auto_ticket_service
from app.services.approval_service import ApprovalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/authority", tags=["authority"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class VerifyReportRequest(BaseModel):
    """Request schema for verifying a report"""
    status: VerificationStatus = Field(..., description="Verification status")
    notes: Optional[str] = Field(default=None, description="Verification notes")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection reason if rejected")
    risk_level: Optional[str] = Field(default=None, description="Risk level: low, medium, high, critical")
    urgency: Optional[str] = Field(default=None, description="Urgency level")
    requires_immediate_action: bool = Field(default=False, description="Requires immediate action")


class ConfirmRecommendationRequest(BaseModel):
    """Request schema for confirming or overriding an AI recommendation"""
    action: str = Field(..., description="Action: confirm, override_approve, override_reject")
    notes: Optional[str] = Field(default=None, description="Confirmation/override notes")
    risk_level: Optional[str] = Field(default=None, description="Risk level: low, medium, high, critical")
    urgency: Optional[str] = Field(default=None, description="Urgency level")
    requires_immediate_action: bool = Field(default=False, description="Requires immediate action")


class RejectReportRequest(BaseModel):
    """Request schema for rejecting a report"""
    reason: str = Field(..., min_length=10, description="Rejection reason")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class ReportDetailResponse(BaseModel):
    """Detailed report response for authorities"""
    report_id: str
    hazard_type: str
    category: str
    description: Optional[str]
    location: dict
    weather: Optional[dict]
    verification_status: str
    verified_by: Optional[str]
    verified_by_name: Optional[str]
    verified_at: Optional[datetime]
    verification_notes: Optional[str]
    rejection_reason: Optional[str]
    risk_level: Optional[str]
    urgency: Optional[str]
    requires_immediate_action: bool

    # Reporter details (only for authorities)
    user_id: str
    user_name: Optional[str]
    user_email: Optional[str]
    user_phone: Optional[str]
    user_credibility: Optional[int]

    # NLP insights
    nlp_sentiment: Optional[str]
    nlp_keywords: Optional[List[str]]
    nlp_risk_score: Optional[float]
    nlp_summary: Optional[str]

    # Engagement
    likes: int
    comments: int
    views: int

    # Media
    image_url: str
    voice_note_url: Optional[str]

    created_at: datetime
    updated_at: datetime


class PendingReportsSummary(BaseModel):
    """Summary of pending reports"""
    pending: int
    high_priority: int
    verified: int
    rejected: int


# ============================================================================
# Verification Panel Endpoints
# ============================================================================

@router.get("/verification-panel/summary", response_model=PendingReportsSummary)
async def get_verification_summary(
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get summary of pending reports for verification panel

    Authority Only
    """
    try:
        # Count pending reports
        pending = await db.hazard_reports.count_documents({
            "verification_status": "pending",
            "is_deleted": False
        })

        # Count verified reports
        verified = await db.hazard_reports.count_documents({
            "verification_status": "verified",
            "is_deleted": False
        })

        # Count rejected reports
        rejected = await db.hazard_reports.count_documents({
            "verification_status": "rejected",
            "is_deleted": False
        })

        # Count high priority (high risk or urgent) among pending
        high_priority = await db.hazard_reports.count_documents({
            "verification_status": "pending",
            "is_deleted": False,
            "$or": [
                {"risk_level": "critical"},
                {"risk_level": "high"},
                {"urgency": "urgent"},
                {"requires_immediate_action": True}
            ]
        })

        return {
            "pending": pending,
            "high_priority": high_priority,
            "verified": verified,
            "rejected": rejected
        }

    except Exception as e:
        logger.error(f"Error getting verification summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch verification summary"
        )


@router.get("/verification-panel/reports")
async def get_pending_reports(
    verification_status: Optional[str] = Query(default="pending", description="Status filter: pending, verified, rejected, all"),
    priority: Optional[str] = Query(default=None, description="Priority filter: high, medium, low, all"),
    hazard_type: Optional[str] = Query(default=None, description="Hazard type filter"),
    search: Optional[str] = Query(default=None, description="Search query"),
    sort_by: Optional[str] = Query(default="newest", description="Sort by: newest, oldest, priority, risk"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get reports for verification panel with filters

    Authority Only - Includes full reporter details and NLP insights
    """
    try:
        # Build query
        query = {"is_deleted": False}

        # Status filter
        if verification_status and verification_status != "all":
            query["verification_status"] = verification_status

        # Hazard type filter
        if hazard_type and hazard_type != "all":
            query["hazard_type"] = hazard_type

        # Build complex filters
        and_conditions = []

        # Search filter
        if search:
            and_conditions.append({
                "$or": [
                    {"description": {"$regex": search, "$options": "i"}},
                    {"location.region": {"$regex": search, "$options": "i"}},
                    {"location.district": {"$regex": search, "$options": "i"}},
                    {"hazard_type": {"$regex": search, "$options": "i"}}
                ]
            })

        # Priority filter
        if priority and priority != "all":
            if priority == "high":
                and_conditions.append({
                    "$or": [
                        {"risk_level": "critical"},
                        {"risk_level": "high"},
                        {"urgency": "urgent"},
                        {"requires_immediate_action": True}
                    ]
                })
            elif priority == "medium":
                query["risk_level"] = "medium"
            elif priority == "low":
                and_conditions.append({
                    "$or": [
                        {"risk_level": "low"},
                        {"risk_level": {"$exists": False}}
                    ]
                })
                query["urgency"] = {"$ne": "urgent"}
                query["requires_immediate_action"] = False

        # Add $and conditions if present
        if and_conditions:
            query["$and"] = and_conditions

        # Determine sort order
        sort_field = "created_at"
        sort_order = -1  # -1 for descending, 1 for ascending

        if sort_by == "oldest":
            sort_order = 1
        elif sort_by == "priority":
            # Sort by risk_level and urgency
            sort_field = "risk_level"
            sort_order = 1  # Will show critical/high first due to alphabetical order
        elif sort_by == "risk":
            sort_field = "nlp_risk_score"
            sort_order = -1

        # Get reports
        cursor = db.hazard_reports.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
        reports = await cursor.to_list(length=limit)

        # Enhance with user data
        enhanced_reports = []
        for report_doc in reports:
            report = HazardReport.from_mongo(report_doc)

            # Get user details
            user_doc = await db.users.find_one({"user_id": report.user_id})
            user_details = {}

            if user_doc:
                # Authorities can see full user details
                user_details = {
                    "reporter_name": user_doc.get("name", "Anonymous"),
                    "user_email": user_doc.get("email"),
                    "user_phone": user_doc.get("phone"),
                    "user_credibility": user_doc.get("credibility_score", 50)
                }
            else:
                user_details = {
                    "reporter_name": "Anonymous"
                }

            # Combine report and user data
            report_dict = report.dict()
            report_dict.update(user_details)

            # Add computed priority field based on risk_level and urgency
            priority = "low"
            if report.requires_immediate_action or report.urgency == "urgent":
                priority = "high"
            elif report.risk_level in ["critical", "high"]:
                priority = "high"
            elif report.risk_level == "medium" or report.urgency == "high":
                priority = "medium"

            report_dict["priority"] = priority
            enhanced_reports.append(report_dict)

        # Get total count
        total_count = await db.hazard_reports.count_documents(query)

        return {
            "reports": enhanced_reports,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error fetching pending reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports"
        )


@router.get("/verification-panel/reports/{report_id}")
async def get_report_details(
    report_id: str,
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get full detailed view of a report for verification

    Authority Only - Includes all fields including PII and NLP insights
    """
    try:
        # Get report
        report_doc = await db.hazard_reports.find_one({"report_id": report_id})

        if not report_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        report = HazardReport.from_mongo(report_doc)

        # Get user details
        user_doc = await db.users.find_one({"user_id": report.user_id})

        # Build response with user details
        response = report.dict()

        if user_doc:
            response.update({
                "user_email": user_doc.get("email"),
                "user_phone": user_doc.get("phone"),
                "user_credibility": user_doc.get("credibility_score", 50),
                "user_total_reports": user_doc.get("total_reports", 0),
                "user_verified_reports": user_doc.get("verified_reports", 0)
            })

        # Increment views
        await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$inc": {"views": 1}}
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report details"
        )


@router.post("/verification-panel/reports/{report_id}/verify")
async def verify_report(
    report_id: str,
    verification: VerifyReportRequest,
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify or reject a hazard report

    Authority Only
    """
    try:
        # Check if report exists
        report_doc = await db.hazard_reports.find_one({"report_id": report_id})

        if not report_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        # Prepare update data
        update_data = {
            "verification_status": verification.status.value,
            "verified_by": current_user.user_id,
            "verified_by_name": current_user.name,
            "verified_at": datetime.now(timezone.utc),
            "verification_notes": verification.notes,
            "updated_at": datetime.now(timezone.utc)
        }

        # Add optional fields
        if verification.rejection_reason:
            update_data["rejection_reason"] = verification.rejection_reason

        if verification.risk_level:
            update_data["risk_level"] = verification.risk_level

        if verification.urgency:
            update_data["urgency"] = verification.urgency

        update_data["requires_immediate_action"] = verification.requires_immediate_action

        # Update report
        result = await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update report"
            )

        # Update user credibility if verified
        ticket_id = None
        if verification.status == VerificationStatus.VERIFIED:
            await db.users.update_one(
                {"user_id": report_doc["user_id"]},
                {
                    "$inc": {
                        "verified_reports": 1,
                        "credibility_score": 5  # Increase credibility
                    }
                }
            )

            # Auto-create ticket for verified reports
            try:
                # Refresh report_doc to get updated data
                updated_report = await db.hazard_reports.find_one({"report_id": report_id})
                if updated_report and not updated_report.get("has_ticket"):
                    auto_ticket_service = get_auto_ticket_service(db)
                    result = await auto_ticket_service.create_ticket_for_approved_report(
                        report_doc=updated_report,
                        approver=current_user,
                        approval_type="authority",
                        db=db
                    )
                    if result:
                        ticket, _ = result
                        ticket_id = ticket.ticket_id
                        logger.info(f"Auto-created ticket {ticket_id} for authority-verified report {report_id}")
            except Exception as ticket_error:
                logger.error(f"Failed to auto-create ticket for report {report_id}: {str(ticket_error)}")
                # Don't fail the verification if ticket creation fails

        elif verification.status == VerificationStatus.REJECTED:
            # Decrease credibility for rejected reports
            await db.users.update_one(
                {"user_id": report_doc["user_id"]},
                {"$inc": {"credibility_score": -3}}
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action=f"REPORT_{verification.status.value.upper()}",
            details={
                "report_id": report_id,
                "status": verification.status.value,
                "risk_level": verification.risk_level
            }
        )

        response_data = {
            "success": True,
            "message": f"Report {verification.status.value} successfully",
            "report_id": report_id,
            "status": verification.status.value
        }

        # Include ticket_id if a ticket was created
        if ticket_id:
            response_data["ticket_id"] = ticket_id
            response_data["message"] = f"Report {verification.status.value} successfully. Ticket {ticket_id} created."

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify report"
        )


# ============================================================================
# V2 Hybrid Verification Endpoints (Analyst & Authority)
# ============================================================================

@router.get("/recommendations/pending")
async def get_pending_recommendations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get reports with AI_RECOMMENDED status awaiting confirmation.

    These are reports with 75-85% AI verification score that need
    analyst/authority confirmation before ticket creation.

    Analyst & Authority Only
    """
    try:
        approval_service = ApprovalService(db)
        result = await approval_service.get_pending_recommendations(
            skip=skip,
            limit=limit
        )

        # Enhance with user data
        enhanced_reports = []
        for report_doc in result.get("reports", []):
            user_doc = await db.users.find_one({"user_id": report_doc.get("user_id")})
            report_dict = dict(report_doc)

            if user_doc:
                report_dict["reporter_name"] = user_doc.get("name", "Anonymous")
                report_dict["user_credibility"] = user_doc.get("credibility_score", 50)
            else:
                report_dict["reporter_name"] = "Anonymous"

            # Add AI verification info
            ai_result = report_doc.get("ai_verification_result", {})
            report_dict["ai_confidence_score"] = ai_result.get("composite_score", 0)
            report_dict["ai_recommendation"] = report_doc.get("ai_recommendation", "unknown")

            enhanced_reports.append(report_dict)

        return {
            "reports": enhanced_reports,
            "total": result.get("total", 0),
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error fetching pending recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pending recommendations"
        )


@router.post("/recommendations/{report_id}/confirm")
async def confirm_ai_recommendation(
    report_id: str,
    request: ConfirmRecommendationRequest,
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Confirm or override an AI recommendation for a report.

    Actions:
    - confirm: Accept the AI recommendation and create ticket
    - override_approve: Override AI and approve (for lower scores)
    - override_reject: Override AI and reject (for any score)

    Analyst & Authority Only
    """
    try:
        # Validate action
        valid_actions = ["confirm", "override_approve", "override_reject"]
        if request.action not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
            )

        approval_service = ApprovalService(db)

        if request.action == "confirm":
            # Confirm AI recommendation
            result = await approval_service.confirm_ai_recommendation(
                report_id=report_id,
                confirming_user=current_user,
                notes=request.notes
            )
        elif request.action == "override_approve":
            # Manual verification with override
            result = await approval_service.manual_verify_report(
                report_id=report_id,
                verifying_user=current_user,
                notes=request.notes,
                risk_level=request.risk_level,
                urgency=request.urgency,
                requires_immediate_action=request.requires_immediate_action
            )
        else:  # override_reject
            if not request.notes or len(request.notes) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rejection requires notes with at least 10 characters"
                )
            result = await approval_service.reject_report(
                report_id=report_id,
                rejecting_user=current_user,
                reason=request.notes
            )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to process recommendation")
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action=f"RECOMMENDATION_{request.action.upper()}",
            details={
                "report_id": report_id,
                "action": request.action,
                "notes": request.notes
            }
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming recommendation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process recommendation"
        )


@router.get("/manual-review-queue")
async def get_manual_review_queue(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get reports requiring manual review (40-75% AI score).

    These reports didn't get auto-approved or recommended,
    so they need full manual verification.

    Analyst & Authority Only
    """
    try:
        # Query for manual review reports
        query = {
            "is_deleted": False,
            "verification_status": "pending",
            "ai_recommendation": AIRecommendation.REVIEW.value
        }

        cursor = db.hazard_reports.find(query).sort("created_at", -1).skip(skip).limit(limit)
        reports = await cursor.to_list(length=limit)

        # Enhance with user data
        enhanced_reports = []
        for report_doc in reports:
            user_doc = await db.users.find_one({"user_id": report_doc.get("user_id")})
            report_dict = dict(report_doc)
            report_dict["_id"] = str(report_dict["_id"])

            if user_doc:
                report_dict["reporter_name"] = user_doc.get("name", "Anonymous")
                report_dict["user_credibility"] = user_doc.get("credibility_score", 50)
            else:
                report_dict["reporter_name"] = "Anonymous"

            # Add AI verification info
            ai_result = report_doc.get("ai_verification_result", {})
            report_dict["ai_confidence_score"] = ai_result.get("composite_score", 0)

            enhanced_reports.append(report_dict)

        total = await db.hazard_reports.count_documents(query)

        return {
            "reports": enhanced_reports,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error fetching manual review queue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch manual review queue"
        )


@router.post("/manual-verify/{report_id}")
async def manual_verify_report(
    report_id: str,
    verification: VerifyReportRequest,
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Manually verify a report (for manual review queue).

    This sets the approval_source to AUTHORITY_MANUAL or ANALYST_VERIFIED
    based on the user's role.

    Analyst & Authority Only
    """
    try:
        approval_service = ApprovalService(db)

        if verification.status == VerificationStatus.VERIFIED:
            result = await approval_service.manual_verify_report(
                report_id=report_id,
                verifying_user=current_user,
                notes=verification.notes,
                risk_level=verification.risk_level,
                urgency=verification.urgency,
                requires_immediate_action=verification.requires_immediate_action
            )
        elif verification.status == VerificationStatus.REJECTED:
            if not verification.rejection_reason or len(verification.rejection_reason) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rejection requires a reason with at least 10 characters"
                )
            result = await approval_service.reject_report(
                report_id=report_id,
                rejecting_user=current_user,
                reason=verification.rejection_reason
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manual verification status must be 'verified' or 'rejected'"
            )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to verify report")
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action=f"MANUAL_VERIFY_{verification.status.value.upper()}",
            details={
                "report_id": report_id,
                "status": verification.status.value,
                "risk_level": verification.risk_level
            }
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error manually verifying report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify report"
        )


@router.get("/verification-stats")
async def get_verification_stats(
    current_user: User = Depends(require_analyst_or_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get verification statistics including hybrid mode metrics.

    Analyst & Authority Only
    """
    try:
        # Count by AI recommendation
        auto_approved = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "approval_source": ApprovalSource.AI_AUTO.value
        })

        ai_recommended_confirmed = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "approval_source": ApprovalSource.AI_RECOMMENDED.value
        })

        authority_manual = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "approval_source": ApprovalSource.AUTHORITY_MANUAL.value
        })

        analyst_verified = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "approval_source": ApprovalSource.ANALYST_VERIFIED.value
        })

        # Pending recommendations
        pending_recommendations = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "verification_status": "pending",
            "ai_recommendation": AIRecommendation.RECOMMEND_APPROVE.value,
            "requires_authority_confirmation": True
        })

        # Manual review queue
        manual_review_queue = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "verification_status": "pending",
            "ai_recommendation": AIRecommendation.REVIEW.value
        })

        # Auto rejected
        auto_rejected = await db.hazard_reports.count_documents({
            "is_deleted": False,
            "verification_status": "rejected",
            "ai_recommendation": AIRecommendation.REJECT.value
        })

        # Total verified
        total_verified = auto_approved + ai_recommended_confirmed + authority_manual + analyst_verified

        return {
            "hybrid_mode": {
                "auto_approved": auto_approved,
                "ai_recommended_confirmed": ai_recommended_confirmed,
                "authority_manual": authority_manual,
                "analyst_verified": analyst_verified,
                "auto_rejected": auto_rejected,
                "total_verified": total_verified
            },
            "queues": {
                "pending_recommendations": pending_recommendations,
                "manual_review": manual_review_queue
            },
            "automation_rate": round(
                (auto_approved / total_verified * 100) if total_verified > 0 else 0, 1
            )
        }

    except Exception as e:
        logger.error(f"Error fetching verification stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch verification statistics"
        )


# ============================================================================
# User Management Endpoints (Authority & Admin)
# ============================================================================

class UserListResponse(BaseModel):
    """Response for user list"""
    user_id: str
    email: Optional[str]
    name: Optional[str]
    role: str
    is_active: bool
    is_banned: bool
    credibility_score: int
    total_reports: int
    verified_reports: int
    created_at: datetime
    last_login: Optional[datetime]


class BanUserRequest(BaseModel):
    """Request to ban a user"""
    reason: str = Field(..., min_length=10, max_length=500)


class AssignRoleRequest(BaseModel):
    """Request to assign a role"""
    role: str = Field(..., description="New role: citizen, analyst, authority, authority_admin")


@router.get("/users")
async def list_users(
    role_filter: Optional[str] = Query(default=None, description="Filter by role"),
    status_filter: Optional[str] = Query(default=None, description="active, banned, inactive"),
    search: Optional[str] = Query(default=None, description="Search by name or email"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get list of users with filters

    Authority & Admin only
    """
    try:
        # Build query
        query = {}

        # Role filter
        if role_filter:
            query["role"] = role_filter

        # Status filter
        if status_filter == "active":
            query["is_active"] = True
            query["is_banned"] = False
        elif status_filter == "banned":
            query["is_banned"] = True
        elif status_filter == "inactive":
            query["is_active"] = False

        # Search filter
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]

        # Get users
        cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)

        # Format response
        user_list = []
        for user_doc in users:
            user = User.from_mongo(user_doc)
            user_list.append({
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "is_active": user.is_active,
                "is_banned": user.is_banned,
                "ban_reason": user.ban_reason if user.is_banned else None,
                "credibility_score": user.credibility_score,
                "total_reports": user.total_reports,
                "verified_reports": user.verified_reports,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "authority_organization": user.authority_organization,
                "authority_designation": user.authority_designation
            })

        # Get total count
        total_count = await db.users.count_documents(query)

        return {
            "users": user_list,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get detailed user information

    Authority & Admin only
    """
    try:
        user_doc = await db.users.find_one({"user_id": user_id})

        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = User.from_mongo(user_doc)

        # Get user's reports
        report_count = await db.hazard_reports.count_documents({"user_id": user_id})
        verified_count = await db.hazard_reports.count_documents({
            "user_id": user_id,
            "verification_status": "verified"
        })
        pending_count = await db.hazard_reports.count_documents({
            "user_id": user_id,
            "verification_status": "pending"
        })

        return {
            "user": user.dict(),
            "statistics": {
                "total_reports": report_count,
                "verified_reports": verified_count,
                "pending_reports": pending_count,
                "credibility_score": user.credibility_score
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user details"
        )


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    request: BanUserRequest,
    current_user: User = Depends(require_admin),  # Admin only
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Ban a user

    Admin only
    """
    try:
        # Check if user exists
        user_doc = await db.users.find_one({"user_id": user_id})

        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Cannot ban yourself
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot ban yourself"
            )

        # Update user
        result = await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "is_banned": True,
                    "ban_reason": request.reason,
                    "banned_at": datetime.now(timezone.utc),
                    "banned_by": current_user.user_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to ban user"
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action="USER_BANNED",
            details={
                "banned_user_id": user_id,
                "reason": request.reason
            }
        )

        return {
            "success": True,
            "message": f"User {user_id} has been banned",
            "reason": request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error banning user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ban user"
        )


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    current_user: User = Depends(require_admin),  # Admin only
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Unban a user

    Admin only
    """
    try:
        # Update user
        result = await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "is_banned": False,
                    "ban_reason": None,
                    "banned_at": None,
                    "banned_by": None,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action="USER_UNBANNED",
            details={"unbanned_user_id": user_id}
        )

        return {
            "success": True,
            "message": f"User {user_id} has been unbanned"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unbanning user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unban user"
        )


@router.post("/users/{user_id}/assign-role")
async def assign_role(
    user_id: str,
    request: AssignRoleRequest,
    current_user: User = Depends(require_admin),  # Admin only
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Assign a role to a user

    Admin only
    """
    try:
        # Validate role
        valid_roles = ["citizen", "analyst", "authority", "authority_admin"]
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )

        # Get current user data
        user_doc = await db.users.find_one({"user_id": user_id})

        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        current_role = user_doc.get("role")

        # Update user role
        result = await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "role": request.role,
                    "previous_role": current_role,
                    "role_assigned_by": current_user.user_id,
                    "role_assigned_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign role"
            )

        # Log audit event
        await log_audit_event(
            db=db,
            user_id=current_user.user_id,
            action="ROLE_ASSIGNED",
            details={
                "target_user_id": user_id,
                "old_role": current_role,
                "new_role": request.role
            }
        )

        return {
            "success": True,
            "message": f"Role updated to {request.role}",
            "user_id": user_id,
            "old_role": current_role,
            "new_role": request.role
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role"
        )


# ============================================================================
# Authority Dashboard & Analytics
# ============================================================================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get dashboard statistics for Authority

    Authority & Admin only
    """
    try:
        # Pending reports count
        pending_reports = await db.hazard_reports.count_documents({
            "verification_status": "pending",
            "is_deleted": False
        })

        # Verified reports (last 7 days)
        from datetime import timedelta
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        recent_verified = await db.hazard_reports.count_documents({
            "verification_status": "verified",
            "verified_at": {"$gte": seven_days_ago}
        })

        # High priority reports
        high_priority = await db.hazard_reports.count_documents({
            "verification_status": "pending",
            "is_deleted": False,
            "$or": [
                {"risk_level": "critical"},
                {"risk_level": "high"},
                {"urgency": "urgent"},
                {"requires_immediate_action": True}
            ]
        })

        # Active alerts
        active_alerts = await db.alerts.count_documents({
            "status": "active",
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gte": datetime.now(timezone.utc)}}
            ]
        })

        # Total users
        total_users = await db.users.count_documents({})

        # Banned users
        banned_users = await db.users.count_documents({"is_banned": True})

        # Recent activity (reports by day for last 7 days)
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": seven_days_ago},
                    "is_deleted": False
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        activity_data = []
        async for doc in db.hazard_reports.aggregate(pipeline):
            activity_data.append({
                "date": doc["_id"],
                "count": doc["count"]
            })

        return {
            "reports": {
                "pending": pending_reports,
                "high_priority": high_priority,
                "recently_verified": recent_verified
            },
            "alerts": {
                "active": active_alerts
            },
            "users": {
                "total": total_users,
                "banned": banned_users
            },
            "activity": activity_data,
            "user": {
                "name": current_user.name,
                "organization": current_user.authority_organization,
                "designation": current_user.authority_designation
            }
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard statistics"
        )


@router.get("/analytics")
async def get_analytics(
    date_range: Optional[str] = Query(default="7days", description="Date range: 7days, 30days, 90days, year, all"),
    region: Optional[str] = Query(default=None, description="Filter by region"),
    current_user: User = Depends(require_authority),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get comprehensive analytics for authority dashboard

    Authority & Admin only
    """
    try:
        from datetime import timedelta

        # Determine date range
        now = datetime.now(timezone.utc)
        date_filters = {
            "7days": now - timedelta(days=7),
            "30days": now - timedelta(days=30),
            "90days": now - timedelta(days=90),
            "year": now - timedelta(days=365),
            "all": None
        }

        start_date = date_filters.get(date_range, date_filters["7days"])

        # Build base query
        base_query = {"is_deleted": False}
        if start_date:
            base_query["created_at"] = {"$gte": start_date}
        if region:
            base_query["location.region"] = region

        # Previous period query for comparisons
        prev_query = {"is_deleted": False}
        if start_date:
            period_length = (now - start_date).days
            prev_start = start_date - timedelta(days=period_length)
            prev_query["created_at"] = {"$gte": prev_start, "$lt": start_date}
        if region:
            prev_query["location.region"] = region

        # Get total reports
        total_reports = await db.hazard_reports.count_documents(base_query)
        prev_total = await db.hazard_reports.count_documents(prev_query)

        # Calculate change percentage
        total_change = 0
        if prev_total > 0:
            total_change = round(((total_reports - prev_total) / prev_total) * 100, 1)

        # Get reports by status
        pending_reports = await db.hazard_reports.count_documents({**base_query, "verification_status": "pending"})
        verified_reports = await db.hazard_reports.count_documents({**base_query, "verification_status": "verified"})
        rejected_reports = await db.hazard_reports.count_documents({**base_query, "verification_status": "rejected"})

        # Get high priority count
        high_priority = await db.hazard_reports.count_documents({
            **base_query,
            "$or": [
                {"risk_level": "critical"},
                {"risk_level": "high"},
                {"urgency": "urgent"},
                {"requires_immediate_action": True}
            ]
        })

        # Calculate percentages
        pending_percentage = round((pending_reports / total_reports * 100), 1) if total_reports > 0 else 0
        verified_percentage = round((verified_reports / total_reports * 100), 1) if total_reports > 0 else 0
        high_priority_percentage = round((high_priority / total_reports * 100), 1) if total_reports > 0 else 0

        # Timeline data
        timeline_data = []
        if start_date:
            days = min((now - start_date).days, 365)  # Cap at 365 days
            for i in range(days + 1):
                day_start = start_date + timedelta(days=i)
                day_end = day_start + timedelta(days=1)

                try:
                    count = await db.hazard_reports.count_documents({
                        "is_deleted": False,
                        "created_at": {"$gte": day_start, "$lt": day_end}
                    })

                    timeline_data.append({
                        "date": day_start.isoformat(),
                        "count": count
                    })
                except Exception as e:
                    logger.warning(f"Error counting reports for {day_start}: {str(e)}")

        # Reports by hazard type
        hazard_type_pipeline = [
            {"$match": base_query},
            {"$group": {"_id": "$hazard_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        hazard_types = {}
        async for doc in db.hazard_reports.aggregate(hazard_type_pipeline):
            hazard_types[doc["_id"]] = doc["count"]

        # Reports by region
        region_pipeline = [
            {"$match": base_query},
            {"$group": {"_id": "$location.region", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        regions_data = {}
        async for doc in db.hazard_reports.aggregate(region_pipeline):
            regions_data[doc["_id"] or "Unknown"] = doc["count"]

        # Get all unique regions for filter
        all_regions_raw = await db.hazard_reports.distinct("location.region")
        all_regions = [r for r in all_regions_raw if r]

        # Calculate average response time
        verified_with_time = await db.hazard_reports.find({
            **base_query,
            "verification_status": "verified",
            "verified_at": {"$exists": True}
        }).to_list(length=1000)

        total_response_time = 0
        count_with_time = 0
        for report in verified_with_time:
            if report.get("verified_at") and report.get("created_at"):
                response_time = (report["verified_at"] - report["created_at"]).total_seconds() / 3600
                total_response_time += response_time
                count_with_time += 1

        avg_response_time_hours = total_response_time / count_with_time if count_with_time > 0 else 0
        avg_response_time = f"{int(avg_response_time_hours)}h {int((avg_response_time_hours % 1) * 60)}m"

        # Verification rate
        verification_rate = round((verified_reports / total_reports * 100), 1) if total_reports > 0 else 0

        # Active reporters
        active_reporters = len(await db.hazard_reports.distinct("user_id", base_query))

        # Recent activity
        try:
            recent_reports = await db.hazard_reports.find(base_query).sort("created_at", -1).limit(20).to_list(length=20)
            recent_activity = []
            for report in recent_reports:
                if report.get("created_at"):
                    recent_activity.append({
                        "hazard_type": str(report.get("hazard_type", "Unknown")),
                        "type": str(report.get("verification_status", "pending")),
                        "verified_by": str(report.get("verified_by_name", "")) if report.get("verified_by_name") else None,
                        "timestamp": report["created_at"].isoformat()
                    })
        except Exception as e:
            logger.warning(f"Error fetching recent activity: {str(e)}")
            recent_activity = []

        return {
            "metrics": {
                "total_reports": total_reports,
                "total_change": total_change,
                "pending_reports": pending_reports,
                "pending_percentage": pending_percentage,
                "verified_reports": verified_reports,
                "verified_percentage": verified_percentage,
                "high_priority": high_priority,
                "high_priority_percentage": high_priority_percentage
            },
            "timeline": timeline_data,
            "by_status": {
                "pending": pending_reports,
                "verified": verified_reports,
                "rejected": rejected_reports
            },
            "by_hazard_type": hazard_types,
            "by_region": regions_data,
            "regions": all_regions,
            "performance": {
                "avg_response_time": avg_response_time,
                "verification_rate": verification_rate,
                "active_reporters": active_reporters
            },
            "recent_activity": recent_activity
        }

    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics"
        )


# Export router
__all__ = ["router"]
