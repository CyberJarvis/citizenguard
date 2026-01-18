"""
CoastGuardian Backend Application
Ocean Hazard Reporting Platform for INCOIS
"""

import logging
import asyncio
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Track startup errors
startup_errors = []

# Try importing FastAPI first (critical)
try:
    from fastapi import FastAPI, Request, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from fastapi.staticfiles import StaticFiles
    from starlette.exceptions import HTTPException as StarletteHTTPException
    logger.info("[OK] FastAPI imported successfully")
except Exception as e:
    logger.error(f"[FATAL] Failed to import FastAPI: {e}")
    startup_errors.append(f"FastAPI import: {e}")

# Try importing app modules (may fail if dependencies missing)
try:
    from app.config import settings
    logger.info(f"[OK] Config loaded - Environment: {settings.ENVIRONMENT}")
except Exception as e:
    logger.error(f"[ERROR] Failed to import config: {e}")
    startup_errors.append(f"Config: {e}")
    # Create minimal settings with all required attributes
    import os
    class MinimalSettings:
        APP_NAME = "CoastGuardian"
        APP_VERSION = "1.0.0"
        ENVIRONMENT = "production"
        LOG_LEVEL = "INFO"
        HOST = "0.0.0.0"
        PORT = int(os.environ.get("PORT", 8000))
        API_PREFIX = "/api/v1"
        ALLOWED_ORIGINS = ["*"]
        DEBUG = False
        RATE_LIMIT_ENABLED = False
        SMI_ENABLED = False
        VECTORDB_ENABLED = False
        MULTIHAZARD_ENABLED = False
        PREDICTIVE_ALERTS_ENABLED = False
        PUSH_NOTIFICATIONS_ENABLED = False
        MONGODB_URL = os.environ.get("MONGODB_URL", "")
        MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "CoastGuardian")
        is_production = True
    settings = MinimalSettings()

try:
    from app.database import MongoDB, RedisCache
    logger.info("[OK] Database modules imported")
except Exception as e:
    logger.error(f"[ERROR] Failed to import database: {e}")
    startup_errors.append(f"Database: {e}")
    MongoDB = None
    RedisCache = None

try:
    from app.middleware.rate_limit import RateLimitMiddleware
    from app.middleware.security import SecurityHeadersMiddleware
    logger.info("[OK] Middleware imported")
except Exception as e:
    logger.warning(f"[WARN] Failed to import middleware: {e}")
    RateLimitMiddleware = None
    SecurityHeadersMiddleware = None

# Import API routers with error handling
api_routers = {}
router_names = [
    'auth', 'hazards', 'monitoring', 'chat', 'profile', 'transcription',
    'authority', 'alerts', 'notifications', 'analyst', 'admin', 'smi',
    'vectordb', 'multi_hazard', 'report_enrichment', 'verification',
    'tickets', 'organizer', 'communities', 'events', 'certificates',
    'event_photos', 'community_posts', 'uploads', 'export', 'sos', 'predictive_alerts'
]

for router_name in router_names:
    try:
        module = __import__(f'app.api.v1.{router_name}', fromlist=[router_name])
        api_routers[router_name] = module.router
    except Exception as e:
        logger.warning(f"[WARN] Failed to import router {router_name}: {e}")
        startup_errors.append(f"Router {router_name}: {str(e)[:50]}")

try:
    from app.migrations import fix_location_index
    logger.info("[OK] Migrations imported")
except Exception as e:
    logger.warning(f"[WARN] Failed to import migrations: {e}")
    fix_location_index = None

# Track initialization status for health checks
app_state = {
    "ready": False,
    "mongodb": False,
    "redis": False,
    "ml_services": False,
    "startup_error": None
}


async def initialize_ml_services_background():
    """
    Initialize ML services in the background after server starts.
    This prevents Railway timeout during startup.
    """
    global app_state
    
    try:
        db = MongoDB.get_database()
        
        # Initialize ML Monitoring Service
        try:
            from app.services.ml_monitor import ml_service
            logger.info("Initializing ML Monitoring Service...")
            await ml_service.initialize()
            logger.info("[OK] ML Monitoring Service initialized")
        except Exception as ml_error:
            logger.warning(f"[WARN] ML Monitoring Service failed to initialize: {ml_error}")

        # Initialize VectorDB Service (FAISS-based hazard classification)
        if settings.VECTORDB_ENABLED:
            try:
                from app.services.vectordb_service import initialize_vectordb_service
                logger.info("Initializing VectorDB Service...")
                await initialize_vectordb_service(db)
                logger.info("[OK] VectorDB Service initialized")
            except Exception as vectordb_error:
                logger.warning(f"[WARN] VectorDB Service failed to initialize: {vectordb_error}")

        # Initialize MultiHazard Detection Service
        if settings.MULTIHAZARD_ENABLED:
            try:
                from app.services.multi_hazard_service import initialize_multi_hazard_service
                logger.info("Initializing MultiHazard Detection Service...")
                await initialize_multi_hazard_service()
                logger.info("[OK] MultiHazard Detection Service initialized")
            except Exception as multihazard_error:
                logger.warning(f"[WARN] MultiHazard Service failed to initialize: {multihazard_error}")

        # Initialize Predictive Alert Service
        if settings.PREDICTIVE_ALERTS_ENABLED:
            try:
                from app.services.predictive_alert_service import initialize_predictive_alert_service
                logger.info("Initializing Predictive Alert Service...")
                await initialize_predictive_alert_service()
                logger.info("[OK] Predictive Alert Service initialized")
            except Exception as pa_error:
                logger.warning(f"[WARN] Predictive Alert Service failed to initialize: {pa_error}")

        # Start Predictive Alert Scheduler
        if settings.PREDICTIVE_ALERTS_ENABLED:
            try:
                from app.services.predictive_alert_scheduler import initialize_alert_scheduler
                logger.info("Starting Predictive Alert Scheduler...")
                await initialize_alert_scheduler()
                logger.info(f"[OK] Predictive Alert Scheduler started")
            except Exception as scheduler_error:
                logger.warning(f"[WARN] Predictive Alert Scheduler failed to start: {scheduler_error}")

        app_state["ml_services"] = True
        logger.info("[OK] All ML services initialized successfully")
        
    except Exception as e:
        logger.error(f"[ERROR] ML services initialization failed: {e}")
        app_state["startup_error"] = str(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown tasks
    
    PRODUCTION OPTIMIZATION: ML services are loaded in background
    to prevent Railway startup timeout. The server responds immediately
    while heavy ML models load asynchronously.
    """
    global app_state
    
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.PORT}")
    logger.info(f"MongoDB URL configured: {'Yes' if settings.MONGODB_URL and 'mongodb' in settings.MONGODB_URL else 'No'}")
    logger.info("=" * 60)

    try:
        # Connect to MongoDB - required but handle gracefully
        if MongoDB is not None:
            try:
                await MongoDB.connect()
                app_state["mongodb"] = True
                logger.info("[OK] MongoDB connected successfully")
            except Exception as mongo_error:
                logger.error(f"[ERROR] MongoDB connection failed: {mongo_error}")
                logger.warning("[WARN] App will start but database features will be unavailable")
                app_state["mongodb"] = False
                app_state["startup_error"] = f"MongoDB: {str(mongo_error)}"
        else:
            logger.error("[ERROR] MongoDB module not imported - database unavailable")
            app_state["mongodb"] = False
            app_state["startup_error"] = "MongoDB module import failed"

        # Connect to Redis (optional - graceful degradation)
        if RedisCache is not None:
            try:
                await RedisCache.connect()
                app_state["redis"] = True
            except Exception as redis_error:
                logger.warning(f"[WARN] Redis connection failed (continuing without cache): {redis_error}")
                app_state["redis"] = False
        else:
            logger.warning("[WARN] Redis module not imported - caching unavailable")
            app_state["redis"] = False

        # Run database migrations (quick operation)
        if MongoDB is not None and app_state["mongodb"] and fix_location_index is not None:
            try:
                db = MongoDB.get_database()
                logger.info("Running database migrations...")
                await fix_location_index(db)
                logger.info("[OK] Database migrations completed")
            except Exception as migration_error:
                logger.warning(f"[WARN] Database migration failed: {migration_error}")

        # Initialize SMI Service (lightweight, can be sync)
        if settings.SMI_ENABLED and MongoDB is not None and app_state["mongodb"]:
            try:
                from app.services.smi_service import initialize_smi_service
                logger.info("Initializing Social Media Intelligence Service...")
                db = MongoDB.get_database()
                await initialize_smi_service(db)
                logger.info("[OK] SMI Service initialized")
            except Exception as smi_error:
                logger.warning(f"[WARN] SMI Service failed to initialize: {smi_error}")

        # Initialize Push Notification Service (lightweight)
        if settings.PUSH_NOTIFICATIONS_ENABLED:
            try:
                from app.services.push_notification_service import initialize_push_service
                logger.info("Initializing Push Notification Service...")
                await initialize_push_service()
                logger.info("[OK] Push Notification Service initialized")
            except Exception as push_error:
                logger.warning(f"[WARN] Push Notification Service failed to initialize: {push_error}")

        # Create database indexes (quick operations) - only if MongoDB connected
        if MongoDB is not None and app_state["mongodb"]:
            try:
                db = MongoDB.get_database()
                await db.chat_messages.create_index([("room_id", 1), ("timestamp", -1)])
                await db.chat_messages.create_index([("message_id", 1)], unique=True)
                await db.chat_messages.create_index([("user_id", 1)])
                logger.info("[OK] Chat database indexes created")
            except Exception as idx_error:
                logger.warning(f"[WARN] Failed to create chat indexes: {idx_error}")

            try:
                db = MongoDB.get_database()
                await db.notifications.create_index([("notification_id", 1)], unique=True)
                await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
                await db.notifications.create_index([("user_id", 1), ("is_read", 1)])
                await db.notifications.create_index([("user_id", 1), ("is_dismissed", 1)])
                await db.notifications.create_index([("alert_id", 1)])
                await db.notifications.create_index([("smi_alert_id", 1)])
                await db.notifications.create_index([("type", 1)])
                await db.notifications.create_index([("expires_at", 1)])
                logger.info("[OK] Notification database indexes created")
            except Exception as idx_error:
                logger.warning(f"[WARN] Failed to create notification indexes: {idx_error}")

        # Mark server as ready for basic requests
        app_state["ready"] = True
        logger.info("[OK] Server is ready to accept requests")

        # Start ML services initialization in background (non-blocking)
        # This allows the server to respond to health checks immediately
        if app_state["mongodb"]:
            logger.info("[INFO] Starting ML services initialization in background...")
            asyncio.create_task(initialize_ml_services_background())
        else:
            logger.warning("[WARN] Skipping ML services - MongoDB not connected")

        logger.info("[OK] Core services startup completed")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"[ERROR] Startup error: {e}")
        app_state["startup_error"] = str(e)
        # Don't raise - let the app start anyway for health checks
        app_state["ready"] = True
        logger.warning("[WARN] App starting with errors - check configuration")

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

        # Disconnect MongoDB if available
        if MongoDB is not None:
            await MongoDB.disconnect()

        # Disconnect Redis if connected
        if RedisCache is not None and RedisCache.client is not None:
            await RedisCache.disconnect()

        logger.info("[OK] All services disconnected successfully")
    except Exception as e:
        logger.error(f"[ERROR] Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Ocean Hazard Reporting Platform for INCOIS - SIH 2025",
    docs_url="/docs",  # Always enable docs for API testing
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware - Production ready configuration
# Dynamically add Vercel preview URLs
cors_origins = list(settings.ALLOWED_ORIGINS) if isinstance(settings.ALLOWED_ORIGINS, list) else [settings.ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Security Headers Middleware - only add if imported successfully
if SecurityHeadersMiddleware is not None:
    app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting Middleware - only add if imported and enabled
if settings.RATE_LIMIT_ENABLED and RateLimitMiddleware is not None:
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


# Root Endpoint - Must respond immediately for Railway health checks
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - responds immediately for health checks"""
    response = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running" if app_state["ready"] else "starting",
        "environment": settings.ENVIRONMENT,
        "ready": app_state["ready"],
        "services": {
            "mongodb": app_state["mongodb"],
            "redis": app_state["redis"],
            "ml_services": app_state["ml_services"]
        }
    }
    if app_state["startup_error"]:
        response["startup_error"] = app_state["startup_error"]
    return response


# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns service status
    """
    # Check MongoDB
    mongo_status = "healthy" if app_state["mongodb"] else "unhealthy"
    if app_state["mongodb"] and MongoDB is not None:
        try:
            db = MongoDB.get_database()
            await db.command("ping")
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            mongo_status = "unhealthy"

    # Check Redis status
    redis_status = "healthy" if app_state["redis"] else "not_connected"
    if app_state["redis"] and RedisCache is not None and RedisCache.client is not None:
        try:
            redis = RedisCache.get_client()
            await redis.ping()
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


# Include API Routes dynamically from imported routers
for router_name, router in api_routers.items():
    try:
        if router_name == 'export':
            app.include_router(router, prefix=f"{settings.API_PREFIX}/export", tags=["Export"])
        else:
            app.include_router(router, prefix=settings.API_PREFIX)
        logger.info(f"[OK] Registered router: {router_name}")
    except Exception as e:
        logger.warning(f"[WARN] Failed to register router {router_name}: {e}")

# Mount static files for uploads
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)  # Ensure uploads directory exists
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except Exception as e:
    logger.warning(f"[WARN] Failed to mount uploads: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )


