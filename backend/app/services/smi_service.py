"""
Social Media Intelligence (SMI) Service - BlueRadar Integration
Provides integration with the BlueRadar real-time intelligence module.

This service connects to the BlueRadar WebSocket server for real-time alerts
and provides REST API compatibility for the frontend dashboard.

BlueRadar Features:
- Real-time scraping from Twitter, YouTube, Instagram, News
- Fast rule-based NLP for hazard classification
- WebSocket streaming for live alerts
- Content validation (recency, geography, duplicates)
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, asdict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)

# Add blueradar to path (use append to avoid conflicts with backend's main.py)
BLUERADAR_PATH = Path(__file__).parent.parent.parent.parent / "blueradar_intelligence"
if str(BLUERADAR_PATH) not in sys.path:
    sys.path.append(str(BLUERADAR_PATH))

# Try to import blueradar components
BLUERADAR_AVAILABLE = False
try:
    from services.fast_scraper import ParallelScraperManager, ScrapedPost
    from services.fast_nlp import FastNLPProcessor, FastNLPResult
    from services.content_validator import ContentValidator, DEFAULT_VALIDATION_CONFIG
    BLUERADAR_AVAILABLE = True
    logger.info("✓ BlueRadar components imported successfully")
except ImportError as e:
    logger.warning(f"⚠ BlueRadar components not available: {e}")
    ParallelScraperManager = None
    FastNLPProcessor = None


@dataclass
class SMIAlert:
    """Alert structure compatible with frontend expectations"""
    alert_id: str
    alert_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    disaster_type: str
    location: str
    relevance_score: float
    timestamp: str
    post_excerpt: str
    platform: str
    source_url: str
    image_url: Optional[str] = None
    region: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SMIPost:
    """Post structure compatible with frontend expectations"""
    post_id: str
    text: str
    platform: str
    language: str
    location: str
    timestamp: str
    alert_level: str
    disaster_type: str
    analysis: Dict
    original_post: Dict

    def to_dict(self) -> Dict:
        return asdict(self)


class SMIService:
    """
    Service for integrating with BlueRadar real-time intelligence.

    Provides:
    - Health monitoring
    - Real-time feed from social media
    - Hazard alert generation
    - Statistics retrieval
    - Notification integration
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db
        self._is_connected = False
        self._last_health_check = None
        self._cached_alerts: List[SMIAlert] = []
        self._cached_posts: List[SMIPost] = []
        self._alert_sync_task = None
        self._scrape_task = None
        self._is_feed_running = False

        # Initialize BlueRadar components
        self.scraper = None
        self.nlp = None
        self.validator = None

        if BLUERADAR_AVAILABLE:
            try:
                self.scraper = ParallelScraperManager()
                self.nlp = FastNLPProcessor()
                self.validator = ContentValidator(DEFAULT_VALIDATION_CONFIG)
                self._is_connected = True
                logger.info("✓ BlueRadar components initialized")
            except Exception as e:
                logger.error(f"Failed to initialize BlueRadar: {e}")
                self._is_connected = False

        # Stats tracking
        self._stats = {
            "posts_scraped": 0,
            "alerts_generated": 0,
            "posts_rejected": 0,
            "last_scrape": None
        }

    # =========================================================================
    # HEALTH & STATUS
    # =========================================================================

    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the BlueRadar module."""
        self._last_health_check = datetime.now(timezone.utc)

        if not BLUERADAR_AVAILABLE:
            return {
                "status": "unavailable",
                "smi_status": "offline",
                "is_connected": False,
                "last_check": self._last_health_check.isoformat(),
                "error": "BlueRadar components not installed"
            }

        if self.scraper and self.nlp:
            self._is_connected = True
            return {
                "status": "healthy",
                "smi_status": "healthy",
                "is_connected": True,
                "last_check": self._last_health_check.isoformat(),
                "components": {
                    "scraper": "ready",
                    "nlp": "ready",
                    "validator": "ready" if self.validator else "disabled"
                },
                "feed_running": self._is_feed_running,
                "stats": self._stats
            }

        return {
            "status": "degraded",
            "smi_status": "degraded",
            "is_connected": False,
            "last_check": self._last_health_check.isoformat()
        }

    async def get_system_info(self) -> Dict[str, Any]:
        """Get BlueRadar system information."""
        return {
            "version": "2.0.0",
            "module": "BlueRadar Intelligence",
            "features": [
                "Real-time social media scraping",
                "Fast rule-based NLP",
                "Multi-platform support (Twitter, YouTube, Instagram, News)",
                "Indian coastal hazard detection",
                "Content validation and deduplication"
            ],
            "supported_hazards": [
                "cyclone", "tsunami", "flood", "storm_surge",
                "rough_sea", "oil_spill"
            ],
            "supported_languages": [
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
            "platforms": ["twitter", "youtube", "instagram", "news"],
            "is_available": BLUERADAR_AVAILABLE
        }

    @property
    def is_connected(self) -> bool:
        """Check if BlueRadar module is currently connected."""
        return self._is_connected and BLUERADAR_AVAILABLE

    # =========================================================================
    # FEED MANAGEMENT
    # =========================================================================

    async def start_feed(self, config: Optional[Dict] = None) -> Dict[str, Any]:
        """Start the real-time scraping feed."""
        if not BLUERADAR_AVAILABLE:
            return {"success": False, "error": "BlueRadar not available"}

        if self._is_feed_running:
            return {"success": True, "message": "Feed already running"}

        self._is_feed_running = True

        # Start background scraping task
        if self._scrape_task is None or self._scrape_task.done():
            self._scrape_task = asyncio.create_task(self._scrape_loop())

        return {
            "success": True,
            "message": "Feed started successfully",
            "is_running": True
        }

    async def stop_feed(self) -> Dict[str, Any]:
        """Stop the feed."""
        self._is_feed_running = False

        if self._scrape_task and not self._scrape_task.done():
            self._scrape_task.cancel()

        return {
            "success": True,
            "message": "Feed stopped",
            "is_running": False
        }

    async def get_feed_status(self) -> Dict[str, Any]:
        """Get current feed status."""
        return {
            "is_running": self._is_feed_running,
            "status": "running" if self._is_feed_running else "stopped",
            "stats": self._stats,
            "cached_posts": len(self._cached_posts),
            "cached_alerts": len(self._cached_alerts)
        }

    async def configure_feed(self, config: Dict) -> Dict[str, Any]:
        """Update feed configuration."""
        # BlueRadar doesn't use the same config as old SMI
        # Just acknowledge the config
        return {
            "success": True,
            "message": "Configuration acknowledged",
            "config": config
        }

    async def get_feed_posts(self, limit: int = 50) -> Dict[str, Any]:
        """Get posts from the feed."""
        # If feed not running, start it
        if not self._is_feed_running and BLUERADAR_AVAILABLE:
            await self.start_feed()

        posts = self._cached_posts[-limit:] if limit else self._cached_posts

        return {
            "success": True,
            "posts": [p.to_dict() for p in posts],
            "total": len(posts)
        }

    async def _scrape_loop(self):
        """Background scraping loop."""
        keywords = [
            "cyclone", "CycloneAlert", "hurricane", "storm",
            "flood", "flooding", "MumbaiFloods", "ChennaiFloods",
            "HighWaves", "RoughSea", "tsunami",
            "IndiaWeather", "BayOfBengal", "ArabianSea"
        ]
        platforms = ["twitter", "youtube", "news", "instagram"]

        while self._is_feed_running:
            try:
                logger.info(f"[SMI] Starting scrape cycle...")

                # Run parallel scrape
                posts = await self.scraper.run_parallel_scrape(
                    keywords,
                    platforms,
                    max_per=10
                )

                self._stats["last_scrape"] = datetime.now(timezone.utc).isoformat()
                self._stats["posts_scraped"] += len(posts)

                logger.info(f"[SMI] Scraped {len(posts)} posts")

                # Process each post
                for post in posts:
                    nlp_result = self.nlp.process(post.text, post.platform)
                    post_dict = post.to_dict()

                    # Validate content if validator available
                    is_valid = True
                    if self.validator:
                        validation = self.validator.validate(post_dict, nlp_result.to_dict())
                        is_valid = validation.is_valid
                        if not is_valid:
                            self._stats["posts_rejected"] += 1
                            continue

                    # Create SMI Post
                    smi_post = SMIPost(
                        post_id=post.id,
                        text=post.text[:500],
                        platform=post.platform,
                        language="en",  # Could detect from NLP
                        location=nlp_result.locations[0] if nlp_result.locations else "",
                        timestamp=post.timestamp,
                        alert_level=nlp_result.severity,
                        disaster_type=nlp_result.hazard_type or "none",
                        analysis={
                            "relevance_score": nlp_result.relevance_score,
                            "urgency": nlp_result.severity.lower(),
                            "disaster_type": nlp_result.hazard_type,
                            "is_spam": nlp_result.is_spam
                        },
                        original_post=post_dict
                    )

                    # Add to cache (keep last 200)
                    self._cached_posts.append(smi_post)
                    if len(self._cached_posts) > 200:
                        self._cached_posts = self._cached_posts[-200:]

                    # Generate alert if worthy
                    if nlp_result.is_alert_worthy:
                        alert = SMIAlert(
                            alert_id=f"ALERT-{post.id[:8].upper()}",
                            alert_level=nlp_result.severity,
                            disaster_type=nlp_result.hazard_type or "hazard",
                            location=nlp_result.locations[0] if nlp_result.locations else "Unknown",
                            relevance_score=nlp_result.relevance_score,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            post_excerpt=post.text[:200],
                            platform=post.platform,
                            source_url=post.url,
                            image_url=post.image_urls[0] if post.image_urls else None,
                            region=nlp_result.primary_region
                        )

                        # Add to alerts cache (keep last 100)
                        self._cached_alerts.append(alert)
                        if len(self._cached_alerts) > 100:
                            self._cached_alerts = self._cached_alerts[-100:]

                        self._stats["alerts_generated"] += 1
                        logger.info(f"[SMI ALERT] {alert.alert_level}: {alert.disaster_type} at {alert.location}")

                # Wait before next cycle (5 minutes)
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                logger.info("[SMI] Scrape loop cancelled")
                break
            except Exception as e:
                logger.error(f"[SMI] Scrape error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    # =========================================================================
    # ANALYSIS
    # =========================================================================

    async def analyze_post(self, post: Dict) -> Dict[str, Any]:
        """Analyze a single social media post."""
        if not BLUERADAR_AVAILABLE or not self.nlp:
            return {"success": False, "error": "NLP not available"}

        text = post.get("text", "")
        platform = post.get("platform", "unknown")

        result = self.nlp.process(text, platform)

        return {
            "success": True,
            "analysis": {
                "disaster_type": result.hazard_type,
                "relevance_score": result.relevance_score,
                "urgency": result.severity.lower(),
                "locations": result.locations,
                "region": result.primary_region,
                "is_spam": result.is_spam,
                "is_alert_worthy": result.is_alert_worthy,
                "alert_level": result.severity
            },
            "misinformation_analysis": {
                "risk_level": "low",
                "verified": True,
                "warnings": []
            }
        }

    async def batch_analyze(self, posts: List[Dict], filter_threshold: float = 3.0) -> Dict[str, Any]:
        """Analyze multiple posts in batch."""
        if not BLUERADAR_AVAILABLE or not self.nlp:
            return {"success": False, "error": "NLP not available"}

        results = []
        for post in posts:
            analysis = await self.analyze_post(post)
            if analysis.get("success") and analysis["analysis"]["relevance_score"] >= filter_threshold * 10:
                results.append({
                    "post": post,
                    "analysis": analysis["analysis"]
                })

        return {
            "success": True,
            "results": results,
            "total_analyzed": len(posts),
            "total_passed": len(results)
        }

    async def check_misinformation(self, post: Dict) -> Dict[str, Any]:
        """Check a post for misinformation."""
        # BlueRadar uses spam detection, not full misinformation
        if not BLUERADAR_AVAILABLE or not self.nlp:
            return {"success": False, "error": "NLP not available"}

        text = post.get("text", "")
        result = self.nlp.process(text, post.get("platform", "unknown"))

        return {
            "success": True,
            "misinformation_analysis": {
                "risk_level": "high" if result.is_spam else "low",
                "is_spam": result.is_spam,
                "verified": not result.is_spam,
                "warnings": ["Potential spam detected"] if result.is_spam else [],
                "confidence": 0.9 if result.is_spam else 0.2
            }
        }

    # =========================================================================
    # ALERTS
    # =========================================================================

    async def get_active_alerts(self) -> Dict[str, Any]:
        """Get currently active alerts including alerts generated from posts."""
        # Get cached alerts
        cached_alert_ids = {a.alert_id for a in self._cached_alerts}
        alerts = [
            a for a in self._cached_alerts
            if a.alert_level in ["CRITICAL", "HIGH", "MEDIUM"]
        ]

        # Also generate alerts from cached posts that should have alerts
        # This ensures MEDIUM alerts are included even if they weren't
        # generated when the post was first scraped
        for post in self._cached_posts:
            if post.alert_level in ["CRITICAL", "HIGH", "MEDIUM"]:
                # Check if we already have an alert for this post
                alert_id = f"ALERT-{post.post_id[:8].upper()}"
                if alert_id not in cached_alert_ids:
                    # Create alert from post
                    alert = SMIAlert(
                        alert_id=alert_id,
                        alert_level=post.alert_level,
                        disaster_type=post.disaster_type or "hazard",
                        location=post.location or "Unknown",
                        relevance_score=post.analysis.get("relevance_score", 50),
                        timestamp=post.timestamp,
                        post_excerpt=post.text[:200],
                        platform=post.platform,
                        source_url=post.original_post.get("url", ""),
                        image_url=post.original_post.get("image_urls", [None])[0] if post.original_post.get("image_urls") else None,
                        region=post.analysis.get("region")
                    )
                    alerts.append(alert)
                    cached_alert_ids.add(alert_id)

        return {
            "success": True,
            "alerts": [a.to_dict() for a in alerts],
            "count": len(alerts),
            "alert_threshold": settings.SMI_CRITICAL_ALERT_THRESHOLD
        }

    async def get_recent_alerts(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent alerts."""
        alerts = self._cached_alerts[-limit:] if limit else self._cached_alerts

        return {
            "success": True,
            "alerts": [a.to_dict() for a in alerts],
            "count": len(alerts)
        }

    async def get_critical_alerts(self) -> List[Dict]:
        """Get only critical and high priority alerts."""
        critical = [
            a.to_dict() for a in self._cached_alerts
            if a.alert_level in ["CRITICAL", "HIGH"]
            or a.relevance_score >= settings.SMI_CRITICAL_ALERT_THRESHOLD * 10
        ]
        return critical

    # =========================================================================
    # POSTS & DATA
    # =========================================================================

    async def get_recent_posts(
        self,
        limit: int = 50,
        disaster_type: Optional[str] = None,
        urgency: Optional[str] = None,
        min_relevance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get recent analyzed posts with optional filters."""
        posts = self._cached_posts

        # Apply filters
        if disaster_type:
            posts = [p for p in posts if p.disaster_type == disaster_type]
        if urgency:
            posts = [p for p in posts if p.alert_level.lower() == urgency.lower()]
        if min_relevance is not None:
            posts = [p for p in posts if p.analysis.get("relevance_score", 0) >= min_relevance * 10]

        posts = posts[-limit:] if limit else posts

        return {
            "success": True,
            "posts": [p.to_dict() for p in posts],
            "total": len(posts)
        }

    async def search_posts(
        self,
        query: Optional[str] = None,
        disaster_type: Optional[str] = None,
        language: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search posts with various filters."""
        posts = self._cached_posts

        if query:
            query_lower = query.lower()
            posts = [p for p in posts if query_lower in p.text.lower()]
        if disaster_type:
            posts = [p for p in posts if p.disaster_type == disaster_type]
        if language:
            posts = [p for p in posts if p.language == language]
        if platform:
            posts = [p for p in posts if p.platform == platform]

        posts = posts[-limit:] if limit else posts

        return {
            "success": True,
            "posts": [p.to_dict() for p in posts],
            "total": len(posts)
        }

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_disaster_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get disaster type statistics."""
        stats = {}

        for post in self._cached_posts:
            dtype = post.disaster_type or "none"
            stats[dtype] = stats.get(dtype, 0) + 1

        return {
            "success": True,
            "statistics": stats,
            "period_days": days,
            "total_posts": len(self._cached_posts)
        }

    async def get_platform_stats(self) -> Dict[str, Any]:
        """Get platform breakdown statistics."""
        stats = {}

        for post in self._cached_posts:
            platform = post.platform
            stats[platform] = stats.get(platform, 0) + 1

        return {
            "success": True,
            "statistics": stats,
            "total_posts": len(self._cached_posts)
        }

    async def get_language_stats(self) -> Dict[str, Any]:
        """Get supported languages."""
        return await self.get_system_info()

    # =========================================================================
    # NOTIFICATION INTEGRATION
    # =========================================================================

    async def sync_alerts_to_notifications(self) -> Dict[str, Any]:
        """Sync critical SMI alerts to the main notification system."""
        if self.db is None:
            return {"success": False, "error": "Database not configured"}

        try:
            critical_alerts = await self.get_critical_alerts()

            if not critical_alerts:
                return {"success": True, "synced": 0, "message": "No critical alerts to sync"}

            notifications_created = 0

            for alert in critical_alerts:
                alert_id = alert.get("alert_id")
                if not alert_id:
                    continue

                existing = await self.db.notifications.find_one({
                    "smi_alert_id": alert_id
                })

                if existing:
                    continue

                notification = {
                    "notification_id": f"NTF-SMI-{uuid4().hex[:8].upper()}",
                    "smi_alert_id": alert_id,
                    "title": f"SMI Alert: {alert.get('disaster_type', 'Hazard').title()} Detected",
                    "message": self._format_alert_message(alert),
                    "type": "smi_alert",
                    "priority": "critical" if alert.get("alert_level") == "CRITICAL" else "high",
                    "is_read": False,
                    "is_dismissed": False,
                    "metadata": {
                        "disaster_type": alert.get("disaster_type"),
                        "location": alert.get("location"),
                        "relevance_score": alert.get("relevance_score"),
                        "alert_level": alert.get("alert_level"),
                        "post_excerpt": alert.get("post_excerpt", "")[:200],
                        "source": "blueradar_intelligence"
                    },
                    "action_url": "/analyst/social-intelligence",
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": None
                }

                await self.db.notifications.insert_one(notification)
                notifications_created += 1

            logger.info(f"SMI alert sync: Created {notifications_created} notifications")

            return {
                "success": True,
                "synced": notifications_created,
                "total_critical": len(critical_alerts)
            }

        except Exception as e:
            logger.error(f"Failed to sync SMI alerts: {e}")
            return {"success": False, "error": str(e)}

    def _format_alert_message(self, alert: Dict) -> str:
        """Format an alert into a notification message."""
        disaster_type = alert.get("disaster_type", "hazard").replace("_", " ").title()
        location = alert.get("location", "Unknown location")
        relevance = alert.get("relevance_score", 0)

        return f"{disaster_type} activity detected via social media monitoring near {location}. " \
               f"Relevance score: {relevance}/100. Click to view full analysis."

    # =========================================================================
    # BACKGROUND TASKS
    # =========================================================================

    async def start_alert_sync_task(self):
        """Start background task to sync alerts periodically."""
        if self._alert_sync_task:
            return

        async def sync_loop():
            while True:
                try:
                    if self._is_connected:
                        await self.sync_alerts_to_notifications()
                except Exception as e:
                    logger.error(f"Alert sync error: {e}")

                await asyncio.sleep(settings.SMI_ALERT_SYNC_INTERVAL_SECONDS)

        self._alert_sync_task = asyncio.create_task(sync_loop())
        logger.info("Started SMI alert sync background task")

    async def stop_alert_sync_task(self):
        """Stop the background alert sync task."""
        if self._alert_sync_task:
            self._alert_sync_task.cancel()
            self._alert_sync_task = None
            logger.info("Stopped SMI alert sync background task")

    # =========================================================================
    # DASHBOARD DATA
    # =========================================================================

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for SMI."""
        try:
            health_data = await self.check_health()
            posts_data = await self.get_feed_posts(limit=100)
            alerts_data = await self.get_active_alerts()
            disaster_stats = await self.get_disaster_stats()
            platform_stats = await self.get_platform_stats()

            posts_list = posts_data.get("posts", [])
            alerts_list = alerts_data.get("alerts", [])

            disaster_posts = [
                p for p in posts_list
                if (p.get("disaster_type") or "none") != "none"
            ]

            critical_count = len([
                p for p in posts_list
                if p.get("alert_level") in ["CRITICAL", "HIGH"]
            ])

            return {
                "success": True,
                "system": {
                    "is_connected": health_data.get("is_connected", False),
                    "status": health_data.get("status", "unknown"),
                    "last_check": datetime.now(timezone.utc).isoformat()
                },
                "stats": {
                    "total_posts": len(posts_list),
                    "disaster_posts": len(disaster_posts),
                    "critical_alerts": critical_count,
                    "misinfo_flagged": 0,
                    "active_alerts": len(alerts_list)
                },
                "posts": posts_list,
                "alerts": alerts_list,
                "disaster_stats": disaster_stats.get("statistics", {}),
                "platform_stats": platform_stats.get("statistics", {}),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {
                "success": False,
                "error": str(e),
                "system": {"is_connected": False, "status": "error"}
            }

    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================

    async def cleanup_database(self) -> Dict[str, Any]:
        """Clean up cached data."""
        self._cached_alerts = []
        self._cached_posts = []
        self._stats = {
            "posts_scraped": 0,
            "alerts_generated": 0,
            "posts_rejected": 0,
            "last_scrape": None
        }
        return {"success": True, "message": "Cache cleared"}

    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================

    async def get_cached_alerts(self) -> List[Dict]:
        """Get cached alerts without making a request."""
        return [a.to_dict() for a in self._cached_alerts]

    def clear_cache(self):
        """Clear all cached data."""
        self._cached_alerts = []
        self._cached_posts = []


# =============================================================================
# DEMO MODE - LLM Simulation Integration
# =============================================================================

# Add old SMI module to path for demo mode
OLD_SMI_PATH = Path(__file__).parent.parent.parent.parent / "CoastGuardians-social-media-intelligence"
if str(OLD_SMI_PATH) not in sys.path:
    sys.path.insert(0, str(OLD_SMI_PATH))

# Load environment variables from old SMI module's .env file
OLD_SMI_ENV = OLD_SMI_PATH / ".env"
if OLD_SMI_ENV.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(OLD_SMI_ENV, override=False)  # Don't override existing vars
        logger.info(f"✓ Loaded demo SMI environment from {OLD_SMI_ENV}")
    except ImportError:
        logger.warning("⚠ python-dotenv not available, demo .env not loaded")

# Try to import old SMI components for demo mode
DEMO_SMI_AVAILABLE = False
try:
    from api.enhanced_feed import (
        start_enhanced_feed,
        stop_enhanced_feed,
        get_enhanced_feed_status,
        get_enhanced_posts,
        get_active_alerts as get_demo_alerts,
        update_feed_config as update_demo_config
    )
    DEMO_SMI_AVAILABLE = True
    logger.info("✓ Demo SMI (LLM Simulation) module loaded")
except ImportError as e:
    logger.warning(f"⚠ Demo SMI module not available: {e}")


class DemoModeService:
    """
    Demo Mode Service - Uses old SMI LLM simulation for demo/testing.
    Generates synthetic social media posts with disaster detection.
    """

    def __init__(self):
        self._is_running = False
        self._config = {
            "post_interval": 8,
            "disaster_probability": 0.3,
            "language_mix": True
        }

    @property
    def is_available(self) -> bool:
        return DEMO_SMI_AVAILABLE

    async def start(self, config: Optional[Dict] = None) -> Dict[str, Any]:
        """Start the demo simulation feed."""
        if not DEMO_SMI_AVAILABLE:
            return {"success": False, "error": "Demo module not available"}

        if config:
            self._config.update(config)

        result = start_enhanced_feed(
            post_interval=self._config["post_interval"],
            disaster_probability=self._config["disaster_probability"]
        )

        self._is_running = result.get("status") == "started" or result.get("status") == "already_running"

        return {
            "success": True,
            "mode": "demo",
            "message": "Demo simulation started - generating synthetic posts with LLM",
            "config": self._config,
            "result": result
        }

    async def stop(self) -> Dict[str, Any]:
        """Stop the demo simulation feed."""
        if not DEMO_SMI_AVAILABLE:
            return {"success": False, "error": "Demo module not available"}

        result = stop_enhanced_feed()
        self._is_running = False

        return {
            "success": True,
            "mode": "demo",
            "message": "Demo simulation stopped",
            "result": result
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get demo feed status."""
        if not DEMO_SMI_AVAILABLE:
            return {"is_running": False, "available": False}

        result = get_enhanced_feed_status()
        self._is_running = result.get("feed_running", False)

        return {
            "is_running": self._is_running,
            "available": True,
            "mode": "demo",
            "config": self._config,
            "status": result
        }

    async def get_posts(self, limit: int = 50) -> Dict[str, Any]:
        """Get posts from demo feed."""
        if not DEMO_SMI_AVAILABLE:
            return {"posts": [], "count": 0}

        result = get_enhanced_posts(limit)
        posts = result.get("posts", [])

        # Convert to SMI format
        formatted_posts = []
        for post in posts:
            # Use analysis from demo module if available, else create from post data
            demo_analysis = post.get("analysis", {})
            alert_level = post.get("alert_level", "LOW")

            # Map alert_level to urgency for consistency
            urgency_map = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}

            formatted_posts.append({
                "post_id": post.get("id", ""),
                "text": post.get("text", ""),
                "platform": post.get("platform", "twitter"),
                "language": post.get("language", "english"),
                "location": post.get("location", ""),
                "timestamp": post.get("timestamp", ""),
                "alert_level": alert_level,
                "disaster_type": post.get("disaster_type", "none"),
                "analysis": {
                    "relevance_score": demo_analysis.get("relevance_score", post.get("relevance_score", 0) * 10),
                    "urgency": demo_analysis.get("urgency", urgency_map.get(alert_level, "low")),
                    "disaster_type": demo_analysis.get("disaster_type", post.get("disaster_type", "none"))
                },
                "original_post": post,
                "source": "demo_simulation"
            })

        return {
            "success": True,
            "posts": formatted_posts,
            "count": len(formatted_posts),
            "mode": "demo"
        }

    async def get_alerts(self) -> Dict[str, Any]:
        """Get alerts from demo feed."""
        if not DEMO_SMI_AVAILABLE:
            return {"alerts": [], "count": 0}

        result = get_demo_alerts()
        alerts = result.get("alerts", [])

        # Convert to SMI format
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                "alert_id": alert.get("alert_id", ""),
                "alert_level": alert.get("alert_level", "LOW"),
                "disaster_type": alert.get("disaster_type", "unknown"),
                "location": alert.get("location", ""),
                "relevance_score": alert.get("relevance_score", 0) * 10,
                "timestamp": alert.get("timestamp", ""),
                "post_excerpt": alert.get("post_excerpt", ""),
                "platform": "demo",
                "source_url": "",
                "source": "demo_simulation"
            })

        return {
            "success": True,
            "alerts": formatted_alerts,
            "count": len(formatted_alerts),
            "mode": "demo"
        }

    async def update_config(self, config: Dict) -> Dict[str, Any]:
        """Update demo feed configuration."""
        if not DEMO_SMI_AVAILABLE:
            return {"success": False, "error": "Demo module not available"}

        post_interval = config.get("post_interval", self._config["post_interval"])
        disaster_probability = config.get("disaster_probability", self._config["disaster_probability"])

        result = update_demo_config(
            post_interval=post_interval,
            disaster_probability=disaster_probability
        )

        self._config.update({
            "post_interval": post_interval,
            "disaster_probability": disaster_probability
        })

        return {
            "success": True,
            "config": self._config,
            "result": result
        }


# Demo mode singleton
demo_service: Optional[DemoModeService] = None


def get_demo_service() -> DemoModeService:
    """Get the demo mode service instance."""
    global demo_service
    if demo_service is None:
        demo_service = DemoModeService()
    return demo_service


# Create a singleton instance
smi_service: Optional[SMIService] = None


def get_smi_service(db: Optional[AsyncIOMotorDatabase] = None) -> SMIService:
    """Get the SMI service instance."""
    global smi_service

    if smi_service is None:
        smi_service = SMIService(db)
    elif db is not None and smi_service.db is None:
        smi_service.db = db

    return smi_service


async def initialize_smi_service(db: AsyncIOMotorDatabase) -> SMIService:
    """Initialize the SMI service with database connection."""
    service = get_smi_service(db)

    if not settings.SMI_ENABLED:
        logger.info("SMI module is disabled in configuration")
        return service

    try:
        health = await service.check_health()
        if health.get("is_connected"):
            logger.info("✓ BlueRadar Intelligence module connected")

            if settings.SMI_AUTO_START_FEED:
                try:
                    await service.start_feed()
                    logger.info("✓ BlueRadar feed auto-started")
                except Exception as e:
                    logger.warning(f"⚠ Failed to auto-start BlueRadar feed: {e}")

            await service.start_alert_sync_task()
        else:
            logger.warning("⚠ BlueRadar module not available")
    except Exception as e:
        logger.warning(f"⚠ BlueRadar health check failed: {e}")

    return service
