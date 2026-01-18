"""
Verification API Routes
Endpoints for the 6-layer verification pipeline.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.middleware.rbac import get_current_user, require_analyst, require_admin
from app.models.hazard import HazardReport, VerificationStatus
from app.models.verification import (
    VerificationResult, VerificationDecision, VerificationAudit,
    VerificationQueueItem, AnalystDecisionRequest, VerificationStatsResponse,
    VerificationThresholds, LayerName
)
from app.services.verification_service import (
    get_verification_service, initialize_verification_service, VerificationService
)
from app.services.auto_ticket_service import get_auto_ticket_service
from app.services.s3_service import s3_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["Verification"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_verification_service_dep(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> VerificationService:
    """Get initialized verification service."""
    service = get_verification_service(db)
    if not service._initialized:
        await service.initialize()
    return service


def map_decision_to_status(decision: VerificationDecision) -> VerificationStatus:
    """Map verification decision to hazard report status."""
    mapping = {
        VerificationDecision.AUTO_APPROVED: VerificationStatus.VERIFIED,
        VerificationDecision.MANUAL_REVIEW: VerificationStatus.NEEDS_MANUAL_REVIEW,
        VerificationDecision.AI_RECOMMENDED: VerificationStatus.NEEDS_MANUAL_REVIEW,  # Legacy - treat as manual review
        VerificationDecision.REJECTED: VerificationStatus.REJECTED,
        VerificationDecision.AUTO_REJECTED: VerificationStatus.AUTO_REJECTED
    }
    return mapping.get(decision, VerificationStatus.NEEDS_MANUAL_REVIEW)  # Default to needs review


# =============================================================================
# PUBLIC HEALTH CHECK (must be before dynamic routes)
# =============================================================================

@router.get("/health")
async def verification_health():
    """
    Health check for verification service.

    Public endpoint - no authentication required.
    """
    try:
        service = get_verification_service()
        return {
            "status": "healthy" if service._initialized else "not_initialized",
            "initialized": service._initialized,
            "layers": ["geofence", "weather", "text", "image", "reporter"],
            "thresholds": {
                "auto_approve": service.AUTO_APPROVE_THRESHOLD,
                "manual_review": service.MANUAL_REVIEW_THRESHOLD
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# =============================================================================
# STATIC ROUTES (must be before dynamic /{report_id} routes)
# =============================================================================

@router.get("/stats", response_model=VerificationStatsResponse)
async def get_verification_stats(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get verification statistics.

    Returns counts, averages, and layer pass rates.

    Requires Analyst role or higher.
    """
    from datetime import timedelta

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        # Aggregate verification statistics
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lte": end_date},
                    "verification_status": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "auto_approved": {
                        "$sum": {"$cond": [{"$eq": ["$verification_status", "verified"]}, 1, 0]}
                    },
                    "manual_review": {
                        "$sum": {"$cond": [{"$eq": ["$verification_status", "needs_manual_review"]}, 1, 0]}
                    },
                    "rejected": {
                        "$sum": {"$cond": [{"$eq": ["$verification_status", "rejected"]}, 1, 0]}
                    },
                    "auto_rejected": {
                        "$sum": {"$cond": [{"$eq": ["$verification_status", "auto_rejected"]}, 1, 0]}
                    },
                    "avg_score": {"$avg": "$verification_score"}
                }
            }
        ]

        result = await db.hazard_reports.aggregate(pipeline).to_list(1)

        if result:
            stats = result[0]
        else:
            stats = {
                "total": 0,
                "auto_approved": 0,
                "manual_review": 0,
                "rejected": 0,
                "auto_rejected": 0,
                "avg_score": 0
            }

        return VerificationStatsResponse(
            total_verifications=stats.get("total", 0),
            auto_approved_count=stats.get("auto_approved", 0),
            manual_review_count=stats.get("manual_review", 0),
            rejected_count=stats.get("rejected", 0),
            auto_rejected_count=stats.get("auto_rejected", 0),
            avg_composite_score=stats.get("avg_score", 0) or 0,
            avg_processing_time_ms=0,
            layer_pass_rates={},
            period_start=start_date,
            period_end=end_date
        )

    except Exception as e:
        logger.error(f"Error fetching verification stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch verification statistics"
        )


@router.get("/thresholds", response_model=VerificationThresholds)
async def get_thresholds(
    current_user: User = Depends(require_analyst)
):
    """
    Get current verification thresholds.

    Requires Analyst role or higher.
    """
    service = get_verification_service()
    return VerificationThresholds(
        auto_approve_threshold=service.AUTO_APPROVE_THRESHOLD,
        manual_review_threshold=service.MANUAL_REVIEW_THRESHOLD,
        geofence_inland_limit_km=20.0,
        geofence_offshore_limit_km=30.0,
        weight_geofence=service.BASE_WEIGHTS[LayerName.GEOFENCE],
        weight_weather=service.BASE_WEIGHTS[LayerName.WEATHER],
        weight_text=service.BASE_WEIGHTS[LayerName.TEXT],
        weight_image=service.BASE_WEIGHTS[LayerName.IMAGE],
        weight_reporter=service.BASE_WEIGHTS[LayerName.REPORTER]
    )


# =============================================================================
# ANALYST ENDPOINTS
# =============================================================================

@router.get("/queue", response_model=List[VerificationQueueItem])
async def get_verification_queue(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get reports awaiting manual review.

    Returns reports with verification_status = 'needs_manual_review'
    sorted by creation date (oldest first for FIFO processing).

    Requires Analyst role or higher.
    """
    try:
        # Query reports needing manual review
        cursor = db.hazard_reports.find({
            "verification_status": VerificationStatus.NEEDS_MANUAL_REVIEW.value
        }).sort("created_at", 1).skip(offset).limit(limit)

        queue_items = []
        now = datetime.now(timezone.utc)

        async for doc in cursor:
            # Work directly with raw document to avoid enum validation issues
            # Some old records might have hazard_type values that don't match current enums

            # Calculate time in queue
            created_at = doc.get("created_at")
            if created_at:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                time_in_queue = int((now - created_at).total_seconds() / 60)
            else:
                created_at = now
                time_in_queue = 0

            # Build layer summary from verification result
            layer_summary = {}
            verification_result = doc.get("verification_result")
            if verification_result and "layer_results" in verification_result:
                for layer in verification_result["layer_results"]:
                    layer_name = layer.get("layer_name", "unknown")
                    layer_status = layer.get("status", "unknown")
                    layer_summary[layer_name] = layer_status

            # Extract location info
            location = doc.get("location", {})
            if isinstance(location, dict):
                lat = location.get("latitude", 0)
                lon = location.get("longitude", 0)
                # Try multiple fields for location name
                district = location.get("district")
                region = location.get("region")
                address = location.get("address")
                # Build location name from available fields
                if district and region:
                    location_name = f"{district}, {region}"
                elif district:
                    location_name = district
                elif region:
                    location_name = region
                elif address:
                    location_name = address
                elif lat and lon:
                    location_name = f"{lat:.4f}, {lon:.4f}"
                else:
                    location_name = "Unknown location"
            else:
                location_name = "Unknown location"

            # Get hazard type as string
            hazard_type = doc.get("hazard_type", "Unknown")
            if hasattr(hazard_type, 'value'):
                hazard_type = hazard_type.value

            queue_items.append(VerificationQueueItem(
                report_id=doc.get("report_id", ""),
                verification_id=doc.get("verification_id") or "",
                hazard_type=str(hazard_type),
                location_name=location_name,
                composite_score=doc.get("verification_score") or 0.0,
                decision=VerificationDecision.MANUAL_REVIEW,
                layer_summary=layer_summary,
                reporter_name=doc.get("user_name"),
                created_at=created_at,
                time_in_queue_minutes=time_in_queue
            ))

        return queue_items

    except Exception as e:
        logger.error(f"Error fetching verification queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch verification queue"
        )


@router.get("/{report_id}")
async def get_verification_details(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get full verification details for a report.

    Returns all layer results, scores, and recommendations.

    Requires Analyst role or higher.
    """
    # Find the report
    doc = await db.hazard_reports.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found"
        )

    # Work directly with raw document to avoid enum validation issues
    hazard_type = doc.get("hazard_type", "Unknown")
    if hasattr(hazard_type, 'value'):
        hazard_type = hazard_type.value

    verification_status = doc.get("verification_status", "pending")
    if hasattr(verification_status, 'value'):
        verification_status = verification_status.value

    # Extract location info
    location = doc.get("location", {})
    if isinstance(location, dict):
        location_data = {
            "latitude": location.get("latitude", 0),
            "longitude": location.get("longitude", 0),
            "address": location.get("address")
        }
    else:
        location_data = {"latitude": 0, "longitude": 0, "address": None}

    # Handle datetime fields
    created_at = doc.get("created_at")
    if created_at:
        created_at = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
    verified_at = doc.get("verified_at")
    if verified_at:
        verified_at = verified_at.isoformat() if hasattr(verified_at, 'isoformat') else str(verified_at)

    # Fetch additional reporter info
    reporter_data = {
        "user_id": doc.get("user_id"),
        "user_name": doc.get("user_name") or "Unknown",
        "name": doc.get("user_name") or "Unknown",
        "email": None,
        "phone": None,
        "reports_count": 0,
        "credibility_score": 50
    }

    # Get reporter details from users collection
    if doc.get("user_id"):
        try:
            user_doc = await db.users.find_one({"user_id": doc.get("user_id")})
            if not user_doc:
                # Try by ObjectId
                from bson import ObjectId
                try:
                    user_doc = await db.users.find_one({"_id": ObjectId(str(doc.get("user_id")))})
                except:
                    pass

            if user_doc:
                reporter_data["name"] = user_doc.get("name") or user_doc.get("full_name") or doc.get("user_name") or "Unknown"
                reporter_data["email"] = user_doc.get("email")
                reporter_data["phone"] = user_doc.get("phone")
                reporter_data["credibility_score"] = user_doc.get("credibility_score", 50)
                # Count total reports by this user
                reports_count = await db.hazard_reports.count_documents({"user_id": doc.get("user_id")})
                reporter_data["reports_count"] = reports_count
        except Exception as e:
            logger.warning(f"Error fetching reporter details: {e}")

    # Extract images
    images = []
    if doc.get("image_url"):
        images.append(doc.get("image_url"))
    if doc.get("images") and isinstance(doc.get("images"), list):
        images.extend(doc.get("images"))

    # Build response
    return {
        "report_id": doc.get("report_id"),
        "hazard_type": str(hazard_type),
        "description": doc.get("description"),
        "severity": doc.get("severity") or "medium",
        "location": location_data,
        "image_url": doc.get("image_url"),
        "images": images,
        "verification_status": str(verification_status),
        "verification_score": doc.get("verification_score"),
        "verification_id": doc.get("verification_id"),
        "verification_result": doc.get("verification_result"),
        "vision_classification": doc.get("vision_classification"),
        "geofence_valid": doc.get("geofence_valid"),
        "geofence_distance_km": doc.get("geofence_distance_km"),
        "environmental_snapshot": doc.get("environmental_snapshot"),
        "hazard_classification": doc.get("hazard_classification"),
        "reporter": reporter_data,
        "created_at": created_at,
        "verified_at": verified_at,
        "verified_by": doc.get("verified_by"),
        "verified_by_name": doc.get("verified_by_name")
    }


@router.post("/{report_id}/decide")
async def make_analyst_decision(
    report_id: str,
    request: AnalystDecisionRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Analyst makes a decision on a report.

    Can approve or reject reports awaiting manual review.

    Requires Analyst role or higher.
    """
    # Find the report
    doc = await db.hazard_reports.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found"
        )

    # Work directly with raw document to avoid enum validation issues
    current_status = doc.get("verification_status", "pending")

    # Validate current status allows decision
    allowed_statuses = [
        VerificationStatus.NEEDS_MANUAL_REVIEW.value,
        VerificationStatus.PENDING.value,
        "needs_manual_review",
        "pending"
    ]
    if current_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report already has status '{current_status}'. Cannot make new decision."
        )

    # Map decision to status
    new_status = map_decision_to_status(request.decision)

    # Update the report
    update_data = {
        "verification_status": new_status.value,
        "verified_at": datetime.now(timezone.utc),
        "verified_by": current_user.user_id,
        "verified_by_name": current_user.name or current_user.email or "Unknown",
        "verification_notes": request.reason,
        "updated_at": datetime.now(timezone.utc)
    }

    if request.decision == VerificationDecision.REJECTED:
        update_data["rejection_reason"] = request.reason

    await db.hazard_reports.update_one(
        {"report_id": report_id},
        {"$set": update_data}
    )

    # Update reporter credibility
    user_id = doc.get("user_id")
    if request.credibility_impact != 0 and user_id:
        credibility_update = {
            "$inc": {
                "credibility_score": request.credibility_impact
            }
        }
        if request.decision == VerificationDecision.AUTO_APPROVED:
            credibility_update["$inc"]["reports_verified_count"] = 1
        elif request.decision == VerificationDecision.REJECTED:
            credibility_update["$inc"]["reports_rejected_count"] = 1

        await db.users.update_one(
            {"user_id": user_id},
            credibility_update
        )

    # Create audit record
    verification_result = doc.get("verification_result")
    audit_record = {
        "audit_id": f"AUD_{report_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "verification_id": doc.get("verification_id"),
        "report_id": report_id,
        "original_decision": verification_result.get("decision") if verification_result else "pending",
        "original_score": doc.get("verification_score") or 0,
        "was_overridden": True,
        "override_decision": request.decision.value,
        "override_by": current_user.user_id,
        "override_by_name": current_user.name or current_user.email or "Unknown",
        "override_reason": request.reason,
        "override_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    }
    await db.verification_audits.insert_one(audit_record)

    # AUTO-GENERATE TICKET for manually approved reports
    ticket_id = None
    ticket_created = False
    ticket_error_message = None

    if request.decision == VerificationDecision.AUTO_APPROVED:
        logger.info(f"Starting ticket creation for approved report {report_id}")
        try:
            # Fetch updated report with all data
            updated_doc = await db.hazard_reports.find_one({"report_id": report_id})

            if not updated_doc:
                logger.error(f"Could not find report {report_id} after approval - cannot create ticket")
                ticket_error_message = "Report not found after approval"
            else:
                # Check if ticket already exists
                existing_ticket = await db.tickets.find_one({"report_id": report_id})
                if existing_ticket:
                    ticket_id = existing_ticket.get("ticket_id")
                    logger.info(f"Ticket {ticket_id} already exists for report {report_id}")
                    ticket_created = False  # Already existed
                else:
                    # Create new ticket
                    auto_ticket_service = get_auto_ticket_service(db)
                    ticket_result = await auto_ticket_service.create_ticket_for_approved_report(
                        report_doc=updated_doc,
                        approver=current_user,
                        approval_type="manual",
                        db=db
                    )

                    if ticket_result:
                        ticket, _ = ticket_result
                        ticket_id = ticket.ticket_id
                        ticket_created = True
                        logger.info(f"✓ Auto-generated ticket {ticket_id} for manually approved report {report_id}")
                    else:
                        # This should not happen if we checked existing_ticket above
                        logger.warning(f"Ticket creation returned None for report {report_id} - possible race condition")
                        ticket_error_message = "Ticket creation returned None"

        except Exception as ticket_error:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"✗ Failed to auto-generate ticket for report {report_id}: {ticket_error}")
            logger.error(f"Ticket creation error details:\n{error_details}")
            ticket_error_message = str(ticket_error)
            # Non-blocking - report is still verified

    logger.info(
        f"Analyst {current_user.user_id} made decision '{request.decision.value}' "
        f"on report {report_id}"
    )

    return {
        "success": True,
        "report_id": report_id,
        "new_status": new_status.value,
        "decision": request.decision.value,
        "decided_by": current_user.user_id,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket_id,
        "ticket_created": ticket_created,
        "ticket_already_existed": ticket_id is not None and not ticket_created,
        "ticket_error": ticket_error_message
    }


@router.post("/{report_id}/rerun")
async def rerun_verification(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database),
    service: VerificationService = Depends(get_verification_service_dep)
):
    """
    Re-run verification pipeline on a report.

    Useful when environmental data or thresholds have changed.

    Requires Analyst role or higher.
    """
    from app.models.hazard import HazardType, HazardCategory

    # Find the report
    doc = await db.hazard_reports.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found"
        )

    # Normalize enum fields before creating HazardReport to handle legacy data
    doc_copy = doc.copy()

    # Normalize hazard_type
    if "hazard_type" in doc_copy:
        ht = doc_copy["hazard_type"]
        valid_types = {e.value for e in HazardType}
        if ht not in valid_types:
            # Try case-insensitive match
            matched = None
            for enum_member in HazardType:
                if enum_member.value.lower() == str(ht).lower():
                    matched = enum_member.value
                    break
            doc_copy["hazard_type"] = matched or HazardType.HIGH_WAVES.value

    # Normalize category
    if "category" in doc_copy:
        cat = doc_copy["category"]
        valid_cats = {e.value for e in HazardCategory}
        if cat not in valid_cats:
            matched = None
            for enum_member in HazardCategory:
                if enum_member.value.lower() == str(cat).lower():
                    matched = enum_member.value
                    break
            doc_copy["category"] = matched or HazardCategory.NATURAL.value

    # Normalize verification_status
    if "verification_status" in doc_copy:
        vs = doc_copy["verification_status"]
        valid_statuses = {e.value for e in VerificationStatus}
        if vs not in valid_statuses:
            matched = None
            for enum_member in VerificationStatus:
                if enum_member.value.lower() == str(vs).lower():
                    matched = enum_member.value
                    break
            doc_copy["verification_status"] = matched or VerificationStatus.PENDING.value

    try:
        report = HazardReport.from_mongo(doc_copy)
    except Exception as e:
        logger.error(f"Error creating HazardReport from document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse report data: {str(e)}"
        )

    # Determine image path for re-verification
    # The image_url may be S3 URL or local path "/uploads/hazards/..."
    image_path = None
    temp_image_path = None  # Track temp file for cleanup
    
    if report.image_url:
        if report.image_url.startswith('http'):
            # S3 URL - download to temp file for verification
            if s3_service.is_enabled:
                logger.info(f"Downloading S3 image for re-verification: {report.image_url}")
                temp_image_path = s3_service.download_from_url_to_temp(report.image_url)
                if temp_image_path:
                    image_path = temp_image_path
                    logger.info(f"S3 image downloaded to: {temp_image_path}")
                else:
                    logger.warning(f"Failed to download S3 image, skipping image verification")
        else:
            # Local path - strip leading slash if present
            image_path = report.image_url.lstrip('/')
            logger.info(f"Re-verification using local image path: {image_path}")

    try:
        # Re-run verification
        result = await service.verify_report(
            report,
            image_path=image_path,
            db=db
        )
    finally:
        # Clean up temporary S3 download file
        if temp_image_path:
            try:
                import os
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                    logger.debug(f"Cleaned up temp file: {temp_image_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {temp_image_path}: {cleanup_error}")

    # Update the report
    new_status = map_decision_to_status(result.decision)

    await db.hazard_reports.update_one(
        {"report_id": report_id},
        {
            "$set": {
                "verification_status": new_status.value,
                "verification_score": result.composite_score,
                "verification_result": result.model_dump(),
                "verification_id": result.verification_id,
                "geofence_valid": result.layer_results[0].status.value == "pass" if result.layer_results else None,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    logger.info(
        f"Re-ran verification for report {report_id}: "
        f"score={result.composite_score:.1f}%, decision={result.decision.value}"
    )

    return {
        "success": True,
        "report_id": report_id,
        "verification_id": result.verification_id,
        "composite_score": result.composite_score,
        "decision": result.decision.value,
        "new_status": new_status.value,
        "processing_time_ms": result.processing_time_ms,
        "layer_summary": {
            lr.layer_name.value: {"status": lr.status.value, "score": lr.score}
            for lr in result.layer_results
        }
    }


# =============================================================================
# TICKET BACKFILL ENDPOINTS
# =============================================================================

@router.post("/backfill-tickets")
async def backfill_tickets_for_verified_reports(
    dry_run: bool = Query(default=True, description="If true, only count reports without simulating"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum reports to process"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create tickets for all verified reports that don't have tickets yet.

    This is a backfill operation for reports that were verified before
    the automatic ticket creation feature was added.

    Use dry_run=true first to see how many reports would be affected.

    Requires Analyst role or higher.
    """
    try:
        # Find verified reports without tickets
        pipeline = [
            {
                "$match": {
                    "verification_status": {"$in": ["verified", VerificationStatus.VERIFIED.value]},
                    "$or": [
                        {"has_ticket": {"$exists": False}},
                        {"has_ticket": False},
                        {"ticket_id": {"$exists": False}},
                        {"ticket_id": None}
                    ]
                }
            },
            {
                "$limit": limit
            }
        ]

        reports_without_tickets = await db.hazard_reports.aggregate(pipeline).to_list(limit)
        total_found = len(reports_without_tickets)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"Found {total_found} verified reports without tickets",
                "count": total_found,
                "reports": [
                    {
                        "report_id": r.get("report_id"),
                        "hazard_type": r.get("hazard_type"),
                        "verification_score": r.get("verification_score"),
                        "verified_at": r.get("verified_at").isoformat() if r.get("verified_at") else None,
                        "user_name": r.get("user_name")
                    }
                    for r in reports_without_tickets[:20]  # Show first 20 in dry run
                ]
            }

        # Process each report and create tickets
        auto_ticket_service = get_auto_ticket_service(db)
        created_tickets = []
        failed_reports = []
        skipped_reports = []

        for report_doc in reports_without_tickets:
            report_id = report_doc.get("report_id")

            try:
                # Double-check ticket doesn't exist (race condition protection)
                existing = await db.tickets.find_one({"report_id": report_id})
                if existing:
                    skipped_reports.append({
                        "report_id": report_id,
                        "reason": "Ticket already exists",
                        "ticket_id": existing.get("ticket_id")
                    })
                    continue

                # Create ticket
                ticket_result = await auto_ticket_service.create_ticket_for_approved_report(
                    report_doc=report_doc,
                    approver=current_user,  # Use current analyst as approver
                    approval_type="backfill",
                    db=db
                )

                if ticket_result:
                    ticket, _ = ticket_result
                    created_tickets.append({
                        "report_id": report_id,
                        "ticket_id": ticket.ticket_id,
                        "priority": ticket.priority.value
                    })
                    logger.info(f"Backfill: Created ticket {ticket.ticket_id} for report {report_id}")
                else:
                    skipped_reports.append({
                        "report_id": report_id,
                        "reason": "Ticket creation returned None"
                    })

            except Exception as e:
                failed_reports.append({
                    "report_id": report_id,
                    "error": str(e)
                })
                logger.error(f"Backfill: Failed to create ticket for report {report_id}: {e}")

        logger.info(
            f"Backfill complete: {len(created_tickets)} created, "
            f"{len(skipped_reports)} skipped, {len(failed_reports)} failed"
        )

        return {
            "success": True,
            "dry_run": False,
            "message": f"Backfill complete: {len(created_tickets)} tickets created",
            "total_found": total_found,
            "created_count": len(created_tickets),
            "skipped_count": len(skipped_reports),
            "failed_count": len(failed_reports),
            "created_tickets": created_tickets,
            "skipped_reports": skipped_reports,
            "failed_reports": failed_reports,
            "executed_by": current_user.user_id,
            "executed_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Backfill operation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backfill operation failed: {str(e)}"
        )


