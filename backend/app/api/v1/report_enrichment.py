"""
Report Enrichment API Routes
Separate endpoints for environmental data fetching and hazard classification.
Part of the report verification loop.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.middleware.rbac import get_current_user, require_analyst
from app.models.hazard import (
    ThreatLevel, EnvironmentalSnapshot, HazardClassification,
    ExtendedWeatherData, MarineData, AstronomyData, SeismicData
)
from app.services.environmental_data_service import (
    get_environmental_service,
    fetch_environmental_snapshot
)
from app.services.report_hazard_classifier import (
    get_hazard_classifier,
    classify_hazard_threat
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrichment", tags=["Report Enrichment"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CoordinatesRequest(BaseModel):
    """Request model for coordinates-based operations."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class WeatherDataRequest(CoordinatesRequest):
    """Request for weather data only."""
    pass


class MarineDataRequest(CoordinatesRequest):
    """Request for marine data only."""
    pass


class AstronomyDataRequest(CoordinatesRequest):
    """Request for astronomy data only."""
    pass


class SeismicDataRequest(CoordinatesRequest):
    """Request for seismic/earthquake data."""
    radius_km: Optional[float] = Field(default=500, description="Search radius in km")
    lookback_days: Optional[int] = Field(default=7, description="Days to look back")
    min_magnitude: Optional[float] = Field(default=3.0, description="Minimum magnitude")


class EnvironmentalDataRequest(CoordinatesRequest):
    """Request for complete environmental data."""
    pass


class ClassificationRequest(BaseModel):
    """Request for threat classification from environmental data."""
    environmental_snapshot: EnvironmentalSnapshot
    reported_hazard_type: Optional[str] = Field(default=None, description="User-reported hazard type")


class EnrichmentRequest(CoordinatesRequest):
    """Request for full enrichment pipeline."""
    reported_hazard_type: Optional[str] = Field(default=None, description="User-reported hazard type")


class ReportEnrichRequest(BaseModel):
    """Request to enrich an existing report."""
    report_id: str = Field(..., description="Report ID to enrich")


class WeatherDataResponse(BaseModel):
    """Response for weather data."""
    success: bool
    data: Optional[ExtendedWeatherData]
    error: Optional[str] = None
    fetched_at: datetime


class MarineDataResponse(BaseModel):
    """Response for marine data."""
    success: bool
    data: Optional[MarineData]
    error: Optional[str] = None
    fetched_at: datetime


class AstronomyDataResponse(BaseModel):
    """Response for astronomy data."""
    success: bool
    data: Optional[AstronomyData]
    error: Optional[str] = None
    fetched_at: datetime


class SeismicDataResponse(BaseModel):
    """Response for seismic data."""
    success: bool
    data: Optional[SeismicData]
    message: Optional[str] = None
    error: Optional[str] = None
    fetched_at: datetime


class EnvironmentalDataResponse(BaseModel):
    """Response for complete environmental data."""
    success: bool
    snapshot: EnvironmentalSnapshot
    coordinates: dict
    fetched_at: datetime


class ClassificationResponse(BaseModel):
    """Response for threat classification."""
    success: bool
    classification: HazardClassification
    threat_summary: dict
    classified_at: datetime


class EnrichmentResponse(BaseModel):
    """Response for full enrichment pipeline."""
    success: bool
    environmental_snapshot: EnvironmentalSnapshot
    hazard_classification: HazardClassification
    threat_level: str
    threat_level_name: str
    primary_hazard: Optional[str]
    recommendations: list
    coordinates: dict
    processing_time_ms: float


class ReportEnrichResponse(BaseModel):
    """Response for report enrichment."""
    success: bool
    report_id: str
    environmental_snapshot: Optional[EnvironmentalSnapshot]
    hazard_classification: Optional[HazardClassification]
    message: str


# =============================================================================
# PUBLIC ENDPOINTS (For frontend integration)
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for enrichment service."""
    service = get_environmental_service()
    classifier = get_hazard_classifier()

    return {
        "status": "healthy",
        "environmental_service": "ready",
        "classifier_service": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/weather", response_model=WeatherDataResponse)
async def fetch_weather_data(request: WeatherDataRequest):
    """
    Fetch current weather data for coordinates.
    Public endpoint - no authentication required.
    """
    try:
        service = get_environmental_service()
        weather, error = await service.fetch_weather_data(
            request.latitude,
            request.longitude
        )

        return WeatherDataResponse(
            success=weather is not None,
            data=weather,
            error=error,
            fetched_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Weather fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch weather data: {str(e)}"
        )


@router.post("/marine", response_model=MarineDataResponse)
async def fetch_marine_data(request: MarineDataRequest):
    """
    Fetch marine/ocean data for coordinates.
    Public endpoint - no authentication required.
    """
    try:
        service = get_environmental_service()
        marine, error = await service.fetch_marine_data(
            request.latitude,
            request.longitude
        )

        return MarineDataResponse(
            success=marine is not None,
            data=marine,
            error=error,
            fetched_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Marine fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch marine data: {str(e)}"
        )


@router.post("/astronomy", response_model=AstronomyDataResponse)
async def fetch_astronomy_data(request: AstronomyDataRequest):
    """
    Fetch astronomy data for coordinates.
    Public endpoint - no authentication required.
    """
    try:
        service = get_environmental_service()
        astronomy, error = await service.fetch_astronomy_data(
            request.latitude,
            request.longitude
        )

        return AstronomyDataResponse(
            success=astronomy is not None,
            data=astronomy,
            error=error,
            fetched_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Astronomy fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch astronomy data: {str(e)}"
        )


@router.post("/seismic", response_model=SeismicDataResponse)
async def fetch_seismic_data(request: SeismicDataRequest):
    """
    Fetch recent earthquake/seismic data near coordinates.
    Public endpoint - no authentication required.
    """
    try:
        service = get_environmental_service()
        seismic, error = await service.fetch_seismic_data(
            request.latitude,
            request.longitude,
            radius_km=request.radius_km,
            lookback_days=request.lookback_days,
            min_magnitude=request.min_magnitude
        )

        message = None
        if seismic is None and error is None:
            message = "No significant earthquakes detected in the area"

        return SeismicDataResponse(
            success=error is None,
            data=seismic,
            message=message,
            error=error,
            fetched_at=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Seismic fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch seismic data: {str(e)}"
        )


@router.post("/environmental", response_model=EnvironmentalDataResponse)
async def fetch_environmental_data(request: EnvironmentalDataRequest):
    """
    Fetch complete environmental data snapshot for coordinates.
    Fetches weather, marine, astronomy, and seismic data concurrently.
    Public endpoint - no authentication required.
    """
    try:
        snapshot = await fetch_environmental_snapshot(
            request.latitude,
            request.longitude
        )

        return EnvironmentalDataResponse(
            success=snapshot.fetch_success,
            snapshot=snapshot,
            coordinates={
                "latitude": request.latitude,
                "longitude": request.longitude
            },
            fetched_at=snapshot.fetched_at
        )

    except Exception as e:
        logger.error(f"Environmental data fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch environmental data: {str(e)}"
        )


@router.post("/classify", response_model=ClassificationResponse)
async def classify_threat(request: ClassificationRequest):
    """
    Classify threat levels from environmental data.
    Pass the environmental snapshot to get threat classification.
    Public endpoint - no authentication required.
    """
    try:
        classification = classify_hazard_threat(
            request.environmental_snapshot,
            request.reported_hazard_type
        )

        # Build threat summary
        threat_summary = {
            "overall": classification.threat_level.value,
            "overall_name": classification.threat_level.name,
            "tsunami": classification.tsunami_threat.value if classification.tsunami_threat else "no_threat",
            "cyclone": classification.cyclone_threat.value if classification.cyclone_threat else "no_threat",
            "high_waves": classification.high_waves_threat.value if classification.high_waves_threat else "no_threat",
            "coastal_flood": classification.coastal_flood_threat.value if classification.coastal_flood_threat else "no_threat",
            "rip_current": classification.rip_current_threat.value if classification.rip_current_threat else "no_threat"
        }

        return ClassificationResponse(
            success=True,
            classification=classification,
            threat_summary=threat_summary,
            classified_at=classification.classified_at
        )

    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to classify threat: {str(e)}"
        )


@router.post("/full", response_model=EnrichmentResponse)
async def full_enrichment_pipeline(request: EnrichmentRequest):
    """
    Execute full enrichment pipeline: fetch environmental data + classify threats.
    This is the main endpoint for report submission enrichment.
    Public endpoint - no authentication required.
    """
    import time
    start_time = time.time()

    try:
        # Step 1: Fetch environmental data
        snapshot = await fetch_environmental_snapshot(
            request.latitude,
            request.longitude
        )

        # Step 2: Classify threat
        classification = classify_hazard_threat(
            snapshot,
            request.reported_hazard_type
        )

        processing_time = (time.time() - start_time) * 1000

        return EnrichmentResponse(
            success=True,
            environmental_snapshot=snapshot,
            hazard_classification=classification,
            threat_level=classification.threat_level.value,
            threat_level_name=classification.threat_level.name,
            primary_hazard=classification.hazard_type,
            recommendations=classification.recommendations or [],
            coordinates={
                "latitude": request.latitude,
                "longitude": request.longitude
            },
            processing_time_ms=round(processing_time, 2)
        )

    except Exception as e:
        logger.error(f"Full enrichment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment failed: {str(e)}"
        )


# =============================================================================
# ANALYST ENDPOINTS (Requires Authentication)
# =============================================================================

@router.post("/report/{report_id}/enrich", response_model=ReportEnrichResponse)
async def enrich_existing_report(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Enrich an existing report with environmental data and classification.
    Requires Analyst role or higher.
    """
    try:
        # Find the report
        report = await db.hazard_reports.find_one({"report_id": report_id})
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )

        # Get coordinates from report
        location = report.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report does not have valid coordinates"
            )

        # Fetch environmental data
        snapshot = await fetch_environmental_snapshot(latitude, longitude)

        # Classify threat
        reported_type = report.get("hazard_type")
        classification = classify_hazard_threat(snapshot, reported_type)

        # Update the report
        update_result = await db.hazard_reports.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "environmental_snapshot": snapshot.model_dump(),
                    "hazard_classification": classification.model_dump(),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if update_result.modified_count == 0:
            logger.warning(f"Report {report_id} was not modified during enrichment")

        logger.info(f"Report {report_id} enriched by {current_user.user_id} - Threat: {classification.threat_level.value}")

        return ReportEnrichResponse(
            success=True,
            report_id=report_id,
            environmental_snapshot=snapshot,
            hazard_classification=classification,
            message=f"Report enriched successfully. Threat level: {classification.threat_level.name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report enrichment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enrich report: {str(e)}"
        )


@router.post("/report/batch-enrich")
async def batch_enrich_reports(
    report_ids: list[str] = Query(..., description="List of report IDs to enrich"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Batch enrich multiple reports.
    Requires Analyst role or higher.
    """
    results = []
    success_count = 0
    error_count = 0

    for report_id in report_ids:
        try:
            # Find the report
            report = await db.hazard_reports.find_one({"report_id": report_id})
            if not report:
                results.append({
                    "report_id": report_id,
                    "success": False,
                    "error": "Report not found"
                })
                error_count += 1
                continue

            # Get coordinates
            location = report.get("location", {})
            latitude = location.get("latitude")
            longitude = location.get("longitude")

            if latitude is None or longitude is None:
                results.append({
                    "report_id": report_id,
                    "success": False,
                    "error": "Invalid coordinates"
                })
                error_count += 1
                continue

            # Fetch and classify
            snapshot = await fetch_environmental_snapshot(latitude, longitude)
            classification = classify_hazard_threat(
                snapshot,
                report.get("hazard_type")
            )

            # Update report
            await db.hazard_reports.update_one(
                {"report_id": report_id},
                {
                    "$set": {
                        "environmental_snapshot": snapshot.model_dump(),
                        "hazard_classification": classification.model_dump(),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            results.append({
                "report_id": report_id,
                "success": True,
                "threat_level": classification.threat_level.value
            })
            success_count += 1

        except Exception as e:
            results.append({
                "report_id": report_id,
                "success": False,
                "error": str(e)
            })
            error_count += 1

    logger.info(f"Batch enrichment by {current_user.user_id}: {success_count} success, {error_count} errors")

    return {
        "success": error_count == 0,
        "total": len(report_ids),
        "success_count": success_count,
        "error_count": error_count,
        "results": results
    }


@router.get("/thresholds")
async def get_classification_thresholds(
    current_user: User = Depends(require_analyst)
):
    """
    Get current classification thresholds.
    Requires Analyst role or higher.
    """
    classifier = get_hazard_classifier()
    return {
        "thresholds": classifier.thresholds.model_dump(),
        "description": {
            "tsunami": "Based on earthquake magnitude, depth, and distance",
            "cyclone": "Based on wind speed and atmospheric pressure",
            "high_waves": "Based on wave height and wind conditions",
            "coastal_flood": "Based on precipitation and tidal conditions",
            "rip_current": "Based on wind, waves, and swell period"
        }
    }
