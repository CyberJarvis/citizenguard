"""
Coast Guardian FastAPI Main Application
Social Media Intelligence API for Marine Disaster Monitoring
"""

import os
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from dotenv import load_dotenv

from api.models import (
    SocialMediaPost, ProcessedPost, BatchAnalysisRequest, BatchAnalysisResponse,
    HealthCheck, SystemStats, RealTimeAlert, AlertConfig, MisinformationAnalysis
)
from api.database import CoastGuardianDatabase
from api.analysis_service import CoastGuardianAnalysisService
# Realtime service removed
from api.vector_service import initialize_vector_db, get_vector_db
from api.enhanced_feed import (
    generate_multilingual_post,
    analyze_post_for_alerts,
    start_enhanced_feed,
    stop_enhanced_feed,
    get_active_alerts,
    update_feed_config,
    get_enhanced_posts,
    get_enhanced_feed_status
)
from prompt_templates import CoastGuardianPrompts

# Load environment variables
load_dotenv()

def _normalize_disaster_type(disaster_type) -> str:
    """Normalize disaster type to match expected enum values"""
    if not disaster_type:
        return "none"

    # Handle various input types
    if isinstance(disaster_type, list):
        if not disaster_type:
            return "none"
        disaster_type = disaster_type[0] if disaster_type else "none"

    # Convert to string and lowercase
    disaster_type = str(disaster_type).lower().strip()

    # Handle empty strings
    if not disaster_type or disaster_type in ['', 'null', 'none']:
        return "none"

    # Mapping of common variations to expected values
    type_mapping = {
        'flood': 'flooding',
        'floods': 'flooding',
        'tornado': 'none',  # Not in our expected types
        'hurricane': 'cyclone',
        'typhoon': 'cyclone',
        'storm': 'cyclone',
        'oil': 'oil_spill',
        'spill': 'oil_spill',
        'quake': 'earthquake',
        'seismic': 'earthquake'
    }

    # Apply mapping if found
    if disaster_type in type_mapping:
        return type_mapping[disaster_type]

    # Valid disaster types
    valid_types = ['tsunami', 'cyclone', 'oil_spill', 'flooding', 'earthquake', 'none']

    # Return if already valid
    if disaster_type in valid_types:
        return disaster_type

    # Default fallback
    return "none"

# Global instances
db = None
analysis_service = None
vector_db = None
realtime_alerts = None
app_start_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global db, analysis_service, vector_db, realtime_alerts, app_start_time

    # Startup
    print("🌊 Starting Coast Guardian API...")
    app_start_time = time.time()

    try:
        # Initialize database
        db = CoastGuardianDatabase()
        print("✅ Database initialized")

        # Skip vector database initialization for performance
        vector_db = None

        # Initialize analysis service
        analysis_service = CoastGuardianAnalysisService()
        print("✅ Analysis service initialized")

        # Skip real-time alerts for simplicity
        realtime_alerts = None

        print("✅ Coast Guardian API started successfully")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise

    yield

    # Shutdown
    # Real-time alerts disabled
    if db:
        db.close()
    if vector_db:
        # Save vector database
        try:
            vector_db.save_index("/tmp/blueradar_vectors")
            print("✅ Vector database saved")
        except:
            pass
    print("👋 Coast Guardian API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Coast Guardian Social Intelligence API",
    description="Advanced marine disaster monitoring through social media intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the project root directory
import pathlib
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# Enhanced Dashboard endpoint
@app.get("/dashboard", tags=["Dashboard"])
async def get_dashboard():
    """Serve the Coast Guardian enhanced dashboard"""
    return FileResponse(PROJECT_ROOT / "enhanced_dashboard.html")

@app.get("/", tags=["Dashboard"])
async def get_root():
    """Serve the enhanced dashboard at root"""
    return FileResponse(PROJECT_ROOT / "enhanced_dashboard.html")

@app.get("/test", tags=["Dashboard"])
async def get_test_dashboard():
    """Serve the test dashboard for debugging"""
    return FileResponse(PROJECT_ROOT / "test_dashboard.html")

# Health check endpoint
@app.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    """API health check"""
    try:
        # Check database connectivity
        db_health = db.get_system_health() if db else {"database_status": "error"}

        # Check LLM service
        llm_status = "healthy" if analysis_service and analysis_service.llm.is_available() else "down"

        uptime = str(int(time.time() - app_start_time)) + "s" if app_start_time else "unknown"

        return HealthCheck(
            status="healthy" if llm_status == "healthy" and db_health.get("database_status") == "healthy" else "degraded",
            components={
                "llm_service": llm_status,
                "database": db_health.get("database_status", "error"),
                "dataset": "available"
            },
            uptime=uptime
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Single post analysis
@app.post("/analyze", response_model=ProcessedPost, tags=["Analysis"])
async def analyze_post(post: SocialMediaPost, background_tasks: BackgroundTasks):
    """Analyze a single social media post for marine disaster relevance"""
    try:
        # Analyze the post
        result = analysis_service.analyze_post(post)

        # Store in database (background task)
        if db:
            background_tasks.add_task(store_post_background, result)

        # Real-time alerts disabled

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Batch analysis
@app.post("/analyze/batch", response_model=BatchAnalysisResponse, tags=["Analysis"])
async def analyze_batch(request: BatchAnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze multiple posts in batch"""
    try:
        start_time = time.time()

        # Process all posts
        results = analysis_service.batch_analyze(request.posts)

        # Filter by relevance threshold
        filtered_results = [
            result for result in results
            if result.analysis.relevance_score >= request.filter_relevance_threshold
        ]

        processing_time = (time.time() - start_time) * 1000

        # Create summary
        summary = {
            "total_input_posts": len(request.posts),
            "processed_posts": len(results),
            "relevant_posts": len(filtered_results),
            "processing_time_ms": processing_time,
            "average_relevance_score": sum(r.analysis.relevance_score for r in results) / len(results) if results else 0
        }

        # Store results in background
        if db:
            background_tasks.add_task(store_batch_background, filtered_results)

        # Real-time alerts disabled

        return BatchAnalysisResponse(
            total_posts=len(request.posts),
            processed_posts=filtered_results,
            processing_summary=summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

# Get recent posts
@app.get("/posts/recent", tags=["Posts"])
async def get_recent_posts(
    limit: int = Query(default=50, ge=1, le=100),
    disaster_filter: Optional[str] = Query(default=None)
):
    """Get recently analyzed posts"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        posts = db.get_recent_posts(limit=limit, disaster_filter=disaster_filter)
        return {"posts": posts, "count": len(posts)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve posts: {str(e)}")

# Search posts
@app.get("/posts/search", tags=["Posts"])
async def search_posts(
    query: str = Query(..., min_length=2),
    disaster_type: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Search posts by text content"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        results = db.search_posts(query=query, disaster_type=disaster_type, limit=limit)
        return {"results": results, "count": len(results)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Statistics endpoints
@app.get("/statistics/disaster", tags=["Statistics"])
async def get_disaster_statistics(days: int = Query(default=7, ge=1, le=30)):
    """Get disaster statistics for specified days"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        stats = db.get_disaster_statistics(days=days)
        return {"statistics": stats, "period_days": days}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")

@app.get("/statistics/platform", tags=["Statistics"])
async def get_platform_statistics():
    """Get statistics by social media platform"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        stats = db.get_platform_statistics()
        return {"platforms": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Platform statistics failed: {str(e)}")

# Alerts endpoints
@app.get("/alerts/recent", tags=["Alerts"])
async def get_recent_alerts(limit: int = Query(default=10, ge=1, le=50)):
    """Get recent alerts"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        alerts = db.get_recent_alerts(limit=limit)
        return {"alerts": alerts, "count": len(alerts)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


# System information
@app.get("/system/info", tags=["System"])
async def get_system_info():
    """Get system information and statistics"""
    try:
        health_data = db.get_system_health() if db else {}
        # vector_stats = vector_db.get_statistics() if vector_db else {}  # Temporarily disabled

        return {
            "system": "Coast Guardian Social Intelligence",
            "version": "1.0.0",
            "uptime": str(int(time.time() - app_start_time)) + "s" if app_start_time else "unknown",
            "database_health": health_data,
            # "vector_database": vector_stats,  # Temporarily disabled
            "supported_languages": ["english", "hindi", "tamil", "telugu", "kannada", "malayalam",
                                  "bengali", "gujarati", "odia", "punjabi", "konkani",
                                  "hinglish", "tanglish", "manglish"],
            "supported_platforms": ["twitter", "facebook", "instagram", "reddit", "youtube", "news"],
            "disaster_types": ["tsunami", "cyclone", "oil_spill", "flooding", "earthquake"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System info failed: {str(e)}")

@app.post("/database/cleanup", tags=["System"])
async def cleanup_database():
    """Clean up all data from database collections"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get counts before cleanup
        collections_info = []
        total_before = 0

        for collection_name in ['social_posts', 'social_analysis', 'misinfo_flags', 'alerts', 'system_stats']:
            try:
                count = db.collections[collection_name].count_documents({})
                total_before += count
                collections_info.append({
                    "collection": collection_name,
                    "before": count
                })
            except:
                pass

        # Delete all documents from each collection
        total_deleted = 0
        for collection_name in ['social_posts', 'social_analysis', 'misinfo_flags', 'alerts', 'system_stats']:
            try:
                result = db.collections[collection_name].delete_many({})
                deleted = result.deleted_count
                total_deleted += deleted

                # Update collection info
                for info in collections_info:
                    if info["collection"] == collection_name:
                        info["deleted"] = deleted
                        info["after"] = 0
            except Exception as e:
                print(f"Error deleting from {collection_name}: {e}")

        return {
            "status": "success",
            "message": f"Database cleaned successfully. Deleted {total_deleted:,} documents.",
            "total_deleted": total_deleted,
            "total_before": total_before,
            "collections": collections_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database cleanup failed: {str(e)}")

# Misinformation analysis endpoint
@app.post("/analyze/misinformation", response_model=Dict[str, Any], tags=["Analysis"])
async def analyze_misinformation(post: SocialMediaPost):
    """Dedicated misinformation analysis for a social media post"""
    try:
        if not analysis_service:
            raise HTTPException(status_code=503, detail="Analysis service not available")

        from api.misinformation_service import CoastGuardianMisinformationDetector
        from api.models import DisasterAnalysis

        # Quick disaster analysis for context
        llm_analysis = analysis_service.llm.analyze_social_post(post.text, post.language)
        disaster_analysis = DisasterAnalysis(
            relevance_score=llm_analysis.get('relevance_score', 0),
            disaster_type=_normalize_disaster_type(llm_analysis.get('disaster_type', 'none')),
            urgency=llm_analysis.get('urgency', 'low'),
            sentiment=llm_analysis.get('sentiment', 'neutral'),
            keywords=llm_analysis.get('keywords', []),
            credibility_indicators=[],
            location_mentioned=post.location,
            language_detected=post.language,
            confidence_score=0.7
        )

        # Perform misinformation analysis
        detector = CoastGuardianMisinformationDetector()
        flags = detector.detect_misinformation(post, disaster_analysis)
        report = detector.generate_misinformation_report(post, disaster_analysis, flags)

        return {
            "post_analysis": {
                "text": post.text[:100] + "..." if len(post.text) > 100 else post.text,
                "platform": post.platform,
                "language": post.language
            },
            "misinformation_detection": report,
            "processing_timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Misinformation analysis failed: {str(e)}")

# Fact verification endpoint
@app.post("/verify/facts", tags=["Verification"])
async def verify_facts(
    text: str = Query(..., min_length=10, description="Text to fact-check"),
    disaster_type: str = Query(default="tsunami", description="Expected disaster type"),
    language: str = Query(default="english", description="Text language")
):
    """Fact verification for disaster-related claims"""
    try:
        if not analysis_service:
            raise HTTPException(status_code=503, detail="Analysis service not available")

        from api.misinformation_service import CoastGuardianMisinformationDetector
        from api.models import DisasterAnalysis

        # Create a temporary post for analysis
        temp_post = SocialMediaPost(
            text=text,
            platform="unknown",
            language=language
        )

        # Create disaster analysis context
        disaster_analysis = DisasterAnalysis(
            relevance_score=5.0,
            disaster_type=_normalize_disaster_type(disaster_type),
            urgency="medium",
            sentiment="neutral",
            keywords=[],
            credibility_indicators=[],
            language_detected=language,
            confidence_score=0.7
        )

        # Perform fact checking
        detector = CoastGuardianMisinformationDetector()
        flags = detector.detect_misinformation(temp_post, disaster_analysis)

        return {
            "text_analyzed": text[:200] + "..." if len(text) > 200 else text,
            "fact_check_results": {
                "suspicious_language": flags.suspicious_language,
                "credibility_issues": flags.credibility_issues,
                "fact_warnings": flags.fact_check_warnings,
                "source_reliability": flags.source_reliability,
                "overall_confidence": flags.confidence_score
            },
            "recommendations": detector._generate_verification_suggestions(disaster_type),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fact verification failed: {str(e)}")

# Priority analysis endpoint for enhanced scoring demonstration
@app.post("/analyze/priority", tags=["Analysis"])
async def analyze_priority_scoring(post: SocialMediaPost):
    """Analyze post and provide detailed priority scoring breakdown"""
    try:
        if not analysis_service:
            raise HTTPException(status_code=503, detail="Analysis service not available")

        # Perform complete analysis
        processed_post = analysis_service.analyze_post(post)

        # Get detailed priority breakdown for demonstration
        priority_breakdown = analysis_service._get_priority_breakdown(
            processed_post.analysis,
            post,
            processed_post.misinformation_analysis
        )

        return {
            "post_summary": {
                "text_preview": post.text[:100] + "..." if len(post.text) > 100 else post.text,
                "platform": post.platform,
                "language": post.language,
                "has_user_data": post.user is not None,
                "engagement_total": (post.likes or 0) + (post.shares or 0) + (post.comments or 0)
            },
            "priority_analysis": {
                "final_priority": processed_post.priority_level,
                "scoring_breakdown": priority_breakdown,
                "disaster_analysis": {
                    "relevance_score": processed_post.analysis.relevance_score,
                    "disaster_type": processed_post.analysis.disaster_type,
                    "urgency": processed_post.analysis.urgency,
                    "confidence": processed_post.analysis.confidence_score
                },
                "misinformation_risk": {
                    "risk_level": processed_post.misinformation_analysis.risk_level if processed_post.misinformation_analysis else "not_analyzed",
                    "confidence": processed_post.misinformation_analysis.confidence_score if processed_post.misinformation_analysis else 0
                }
            },
            "processing_time_ms": processed_post.processing_time_ms,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Priority analysis failed: {str(e)}")

# WebSocket functionality removed for simplicity

# Server-Sent Events functionality removed for simplicity

# Alert subscription functionality removed

# Real-time statistics removed

# Simulation endpoint for demo
@app.post("/simulate/post", response_model=ProcessedPost, tags=["Simulation"])
async def simulate_social_post(
    disaster_type: str = Query(..., description="Type of disaster to simulate"),
    location: str = Query(default="Mumbai", description="Location for the post"),
    platform: str = Query(default="twitter", description="Social media platform"),
    language: str = Query(default="english", description="Language of the post")
):
    """Simulate a social media post for testing purposes"""
    try:
        # Generate realistic post
        post_text = CoastGuardianPrompts.generate_realistic_post(
            disaster_type=disaster_type,
            location=location,
            platform=platform,
            language=language,
            urgency="high"
        )

        # Create post object
        simulated_post = SocialMediaPost(
            text=post_text,
            platform=platform,
            language=language,
            location=location
        )

        # Analyze the simulated post
        result = analysis_service.analyze_post(simulated_post)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

# LLM-Powered Dummy Data Generation for Frontend
@app.get("/generate/post", tags=["Dummy Data"])
async def generate_dummy_post(
    disaster_type: str = Query("random", description="Type of disaster (tsunami, cyclone, oil_spill, flooding, earthquake, random)"),
    platform: str = Query("random", description="Social media platform (twitter, facebook, instagram, news, reddit, random)"),
    language: str = Query("english", description="Language for the post"),
    location: str = Query("random", description="Indian coastal location"),
):
    """Generate a realistic social media post using LLM for frontend simulation"""
    try:
        if not analysis_service or not analysis_service.llm:
            raise HTTPException(status_code=503, detail="LLM service not available")

        # Generate post using LLM
        post_data = analysis_service.llm.generate_social_media_post(
            disaster_type=disaster_type,
            platform=platform,
            language=language,
            location=location
        )

        # Generate user profile
        user_profile = analysis_service.llm.generate_user_profile(platform)

        # Create complete social media post structure
        from datetime import datetime, timezone
        import uuid

        complete_post = {
            "post_id": str(uuid.uuid4()),
            "text": post_data["text"],
            "platform": post_data["platform"],
            "language": post_data["language"],
            "location": post_data["location"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_profile,
            "engagement": {
                "likes": __import__("random").randint(5, 500),
                "shares": __import__("random").randint(1, 100),
                "comments": __import__("random").randint(0, 50),
                "retweets": __import__("random").randint(1, 80) if platform == "twitter" else 0
            },
            "metadata": {
                "generated": True,
                "expected_disaster_type": post_data.get("disaster_type", "unknown"),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }

        return complete_post

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post generation failed: {str(e)}")

@app.get("/generate/feed", tags=["Dummy Data"])
async def generate_dummy_feed(
    count: int = Query(10, ge=1, le=50, description="Number of posts to generate"),
    disaster_types: str = Query("all", description="Comma-separated disaster types or 'all'"),
    platforms: str = Query("all", description="Comma-separated platforms or 'all'"),
    languages: str = Query("english", description="Comma-separated languages"),
    time_span_minutes: int = Query(60, ge=5, le=1440, description="Time span for posts in minutes")
):
    """Generate a realistic social media feed for frontend simulation"""
    try:
        if not analysis_service or not analysis_service.llm:
            raise HTTPException(status_code=503, detail="LLM service not available")

        # Parse parameters
        disaster_type_list = disaster_types.split(",") if disaster_types != "all" else ["random"]
        platform_list = platforms.split(",") if platforms != "all" else ["random"]
        language_list = languages.split(",")

        from datetime import datetime, timezone, timedelta
        import random

        posts = []
        current_time = datetime.now(timezone.utc)

        for i in range(count):
            # Randomize parameters for each post
            disaster_type = random.choice(disaster_type_list)
            platform = random.choice(platform_list)
            language = random.choice(language_list)

            # Generate post
            post_data = analysis_service.llm.generate_social_media_post(
                disaster_type=disaster_type,
                platform=platform,
                language=language,
                location="random"
            )

            # Generate user profile
            user_profile = analysis_service.llm.generate_user_profile(platform)

            # Calculate timestamp (spread across time span)
            time_offset = random.randint(0, time_span_minutes)
            post_timestamp = current_time - timedelta(minutes=time_offset)

            complete_post = {
                "post_id": str(__import__("uuid").uuid4()),
                "text": post_data["text"],
                "platform": post_data["platform"],
                "language": post_data["language"],
                "location": post_data["location"],
                "timestamp": post_timestamp.isoformat(),
                "user": user_profile,
                "engagement": {
                    "likes": random.randint(5, 500),
                    "shares": random.randint(1, 100),
                    "comments": random.randint(0, 50),
                    "retweets": random.randint(1, 80) if platform == "twitter" else 0
                },
                "metadata": {
                    "generated": True,
                    "expected_disaster_type": post_data.get("disaster_type", "unknown"),
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            }

            posts.append(complete_post)

        # Sort by timestamp (newest first)
        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "posts": posts,
            "total_count": len(posts),
            "parameters": {
                "disaster_types": disaster_type_list,
                "platforms": platform_list,
                "languages": language_list,
                "time_span_minutes": time_span_minutes
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feed generation failed: {str(e)}")

# Streaming functionality removed

# Background tasks
async def store_post_background(processed_post: ProcessedPost):
    """Background task to store processed post"""
    try:
        if db:
            db.store_processed_post(processed_post)
    except Exception as e:
        print(f"❌ Background storage error: {e}")

async def store_batch_background(processed_posts: List[ProcessedPost]):
    """Background task to store batch results"""
    try:
        if db:
            for post in processed_posts:
                db.store_processed_post(post)
    except Exception as e:
        print(f"❌ Background batch storage error: {e}")

# Alert background tasks removed

# Live Social Media Feed Simulation
import threading
import random
import queue
from datetime import datetime, timezone
from typing import List

# Global feed queue and control
live_feed_queue = queue.Queue(maxsize=100)
feed_thread = None
feed_running = False

def generate_dummy_post():
    """Generate realistic dummy social media posts"""

    # Template posts for different scenarios
    normal_posts = [
        "Beautiful sunrise at Marina Beach! Perfect morning for a walk 🌅",
        "Had amazing seafood at Kochi port today! Fresh catch 🐟",
        "Mumbai Marine Drive looks stunning in the evening lights ✨",
        "Fishing boat spotted near Visakhapatnam port this morning",
        "Great weather for sailing today! Calm seas everywhere 🌊",
        "Weekend trip to Goa beaches was incredible! Crystal clear water",
        "Chennai port workers doing excellent job as always 👷‍♂️",
        "Planning a boat trip to Andaman islands next month 🏝️",
        "Local fishermen brought good catch today in Mangalore",
        "Evening walk along Juhu beach with family was lovely 👨‍👩‍👧‍👦"
    ]

    disaster_posts = [
        "URGENT: Large waves approaching Puri beach! Everyone move to safety immediately! 🌊⚠️",
        "Breaking: Oil spill reported near Kandla port - environmental emergency unfolding 🛢️",
        "Cyclone Tej intensifying rapidly - wind speed 180 kmph recorded near Paradip! 🌪️",
        "ALERT: Tsunami warning issued for Tamil Nadu coast by IMD - evacuate coastal areas NOW!",
        "Heavy flooding in Mumbai port area after sudden storm - situation critical 🌧️",
        "Emergency: Coast Guard rescuing fishermen trapped by rough seas near Kochi ⛑️",
        "BREAKING: Earthquake magnitude 6.2 felt in Andaman - possible tsunami threat!",
        "Oil tanker accident near Chennai port - massive spill threatening marine life 🐟",
        "Severe cyclone approaching Gujarat coast - evacuation orders issued for Bhavnagar",
        "URGENT: Flash flooding reported in Kolkata port - immediate assistance needed! 🆘"
    ]

    # 70% normal posts, 30% disaster posts for realistic simulation
    if random.random() < 0.7:
        text = random.choice(normal_posts)
        expected_type = "none"
    else:
        text = random.choice(disaster_posts)
        expected_type = random.choice(["tsunami", "cyclone", "oil_spill", "flooding", "earthquake"])

    # Random user data
    usernames = ["@coastwatch", "@fisherman_raj", "@mumbai_marine", "@chennai_sailor",
                "@goa_beaches", "@ocean_explorer", "@coastal_news", "@sea_lover",
                "@beach_walker", "@marine_life", "@port_worker", "@sailor_sam"]

    platforms = ["twitter", "facebook", "instagram", "news"]
    locations = ["Mumbai", "Chennai", "Kochi", "Visakhapatnam", "Kandla", "Paradip",
               "Marine Drive", "Marina Beach", "Juhu Beach", "Goa", "Andaman"]

    post = {
        "id": f"post_{int(datetime.now(timezone.utc).timestamp())}_{random.randint(1000, 9999)}",
        "text": text,
        "platform": random.choice(platforms),
        "language": "english",
        "user": {
            "username": random.choice(usernames),
            "verified": random.random() < 0.2,
            "follower_count": random.randint(50, 10000)
        },
        "location": random.choice(locations),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engagement": {
            "likes": random.randint(5, 500),
            "shares": random.randint(0, 100),
            "comments": random.randint(0, 50)
        },
        "expected_disaster_type": expected_type
    }

    return post

def feed_generator():
    """Background thread to generate continuous feed"""
    global feed_running

    while feed_running:
        try:
            post = generate_dummy_post()

            # Add to queue (remove old posts if queue is full)
            if live_feed_queue.full():
                try:
                    live_feed_queue.get_nowait()
                except queue.Empty:
                    pass

            live_feed_queue.put(post)
            print(f"📱 Generated post: {post['text'][:50]}...")

            # Wait 8-15 seconds between posts for realistic timing
            time.sleep(random.randint(8, 15))

        except Exception as e:
            print(f"❌ Feed generation error: {e}")
            time.sleep(5)

@app.post("/feed/start", tags=["Live Feed"])
async def start_live_feed():
    """Start the live social media feed simulation"""
    global feed_thread, feed_running

    if feed_running:
        return {"status": "already_running", "message": "Live feed is already running"}

    try:
        feed_running = True
        feed_thread = threading.Thread(target=feed_generator, daemon=True)
        feed_thread.start()

        return {
            "status": "started",
            "message": "Live social media feed started successfully",
            "feed_url": "/feed/posts"
        }
    except Exception as e:
        feed_running = False
        raise HTTPException(status_code=500, detail=f"Failed to start feed: {str(e)}")

@app.post("/feed/stop", tags=["Live Feed"])
async def stop_live_feed():
    """Stop the live social media feed simulation"""
    global feed_running

    if not feed_running:
        return {"status": "not_running", "message": "Live feed is not running"}

    feed_running = False
    return {"status": "stopped", "message": "Live social media feed stopped"}

@app.get("/feed/posts", tags=["Live Feed"])
async def get_live_posts(limit: int = Query(default=20, ge=1, le=50)):
    """Get recent posts from the live feed"""
    try:
        posts = []
        temp_queue = queue.Queue()

        # Get all posts from queue
        while not live_feed_queue.empty() and len(posts) < limit:
            try:
                post = live_feed_queue.get_nowait()
                posts.append(post)
                temp_queue.put(post)
            except queue.Empty:
                break

        # Put posts back in queue
        while not temp_queue.empty():
            live_feed_queue.put(temp_queue.get_nowait())

        # Sort by timestamp (newest first)
        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "posts": posts[:limit],
            "count": len(posts),
            "feed_running": feed_running,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get posts: {str(e)}")

@app.get("/feed/status", tags=["Live Feed"])
async def get_feed_status():
    """Get live feed status and statistics"""
    try:
        return {
            "feed_running": feed_running,
            "queue_size": live_feed_queue.qsize(),
            "max_queue_size": live_feed_queue.maxsize,
            "thread_alive": feed_thread.is_alive() if feed_thread else False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

# Enhanced Feed Endpoints
@app.post("/feed/start/enhanced", tags=["Enhanced Live Feed"])
async def start_enhanced_live_feed():
    """Start the enhanced multilingual live feed"""
    try:
        result = start_enhanced_feed()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start enhanced feed: {str(e)}")

@app.post("/feed/configure", tags=["Enhanced Live Feed"])
async def configure_live_feed(
    post_interval: Optional[int] = Query(None, description="Seconds between posts", ge=3, le=30),
    disaster_probability: Optional[float] = Query(None, description="Probability of disaster posts", ge=0.0, le=1.0),
    language_mix: Optional[float] = Query(None, description="Multi-language mix ratio", ge=0.0, le=1.0),
    primary_language: Optional[str] = Query(None, description="Primary language for posts")
):
    """Update enhanced feed configuration dynamically"""
    try:
        # Only pass supported parameters to update_feed_config
        config_updates = {}
        if post_interval is not None:
            config_updates['post_interval'] = post_interval
        if disaster_probability is not None:
            config_updates['disaster_probability'] = disaster_probability

        # Call update_feed_config with only supported parameters
        result = update_feed_config(**config_updates) if config_updates else {
            "status": "no_updates",
            "config": {
                "post_interval": 8,
                "disaster_probability": 0.3,
                "languages": ["english", "hindi", "tamil", "bengali", "gujarati", "marathi", "telugu", "kannada", "malayalam"]
            }
        }

        # Note: language_mix and primary_language are received but not yet implemented
        # This allows the dashboard sliders to work without errors
        if language_mix is not None or primary_language is not None:
            result["note"] = "Language configuration received but not yet applied to feed generation"

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

@app.get("/feed/enhanced", tags=["Enhanced Live Feed"])
async def get_enhanced_feed(
    limit: int = Query(default=50, ge=1, le=100, description="Number of posts to return")
):
    """Get enhanced feed posts with analysis"""
    try:
        result = get_enhanced_posts(limit=limit)
        status = get_enhanced_feed_status()
        return {
            "posts": result.get("posts", []),
            "stats": {
                "total_posts": result.get("total_posts", 0),
                "disaster_posts": result.get("disaster_posts", 0),
                "languages_detected": result.get("languages_detected", 1)
            },
            "feed_running": status.get("feed_running", False),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced feed: {str(e)}")

@app.get("/alerts/active", tags=["Enhanced Alerts"])
async def get_active_alerts_endpoint():
    """Get currently active alerts from enhanced feed"""
    try:
        alerts = get_active_alerts()
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}")

@app.get("/languages/supported", tags=["Enhanced Languages"])
async def get_supported_languages_endpoint():
    """Get list of supported languages for enhanced feed"""
    try:
        languages = [
            {"code": "english", "name": "English", "native": "English"},
            {"code": "hindi", "name": "Hindi", "native": "हिंदी"},
            {"code": "tamil", "name": "Tamil", "native": "தமிழ்"},
            {"code": "telugu", "name": "Telugu", "native": "తెలుగు"},
            {"code": "bengali", "name": "Bengali", "native": "বাংলা"},
            {"code": "gujarati", "name": "Gujarati", "native": "ગુજરાતી"},
            {"code": "marathi", "name": "Marathi", "native": "मराठी"},
            {"code": "kannada", "name": "Kannada", "native": "ಕನ್ನಡ"},
            {"code": "malayalam", "name": "Malayalam", "native": "മലയാളം"}
        ]
        return {
            "languages": languages,
            "total_count": len(languages),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supported languages: {str(e)}")

# Error handlers
# Demo feed functionality removed

# Live feed functionality removed

# Enhanced NLP endpoints removed

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )