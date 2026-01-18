"""
Hazard Reports Endpoints
API endpoints for hazard reporting and management
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query
)
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.config import settings
from app.database import get_database
from app.models.user import User, UserRole
from app.models.hazard import (
    HazardReport,
    HazardReportCreate,
    HazardReportUpdate,
    HazardReportVerify,
    HazardReportResponse,
    HazardReportListResponse,
    HazardType,
    HazardCategory,
    VerificationStatus,
    Location,
    WeatherData,
    ThreatLevel
)
from app.middleware.security import get_current_user
from app.utils.security import generate_user_id
from app.utils.audit import AuditLogger
from app.services.environmental_data_service import fetch_environmental_snapshot
from app.services.report_hazard_classifier import classify_hazard_threat
from app.services.verification_service import get_verification_service, VerificationService
from app.services.auto_ticket_service import get_auto_ticket_service
from app.services.approval_service import get_approval_service
from app.models.verification import VerificationDecision, AIRecommendation
from app.models.hazard import ApprovalSource, TicketCreationStatus
from app.services.s3_service import s3_service
from pydantic import BaseModel, Field
import json

logger = logging.getLogger(__name__)


# Request model for S3-based hazard report creation
class HazardReportS3Create(BaseModel):
    """Request model for creating hazard report with S3 URLs"""
    hazard_type: str = Field(..., description="Type of hazard")
    category: str = Field(..., description="Hazard category (natural/humanMade)")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    address: str = Field(..., description="Address description")
    description: Optional[str] = Field(None, description="Additional description")
    weather: Optional[dict] = Field(None, description="Weather data")
    image_url: str = Field(..., description="S3 public URL of the uploaded image")
    voice_note_url: Optional[str] = Field(None, description="S3 public URL of voice note")

router = APIRouter(prefix="/hazards", tags=["Hazard Reports"])

# File upload configuration
UPLOAD_DIR = "uploads/hazards"
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VOICE_SIZE = 5 * 1024 * 1024   # 5MB
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]
ALLOWED_VOICE_TYPES = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/webm"]

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_upload_file(
    upload_file: UploadFile,
    max_size: int,
    allowed_types: List[str]
) -> str:
    """Save uploaded file and return the file path"""

    # Validate file type
    if upload_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )

    # Read file content
    content = await upload_file.read()

    # Validate file size
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size / 1024 / 1024}MB"
        )

    # Generate unique filename
    file_extension = upload_file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Return relative path for storage
    return f"/{file_path}"


@router.post("", status_code=status.HTTP_201_CREATED, response_model=HazardReportResponse)
async def create_hazard_report(
    hazard_type: str = Form(...),
    category: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    description: Optional[str] = Form(None),
    weather: Optional[str] = Form(None),  # JSON string
    image: UploadFile = File(...),
    voice_note: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new hazard report

    Requires authentication. Uploads image and optional voice note,
    stores location and weather data, sets initial verification status to pending.
    """
    try:
        # Validate hazard type and category
        try:
            hazard_type_enum = HazardType(hazard_type)
            category_enum = HazardCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid hazard type or category"
            )

        # Save image file
        image_path = await save_upload_file(image, MAX_IMAGE_SIZE, ALLOWED_IMAGE_TYPES)

        # Save voice note if provided
        voice_note_path = None
        if voice_note:
            voice_note_path = await save_upload_file(
                voice_note,
                MAX_VOICE_SIZE,
                ALLOWED_VOICE_TYPES
            )

        # Parse weather data
        weather_data = None
        if weather:
            try:
                weather_dict = json.loads(weather)
                weather_data = WeatherData(**weather_dict)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid weather data: {e}")

        # Parse address to extract region and district
        region = None
        district = None

        if address:
            # Indian states for matching
            indian_states = [
                'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
                'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
                'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
                'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
                'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
                'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli',
                'Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
            ]

            # Try to find state in address
            address_upper = address.upper()
            for state in indian_states:
                if state.upper() in address_upper:
                    region = state
                    break

            # Try to extract district/city (usually the last significant part before state)
            # Split by comma and take the part before the state
            parts = [p.strip() for p in address.split(',')]
            if len(parts) >= 2:
                # If we found a region, district is usually the part before it
                if region:
                    for i, part in enumerate(parts):
                        if region.upper() in part.upper():
                            if i > 0:
                                district = parts[i-1]
                            break
                else:
                    # Otherwise, take the second-to-last part as district
                    district = parts[-2] if len(parts) > 1 else None

        # Create location object
        location = Location(
            latitude=latitude,
            longitude=longitude,
            address=address,
            region=region,
            district=district
        )

        # Fetch environmental data and classify threat at submission time
        environmental_snapshot = None
        hazard_classification = None
        try:
            logger.info(f"Fetching environmental data for coordinates ({latitude}, {longitude})")
            environmental_snapshot = await fetch_environmental_snapshot(latitude, longitude)

            # Classify threat based on environmental data
            hazard_classification = classify_hazard_threat(
                environmental_snapshot,
                hazard_type  # Pass the user-reported hazard type for context
            )

            logger.info(f"Threat classification: {hazard_classification.threat_level.value} - {hazard_classification.hazard_type or 'none'}")
        except Exception as enrich_error:
            logger.warning(f"Environmental enrichment failed (non-blocking): {enrich_error}")
            # Continue without environmental data - non-blocking error

        # Generate report ID
        report_id = f"RPT_{generate_user_id()}"

        # Create hazard report document
        hazard_report = HazardReport(
            report_id=report_id,
            user_id=current_user.user_id,
            user_name=current_user.name,
            hazard_type=hazard_type_enum,
            category=category_enum,
            description=description,
            image_url=image_path,
            voice_note_url=voice_note_path,
            location=location,
            weather=weather_data,
            environmental_snapshot=environmental_snapshot,
            hazard_classification=hazard_classification,
            verification_status=VerificationStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Insert into database
        result = await db.hazard_reports.insert_one(
            hazard_report.model_dump(by_alias=True, exclude={"id"})
        )

        # Retrieve the created report
        created_report = await db.hazard_reports.find_one({"_id": result.inserted_id})

        # Run 6-Layer Verification Pipeline
        verification_result = None
        try:
            logger.info(f"Running verification pipeline for report {report_id}")
            verification_service = get_verification_service(db)

            if not verification_service._initialized:
                await verification_service.initialize()

            # Get absolute image path for vision model
            abs_image_path = image_path.lstrip('/') if image_path else None

            # Run verification
            verification_result = await verification_service.verify_report(
                hazard_report,
                image_path=abs_image_path,
                db=db
            )

            # Map verification decision to status (simplified - only 4 statuses)
            decision_to_status = {
                VerificationDecision.AUTO_APPROVED: VerificationStatus.VERIFIED,
                VerificationDecision.MANUAL_REVIEW: VerificationStatus.NEEDS_MANUAL_REVIEW,
                VerificationDecision.AI_RECOMMENDED: VerificationStatus.NEEDS_MANUAL_REVIEW,  # Legacy
                VerificationDecision.REJECTED: VerificationStatus.REJECTED,
                VerificationDecision.AUTO_REJECTED: VerificationStatus.AUTO_REJECTED
            }
            new_status = decision_to_status.get(
                verification_result.decision,
                VerificationStatus.NEEDS_MANUAL_REVIEW  # Default to needs review
            )

            # Extract geofence data
            geofence_result = next(
                (lr for lr in verification_result.layer_results if lr.layer_name.value == "geofence"),
                None
            )
            geofence_valid = geofence_result.status.value == "pass" if geofence_result else None
            geofence_distance = None
            if geofence_result and geofence_result.data:
                geofence_distance = geofence_result.data.get("distance_to_coast_km")

            # Extract vision classification
            vision_result = next(
                (lr for lr in verification_result.layer_results if lr.layer_name.value == "image"),
                None
            )
            vision_classification = vision_result.data if vision_result else None

            # Update report with verification results
            await db.hazard_reports.update_one(
                {"_id": result.inserted_id},
                {
                    "$set": {
                        "verification_status": new_status.value,
                        "verification_score": verification_result.composite_score,
                        "verification_result": verification_result.model_dump(),
                        "verification_id": verification_result.verification_id,
                        "geofence_valid": geofence_valid,
                        "geofence_distance_km": geofence_distance,
                        "vision_classification": vision_classification,
                        "verified_at": datetime.now(timezone.utc) if new_status == VerificationStatus.VERIFIED else None,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            # Refresh created report with verification data
            created_report = await db.hazard_reports.find_one({"_id": result.inserted_id})

            logger.info(
                f"Verification complete for {report_id}: "
                f"score={verification_result.composite_score:.1f}%, "
                f"decision={verification_result.decision.value}"
            )

            # AUTO-GENERATE TICKET for AI-approved reports
            if new_status == VerificationStatus.VERIFIED:
                try:
                    auto_ticket_service = get_auto_ticket_service(db)
                    ticket_result = await auto_ticket_service.create_ticket_for_approved_report(
                        report_doc=created_report,
                        approver=None,  # No manual approver for AI-approval
                        approval_type="auto",
                        db=db
                    )
                    if ticket_result:
                        ticket, _ = ticket_result
                        logger.info(f"Auto-generated ticket {ticket.ticket_id} for AI-approved report {report_id}")
                        # Refresh report to include ticket data
                        created_report = await db.hazard_reports.find_one({"_id": result.inserted_id})
                except Exception as ticket_error:
                    logger.warning(f"Failed to auto-generate ticket for report {report_id}: {ticket_error}")
                    # Non-blocking - report is still verified

        except Exception as verify_error:
            logger.warning(f"Verification pipeline failed (non-blocking): {verify_error}")
            # Continue without verification - report remains in PENDING status

        # Log audit event
        await AuditLogger.log(
            db=db,
            user_id=current_user.user_id,
            action="hazard_report_created",
            details={
                "hazard_type": hazard_type,
                "category": category,
                "report_id": report_id,
                "verification_score": verification_result.composite_score if verification_result else None,
                "verification_decision": verification_result.decision.value if verification_result else "pending"
            }
        )

        logger.info(f"Hazard report created: {report_id} by user {current_user.user_id}")

        # Convert ObjectId to string for response
        created_report["_id"] = str(created_report["_id"])

        return HazardReportResponse(**created_report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create hazard report"
        )


@router.post("/s3", status_code=status.HTTP_201_CREATED, response_model=HazardReportResponse)
async def create_hazard_report_s3(
    report_data: HazardReportS3Create,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new hazard report with S3 URLs (presigned upload)

    This endpoint is used when images are uploaded directly to S3 using presigned URLs.
    The frontend first uploads the image to S3, then submits this form with the S3 URL.

    **Flow:**
    1. Frontend calls `/api/v1/uploads/presigned-url` to get upload URL
    2. Frontend uploads image directly to S3
    3. Frontend calls this endpoint with the S3 public URL
    """
    try:
        # Validate hazard type and category
        try:
            hazard_type_enum = HazardType(report_data.hazard_type)
            category_enum = HazardCategory(report_data.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid hazard type or category"
            )

        # Validate S3 URL (must be from our bucket)
        if s3_service.is_enabled:
            from app.config import settings
            if not report_data.image_url.startswith(settings.s3_base_url):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image URL. Must be uploaded to CoastGuardian S3 bucket."
                )
            if report_data.voice_note_url and not report_data.voice_note_url.startswith(settings.s3_base_url):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid voice note URL. Must be uploaded to CoastGuardian S3 bucket."
                )

        # Parse weather data
        weather_data = None
        if report_data.weather:
            try:
                weather_data = WeatherData(**report_data.weather)
            except ValueError as e:
                logger.warning(f"Invalid weather data: {e}")

        # Parse address to extract region and district
        region = None
        district = None
        address = report_data.address

        if address:
            indian_states = [
                'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
                'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
                'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
                'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
                'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
                'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli',
                'Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
            ]

            address_upper = address.upper()
            for state in indian_states:
                if state.upper() in address_upper:
                    region = state
                    break

            parts = [p.strip() for p in address.split(',')]
            if len(parts) >= 2:
                if region:
                    for i, part in enumerate(parts):
                        if region.upper() in part.upper():
                            if i > 0:
                                district = parts[i-1]
                            break
                else:
                    district = parts[-2] if len(parts) > 1 else None

        # Create location object
        location = Location(
            latitude=report_data.latitude,
            longitude=report_data.longitude,
            address=address,
            region=region,
            district=district
        )

        # Fetch environmental data and classify threat
        environmental_snapshot = None
        hazard_classification = None
        try:
            logger.info(f"Fetching environmental data for coordinates ({report_data.latitude}, {report_data.longitude})")
            environmental_snapshot = await fetch_environmental_snapshot(report_data.latitude, report_data.longitude)
            hazard_classification = classify_hazard_threat(
                environmental_snapshot,
                report_data.hazard_type
            )
            logger.info(f"Threat classification: {hazard_classification.threat_level.value}")
        except Exception as enrich_error:
            logger.warning(f"Environmental enrichment failed (non-blocking): {enrich_error}")

        # Generate report ID
        report_id = f"RPT_{generate_user_id()}"

        # Create hazard report document
        hazard_report = HazardReport(
            report_id=report_id,
            user_id=current_user.user_id,
            user_name=current_user.name,
            hazard_type=hazard_type_enum,
            category=category_enum,
            description=report_data.description,
            image_url=report_data.image_url,  # S3 URL
            voice_note_url=report_data.voice_note_url,  # S3 URL or None
            location=location,
            weather=weather_data,
            environmental_snapshot=environmental_snapshot,
            hazard_classification=hazard_classification,
            verification_status=VerificationStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Insert into database
        result = await db.hazard_reports.insert_one(
            hazard_report.model_dump(by_alias=True, exclude={"id"})
        )

        created_report = await db.hazard_reports.find_one({"_id": result.inserted_id})

        # Run 6-Layer Verification Pipeline
        verification_result = None
        temp_image_path = None  # Track temp file for cleanup
        try:
            logger.info(f"Running verification pipeline for report {report_id}")
            verification_service = get_verification_service(db)

            if not verification_service._initialized:
                await verification_service.initialize()

            # For S3 images, download to temp file for vision analysis
            image_path = None
            if s3_service.is_enabled and report_data.image_url:
                logger.info(f"Downloading S3 image for verification: {report_data.image_url}")
                temp_image_path = s3_service.download_from_url_to_temp(report_data.image_url)
                if temp_image_path:
                    image_path = temp_image_path
                    logger.info(f"S3 image downloaded to: {temp_image_path}")
                else:
                    logger.warning(f"Failed to download S3 image, skipping image verification")

            verification_result = await verification_service.verify_report(
                hazard_report,
                image_path=image_path,
                db=db
            )

            decision_to_status = {
                VerificationDecision.AUTO_APPROVED: VerificationStatus.VERIFIED,
                VerificationDecision.MANUAL_REVIEW: VerificationStatus.NEEDS_MANUAL_REVIEW,
                VerificationDecision.AI_RECOMMENDED: VerificationStatus.NEEDS_MANUAL_REVIEW,
                VerificationDecision.REJECTED: VerificationStatus.REJECTED,
                VerificationDecision.AUTO_REJECTED: VerificationStatus.AUTO_REJECTED
            }
            new_status = decision_to_status.get(
                verification_result.decision,
                VerificationStatus.NEEDS_MANUAL_REVIEW
            )

            geofence_result = next(
                (lr for lr in verification_result.layer_results if lr.layer_name.value == "geofence"),
                None
            )
            geofence_valid = geofence_result.status.value == "pass" if geofence_result else None
            geofence_distance = None
            if geofence_result and geofence_result.data:
                geofence_distance = geofence_result.data.get("distance_to_coast_km")

            vision_result = next(
                (lr for lr in verification_result.layer_results if lr.layer_name.value == "image"),
                None
            )
            vision_classification = vision_result.data if vision_result else None

            await db.hazard_reports.update_one(
                {"_id": result.inserted_id},
                {
                    "$set": {
                        "verification_status": new_status.value,
                        "verification_score": verification_result.composite_score,
                        "verification_result": verification_result.model_dump(),
                        "verification_id": verification_result.verification_id,
                        "geofence_valid": geofence_valid,
                        "geofence_distance_km": geofence_distance,
                        "vision_classification": vision_classification,
                        "verified_at": datetime.now(timezone.utc) if new_status == VerificationStatus.VERIFIED else None,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            created_report = await db.hazard_reports.find_one({"_id": result.inserted_id})

            logger.info(
                f"Verification complete for {report_id}: "
                f"score={verification_result.composite_score:.1f}%, "
                f"decision={verification_result.decision.value}"
            )

            # AUTO-GENERATE TICKET for AI-approved reports
            if new_status == VerificationStatus.VERIFIED:
                try:
                    auto_ticket_service = get_auto_ticket_service(db)
                    ticket_result = await auto_ticket_service.create_ticket_for_approved_report(
                        report_doc=created_report,
                        approver=None,
                        approval_type="auto",
                        db=db
                    )
                    if ticket_result:
                        ticket, _ = ticket_result
                        logger.info(f"Auto-generated ticket {ticket.ticket_id} for AI-approved report {report_id}")
                        created_report = await db.hazard_reports.find_one({"_id": result.inserted_id})
                except Exception as ticket_error:
                    logger.warning(f"Failed to auto-generate ticket for report {report_id}: {ticket_error}")

        except Exception as verify_error:
            logger.warning(f"Verification pipeline failed (non-blocking): {verify_error}")
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

        # Log audit event
        await AuditLogger.log(
            db=db,
            user_id=current_user.user_id,
            action="hazard_report_created",
            details={
                "hazard_type": report_data.hazard_type,
                "category": report_data.category,
                "report_id": report_id,
                "storage": "s3",
                "verification_score": verification_result.composite_score if verification_result else None,
                "verification_decision": verification_result.decision.value if verification_result else "pending"
            }
        )

        logger.info(f"Hazard report created (S3): {report_id} by user {current_user.user_id}")

        created_report["_id"] = str(created_report["_id"])
        return HazardReportResponse(**created_report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating hazard report (S3): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create hazard report"
        )


@router.get("/timeline")
async def get_hazard_timeline(
    time_range: str = Query(..., regex="^(6h|24h|48h_future)$", description="Time range: 6h, 24h, or 48h_future"),
    include_forecast: bool = Query(default=True, description="Include forecast data for future range"),
    include_heatmap: bool = Query(default=True, description="Include heatmap data points"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get hazard data filtered by time range for timeline visualization.

    - 6h: Last 6 hours of data
    - 24h: Last 24 hours of data
    - 48h_future: Forecast data for next 48 hours

    This endpoint supports the Incident Timeline feature on the map.
    """
    from datetime import timedelta
    import httpx

    try:
        now = datetime.now(timezone.utc)
        is_future = time_range == "48h_future"

        # Determine time bounds
        if time_range == "6h":
            cutoff_time = now - timedelta(hours=6)
            query_time = {"$gte": cutoff_time, "$lte": now}
        elif time_range == "24h":
            cutoff_time = now - timedelta(hours=24)
            query_time = {"$gte": cutoff_time, "$lte": now}
        else:  # 48h_future
            # For future, we return forecast data instead of historical reports
            cutoff_time = now
            query_time = None  # No historical query for future

        reports = []
        heatmap_points = []
        forecast_data = None
        forecast_cone = None

        if not is_future:
            # Fetch historical reports
            query = {
                "is_deleted": False,
                "is_active": True,
                "created_at": query_time,
                "verification_status": {"$in": [
                    VerificationStatus.VERIFIED.value,
                    VerificationStatus.PENDING.value
                ]}
            }

            cursor = db.hazard_reports.find(query).sort("created_at", -1).limit(500)
            raw_reports = await cursor.to_list(length=500)

            for report in raw_reports:
                lat = report.get("location", {}).get("latitude")
                lon = report.get("location", {}).get("longitude")

                if lat and lon:
                    reports.append({
                        "id": report.get("report_id"),
                        "hazard_type": report.get("hazard_type"),
                        "severity": report.get("severity", "medium"),
                        "description": report.get("description", "")[:200],
                        "latitude": lat,
                        "longitude": lon,
                        "verification_status": report.get("verification_status"),
                        "created_at": report.get("created_at").isoformat() if report.get("created_at") else None,
                        "region": report.get("location", {}).get("region"),
                    })

                    if include_heatmap:
                        severity_weight = {
                            "critical": 1.0, "high": 0.8,
                            "medium": 0.6, "low": 0.4
                        }
                        weight = severity_weight.get(
                            report.get("severity", "medium").lower(), 0.5
                        )
                        heatmap_points.append([lat, lon, weight])

        # Fetch forecast data for future timeline
        if is_future and include_forecast:
            try:
                # Fetch weather forecast for key coastal locations
                forecast_locations = [
                    {"name": "Chennai Coast", "lat": 13.08, "lon": 80.27},
                    {"name": "Mumbai Coast", "lat": 19.08, "lon": 72.88},
                    {"name": "Kolkata Coast", "lat": 22.57, "lon": 88.36},
                    {"name": "Visakhapatnam", "lat": 17.69, "lon": 83.22},
                    {"name": "Kochi", "lat": 9.93, "lon": 76.27},
                ]

                forecast_data = []
                async with httpx.AsyncClient(timeout=15.0) as client:
                    for loc in forecast_locations:
                        try:
                            # Use Open-Meteo Marine API for forecast
                            response = await client.get(
                                "https://marine-api.open-meteo.com/v1/marine",
                                params={
                                    "latitude": loc["lat"],
                                    "longitude": loc["lon"],
                                    "hourly": "wave_height,wave_direction,wave_period",
                                    "forecast_days": 2,
                                    "timezone": "auto"
                                }
                            )

                            if response.status_code == 200:
                                api_data = response.json()
                                hourly = api_data.get("hourly", {})
                                times = hourly.get("time", [])
                                wave_heights = hourly.get("wave_height", [])

                                # Get max predicted wave height
                                max_wave = max(wave_heights) if wave_heights else 1.0

                                # Determine forecast risk level
                                if max_wave >= 2.5:
                                    risk_level = "HIGH"
                                    color = "#ef4444"
                                elif max_wave >= 1.5:
                                    risk_level = "MODERATE"
                                    color = "#f97316"
                                else:
                                    risk_level = "LOW"
                                    color = "#22c55e"

                                forecast_data.append({
                                    "location": loc["name"],
                                    "lat": loc["lat"],
                                    "lon": loc["lon"],
                                    "max_wave_height": round(max_wave, 2),
                                    "risk_level": risk_level,
                                    "color": color,
                                    "forecast_hours": len(times),
                                    "hourly_data": [
                                        {
                                            "time": times[i],
                                            "wave_height": wave_heights[i] if i < len(wave_heights) else None
                                        }
                                        for i in range(min(48, len(times)))  # Next 48 hours
                                    ]
                                })

                                # Add forecast-based heatmap points
                                if include_heatmap:
                                    weight = min(1.0, max_wave / 3.0)
                                    heatmap_points.append([loc["lat"], loc["lon"], weight])

                        except Exception as e:
                            logger.warning(f"Failed to fetch forecast for {loc['name']}: {e}")

                # Generate forecast uncertainty cone (simplified)
                # In production, this would use actual cyclone track predictions
                forecast_cone = {
                    "type": "FeatureCollection",
                    "features": []
                }

                # Add forecast points as potential hazard zones
                for fd in forecast_data:
                    if fd["risk_level"] in ["HIGH", "MODERATE"]:
                        # Create uncertainty circle around high-risk locations
                        forecast_cone["features"].append({
                            "type": "Feature",
                            "properties": {
                                "location": fd["location"],
                                "risk_level": fd["risk_level"],
                                "max_wave": fd["max_wave_height"],
                                "radius_km": 50 if fd["risk_level"] == "HIGH" else 30
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": [fd["lon"], fd["lat"]]
                            }
                        })

            except Exception as e:
                logger.warning(f"Failed to fetch forecast data: {e}")
                forecast_data = []

        # Calculate statistics
        severity_counts = {
            "critical": sum(1 for r in reports if r.get("severity", "").lower() == "critical"),
            "high": sum(1 for r in reports if r.get("severity", "").lower() == "high"),
            "medium": sum(1 for r in reports if r.get("severity", "").lower() == "medium"),
            "low": sum(1 for r in reports if r.get("severity", "").lower() == "low"),
        }

        return {
            "success": True,
            "data": {
                "time_range": time_range,
                "is_future": is_future,
                "reports": reports,
                "heatmap_points": heatmap_points if include_heatmap else [],
                "forecast_data": forecast_data if is_future else None,
                "forecast_cone": forecast_cone if is_future else None,
                "statistics": {
                    "total_reports": len(reports),
                    **severity_counts,
                    "forecast_locations": len(forecast_data) if forecast_data else 0
                }
            },
            "meta": {
                "time_range": time_range,
                "include_forecast": include_forecast,
                "include_heatmap": include_heatmap,
                "generated_at": now.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error fetching timeline data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch timeline data"
        )


@router.get("/map-data")
async def get_map_data(
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours (1-168, default 24)"),
    include_heatmap: bool = Query(default=True, description="Include heatmap data points"),
    include_clusters: bool = Query(default=True, description="Include cluster data"),
    min_severity: Optional[str] = Query(default=None, description="Filter by minimum severity"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get optimized map data with time-based filtering

    Returns reports, heatmap points, and statistics for the map visualization.
    Data is filtered to show only the last N hours (default 24h).
    This endpoint implements automatic 24-hour cleanup by only returning recent data.
    """
    from datetime import timedelta

    try:
        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Base query for reports
        query = {
            "is_deleted": False,
            "is_active": True,
            "created_at": {"$gte": cutoff_time},
            "verification_status": {"$in": [
                VerificationStatus.VERIFIED.value,
                VerificationStatus.PENDING.value
            ]}
        }

        # Add severity filter if specified
        if min_severity:
            query["severity"] = {"$gte": min_severity}

        # Fetch reports
        cursor = db.hazard_reports.find(query).sort("created_at", -1).limit(500)
        reports = await cursor.to_list(length=500)

        # Process reports for response
        processed_reports = []
        heatmap_points = []

        for report in reports:
            report["_id"] = str(report["_id"])

            # Extract coordinates
            lat = report.get("location", {}).get("latitude")
            lon = report.get("location", {}).get("longitude")

            if lat and lon:
                processed_reports.append({
                    "id": report.get("report_id"),
                    "hazard_type": report.get("hazard_type"),
                    "severity": report.get("severity", "medium"),
                    "description": report.get("description", "")[:200],  # Truncate for performance
                    "latitude": lat,
                    "longitude": lon,
                    "verification_status": report.get("verification_status"),
                    "created_at": report.get("created_at").isoformat() if report.get("created_at") else None,
                    "region": report.get("location", {}).get("region"),
                })

                # Generate heatmap point
                if include_heatmap:
                    severity_weight = {
                        "critical": 1.0,
                        "high": 0.8,
                        "medium": 0.6,
                        "low": 0.4
                    }
                    weight = severity_weight.get(
                        report.get("severity", "medium").lower(),
                        0.5
                    )
                    heatmap_points.append([lat, lon, weight])

        # Calculate statistics
        total_reports = len(processed_reports)
        severity_counts = {
            "critical": sum(1 for r in processed_reports if r.get("severity", "").lower() == "critical"),
            "high": sum(1 for r in processed_reports if r.get("severity", "").lower() == "high"),
            "medium": sum(1 for r in processed_reports if r.get("severity", "").lower() == "medium"),
            "low": sum(1 for r in processed_reports if r.get("severity", "").lower() == "low"),
        }

        return {
            "success": True,
            "data": {
                "reports": processed_reports if include_clusters else [],
                "heatmap_points": heatmap_points if include_heatmap else [],
                "statistics": {
                    "total_reports": total_reports,
                    "critical_count": severity_counts["critical"],
                    "high_count": severity_counts["high"],
                    "medium_count": severity_counts["medium"],
                    "low_count": severity_counts["low"],
                    "last_update": datetime.now(timezone.utc).isoformat()
                }
            },
            "meta": {
                "hours_filter": hours,
                "cutoff_time": cutoff_time.isoformat(),
                "refresh_interval": 60,  # Recommended refresh in seconds
                "include_heatmap": include_heatmap,
                "include_clusters": include_clusters
            }
        }

    except Exception as e:
        logger.error(f"Error fetching map data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch map data"
        )


@router.get("", response_model=HazardReportListResponse)
async def list_hazard_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    verification_status: Optional[VerificationStatus] = Query(None, description="Filter by verification status"),
    category: Optional[HazardCategory] = Query(None, description="Filter by category"),
    hazard_type: Optional[HazardType] = Query(None, description="Filter by hazard type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List hazard reports with pagination and filters

    Public endpoint - no authentication required for viewing verified reports.
    Returns only verified and active reports by default.
    """
    try:
        # Build query filter
        query = {
            "is_deleted": False,
            "is_active": True
        }

        # Only show verified reports to public (unless filtered otherwise)
        if verification_status:
            query["verification_status"] = verification_status.value
        else:
            query["verification_status"] = VerificationStatus.VERIFIED.value

        if category:
            query["category"] = category.value

        if hazard_type:
            query["hazard_type"] = hazard_type.value

        if user_id:
            query["user_id"] = user_id

        # Get total count
        total = await db.hazard_reports.count_documents(query)

        # Calculate pagination
        skip = (page - 1) * page_size

        # Fetch reports
        cursor = db.hazard_reports.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        reports = await cursor.to_list(length=page_size)

        # Collect unique user IDs to fetch profile pictures
        user_ids = list(set(report.get("user_id") for report in reports if report.get("user_id")))

        # Fetch user profile pictures in one query
        user_profiles = {}
        if user_ids:
            users_cursor = db.users.find(
                {"user_id": {"$in": user_ids}},
                {"user_id": 1, "profile_picture": 1}
            )
            async for user in users_cursor:
                user_profiles[user["user_id"]] = user.get("profile_picture")

        # Convert ObjectId to string and add profile pictures
        for report in reports:
            report["_id"] = str(report["_id"])
            # Add user profile picture
            report["user_profile_picture"] = user_profiles.get(report.get("user_id"))

        return HazardReportListResponse(
            total=total,
            page=page,
            page_size=page_size,
            reports=[HazardReportResponse(**report) for report in reports]
        )

    except Exception as e:
        logger.error(f"Error listing hazard reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list hazard reports"
        )


@router.get("/my-reports", response_model=HazardReportListResponse)
async def get_my_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get current user's hazard reports

    Requires authentication. Returns all reports by the current user.
    """
    try:
        query = {
            "user_id": current_user.user_id,
            "is_deleted": False
        }

        total = await db.hazard_reports.count_documents(query)
        skip = (page - 1) * page_size

        cursor = db.hazard_reports.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        reports = await cursor.to_list(length=page_size)

        for report in reports:
            report["_id"] = str(report["_id"])

        return HazardReportListResponse(
            total=total,
            page=page,
            page_size=page_size,
            reports=[HazardReportResponse(**report) for report in reports]
        )

    except Exception as e:
        logger.error(f"Error fetching user reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports"
        )


# ============================================================
# User Liked Reports Endpoint
# ============================================================

@router.get("/my-likes")
async def get_my_liked_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get list of report IDs that the current user has liked.
    Used by frontend to show proper like state for each report.
    """
    try:
        cursor = db.hazard_likes.find(
            {"user_id": current_user.user_id},
            {"report_id": 1, "_id": 0}
        )
        likes = await cursor.to_list(length=1000)
        liked_report_ids = [like["report_id"] for like in likes]

        return {
            "success": True,
            "liked_report_ids": liked_report_ids,
            "count": len(liked_report_ids)
        }
    except Exception as e:
        logger.error(f"Error fetching user likes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch liked reports"
        )


# ============================================================
# Ocean Wave & Current Data Endpoint
# ============================================================

@router.get("/ocean-data")
async def get_ocean_data(
    include_waves: bool = Query(default=True, description="Include wave height data"),
    include_currents: bool = Query(default=True, description="Include ocean current data"),
):
    """
    Get real-time ocean wave and current data for Bay of Bengal region.
    Uses Open-Meteo Marine API for wave data.
    """
    import httpx

    try:
        # Key locations in Bay of Bengal for wave data
        wave_locations = [
            {"name": "Central Bay", "lat": 15.0, "lon": 88.0},
            {"name": "North Bay", "lat": 18.0, "lon": 90.0},
            {"name": "South Bay", "lat": 10.0, "lon": 85.0},
            {"name": "Andaman Sea", "lat": 12.0, "lon": 93.0},
            {"name": "East Coast India", "lat": 13.0, "lon": 80.5},
            {"name": "West Bay", "lat": 14.0, "lon": 82.0},
            {"name": "Sri Lanka", "lat": 8.0, "lon": 81.0},
        ]

        wave_zones = []
        current_paths = []

        if include_waves:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for loc in wave_locations:
                    try:
                        # Open-Meteo Marine API - completely free, no API key needed
                        response = await client.get(
                            "https://marine-api.open-meteo.com/v1/marine",
                            params={
                                "latitude": loc["lat"],
                                "longitude": loc["lon"],
                                "current": "wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction",
                                "timezone": "auto"
                            }
                        )

                        if response.status_code == 200:
                            data = response.json()
                            current_data = data.get("current", {})

                            wave_height = current_data.get("wave_height", 1.0)
                            wave_direction = current_data.get("wave_direction", 0)
                            wave_period = current_data.get("wave_period", 8)
                            swell_height = current_data.get("swell_wave_height", 0.5)

                            # Determine wave level and color based on height
                            if wave_height >= 2.5:
                                level = "Very High"
                                color = "#dc2626"  # Red
                            elif wave_height >= 2.0:
                                level = "High"
                                color = "#ef4444"  # Light red
                            elif wave_height >= 1.5:
                                level = "Moderate-High"
                                color = "#f97316"  # Orange
                            elif wave_height >= 1.0:
                                level = "Moderate"
                                color = "#eab308"  # Yellow
                            else:
                                level = "Low"
                                color = "#22c55e"  # Green

                            # Radius based on wave height (bigger waves = bigger zone)
                            radius = int(80000 + wave_height * 40000)

                            wave_zones.append({
                                "name": loc["name"],
                                "center": [loc["lat"], loc["lon"]],
                                "radius": radius,
                                "waveHeight": round(wave_height, 2),
                                "waveDirection": wave_direction,
                                "wavePeriod": round(wave_period, 1),
                                "swellHeight": round(swell_height, 2),
                                "level": level,
                                "color": color,
                                "height": f"{wave_height:.1f}m"
                            })
                    except Exception as e:
                        logger.warning(f"Failed to fetch wave data for {loc['name']}: {e}")
                        # Add fallback data
                        wave_zones.append({
                            "name": loc["name"],
                            "center": [loc["lat"], loc["lon"]],
                            "radius": 100000,
                            "waveHeight": 1.0,
                            "waveDirection": 0,
                            "wavePeriod": 8,
                            "swellHeight": 0.5,
                            "level": "Moderate",
                            "color": "#eab308",
                            "height": "1.0m"
                        })

        if include_currents:
            # Ocean current data (based on seasonal patterns - would need specialized API for real-time)
            # These are typical Bay of Bengal circulation patterns
            current_paths = [
                {
                    "name": "East India Coastal Current",
                    "path": [[8.5, 80], [10, 80.2], [12, 80.5], [14, 81], [16, 81.5], [18, 82.5], [20, 84], [21.5, 87]],
                    "color": "#22d3ee",
                    "speed": "0.5-0.8 m/s",
                    "direction": "Northward",
                    "description": "Summer monsoon coastal current"
                },
                {
                    "name": "Bay of Bengal Gyre",
                    "path": [[18, 85], [16, 88], [13, 90], [10, 89], [9, 86], [10, 83], [13, 82], [16, 83], [18, 85]],
                    "color": "#3b82f6",
                    "speed": "0.3-0.5 m/s",
                    "direction": "Clockwise",
                    "description": "Main circulation pattern"
                },
                {
                    "name": "North Equatorial Current",
                    "path": [[8, 95], [8, 92], [7.5, 88], [7, 84], [6.5, 80], [6, 76]],
                    "color": "#f97316",
                    "speed": "0.8-1.2 m/s",
                    "direction": "Westward",
                    "description": "Equatorial current system"
                },
                {
                    "name": "West India Coastal Current",
                    "path": [[20, 72], [18, 73], [15, 74], [12, 75], [9, 76], [7, 77]],
                    "color": "#22d3ee",
                    "speed": "0.4-0.6 m/s",
                    "direction": "Southward",
                    "description": "Arabian Sea coastal current"
                },
                {
                    "name": "Andaman Sea Current",
                    "path": [[14, 96], [12, 95], [10, 94], [8, 93]],
                    "color": "#8b5cf6",
                    "speed": "0.2-0.4 m/s",
                    "direction": "Southward",
                    "description": "Andaman Sea circulation"
                },
                {
                    "name": "Sri Lanka Dome",
                    "path": [[9, 82], [8, 80], [7, 81], [7.5, 83], [9, 82]],
                    "color": "#10b981",
                    "speed": "0.3-0.5 m/s",
                    "direction": "Circular",
                    "description": "Upwelling zone near Sri Lanka"
                }
            ]

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "Open-Meteo Marine API",
            "waveZones": wave_zones,
            "currentPaths": current_paths,
            "metadata": {
                "region": "Bay of Bengal & Indian Ocean",
                "updateFrequency": "Hourly",
                "dataSource": "https://open-meteo.com/en/docs/marine-weather-api"
            }
        }

    except Exception as e:
        logger.error(f"Error fetching ocean data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ocean data: {str(e)}"
        )


@router.get("/{report_id}", response_model=HazardReportResponse)
async def get_hazard_report(
    report_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get a single hazard report by ID

    Public endpoint - increments view count.
    """
    try:
        # Find report
        report = await db.hazard_reports.find_one({"report_id": report_id, "is_deleted": False})

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hazard report not found"
            )

        # Increment view count
        await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$inc": {"views": 1}}
        )

        report["views"] += 1
        report["_id"] = str(report["_id"])

        return HazardReportResponse(**report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hazard report"
        )


@router.patch("/{report_id}/verify", response_model=HazardReportResponse)
async def verify_hazard_report(
    report_id: str,
    verify_data: HazardReportVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify or reject a hazard report

    Requires analyst or admin role. Updates verification status and awards
    credibility points to the reporter.
    """
    try:
        # Check if user has permission
        if current_user.role not in [UserRole.ANALYST, UserRole.AUTHORITY_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only analysts and admins can verify reports"
            )

        # Find report
        report = await db.hazard_reports.find_one({"report_id": report_id, "is_deleted": False})

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hazard report not found"
            )

        # Update verification status
        update_data = {
            "verification_status": verify_data.verification_status.value,
            "verified_by": current_user.user_id,
            "verified_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "credibility_impact": verify_data.credibility_impact
        }

        if verify_data.verification_notes:
            update_data["verification_notes"] = verify_data.verification_notes

        result = await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$set": update_data}
        )

        # Update user's credibility score
        if verify_data.verification_status == VerificationStatus.VERIFIED:
            # Award credibility points
            await db.users.update_one(
                {"user_id": report["user_id"]},
                {
                    "$inc": {
                        "credibility_score": verify_data.credibility_impact,
                        "verified_reports": 1
                    }
                }
            )
        elif verify_data.verification_status == VerificationStatus.REJECTED:
            # Deduct credibility points
            await db.users.update_one(
                {"user_id": report["user_id"]},
                {"$inc": {"credibility_score": -verify_data.credibility_impact}}
            )

        # Update total reports count
        await db.users.update_one(
            {"user_id": report["user_id"]},
            {"$inc": {"total_reports": 1}}
        )

        # Log audit event
        await AuditLogger.log(
            db=db,
            user_id=current_user.user_id,
            action="hazard_report_verified",
            details={
                "report_id": report_id,
                "status": verify_data.verification_status.value,
                "credibility_impact": verify_data.credibility_impact
            }
        )

        # Fetch updated report
        updated_report = await db.hazard_reports.find_one({"report_id": report_id})
        updated_report["_id"] = str(updated_report["_id"])

        logger.info(f"Hazard report {report_id} verified by {current_user.user_id}")

        return HazardReportResponse(**updated_report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify hazard report"
        )


@router.post("/{report_id}/like")
async def like_hazard_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Like/unlike a hazard report

    Requires authentication. Toggles like status for the current user.
    Only verified reports can be liked.
    """
    try:
        # Check if report exists
        report = await db.hazard_reports.find_one({"report_id": report_id, "is_deleted": False})

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hazard report not found"
            )

        # Only allow likes on verified reports
        if report.get("verification_status") != "verified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only verified reports can be liked"
            )

        # Check if user already liked
        like = await db.hazard_likes.find_one({
            "report_id": report_id,
            "user_id": current_user.user_id
        })

        if like:
            # Unlike - remove like and decrement counter (only if likes > 0)
            await db.hazard_likes.delete_one({
                "report_id": report_id,
                "user_id": current_user.user_id
            })
            # Only decrement if likes > 0 to prevent negative values
            await db.hazard_reports.update_one(
                {"report_id": report_id, "likes": {"$gt": 0}},
                {"$inc": {"likes": -1}}
            )
            # Get updated count and ensure non-negative
            updated_report = await db.hazard_reports.find_one({"report_id": report_id})
            likes_count = max(0, updated_report.get("likes", 0))
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Report unliked",
                    "is_liked": False,
                    "likes_count": likes_count
                },
                status_code=status.HTTP_200_OK
            )
        else:
            # Like - add like and increment counter
            await db.hazard_likes.insert_one({
                "report_id": report_id,
                "user_id": current_user.user_id,
                "created_at": datetime.now(timezone.utc)
            })
            await db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$inc": {"likes": 1}}
            )
            # Get updated count
            updated_report = await db.hazard_reports.find_one({"report_id": report_id})
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Report liked",
                    "is_liked": True,
                    "likes_count": updated_report.get("likes", 0)
                },
                status_code=status.HTTP_200_OK
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error liking hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to like hazard report"
        )


@router.post("/{report_id}/view")
async def record_hazard_report_view(
    report_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Record a view for a hazard report

    No authentication required. Increments the view counter for the report.
    """
    try:
        # Check if report exists
        report = await db.hazard_reports.find_one({"report_id": report_id, "is_deleted": False})

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hazard report not found"
            )

        # Increment view count
        result = await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$inc": {"views": 1}}
        )

        # Get updated count
        updated_report = await db.hazard_reports.find_one({"report_id": report_id})
        views_count = updated_report.get("views", 0)

        return JSONResponse(
            content={
                "success": True,
                "views_count": views_count
            },
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording view for hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record view"
        )


@router.post("/{report_id}/report")
async def report_hazard_report(
    report_id: str,
    reason: str = Form(..., min_length=10, max_length=500),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Report a hazard report for inappropriate content

    Requires authentication. Users can report posts for:
    - Misinformation
    - Spam
    - Inappropriate content
    - Other violations
    """
    try:
        # Check if report exists
        report = await db.hazard_reports.find_one({"report_id": report_id, "is_deleted": False})

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hazard report not found"
            )

        # Prevent users from reporting their own posts
        if report.get("user_id") == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot report your own post"
            )

        # Check if user already reported this post
        existing_report = await db.hazard_report_flags.find_one({
            "report_id": report_id,
            "reporter_id": current_user.user_id
        })

        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reported this post"
            )

        # Create the flag/report
        flag_data = {
            "flag_id": f"FLG-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            "report_id": report_id,
            "reporter_id": current_user.user_id,
            "reporter_name": current_user.name or "Anonymous",
            "reason": reason,
            "status": "pending",  # pending, reviewed, dismissed
            "created_at": datetime.now(timezone.utc),
            "reviewed_at": None,
            "reviewed_by": None
        }

        await db.hazard_report_flags.insert_one(flag_data)

        # Increment report count on the hazard report
        await db.hazard_reports.update_one(
            {"report_id": report_id},
            {"$inc": {"report_flags_count": 1}}
        )

        return JSONResponse(
            content={
                "success": True,
                "message": "Report submitted successfully. Our team will review it.",
                "flag_id": flag_data["flag_id"]
            },
            status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to report hazard report"
        )


@router.delete("/{report_id}")
async def delete_hazard_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a hazard report (soft delete)

    Requires authentication. Users can only delete their own reports.
    Admins can delete any report.
    """
    try:
        # Find report
        report = await db.hazard_reports.find_one({"report_id": report_id, "is_deleted": False})

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hazard report not found"
            )

        # Check permission
        if report["user_id"] != current_user.user_id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this report"
            )


        # Soft delete
        await db.hazard_reports.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "is_deleted": True,
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        # Log audit event
        await AuditLogger.log(
            db=db,
            user_id=current_user.user_id,
            action="hazard_report_deleted",
            details={"report_id": report_id}
        )

        logger.info(f"Hazard report {report_id} deleted by {current_user.user_id}")

        return JSONResponse(
            content={"message": "Hazard report deleted successfully"},
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting hazard report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete hazard report"
        )


# =============================================================================
# V2 ENDPOINTS - Hybrid Verification Mode
# =============================================================================

@router.get("/pending-recommendations")
async def get_pending_recommendations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get reports with AI recommendations awaiting confirmation (V2).

    These are reports with scores 75-85% where AI recommends approval
    but authority/analyst confirmation is needed before ticket creation.

    Requires authority or analyst role.
    """
    # Check permissions
    if current_user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and authorities can view pending recommendations"
        )

    try:
        approval_service = get_approval_service(db)
        skip = (page - 1) * page_size

        results = await approval_service.get_pending_recommendations(
            limit=page_size,
            skip=skip
        )

        # Get total count
        total_count = await db.verification_results.count_documents({
            "ai_recommendation": AIRecommendation.RECOMMEND_APPROVE.value,
            "requires_authority_confirmation": True,
            "$or": [
                {"authority_confirmation": None},
                {"authority_confirmation": {"$exists": False}}
            ]
        })

        return {
            "success": True,
            "data": {
                "reports": results,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }

    except Exception as e:
        logger.error(f"Error getting pending recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending recommendations"
        )


@router.get("/manual-review-queue")
async def get_manual_review_queue(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get reports in manual review queue (V2).

    These are reports with scores 40-75% that need full manual review.

    Requires authority or analyst role.
    """
    if current_user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and authorities can view manual review queue"
        )

    try:
        approval_service = get_approval_service(db)
        skip = (page - 1) * page_size

        results = await approval_service.get_manual_review_queue(
            limit=page_size,
            skip=skip
        )

        # Get total count
        total_count = await db.verification_results.count_documents({
            "ai_recommendation": AIRecommendation.REVIEW.value,
            "$or": [
                {"authority_confirmation": None},
                {"authority_confirmation": {"$exists": False}}
            ]
        })

        return {
            "success": True,
            "data": {
                "reports": results,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }

    except Exception as e:
        logger.error(f"Error getting manual review queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get manual review queue"
        )


@router.get("/approval-stats")
async def get_approval_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get approval statistics for the specified period (V2).

    Shows breakdown by approval source (AI_AUTO, AI_RECOMMENDED, AUTHORITY_MANUAL, etc.)

    Requires authority or analyst role.
    """
    if current_user.role not in [UserRole.ANALYST, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only analysts and authorities can view approval statistics"
        )

    try:
        from datetime import timedelta

        approval_service = get_approval_service(db)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        stats = await approval_service.get_approval_stats(
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting approval stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approval statistics"
        )