@router.post("/{report_id}/create-ticket")
async def create_ticket_for_verified_report(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Manually create a ticket for a specific verified report.

    Use this if a ticket was not automatically created during approval.

    Requires Analyst role or higher.
    """
    # Find the report
    doc = await db.hazard_reports.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found"
        )

    # Check if report is verified
    verification_status = doc.get("verification_status", "pending")
    if verification_status not in ["verified", VerificationStatus.VERIFIED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not verified (status: {verification_status}). Only verified reports can have tickets."
        )

    # Check if ticket already exists
    existing_ticket = await db.tickets.find_one({"report_id": report_id})
    if existing_ticket:
        return {
            "success": True,
            "message": "Ticket already exists for this report",
            "ticket_id": existing_ticket.get("ticket_id"),
            "ticket_already_existed": True
        }

    # Create ticket
    try:
        auto_ticket_service = get_auto_ticket_service(db)
        ticket_result = await auto_ticket_service.create_ticket_for_approved_report(
            report_doc=doc,
            approver=current_user,
            approval_type="manual_creation",
            db=db
        )

        if ticket_result:
            ticket, _ = ticket_result
            logger.info(f"Manually created ticket {ticket.ticket_id} for report {report_id}")

            return {
                "success": True,
                "message": f"Ticket created successfully",
                "report_id": report_id,
                "ticket_id": ticket.ticket_id,
                "priority": ticket.priority.value,
                "created_by": current_user.user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ticket creation returned None - unexpected error"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create ticket for report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )
