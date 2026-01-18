"""
Social Media Intelligence (SMI) API Routes
Endpoints for accessing the SMI module functionality with authentication.

All endpoints require at least Analyst role for access.
Authority Admin has full access to all features including feed control.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_database
from app.models.user import User
from app.models.rbac import UserRole
from app.middleware.rbac import (
    get_current_user,
    require_analyst,
    require_admin,
)
from app.services.smi_service import get_smi_service, SMIService, get_demo_service, DemoModeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smi", tags=["Social Media Intelligence"])


# =============================================================================
# DEPENDENCY: Get SMI Service with DB (defined early for use in all endpoints)
# =============================================================================

async def get_smi_with_db(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> SMIService:
    """Get SMI service instance with database connection."""
    return get_smi_service(db)


# =============================================================================
# PUBLIC ENDPOINTS (No Authentication Required - For Citizen Dashboard)
# =============================================================================

@router.get("/public/health")
async def public_health_check(
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Public health check for SMI module.
    No authentication required - used by citizen dashboard.
    """
    try:
        health = await smi.check_health()
        return {
            "success": True,
            "data": {
                "status": health.get("smi_status", "offline"),
                "is_connected": health.get("is_connected", False)
            },
            "enabled": settings.SMI_ENABLED
        }
    except Exception as e:
        return {
            "success": False,
            "data": {"status": "offline", "is_connected": False},
            "enabled": settings.SMI_ENABLED
        }


@router.get("/public/alerts")
async def public_get_alerts(
    limit: int = Query(default=20, ge=1, le=50),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get active SMI alerts for public display (citizen dashboard).
    No authentication required.
    Returns limited alert data without sensitive information.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"alerts": [], "count": 0}
        }

    try:
        result = await smi.get_active_alerts()
        alerts = result.get("alerts", [])

        # Filter and sanitize alerts for public display
        public_alerts = []
        for alert in alerts[:limit]:
            public_alert = {
                "alert_level": alert.get("alert_level", "LOW"),
                "disaster_type": alert.get("disaster_type", "unknown"),
                "location": alert.get("location", ""),
                "relevance_score": alert.get("relevance_score", 0),
                "timestamp": alert.get("timestamp"),
                "post_excerpt": alert.get("post_excerpt", "")[:200] if alert.get("post_excerpt") else "",
                # Include source URL and platform for alerts
                "source_url": alert.get("source_url", ""),
                "platform": alert.get("platform", ""),
                "image_url": alert.get("image_url", "")
            }
            public_alerts.append(public_alert)

        return {
            "success": True,
            "data": {
                "alerts": public_alerts,
                "count": len(public_alerts)
            }
        }

    except Exception as e:
        logger.error(f"Public alerts fetch error: {e}")
        return {
            "success": False,
            "data": {"alerts": [], "count": 0}
        }


@router.get("/public/feed")
async def public_get_feed(
    limit: int = Query(default=20, ge=1, le=50),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get recent SMI feed posts for public display (citizen dashboard).
    No authentication required.
    Returns only disaster-related posts with limited data.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"posts": [], "count": 0}
        }

    try:
        # Try to auto-start feed if not running
        try:
            await smi.start_feed()
        except:
            pass

        result = await smi.get_feed_posts(limit=limit * 2)  # Get more to filter
        posts = result.get("posts", [])

        # Filter only disaster-related posts and sanitize for public
        public_posts = []
        for post in posts:
            disaster_type = post.get("analysis", {}).get("disaster_type") or post.get("disaster_type", "none")
            if disaster_type and disaster_type != "none":
                original = post.get("original_post", post)
                public_post = {
                    "alert_level": post.get("alert_level", "LOW"),
                    "disaster_type": disaster_type,
                    "text": (original.get("text", "") or post.get("text", ""))[:300],
                    "location": original.get("location", ""),
                    "platform": original.get("platform", "social"),
                    "timestamp": original.get("timestamp"),
                    "language": original.get("language", "en"),
                    "analysis": {
                        "urgency": post.get("analysis", {}).get("urgency", "low"),
                        "relevance_score": post.get("analysis", {}).get("relevance_score", 0)
                    },
                    # Include author and source URL from scraped data
                    "author": original.get("author", ""),
                    "source_url": original.get("url", ""),
                    "image_urls": original.get("image_urls", []),
                    "engagement": original.get("engagement", {})
                }
                public_posts.append(public_post)

                if len(public_posts) >= limit:
                    break

        return {
            "success": True,
            "data": {
                "posts": public_posts,
                "count": len(public_posts)
            }
        }

    except Exception as e:
        logger.error(f"Public feed fetch error: {e}")
        return {
            "success": False,
            "data": {"posts": [], "count": 0}
        }


@router.get("/public/stats")
async def public_get_stats(
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get basic SMI statistics for public display.
    No authentication required.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"statistics": {}}
        }

    try:
        result = await smi.get_disaster_stats()
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Public stats fetch error: {e}")
        return {
            "success": False,
            "data": {"statistics": {}}
        }


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FeedConfigRequest(BaseModel):
    """Feed configuration request."""
    post_interval: int = Field(default=8, ge=3, le=30, description="Seconds between posts")
    disaster_probability: float = Field(default=0.3, ge=0.0, le=1.0, description="Probability of disaster posts")


class AnalyzePostRequest(BaseModel):
    """Request to analyze a single post."""
    text: str = Field(..., min_length=1, max_length=2000, description="Post content")
    platform: str = Field(default="twitter", description="Source platform")
    language: str = Field(default="english", description="Post language")
    location: Optional[str] = Field(default=None, description="Location")
    user: Optional[dict] = Field(default=None, description="User info")


class BatchAnalyzeRequest(BaseModel):
    """Request to analyze multiple posts."""
    posts: List[dict] = Field(..., description="List of posts to analyze")
    filter_threshold: float = Field(default=3.0, ge=0, le=10, description="Minimum relevance score")


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@router.get("/health")
async def get_smi_health(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Check SMI module health status.

    Returns connection status and system information.
    """
    try:
        health = await smi.check_health()

        return {
            "success": True,
            "data": health,
            "enabled": settings.SMI_ENABLED
        }

    except Exception as e:
        logger.error(f"SMI health check failed: {e}")
        return {
            "success": False,
            "data": {
                "smi_status": "offline",
                "is_connected": False,
                "error": str(e)
            },
            "enabled": settings.SMI_ENABLED
        }


@router.get("/system/info")
async def get_system_info(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get SMI system information.

    Returns supported languages, locations, and version info.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        info = await smi.get_system_info()

        return {
            "success": True,
            "data": info
        }

    except Exception as e:
        logger.error(f"Failed to get SMI system info: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module unavailable"
        )


# =============================================================================
# DASHBOARD ENDPOINT
# =============================================================================

@router.get("/dashboard")
async def get_smi_dashboard(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get comprehensive SMI dashboard data.

    Returns:
    - System status
    - Statistics (total posts, disasters, alerts)
    - Recent posts
    - Active alerts
    - Disaster and platform breakdowns
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "error": "SMI module is disabled",
            "data": {
                "system": {"is_connected": False, "status": "disabled"},
                "stats": {},
                "posts": [],
                "alerts": []
            }
        }

    try:
        data = await smi.get_dashboard_data()

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        logger.error(f"Failed to get SMI dashboard: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "system": {"is_connected": False, "status": "error"},
                "stats": {},
                "posts": [],
                "alerts": []
            }
        }


# =============================================================================
# FEED MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/feed/start")
async def start_feed(
    config: Optional[FeedConfigRequest] = None,
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Start the SMI enhanced feed.

    Analysts can start the feed with default or custom configuration.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        feed_config = None
        if config:
            feed_config = {
                "post_interval": config.post_interval,
                "disaster_probability": config.disaster_probability
            }

        result = await smi.start_feed(feed_config)

        logger.info(f"SMI feed started by user {current_user.user_id}")

        return {
            "success": True,
            "message": "Feed started successfully",
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to start SMI feed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start feed"
        )


@router.post("/feed/stop")
async def stop_feed(
    current_user: User = Depends(require_admin),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Stop the SMI feed.

    Requires Authority Admin role.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        result = await smi.stop_feed()

        logger.info(f"SMI feed stopped by admin {current_user.user_id}")

        return {
            "success": True,
            "message": "Feed stopped successfully",
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to stop SMI feed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop feed"
        )


@router.get("/feed/status")
async def get_feed_status(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get current feed status.

    Returns feed running state and configuration.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"is_running": False, "status": "disabled"}
        }

    try:
        status_data = await smi.get_feed_status()

        return {
            "success": True,
            "data": status_data
        }

    except Exception as e:
        logger.error(f"Failed to get feed status: {e}")
        return {
            "success": False,
            "data": {"is_running": False, "error": str(e)}
        }


@router.post("/feed/configure")
async def configure_feed(
    config: FeedConfigRequest,
    current_user: User = Depends(require_admin),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Update feed configuration.

    Requires Authority Admin role.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        result = await smi.configure_feed({
            "post_interval": config.post_interval,
            "disaster_probability": config.disaster_probability
        })

        logger.info(f"SMI feed configured by admin {current_user.user_id}: {config.dict()}")

        return {
            "success": True,
            "message": "Feed configuration updated",
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to configure feed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure feed"
        )


@router.get("/feed/posts")
async def get_feed_posts(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum posts to return"),
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get posts from the enhanced feed.

    Returns analyzed social media posts with disaster detection results.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"posts": [], "total": 0}
        }

    try:
        result = await smi.get_feed_posts(limit=limit)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get feed posts: {e}")
        return {
            "success": False,
            "data": {"posts": [], "total": 0, "error": str(e)}
        }


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/analyze")
async def analyze_post(
    request: AnalyzePostRequest,
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Analyze a single social media post.

    Performs disaster detection, misinformation check, and sentiment analysis.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        post_data = {
            "text": request.text,
            "platform": request.platform,
            "language": request.language,
            "location": request.location,
            "user": request.user
        }

        result = await smi.analyze_post(post_data)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to analyze post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze post"
        )


@router.post("/analyze/batch")
async def batch_analyze_posts(
    request: BatchAnalyzeRequest,
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Analyze multiple posts in batch.

    Filters results by relevance threshold.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        result = await smi.batch_analyze(request.posts, request.filter_threshold)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to batch analyze: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch analyze posts"
        )


@router.post("/analyze/misinformation")
async def check_misinformation(
    request: AnalyzePostRequest,
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Check a post for misinformation.

    Performs detailed misinformation analysis including:
    - Suspicious language detection
    - Credibility assessment
    - Fact-check warnings
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        result = await smi.check_misinformation({
            "text": request.text,
            "platform": request.platform,
            "language": request.language
        })

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to check misinformation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check misinformation"
        )


# =============================================================================
# ALERTS ENDPOINTS
# =============================================================================

@router.get("/alerts/active")
async def get_active_alerts(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get currently active SMI alerts.

    Returns alerts that are currently being tracked.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"alerts": [], "count": 0}
        }

    try:
        result = await smi.get_active_alerts()

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        return {
            "success": False,
            "data": {"alerts": [], "count": 0, "error": str(e)}
        }


@router.get("/alerts/critical")
async def get_critical_alerts(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get only critical and high priority alerts.

    These are alerts that require immediate attention.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"alerts": [], "count": 0}
        }

    try:
        alerts = await smi.get_critical_alerts()

        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "count": len(alerts),
                "threshold": settings.SMI_CRITICAL_ALERT_THRESHOLD
            }
        }

    except Exception as e:
        logger.error(f"Failed to get critical alerts: {e}")
        return {
            "success": False,
            "data": {"alerts": [], "count": 0, "error": str(e)}
        }


@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum alerts to return"),
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get recent alerts from database.

    Returns historical alert data.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"alerts": [], "count": 0}
        }

    try:
        result = await smi.get_recent_alerts(limit=limit)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get recent alerts: {e}")
        return {
            "success": False,
            "data": {"alerts": [], "count": 0, "error": str(e)}
        }


@router.post("/alerts/sync")
async def sync_alerts_to_notifications(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Manually sync SMI alerts to notification system.

    Requires Authority Admin role.
    Creates notifications for critical alerts.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        result = await smi.sync_alerts_to_notifications()

        return {
            "success": True,
            "message": "Alert sync completed",
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to sync alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync alerts"
        )


# =============================================================================
# POSTS & DATA ENDPOINTS
# =============================================================================

@router.get("/posts/recent")
async def get_recent_posts(
    limit: int = Query(default=50, ge=1, le=200),
    disaster_type: Optional[str] = Query(default=None, description="Filter by disaster type"),
    urgency: Optional[str] = Query(default=None, description="Filter by urgency level"),
    min_relevance: Optional[float] = Query(default=None, ge=0, le=10),
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get recent analyzed posts with optional filters.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"posts": [], "total": 0}
        }

    try:
        result = await smi.get_recent_posts(
            limit=limit,
            disaster_type=disaster_type,
            urgency=urgency,
            min_relevance=min_relevance
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get recent posts: {e}")
        return {
            "success": False,
            "data": {"posts": [], "total": 0, "error": str(e)}
        }


@router.get("/posts/search")
async def search_posts(
    query: Optional[str] = Query(default=None, description="Search query"),
    disaster_type: Optional[str] = Query(default=None),
    language: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Search posts with various filters.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"posts": [], "total": 0}
        }

    try:
        result = await smi.search_posts(
            query=query,
            disaster_type=disaster_type,
            language=language,
            platform=platform,
            limit=limit
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to search posts: {e}")
        return {
            "success": False,
            "data": {"posts": [], "total": 0, "error": str(e)}
        }


# =============================================================================
# STATISTICS ENDPOINTS
# =============================================================================

@router.get("/statistics/disaster")
async def get_disaster_statistics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get disaster type statistics.

    Returns breakdown of detected disasters by type.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"statistics": {}}
        }

    try:
        result = await smi.get_disaster_stats(days=days)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get disaster stats: {e}")
        return {
            "success": False,
            "data": {"statistics": {}, "error": str(e)}
        }


@router.get("/statistics/platform")
async def get_platform_statistics(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get platform breakdown statistics.

    Returns post counts by platform.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": False,
            "data": {"statistics": {}}
        }

    try:
        result = await smi.get_platform_stats()

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get platform stats: {e}")
        return {
            "success": False,
            "data": {"statistics": {}, "error": str(e)}
        }


@router.get("/languages")
async def get_supported_languages(
    current_user: User = Depends(require_analyst),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Get list of supported languages.
    """
    if not settings.SMI_ENABLED:
        return {
            "success": True,
            "data": {
                "languages": [
                    {"code": "en", "name": "English"},
                    {"code": "hi", "name": "Hindi"},
                    {"code": "ta", "name": "Tamil"},
                    {"code": "te", "name": "Telugu"},
                    {"code": "kn", "name": "Kannada"},
                    {"code": "ml", "name": "Malayalam"},
                    {"code": "bn", "name": "Bengali"},
                    {"code": "gu", "name": "Gujarati"},
                    {"code": "mr", "name": "Marathi"}
                ],
                "total": 9
            }
        }

    try:
        result = await smi.get_language_stats()

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to get languages: {e}")
        return {
            "success": False,
            "data": {"languages": [], "error": str(e)}
        }


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/database/cleanup")
async def cleanup_database(
    current_user: User = Depends(require_admin),
    smi: SMIService = Depends(get_smi_with_db)
):
    """
    Clean up SMI database.

    Requires Authority Admin role.
    Removes all stored SMI data.
    """
    if not settings.SMI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMI module is disabled"
        )

    try:
        result = await smi.cleanup_database()

        logger.warning(f"SMI database cleanup initiated by admin {current_user.user_id}")

        return {
            "success": True,
            "message": "Database cleanup completed",
            "data": result
        }

    except Exception as e:
        logger.error(f"Failed to cleanup database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup database"
        )


