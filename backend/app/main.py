"""
CoastGuardian Backend Application
Ocean Hazard Reporting Platform for INCOIS
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import MongoDB, RedisCache
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.api.v1 import auth, hazards, monitoring, chat, profile, transcription, authority, alerts, notifications, analyst, admin, smi, vectordb, multi_hazard, report_enrichment, verification, tickets, organizer, communities, events, certificates, event_photos, community_posts, uploads, export, sos, predictive_alerts
from app.migrations import fix_location_index

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown tasks
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    try:
        # Connect to MongoDB (required)
        await MongoDB.connect()

        # Connect to Redis (optional - graceful degradation)
        try:
            await RedisCache.connect()
        except Exception as redis_error:
            logger.warning(f"[WARN] Redis connection failed (continuing without cache): {redis_error}")
            logger.warning("[WARN] Rate limiting and session features will be disabled")

        # Run database migrations
        try:
            db = MongoDB.get_database()
            logger.info("Running database migrations...")
            await fix_location_index(db)
            logger.info("[OK] Database migrations completed")
        except Exception as migration_error:
            logger.error(f"[WARN] Database migration failed: {migration_error}")
            logger.warning("[WARN] Some features may not work correctly")

        # Initialize ML Monitoring Service
        try:
            from app.services.ml_monitor import ml_service
            logger.info("Initializing ML Monitoring Service...")
            await ml_service.initialize()
            logger.info("[OK] ML Monitoring Service initialized")
        except Exception as ml_error:
            logger.error(f"[WARN] ML Monitoring Service failed to initialize: {ml_error}")
            logger.warning("[WARN] Monitoring endpoints will return empty data until initialized")

        # Initialize Social Media Intelligence (SMI) Service
        if settings.SMI_ENABLED:
            try:
                from app.services.smi_service import initialize_smi_service
                logger.info("Initializing Social Media Intelligence Service...")
                await initialize_smi_service(db)
                logger.info("[OK] SMI Service initialized")
            except Exception as smi_error:
                logger.warning(f"[WARN] SMI Service failed to initialize: {smi_error}")
                logger.warning("[WARN] SMI endpoints will be unavailable")
        else:
            logger.info("[INFO] SMI module is disabled in configuration")

        # Initialize VectorDB Service (FAISS-based hazard classification)
        if settings.VECTORDB_ENABLED:
            try:
                from app.services.vectordb_service import initialize_vectordb_service
                logger.info("Initializing VectorDB Service...")
                await initialize_vectordb_service(db)
                logger.info("[OK] VectorDB Service initialized")
            except Exception as vectordb_error:
                logger.warning(f"[WARN] VectorDB Service failed to initialize: {vectordb_error}")
                logger.warning("[WARN] VectorDB endpoints will return errors until initialized")
        else:
            logger.info("[INFO] VectorDB module is disabled in configuration")

        # Initialize MultiHazard Detection Service
        if settings.MULTIHAZARD_ENABLED:
            try:
                from app.services.multi_hazard_service import initialize_multi_hazard_service
                logger.info("Initializing MultiHazard Detection Service...")
                await initialize_multi_hazard_service()
                logger.info("[OK] MultiHazard Detection Service initialized")
            except Exception as multihazard_error:
                logger.warning(f"[WARN] MultiHazard Service failed to initialize: {multihazard_error}")
                logger.warning("[WARN] MultiHazard endpoints will be unavailable")
        else:
            logger.info("[INFO] MultiHazard module is disabled in configuration")

        # Initialize Predictive Alert Service
        if settings.PREDICTIVE_ALERTS_ENABLED:
            try:
                from app.services.predictive_alert_service import initialize_predictive_alert_service
                logger.info("Initializing Predictive Alert Service...")
                await initialize_predictive_alert_service()
                logger.info("[OK] Predictive Alert Service initialized")
            except Exception as pa_error:
                logger.warning(f"[WARN] Predictive Alert Service failed to initialize: {pa_error}")
                logger.warning("[WARN] Predictive alert endpoints will be unavailable")

        # Initialize Push Notification Service
        if settings.PUSH_NOTIFICATIONS_ENABLED:
            try:
                from app.services.push_notification_service import initialize_push_service
                logger.info("Initializing Push Notification Service...")
                await initialize_push_service()
                logger.info("[OK] Push Notification Service initialized")
            except Exception as push_error:
                logger.warning(f"[WARN] Push Notification Service failed to initialize: {push_error}")
                logger.warning("[WARN] Push notifications will be unavailable")
        else:
            logger.info("[INFO] Push notifications are disabled (VAPID keys not configured)")

        # Create database indexes for chat
        try:
            db = MongoDB.get_database()
            await db.chat_messages.create_index([("room_id", 1), ("timestamp", -1)])
            await db.chat_messages.create_index([("message_id", 1)], unique=True)
            await db.chat_messages.create_index([("user_id", 1)])
            logger.info("[OK] Chat database indexes created")
        except Exception as idx_error:
            logger.warning(f"[WARN] Failed to create chat indexes: {idx_error}")

        # Create database indexes for notifications
        try:
            db = MongoDB.get_database()
            await db.notifications.create_index([("notification_id", 1)], unique=True)
            await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
            await db.notifications.create_index([("user_id", 1), ("is_read", 1)])
            await db.notifications.create_index([("user_id", 1), ("is_dismissed", 1)])
            await db.notifications.create_index([("alert_id", 1)])
            await db.notifications.create_index([("smi_alert_id", 1)])  # SMI alert index
            await db.notifications.create_index([("type", 1)])  # For filtering by notification type
            await db.notifications.create_index([("expires_at", 1)])
            logger.info("[OK] Notification database indexes created")
        except Exception as idx_error:
            logger.warning(f"[WARN] Failed to create notification indexes: {idx_error}")

        # Start Predictive Alert Scheduler (background task)
        if settings.PREDICTIVE_ALERTS_ENABLED:
            try:
                from app.services.predictive_alert_scheduler import initialize_alert_scheduler
                logger.info("Starting Predictive Alert Scheduler...")
                await initialize_alert_scheduler()
                logger.info(f"[OK] Predictive Alert Scheduler started (interval: {settings.PREDICTIVE_ALERT_CHECK_INTERVAL}s)")
            except Exception as scheduler_error:
                logger.warning(f"[WARN] Predictive Alert Scheduler failed to start: {scheduler_error}")
                logger.warning("[WARN] Automatic alert checks will be unavailable")

        logger.info("[OK] All services connected successfully")

    except Exception as e:
        logger.error(f"[ERROR] Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")

    try:
        # Shutdown Predictive Alert Scheduler
        if settings.PREDICTIVE_ALERTS_ENABLED:
            try:
                from app.services.predictive_alert_scheduler import shutdown_alert_scheduler
                await shutdown_alert_scheduler()
                logger.info("[OK] Predictive Alert Scheduler stopped")
            except Exception as scheduler_error:
                logger.warning(f"[WARN] Alert Scheduler shutdown error: {scheduler_error}")

        # Shutdown MultiHazard service (stop monitoring)
        if settings.MULTIHAZARD_ENABLED:
            try:
                from app.services.multi_hazard_service import get_multi_hazard_service
                multi_hazard_service = get_multi_hazard_service()
                await multi_hazard_service.shutdown()
                logger.info("[OK] MultiHazard Service shutdown complete")
            except Exception as mh_error:
                logger.warning(f"[WARN] MultiHazard shutdown error: {mh_error}")

        await MongoDB.disconnect()

        # Disconnect Redis if connected
        if RedisCache.client is not None:
            await RedisCache.disconnect()

        logger.info("[OK] All services disconnected successfully")
    except Exception as e:
        logger.error(f"[ERROR] Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Ocean Hazard Reporting Platform for INCOIS - SIH 2025",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting Middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": errors
            }
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't expose internal errors in production
    if settings.is_production:
        message = "An internal error occurred"
    else:
        message = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message
            }
        }
    )


# Root Endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT
    }


# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns service status
    """
    try:
        # Check MongoDB
        db = MongoDB.get_database()
        await db.command("ping")
        mongo_status = "healthy"
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        mongo_status = "unhealthy"

    try:
        # Check Redis (if connected)
        if RedisCache.client is not None:
            redis = RedisCache.get_client()
            await redis.ping()
            redis_status = "healthy"
        else:
            redis_status = "not_connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"

    # Overall status is healthy if MongoDB is healthy (Redis is optional)
    overall_status = "healthy" if mongo_status == "healthy" else "unhealthy"

    # Add warning if Redis is not connected but MongoDB is healthy
    if mongo_status == "healthy" and redis_status != "healthy":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "services": {
            "mongodb": mongo_status,
            "redis": redis_status
        },
        "version": settings.APP_VERSION
    }


# Include API Routes
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(hazards.router, prefix=settings.API_PREFIX)
app.include_router(monitoring.router, prefix=settings.API_PREFIX)
app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(profile.router, prefix=settings.API_PREFIX)
app.include_router(transcription.router, prefix=settings.API_PREFIX)
app.include_router(authority.router, prefix=settings.API_PREFIX)  # Authority/RBAC endpoints
app.include_router(alerts.router, prefix=settings.API_PREFIX)  # Alert management
app.include_router(notifications.router, prefix=settings.API_PREFIX)  # Notification system
app.include_router(analyst.router, prefix=settings.API_PREFIX)  # Analyst module
app.include_router(admin.router, prefix=settings.API_PREFIX)  # Admin module (Super Admin)
app.include_router(smi.router, prefix=settings.API_PREFIX)  # Social Media Intelligence module
app.include_router(vectordb.router, prefix=settings.API_PREFIX)  # VectorDB hazard classification
app.include_router(multi_hazard.router, prefix=settings.API_PREFIX)  # MultiHazard detection module
app.include_router(report_enrichment.router, prefix=settings.API_PREFIX)  # Report enrichment (environmental data + classification)
app.include_router(verification.router, prefix=settings.API_PREFIX)  # 6-Layer verification pipeline
app.include_router(tickets.router, prefix=settings.API_PREFIX)  # Ticketing system for three-way communication
app.include_router(organizer.router, prefix=settings.API_PREFIX)  # Organizer application & verification
app.include_router(communities.router, prefix=settings.API_PREFIX)  # Community management
app.include_router(events.router, prefix=settings.API_PREFIX)  # Events and gamification
app.include_router(export.router, prefix=f"{settings.API_PREFIX}/export", tags=["Export"])  # Unified data export
app.include_router(certificates.router, prefix=settings.API_PREFIX)  # Certificate generation and download
app.include_router(event_photos.router, prefix=settings.API_PREFIX)  # Event photo gallery
app.include_router(community_posts.router, prefix=settings.API_PREFIX)  # Community posts
app.include_router(uploads.router, prefix=settings.API_PREFIX)  # S3 upload presigned URLs
app.include_router(sos.router, prefix=settings.API_PREFIX)  # SOS emergency alerts for fishermen
app.include_router(predictive_alerts.router, prefix=settings.API_PREFIX)  # Predictive alerts and push notifications

# Mount static files for uploads
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)  # Ensure uploads directory exists
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )


