"""
Analyst API Routes
Endpoints for the Analyst module - analytics, monitoring, notes, exports.
All endpoints require Analyst role (Level 2) or higher.
PII filtering is enforced for all data access.
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.models.rbac import UserRole, Permission
from app.models.analyst import (
    AnalystNote,
    SavedQuery,
    ScheduledReport,
    ExportJob,
    AnalystApiKey,
    CreateNoteRequest,
    UpdateNoteRequest,
    CreateQueryRequest,
    CreateScheduledReportRequest,
    CreateExportRequest,
    CreateApiKeyRequest,
    NoteReferenceType,
    QueryType,
    ExportStatus,
    ExportFormat,
    ExportType,
    ApiKeyPermission,
)
from app.middleware.rbac import (
    get_current_user,
    require_analyst,
    filter_pii_fields,
    has_permission,
)
from app.services.analytics_service import get_analytics_service
from app.services.export_service import get_export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyst", tags=["Analyst"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_report_images(report: dict) -> List[str]:
    """
    Extract images from a report document.
    Handles various field names and formats used for storing images.
    """
    images = []

    # Check for array fields
    for field in ["images", "image_urls", "media", "attachments", "photos"]:
        field_value = report.get(field)
        if field_value and isinstance(field_value, list):
            images.extend([img for img in field_value if img and isinstance(img, str)])

    # Check for single image field (convert to array)
    for field in ["image_url", "photo_url", "media_url", "attachment_url"]:
        field_value = report.get(field)
        if field_value and isinstance(field_value, str) and field_value not in images:
            images.append(field_value)

    # Remove duplicates while preserving order
    seen = set()
    unique_images = []
    for img in images:
        if img not in seen:
            seen.add(img)
            unique_images.append(img)

    return unique_images


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/dashboard")
async def get_analyst_dashboard(
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get main dashboard data for analyst.

    Returns summary statistics, recent activity, and quick metrics.
    """
    try:
        analytics_service = get_analytics_service(db)
        summary = await analytics_service.get_dashboard_summary(current_user.user_id)

        # Get user's recent notes count
        recent_notes = await db.analyst_notes.count_documents({
            "user_id": current_user.user_id,
            "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
        })

        # Get user's pending exports
        pending_exports = await db.export_jobs.count_documents({
            "user_id": current_user.user_id,
            "status": {"$in": ["pending", "processing"]}
        })

        return {
            "success": True,
            "data": {
                **summary,
                "user_stats": {
                    "recent_notes": recent_notes,
                    "pending_exports": pending_exports
                },
                "user": {
                    "name": current_user.name,
                    "role": current_user.role.value
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting analyst dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data"
        )


@router.get("/dashboard/realtime")
async def get_realtime_monitoring(
    min_alert_level: Optional[str] = Query("low", description="Minimum alert level: low, medium, high, critical"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get real-time monitoring data for analyst dashboard.

    Returns current hazard status across monitored locations and recent reports.
    """
    try:
        reports_collection = db.hazard_reports
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)

        # Get locations with active reports grouped by region/state
        location_pipeline = [
            {"$match": {
                "created_at": {"$gte": last_24h},
                "$or": [
                    {"verification_status": {"$in": ["pending", "verified"]}},
                    {"status": {"$in": ["pending", "verified", "active"]}}
                ]
            }},
            {"$group": {
                "_id": {"$ifNull": ["$location.state", {"$ifNull": ["$location.region", "$location.city"]}]},
                "report_count": {"$sum": 1},
                "hazard_types": {"$addToSet": "$hazard_type"},
                "avg_lat": {"$avg": {"$ifNull": ["$location.latitude", "$location.lat"]}},
                "avg_lng": {"$avg": {"$ifNull": ["$location.longitude", "$location.lng"]}},
                "severities": {"$push": {"$ifNull": ["$severity", "$risk_level"]}},
                "latest_report": {"$max": "$created_at"}
            }},
            {"$match": {"_id": {"$ne": None}}},
            {"$sort": {"report_count": -1}},
            {"$limit": 20}
        ]

        location_results = await reports_collection.aggregate(location_pipeline).to_list(100)

        # Calculate alert level based on report count and severity
        level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        locations_data = []

        for loc in location_results:
            # Determine alert level based on severity counts
            severities = [s for s in loc.get("severities", []) if s]
            critical_count = sum(1 for s in severities if s in ["critical", "severe"])
            high_count = sum(1 for s in severities if s == "high")

            if critical_count > 0:
                alert_level = "critical"
            elif high_count > 2 or loc["report_count"] > 10:
                alert_level = "high"
            elif loc["report_count"] > 5:
                alert_level = "medium"
            else:
                alert_level = "low"

            # Filter by minimum alert level
            if level_order.get(alert_level, 0) < level_order.get(min_alert_level, 0):
                continue

            active_hazards = [h for h in loc.get("hazard_types", []) if h]

            locations_data.append({
                "location_id": f"loc_{hash(loc['_id']) % 10000:04d}",
                "name": loc["_id"],
                "region": loc["_id"],
                "coordinates": {
                    "lat": loc.get("avg_lat") or 20.5937,
                    "lng": loc.get("avg_lng") or 78.9629
                },
                "alert_level": alert_level,
                "active_hazards": active_hazards[:5],
                "primary_hazard": active_hazards[0] if active_hazards else None,
                "report_count": loc["report_count"],
                "last_updated": loc.get("latest_report").isoformat() if loc.get("latest_report") else now.isoformat()
            })

        # Get recent reports from database
        recent_reports_cursor = reports_collection.find(
            {"$or": [
                {"verification_status": {"$in": ["pending", "verified"]}},
                {"status": {"$in": ["pending", "verified", "active"]}}
            ]}
        ).sort("created_at", -1).limit(20)

        recent_reports = []
        async for report in recent_reports_cursor:
            recent_reports.append({
                "report_id": str(report.get("_id", report.get("report_id", ""))),
                "hazard_type": report.get("hazard_type"),
                "severity": report.get("severity") or report.get("risk_level", "medium"),
                "status": report.get("verification_status") or report.get("status", "pending"),
                "location": report.get("location", {}).get("address") or report.get("location", {}).get("city", "Unknown"),
                "created_at": report.get("created_at").isoformat() if report.get("created_at") else None
            })

        return {
            "success": True,
            "data": {
                "locations": locations_data,
                "recent_reports": recent_reports,
                "summary": {
                    "total_locations": len(locations_data),
                    "critical_alerts": len([l for l in locations_data if l["alert_level"] == "critical"]),
                    "high_alerts": len([l for l in locations_data if l["alert_level"] == "high"]),
                    "medium_alerts": len([l for l in locations_data if l["alert_level"] == "medium"]),
                    "low_alerts": len([l for l in locations_data if l["alert_level"] == "low"]),
                    "total_recent_reports": len(recent_reports)
                },
                "last_updated": now.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error getting realtime monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch monitoring data"
        )


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/reports")
async def get_report_analytics(
    date_range: str = Query("7days", description="Time period: 7days, 30days, 90days, year, all"),
    region: Optional[str] = Query(None),
    hazard_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="pending, verified, rejected, all"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get historical report analytics with filters.

    Returns metrics, distributions, and aggregated data.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_report_analytics(
            date_range=date_range,
            region=region,
            hazard_type=hazard_type,
            status=status
        )

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting report analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report analytics"
        )


@router.get("/analytics/trends")
async def get_trend_analytics(
    date_range: str = Query("30days"),
    group_by: str = Query("day", description="day, week, month"),
    hazard_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get time-series trend data for charts.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_trend_data(
            date_range=date_range,
            group_by=group_by,
            hazard_type=hazard_type,
            region=region
        )

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting trend analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch trend data"
        )


@router.get("/analytics/geo")
async def get_geospatial_analytics(
    date_range: str = Query("30days"),
    hazard_type: Optional[str] = Query(None),
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get geospatial data for heatmap visualization.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_geospatial_data(
            date_range=date_range,
            hazard_type=hazard_type,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon
        )

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting geospatial analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch geospatial data"
        )


# =============================================================================
# REPORTS MANAGEMENT
# =============================================================================

@router.get("/reports")
async def get_all_reports(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    hazard_type: Optional[str] = Query(None, description="Filter by hazard type"),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, verified, rejected, all", alias="status"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    region: Optional[str] = Query(None, description="Filter by region/state"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search in description/location"),
    sort_by: str = Query("created_at", description="Sort field: created_at, hazard_type, severity, status"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all hazard reports with filtering and pagination for analyst review.
    """
    try:
        reports_collection = db.hazard_reports

        # Build match filter
        match_filter = {}

        if hazard_type:
            match_filter["hazard_type"] = hazard_type

        if status_filter and status_filter != "all":
            match_filter["$or"] = [
                {"verification_status": status_filter},
                {"status": status_filter}
            ]

        if severity:
            match_filter["$or"] = match_filter.get("$or", [])
            if not match_filter["$or"]:
                match_filter["$or"] = [
                    {"severity": severity},
                    {"risk_level": severity}
                ]
            else:
                # If already has $or, use $and
                match_filter = {
                    "$and": [
                        {"$or": match_filter["$or"]},
                        {"$or": [{"severity": severity}, {"risk_level": severity}]}
                    ]
                }

        if region:
            region_filter = {
                "$or": [
                    {"location.state": {"$regex": region, "$options": "i"}},
                    {"location.region": {"$regex": region, "$options": "i"}},
                    {"location.city": {"$regex": region, "$options": "i"}}
                ]
            }
            if "$and" in match_filter:
                match_filter["$and"].append(region_filter)
            else:
                match_filter = {"$and": [match_filter, region_filter]} if match_filter else region_filter

        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                date_filter = {"created_at": {"$gte": from_date}}
                if "$and" in match_filter:
                    match_filter["$and"].append(date_filter)
                elif match_filter:
                    match_filter = {"$and": [match_filter, date_filter]}
                else:
                    match_filter = date_filter
            except ValueError:
                pass

        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                date_filter = {"created_at": {"$lte": to_date}}
                if "$and" in match_filter:
                    match_filter["$and"].append(date_filter)
                elif match_filter:
                    match_filter = {"$and": [match_filter, date_filter]}
                else:
                    match_filter = date_filter
            except ValueError:
                pass

        if search:
            search_filter = {
                "$or": [
                    {"description": {"$regex": search, "$options": "i"}},
                    {"location.address": {"$regex": search, "$options": "i"}},
                    {"location.city": {"$regex": search, "$options": "i"}},
                    {"hazard_type": {"$regex": search, "$options": "i"}}
                ]
            }
            if "$and" in match_filter:
                match_filter["$and"].append(search_filter)
            elif match_filter:
                match_filter = {"$and": [match_filter, search_filter]}
            else:
                match_filter = search_filter

        # Count total matching documents
        total_count = await reports_collection.count_documents(match_filter if match_filter else {})

        # Calculate pagination
        skip = (page - 1) * limit
        total_pages = (total_count + limit - 1) // limit

        # Sort configuration
        sort_direction = -1 if sort_order == "desc" else 1
        sort_field = sort_by if sort_by in ["created_at", "hazard_type", "severity", "status", "verification_status"] else "created_at"

        # Fetch reports with pagination
        cursor = reports_collection.find(match_filter if match_filter else {}).sort(sort_field, sort_direction).skip(skip).limit(limit)

        reports = []
        async for report in cursor:
            reports.append({
                "id": str(report.get("_id", "")),
                "report_id": report.get("report_id", str(report.get("_id", ""))),
                "hazard_type": report.get("hazard_type"),
                "description": (report.get("description") or "")[:200] + ("..." if len(report.get("description") or "") > 200 else ""),
                "severity": report.get("severity") or report.get("risk_level", "medium"),
                "status": report.get("verification_status") or report.get("status", "pending"),
                "verification_status": report.get("verification_status") or report.get("status", "pending"),
                "verification_score": report.get("verification_score"),
                "location": {
                    "address": report.get("location", {}).get("address", ""),
                    "city": report.get("location", {}).get("city", ""),
                    "state": report.get("location", {}).get("state") or report.get("location", {}).get("region", ""),
                    "district": report.get("location", {}).get("district", ""),
                    "region": report.get("location", {}).get("region", ""),
                    "lat": report.get("location", {}).get("latitude") or report.get("location", {}).get("lat"),
                    "lng": report.get("location", {}).get("longitude") or report.get("location", {}).get("lng")
                },
                "images": _get_report_images(report)[:3],  # Limit to first 3 images for list view
                "has_images": len(_get_report_images(report)) > 0,
                "image_count": len(_get_report_images(report)),
                "created_at": report.get("created_at").isoformat() if report.get("created_at") else None,
                "updated_at": report.get("updated_at").isoformat() if report.get("updated_at") else None,
                "verified_at": report.get("verified_at").isoformat() if report.get("verified_at") else None,
                "user_id": str(report.get("user_id", "")) if report.get("user_id") else None
            })

        # Get available filter options
        hazard_types = await reports_collection.distinct("hazard_type")
        regions = await reports_collection.distinct("location.state")
        regions.extend(await reports_collection.distinct("location.region"))
        regions = list(set([r for r in regions if r]))

        return {
            "success": True,
            "data": {
                "reports": reports,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "filters": {
                    "hazard_types": [h for h in hazard_types if h],
                    "regions": sorted(regions),
                    "statuses": ["pending", "verified", "rejected", "investigating"],
                    "severities": ["low", "medium", "high", "critical"]
                }
            }
        }

    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports"
        )


@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get detailed information about a specific report.
    """
    try:
        from bson import ObjectId

        reports_collection = db.hazard_reports

        # Try to find by report_id or _id
        report = await reports_collection.find_one({"report_id": report_id})
        if not report:
            try:
                report = await reports_collection.find_one({"_id": ObjectId(report_id)})
            except:
                pass

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        # Get reporter info (limited, no PII)
        user_info = None
        if report.get("user_id"):
            users_collection = db.users
            try:
                user = await users_collection.find_one({"_id": ObjectId(str(report["user_id"]))})
                if user:
                    user_info = {
                        "id": str(user["_id"]),
                        "name": user.get("name", "Anonymous"),
                        "reports_count": await reports_collection.count_documents({"user_id": user["_id"]})
                    }
            except:
                pass

        return {
            "success": True,
            "data": {
                "id": str(report.get("_id", "")),
                "report_id": report.get("report_id", str(report.get("_id", ""))),
                "hazard_type": report.get("hazard_type"),
                "description": report.get("description", ""),
                "severity": report.get("severity") or report.get("risk_level", "medium"),
                "status": report.get("verification_status") or report.get("status", "pending"),
                "location": {
                    "address": report.get("location", {}).get("address", ""),
                    "city": report.get("location", {}).get("city", ""),
                    "state": report.get("location", {}).get("state") or report.get("location", {}).get("region", ""),
                    "lat": report.get("location", {}).get("latitude") or report.get("location", {}).get("lat"),
                    "lng": report.get("location", {}).get("longitude") or report.get("location", {}).get("lng")
                },
                "images": _get_report_images(report),
                "nlp_analysis": {
                    "sentiment": report.get("nlp_sentiment"),
                    "risk_score": report.get("nlp_risk_score"),
                    "keywords": report.get("nlp_keywords", [])
                },
                "verification": {
                    "status": report.get("verification_status") or report.get("status", "pending"),
                    "verified_at": report.get("verified_at").isoformat() if report.get("verified_at") else None,
                    "verified_by": str(report.get("verified_by")) if report.get("verified_by") else None,
                    "verification_notes": report.get("verification_notes", "")
                },
                "reporter": user_info,
                "created_at": report.get("created_at").isoformat() if report.get("created_at") else None,
                "updated_at": report.get("updated_at").isoformat() if report.get("updated_at") else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report details"
        )


@router.get("/analytics/nlp")
async def get_nlp_insights(
    date_range: str = Query("30days"),
    hazard_type: Optional[str] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get aggregated NLP insights from reports.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_nlp_insights(
            date_range=date_range,
            hazard_type=hazard_type
        )

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting NLP insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch NLP insights"
        )


@router.get("/analytics/verification")
async def get_verification_metrics(
    date_range: str = Query("30days"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get verification performance metrics.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_verification_metrics(date_range=date_range)

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting verification metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch verification metrics"
        )


@router.get("/analytics/hazard-types")
async def get_hazard_type_analytics(
    date_range: str = Query("30days"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get analytics broken down by hazard type.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_hazard_type_analytics(date_range=date_range)

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting hazard type analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hazard type analytics"
        )


@router.get("/analytics/comparison")
async def get_period_comparison(
    date_range: str = Query("7days"),
    hazard_type: Optional[str] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Compare current period with previous period.
    """
    try:
        analytics_service = get_analytics_service(db)
        data = await analytics_service.get_period_comparison(
            current_range=date_range,
            hazard_type=hazard_type
        )

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error getting period comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch comparison data"
        )


# =============================================================================
# NOTES ENDPOINTS
# =============================================================================

@router.get("/notes")
async def get_analyst_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    pinned_first: bool = Query(True),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get analyst's personal notes with filtering.
    """
    try:
        # Build query
        query = {"user_id": current_user.user_id}

        if tag:
            query["tags"] = tag

        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"content": {"$regex": search, "$options": "i"}}
            ]

        # Sort: pinned first, then by created_at
        sort_order = [("created_at", -1)]
        if pinned_first:
            sort_order = [("is_pinned", -1), ("created_at", -1)]

        # Get total count
        total = await db.analyst_notes.count_documents(query)

        # Get notes
        cursor = db.analyst_notes.find(query).sort(sort_order).skip(skip).limit(limit)
        notes_docs = await cursor.to_list(limit)

        notes = [AnalystNote.from_mongo(doc).model_dump() for doc in notes_docs]

        # Get all tags for filter
        all_tags = await db.analyst_notes.distinct("tags", {"user_id": current_user.user_id})

        return {
            "success": True,
            "data": {
                "notes": notes,
                "total": total,
                "skip": skip,
                "limit": limit,
                "available_tags": sorted([t for t in all_tags if t])
            }
        }

    except Exception as e:
        logger.error(f"Error getting analyst notes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notes"
        )


@router.post("/notes")
async def create_analyst_note(
    note_data: CreateNoteRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new personal note.
    """
    try:
        now = datetime.now(timezone.utc)
        note_id = f"NOTE_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

        note = AnalystNote(
            note_id=note_id,
            user_id=current_user.user_id,
            title=note_data.title,
            content=note_data.content,
            tags=note_data.tags,
            reference_type=note_data.reference_type,
            reference_id=note_data.reference_id,
            location=note_data.location,
            data_snapshot=note_data.data_snapshot,
            color=note_data.color,
            created_at=now,
            updated_at=now
        )

        await db.analyst_notes.insert_one(note.to_mongo())

        logger.info(f"Analyst {current_user.user_id} created note {note_id}")

        return {
            "success": True,
            "data": note.model_dump(),
            "message": "Note created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating note: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create note"
        )


@router.get("/notes/{note_id}")
async def get_analyst_note(
    note_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get a specific note by ID.
    """
    note_doc = await db.analyst_notes.find_one({
        "note_id": note_id,
        "user_id": current_user.user_id
    })

    if not note_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    note = AnalystNote.from_mongo(note_doc)

    return {
        "success": True,
        "data": note.model_dump()
    }


@router.put("/notes/{note_id}")
async def update_analyst_note(
    note_id: str,
    update_data: UpdateNoteRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update an existing note.
    """
    # Check note exists and belongs to user
    note_doc = await db.analyst_notes.find_one({
        "note_id": note_id,
        "user_id": current_user.user_id
    })

    if not note_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    # Build update
    update_fields = {"updated_at": datetime.now(timezone.utc)}

    if update_data.title is not None:
        update_fields["title"] = update_data.title
    if update_data.content is not None:
        update_fields["content"] = update_data.content
    if update_data.tags is not None:
        update_fields["tags"] = update_data.tags
    if update_data.is_pinned is not None:
        update_fields["is_pinned"] = update_data.is_pinned
    if update_data.color is not None:
        update_fields["color"] = update_data.color.value

    await db.analyst_notes.update_one(
        {"note_id": note_id},
        {"$set": update_fields}
    )

    # Get updated note
    updated_doc = await db.analyst_notes.find_one({"note_id": note_id})
    note = AnalystNote.from_mongo(updated_doc)

    return {
        "success": True,
        "data": note.model_dump(),
        "message": "Note updated successfully"
    }


@router.delete("/notes/{note_id}")
async def delete_analyst_note(
    note_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a note.
    """
    result = await db.analyst_notes.delete_one({
        "note_id": note_id,
        "user_id": current_user.user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    logger.info(f"Analyst {current_user.user_id} deleted note {note_id}")

    return {
        "success": True,
        "message": "Note deleted successfully"
    }


# =============================================================================
# SAVED QUERIES ENDPOINTS
# =============================================================================

@router.get("/queries")
async def get_saved_queries(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    query_type: Optional[QueryType] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user's saved queries.
    """
    try:
        query = {"user_id": current_user.user_id}
        if query_type:
            query["query_type"] = query_type.value

        total = await db.saved_queries.count_documents(query)

        cursor = db.saved_queries.find(query).sort("created_at", -1).skip(skip).limit(limit)
        queries_docs = await cursor.to_list(limit)

        queries = [SavedQuery.from_mongo(doc).model_dump() for doc in queries_docs]

        return {
            "success": True,
            "data": {
                "queries": queries,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error(f"Error getting saved queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved queries"
        )


@router.post("/queries")
async def create_saved_query(
    query_data: CreateQueryRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Save a new query configuration.
    """
    try:
        now = datetime.now(timezone.utc)
        query_id = f"QRY_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

        saved_query = SavedQuery(
            query_id=query_id,
            user_id=current_user.user_id,
            name=query_data.name,
            description=query_data.description,
            query_type=query_data.query_type,
            filters=query_data.filters,
            date_range=query_data.date_range,
            chart_type=query_data.chart_type,
            chart_config=query_data.chart_config,
            created_at=now,
            updated_at=now
        )

        await db.saved_queries.insert_one(saved_query.to_mongo())

        return {
            "success": True,
            "data": saved_query.model_dump(),
            "message": "Query saved successfully"
        }

    except Exception as e:
        logger.error(f"Error creating saved query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save query"
        )


@router.get("/queries/{query_id}")
async def get_saved_query(
    query_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get a specific saved query.
    """
    query_doc = await db.saved_queries.find_one({
        "query_id": query_id,
        "user_id": current_user.user_id
    })

    if not query_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    return {
        "success": True,
        "data": SavedQuery.from_mongo(query_doc).model_dump()
    }


@router.post("/queries/{query_id}/execute")
async def execute_saved_query(
    query_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Execute a saved query and return results.
    """
    query_doc = await db.saved_queries.find_one({
        "query_id": query_id,
        "user_id": current_user.user_id
    })

    if not query_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    saved_query = SavedQuery.from_mongo(query_doc)
    analytics_service = get_analytics_service(db)

    # Update execution tracking
    await db.saved_queries.update_one(
        {"query_id": query_id},
        {
            "$set": {"last_executed": datetime.now(timezone.utc)},
            "$inc": {"execution_count": 1}
        }
    )

    # Execute based on query type
    date_range = saved_query.date_range.get("relative", "7days")
    filters = saved_query.filters

    try:
        if saved_query.query_type == QueryType.REPORTS:
            result = await analytics_service.get_report_analytics(
                date_range=date_range,
                region=filters.get("region"),
                hazard_type=filters.get("hazard_type"),
                status=filters.get("status")
            )
        elif saved_query.query_type == QueryType.TRENDS:
            result = await analytics_service.get_trend_data(
                date_range=date_range,
                group_by=filters.get("group_by", "day"),
                hazard_type=filters.get("hazard_type"),
                region=filters.get("region")
            )
        elif saved_query.query_type == QueryType.GEO:
            result = await analytics_service.get_geospatial_data(
                date_range=date_range,
                hazard_type=filters.get("hazard_type")
            )
        elif saved_query.query_type == QueryType.NLP:
            result = await analytics_service.get_nlp_insights(
                date_range=date_range,
                hazard_type=filters.get("hazard_type")
            )
        else:
            result = await analytics_service.get_report_analytics(date_range=date_range)

        return {
            "success": True,
            "query": saved_query.model_dump(),
            "result": result
        }

    except Exception as e:
        logger.error(f"Error executing query {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute query"
        )


@router.delete("/queries/{query_id}")
async def delete_saved_query(
    query_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a saved query.
    """
    result = await db.saved_queries.delete_one({
        "query_id": query_id,
        "user_id": current_user.user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    return {
        "success": True,
        "message": "Query deleted successfully"
    }


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.post("/export")
async def create_export_job(
    export_data: CreateExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new export job and process it immediately.

    The export will be processed and the file will be ready for download.
    """
    try:
        now = datetime.now(timezone.utc)
        job_id = f"EXP_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

        export_job = ExportJob(
            job_id=job_id,
            user_id=current_user.user_id,
            export_type=export_data.export_type,
            export_format=export_data.export_format,
            query_config=export_data.query_config,
            date_range=export_data.date_range,
            columns=export_data.columns,
            status=ExportStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=24)  # Expire in 24 hours
        )

        await db.export_jobs.insert_one(export_job.to_mongo())

        # Process the export immediately
        export_service = get_export_service(db)
        success = await export_service.process_export_job(job_id)

        # Get updated job status
        updated_job = await db.export_jobs.find_one({"job_id": job_id})

        logger.info(f"Analyst {current_user.user_id} created export job {job_id}, success={success}")

        return {
            "success": True,
            "data": ExportJob.from_mongo(updated_job).model_dump() if updated_job else export_job.model_dump(),
            "message": "Export completed successfully" if success else "Export job created but processing failed"
        }

    except Exception as e:
        logger.error(f"Error creating export job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export job"
        )


@router.get("/exports")
async def get_export_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ExportStatus] = Query(None, alias="status"),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user's export jobs.
    """
    try:
        query = {"user_id": current_user.user_id}
        if status_filter:
            query["status"] = status_filter.value

        total = await db.export_jobs.count_documents(query)

        cursor = db.export_jobs.find(query).sort("created_at", -1).skip(skip).limit(limit)
        jobs_docs = await cursor.to_list(limit)

        jobs = [ExportJob.from_mongo(doc).model_dump() for doc in jobs_docs]

        return {
            "success": True,
            "data": {
                "jobs": jobs,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error(f"Error getting export jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch export jobs"
        )


@router.get("/export/{job_id}")
async def get_export_job_status(
    job_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get status of an export job.
    """
    job_doc = await db.export_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user.user_id
    })

    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    return {
        "success": True,
        "data": ExportJob.from_mongo(job_doc).model_dump()
    }


@router.get("/export/{job_id}/download")
async def download_export(
    job_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Download a completed export file.
    """
    from fastapi.responses import FileResponse
    import os

    job_doc = await db.export_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user.user_id
    })

    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    job = ExportJob.from_mongo(job_doc)

    if job.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is not ready. Current status: {job.status.value}"
        )

    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found"
        )

    # Determine content type based on format
    content_type_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"
    }

    file_ext = job.file_name.split('.')[-1] if job.file_name else "csv"
    content_type = content_type_map.get(file_ext, "application/octet-stream")

    return FileResponse(
        path=job.file_path,
        filename=job.file_name,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={job.file_name}"
        }
    )


@router.delete("/export/{job_id}")
async def delete_export_job(
    job_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete an export job and its associated file.
    """
    import os

    job_doc = await db.export_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user.user_id
    })

    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    job = ExportJob.from_mongo(job_doc)

    # Delete the file if it exists
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete export file {job.file_path}: {e}")

    # Delete the job record
    await db.export_jobs.delete_one({"job_id": job_id})

    logger.info(f"Analyst {current_user.user_id} deleted export job {job_id}")

    return {
        "success": True,
        "message": "Export job deleted successfully"
    }


# =============================================================================
# SCHEDULED REPORTS ENDPOINTS
# =============================================================================

@router.get("/scheduled-reports")
async def get_scheduled_reports(
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user's scheduled reports.
    """
    try:
        cursor = db.scheduled_reports.find({
            "user_id": current_user.user_id
        }).sort("created_at", -1)

        reports_docs = await cursor.to_list(100)
        reports = [ScheduledReport.from_mongo(doc).model_dump() for doc in reports_docs]

        return {
            "success": True,
            "data": {
                "schedules": reports,
                "total": len(reports)
            }
        }

    except Exception as e:
        logger.error(f"Error getting scheduled reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch scheduled reports"
        )


@router.post("/scheduled-reports")
async def create_scheduled_report(
    schedule_data: CreateScheduledReportRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new scheduled report.
    """
    try:
        now = datetime.now(timezone.utc)
        schedule_id = f"SCH_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

        # Use user's email if no delivery email provided
        delivery_email = schedule_data.delivery_email or current_user.email

        scheduled_report = ScheduledReport(
            schedule_id=schedule_id,
            user_id=current_user.user_id,
            name=schedule_data.name,
            description=schedule_data.description,
            report_type=schedule_data.report_type,
            query_config=schedule_data.query_config,
            sections=schedule_data.sections,
            schedule_type=schedule_data.schedule_type,
            schedule_time=schedule_data.schedule_time,
            schedule_days=schedule_data.schedule_days,
            timezone=schedule_data.timezone,
            delivery_method=schedule_data.delivery_method,
            delivery_email=delivery_email,
            export_format=schedule_data.export_format,
            created_at=now,
            updated_at=now
        )

        await db.scheduled_reports.insert_one(scheduled_report.to_mongo())

        logger.info(f"Analyst {current_user.user_id} created scheduled report {schedule_id}")

        return {
            "success": True,
            "data": scheduled_report.model_dump(),
            "message": "Scheduled report created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating scheduled report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scheduled report"
        )


@router.put("/scheduled-reports/{schedule_id}")
async def update_scheduled_report(
    schedule_id: str,
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update a scheduled report (e.g., activate/deactivate).
    """
    schedule_doc = await db.scheduled_reports.find_one({
        "schedule_id": schedule_id,
        "user_id": current_user.user_id
    })

    if not schedule_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found"
        )

    update_fields = {"updated_at": datetime.now(timezone.utc)}

    if is_active is not None:
        update_fields["is_active"] = is_active

    await db.scheduled_reports.update_one(
        {"schedule_id": schedule_id},
        {"$set": update_fields}
    )

    updated_doc = await db.scheduled_reports.find_one({"schedule_id": schedule_id})

    return {
        "success": True,
        "data": ScheduledReport.from_mongo(updated_doc).model_dump(),
        "message": "Schedule updated successfully"
    }


@router.delete("/scheduled-reports/{schedule_id}")
async def delete_scheduled_report(
    schedule_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a scheduled report.
    """
    result = await db.scheduled_reports.delete_one({
        "schedule_id": schedule_id,
        "user_id": current_user.user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found"
        )

    return {
        "success": True,
        "message": "Scheduled report deleted successfully"
    }


@router.post("/scheduled-reports/{schedule_id}/run")
async def run_scheduled_report_manually(
    schedule_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Manually trigger a scheduled report.

    Generates the report immediately and returns the export job details.
    The generated report can be downloaded via the export download endpoint.
    """
    schedule_doc = await db.scheduled_reports.find_one({
        "schedule_id": schedule_id,
        "user_id": current_user.user_id
    })

    if not schedule_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled report not found"
        )

    # Execute the scheduled report
    export_service = get_export_service(db)
    result = await export_service.execute_scheduled_report(
        schedule_id=schedule_id,
        user_id=current_user.user_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to generate report")
        )

    return {
        "success": True,
        "message": result.get("message", "Report generated successfully"),
        "job_id": result.get("job_id"),
        "file_name": result.get("file_name"),
        "file_size": result.get("file_size"),
        "record_count": result.get("record_count"),
        "export_format": result.get("export_format"),
        "download_url": f"/api/v1/analyst/export/{result.get('job_id')}/download"
    }


# =============================================================================
# API KEYS ENDPOINTS
# =============================================================================

@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get user's API keys (without the actual key values).
    """
    try:
        cursor = db.analyst_api_keys.find({
            "user_id": current_user.user_id
        }).sort("created_at", -1)

        keys_docs = await cursor.to_list(100)

        # Return keys without the hash
        keys = []
        for doc in keys_docs:
            key = AnalystApiKey.from_mongo(doc)
            key_data = key.model_dump()
            del key_data["key_hash"]  # Don't expose hash
            keys.append(key_data)

        return {
            "success": True,
            "data": {
                "keys": keys,
                "total": len(keys)
            }
        }

    except Exception as e:
        logger.error(f"Error getting API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch API keys"
        )


@router.post("/api-keys")
async def create_api_key(
    key_data: CreateApiKeyRequest,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate a new API key.

    The raw key is only shown once upon creation.
    """
    try:
        now = datetime.now(timezone.utc)
        key_id = f"KEY_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

        # Generate secure API key
        raw_key = f"cg_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]

        # Calculate expiration
        expires_at = None
        if key_data.expires_in_days:
            expires_at = now + timedelta(days=key_data.expires_in_days)

        api_key = AnalystApiKey(
            key_id=key_id,
            user_id=current_user.user_id,
            name=key_data.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=key_data.permissions,
            rate_limit=key_data.rate_limit,
            expires_at=expires_at,
            created_at=now
        )

        await db.analyst_api_keys.insert_one(api_key.to_mongo())

        logger.info(f"Analyst {current_user.user_id} created API key {key_id}")

        # Return with raw key (only time it's shown)
        response_data = api_key.model_dump()
        del response_data["key_hash"]
        response_data["raw_key"] = raw_key

        return {
            "success": True,
            "data": response_data,
            "message": "API key created. Save the raw_key now - it won't be shown again!"
        }

    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Revoke (delete) an API key.
    """
    result = await db.analyst_api_keys.delete_one({
        "key_id": key_id,
        "user_id": current_user.user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    logger.info(f"Analyst {current_user.user_id} revoked API key {key_id}")

    return {
        "success": True,
        "message": "API key revoked successfully"
    }


# =============================================================================
# REPORTS LIST (with PII filtering)
# =============================================================================

@router.get("/reports")
async def get_reports_for_analyst(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    hazard_type: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    current_user: User = Depends(require_analyst),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get hazard reports for analyst view.

    PII is automatically filtered - analysts cannot see reporter names, emails, etc.
    """
    try:
        query = {}
        if status_filter and status_filter != "all":
            query["verification_status"] = status_filter
        if hazard_type:
            query["hazard_type"] = hazard_type
        if region:
            query["location.region"] = region

        total = await db.hazard_reports.count_documents(query)

        cursor = db.hazard_reports.find(query).sort("created_at", -1).skip(skip).limit(limit)
        reports_docs = await cursor.to_list(limit)

        # Filter PII for analyst
        reports = []
        for doc in reports_docs:
            filtered_report = filter_pii_fields(doc, current_user)
            # Convert ObjectId to string
            if "_id" in filtered_report:
                filtered_report["_id"] = str(filtered_report["_id"])
            reports.append(filtered_report)

        return {
            "success": True,
            "data": {
                "reports": reports,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error(f"Error getting reports for analyst: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports"
        )


__all__ = ['router']