# =============================================================================
# CONFIGURATION ENDPOINT
# =============================================================================

@router.get("/config")
async def get_smi_config(
    current_user: User = Depends(require_analyst)
):
    """
    Get SMI module configuration.

    Returns public configuration settings.
    """
    demo = get_demo_service()

    return {
        "success": True,
        "data": {
            "enabled": settings.SMI_ENABLED,
            "base_url": settings.SMI_BASE_URL if current_user.role == UserRole.AUTHORITY_ADMIN else None,
            "alert_threshold": settings.SMI_CRITICAL_ALERT_THRESHOLD,
            "auto_start_feed": settings.SMI_AUTO_START_FEED,
            "default_post_interval": settings.SMI_DEFAULT_POST_INTERVAL,
            "default_disaster_probability": settings.SMI_DEFAULT_DISASTER_PROBABILITY,
            "alert_sync_interval": settings.SMI_ALERT_SYNC_INTERVAL_SECONDS,
            "demo_mode_available": demo.is_available
        }
    }


# =============================================================================
# DEMO MODE ENDPOINTS (LLM Simulation)
# =============================================================================

class DemoConfigRequest(BaseModel):
    """Demo mode configuration request."""
    post_interval: int = Field(default=8, ge=3, le=30, description="Seconds between posts")
    disaster_probability: float = Field(default=0.3, ge=0.0, le=1.0, description="Probability of disaster posts")


@router.get("/demo/status")
async def get_demo_status(
    current_user: User = Depends(require_analyst)
):
    """
    Get demo mode status.

    Returns whether demo simulation is running and its configuration.
    """
    demo = get_demo_service()
    status_data = await demo.get_status()

    return {
        "success": True,
        "data": status_data
    }


@router.post("/demo/start")
async def start_demo_mode(
    config: Optional[DemoConfigRequest] = None,
    current_user: User = Depends(require_analyst)
):
    """
    Start demo simulation mode.

    Generates synthetic social media posts with disaster scenarios
    using LLM-based simulation. Useful for demos and testing.
    """
    demo = get_demo_service()

    if not demo.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo mode is not available"
        )

    config_dict = None
    if config:
        config_dict = {
            "post_interval": config.post_interval,
            "disaster_probability": config.disaster_probability
        }

    result = await demo.start(config_dict)
    logger.info(f"Demo mode started by user {current_user.user_id}")

    return {
        "success": True,
        "message": "Demo simulation started",
        "data": result
    }


@router.post("/demo/stop")
async def stop_demo_mode(
    current_user: User = Depends(require_analyst)
):
    """
    Stop demo simulation mode.
    """
    demo = get_demo_service()

    result = await demo.stop()
    logger.info(f"Demo mode stopped by user {current_user.user_id}")

    return {
        "success": True,
        "message": "Demo simulation stopped",
        "data": result
    }


@router.post("/demo/configure")
async def configure_demo_mode(
    config: DemoConfigRequest,
    current_user: User = Depends(require_analyst)
):
    """
    Update demo mode configuration.
    """
    demo = get_demo_service()

    if not demo.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo mode is not available"
        )

    result = await demo.update_config({
        "post_interval": config.post_interval,
        "disaster_probability": config.disaster_probability
    })

    return {
        "success": True,
        "message": "Demo configuration updated",
        "data": result
    }


@router.get("/demo/posts")
async def get_demo_posts(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_analyst)
):
    """
    Get posts from demo simulation.
    """
    demo = get_demo_service()
    result = await demo.get_posts(limit)

    return {
        "success": True,
        "data": result
    }


@router.get("/demo/alerts")
async def get_demo_alerts(
    current_user: User = Depends(require_analyst)
):
    """
    Get alerts from demo simulation.
    """
    demo = get_demo_service()
    result = await demo.get_alerts()

    return {
        "success": True,
        "data": result
    }


# =============================================================================
# PUBLIC DEMO ENDPOINTS (For citizen dashboard demo)
# =============================================================================

@router.get("/public/demo/status")
async def public_demo_status():
    """
    Public endpoint for demo mode status.
    No authentication required.
    """
    demo = get_demo_service()
    status_data = await demo.get_status()

    return {
        "success": True,
        "data": {
            "is_running": status_data.get("is_running", False),
            "available": status_data.get("available", False),
            "mode": "demo"
        }
    }


@router.get("/public/demo/feed")
async def public_demo_feed(
    limit: int = Query(default=20, ge=1, le=50)
):
    """
    Get demo feed posts for public display.
    No authentication required.
    """
    demo = get_demo_service()
    result = await demo.get_posts(limit)
    posts = result.get("posts", [])

    # Filter for disaster-related posts only
    public_posts = []
    for post in posts:
        disaster_type = post.get("disaster_type", "none")
        if disaster_type and disaster_type != "none":
            # Get the original_post which contains user info with username
            original = post.get("original_post", {})
            public_posts.append({
                "alert_level": post.get("alert_level", "LOW"),
                "disaster_type": disaster_type,
                "text": post.get("text", "")[:300],
                "location": post.get("location", ""),
                "platform": post.get("platform", "demo"),
                "timestamp": post.get("timestamp"),
                "language": post.get("language", "english"),
                "source": "demo_simulation",
                # Include original_post with user info for username display
                "original_post": original,
                # Include analysis object for frontend consistency
                "analysis": post.get("analysis", {})
            })

    return {
        "success": True,
        "data": {
            "posts": public_posts[:limit],
            "count": len(public_posts),
            "mode": "demo"
        }
    }


@router.get("/public/demo/alerts")
async def public_demo_alerts(
    limit: int = Query(default=20, ge=1, le=50)
):
    """
    Get demo alerts for public display.
    No authentication required.
    """
    demo = get_demo_service()
    result = await demo.get_alerts()
    alerts = result.get("alerts", [])

    # Sanitize for public display
    public_alerts = []
    for alert in alerts[:limit]:
        public_alerts.append({
            "alert_level": alert.get("alert_level", "LOW"),
            "disaster_type": alert.get("disaster_type", "unknown"),
            "location": alert.get("location", ""),
            "relevance_score": alert.get("relevance_score", 0),
            "timestamp": alert.get("timestamp"),
            "post_excerpt": alert.get("post_excerpt", "")[:200],
            "source": "demo_simulation"
        })

    return {
        "success": True,
        "data": {
            "alerts": public_alerts,
            "count": len(public_alerts),
            "mode": "demo"
        }
    }


@router.post("/public/demo/start")
async def public_start_demo(
    config: Optional[DemoConfigRequest] = None
):
    """
    Start demo simulation mode - public endpoint.
    No authentication required (demo is for demonstration purposes).
    """
    demo = get_demo_service()

    if not demo.is_available:
        return {
            "success": False,
            "message": "Demo mode is not available - old SMI module not found",
            "data": {"is_running": False}
        }

    config_dict = None
    if config:
        config_dict = {
            "post_interval": config.post_interval,
            "disaster_probability": config.disaster_probability
        }

    result = await demo.start(config_dict)
    logger.info("Demo mode started via public endpoint")

    return {
        "success": True,
        "message": "Demo simulation started",
        "data": result
    }


@router.post("/public/demo/stop")
async def public_stop_demo():
    """
    Stop demo simulation mode - public endpoint.
    No authentication required.
    """
    demo = get_demo_service()
    result = await demo.stop()
    logger.info("Demo mode stopped via public endpoint")

    return {
        "success": True,
        "message": "Demo simulation stopped",
        "data": result
    }


@router.post("/public/demo/configure")
async def public_configure_demo(
    config: DemoConfigRequest
):
    """
    Update demo mode configuration - public endpoint.
    No authentication required.
    """
    demo = get_demo_service()

    if not demo.is_available:
        return {
            "success": False,
            "message": "Demo mode is not available",
            "data": {}
        }

    result = await demo.update_config({
        "post_interval": config.post_interval,
        "disaster_probability": config.disaster_probability
    })

    return {
        "success": True,
        "message": "Demo configuration updated",
        "data": result
    }
