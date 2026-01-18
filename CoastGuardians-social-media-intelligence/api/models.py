"""
CoastGuardian API Data Models
Pydantic models for request/response validation
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
import uuid

# Enums for validation
DisasterType = Literal["tsunami", "cyclone", "oil_spill", "flooding", "earthquake", "none"]
UrgencyLevel = Literal["critical", "high", "medium", "low"]
SentimentType = Literal["negative", "neutral", "positive"]
PlatformType = Literal["twitter", "facebook", "instagram", "reddit", "youtube", "news"]
LanguageType = Literal["english", "hindi", "tamil", "telugu", "kannada", "malayalam",
                      "bengali", "gujarati", "odia", "punjabi", "konkani",
                      "hinglish", "tanglish", "manglish"]

class UserProfile(BaseModel):
    """Social media user profile"""
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    follower_count: int = Field(ge=0, le=100000000)
    verified: bool = False
    location: Optional[str] = None

class SocialMediaPost(BaseModel):
    """Social media post input"""
    text: str = Field(min_length=1, max_length=2000)
    platform: PlatformType
    language: LanguageType = "english"
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: Optional[str] = None
    user: Optional[UserProfile] = None
    media_urls: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []

    # Social engagement metrics for priority scoring
    likes: Optional[int] = Field(default=0, ge=0)
    shares: Optional[int] = Field(default=0, ge=0)
    comments: Optional[int] = Field(default=0, ge=0)
    retweets: Optional[int] = Field(default=0, ge=0)  # Twitter specific

class DisasterAnalysis(BaseModel):
    """Marine disaster analysis result"""
    relevance_score: float = Field(ge=0, le=10)
    disaster_type: DisasterType
    urgency: UrgencyLevel
    sentiment: SentimentType
    keywords: List[str] = []
    credibility_indicators: List[str] = []
    location_mentioned: Optional[str] = None
    language_detected: LanguageType
    confidence_score: float = Field(ge=0.0, le=1.0)

class MisinformationAnalysis(BaseModel):
    """Misinformation detection results"""
    risk_level: Literal["minimal_misinformation_risk", "low_misinformation_risk",
                       "moderate_misinformation_risk", "high_misinformation_risk"]
    confidence_score: float = Field(ge=0, le=1, description="Misinformation confidence (0-1)")
    suspicious_language_flags: List[str] = []
    credibility_concerns: List[str] = []
    fact_check_warnings: List[str] = []
    source_reliability: Literal["very_low_reliability", "low_reliability",
                               "moderate_reliability", "high_reliability"]
    verification_suggestions: List[str] = []
    recommendation: str

class ProcessedPost(BaseModel):
    """Processed social media post with analysis"""
    post_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_post: SocialMediaPost
    analysis: DisasterAnalysis
    misinformation_analysis: Optional[MisinformationAnalysis] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float
    priority_level: Literal["P0", "P1", "P2", "P3", "P4"] = "P4"

class BatchAnalysisRequest(BaseModel):
    """Batch analysis request"""
    posts: List[SocialMediaPost]
    include_raw_data: bool = False
    filter_relevance_threshold: float = Field(default=3.0, ge=0, le=10)

class BatchAnalysisResponse(BaseModel):
    """Batch analysis response"""
    total_posts: int
    processed_posts: List[ProcessedPost]
    processing_summary: Dict[str, Any]
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    processed_at: datetime = Field(default_factory=datetime.utcnow)

class AlertConfig(BaseModel):
    """Alert configuration"""
    min_relevance_score: float = Field(default=7.0, ge=0, le=10)
    disaster_types: List[DisasterType] = ["tsunami", "cyclone"]
    urgency_levels: List[UrgencyLevel] = ["critical", "high"]
    locations: List[str] = []
    keywords: List[str] = []

class RealTimeAlert(BaseModel):
    """Real-time alert"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    post: ProcessedPost
    alert_reason: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    notification_sent: bool = False

class PlatformStats(BaseModel):
    """Platform statistics"""
    platform: PlatformType
    total_posts: int
    disaster_posts: int
    avg_relevance_score: float
    top_disaster_types: List[Dict[str, Any]]
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class LanguageStats(BaseModel):
    """Language statistics"""
    language: LanguageType
    total_posts: int
    disaster_posts: int
    common_keywords: List[str]
    avg_confidence: float

class SystemStats(BaseModel):
    """System-wide statistics"""
    total_posts_processed: int
    total_alerts_generated: int
    platform_breakdown: List[PlatformStats]
    language_breakdown: List[LanguageStats]
    disaster_distribution: Dict[DisasterType, int]
    urgency_distribution: Dict[UrgencyLevel, int]
    average_processing_time_ms: float
    last_24h_posts: int
    system_uptime: str

class HealthCheck(BaseModel):
    """API health check response"""
    status: Literal["healthy", "degraded", "down"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"
    components: Dict[str, str] = {
        "llm_service": "unknown",
        "database": "unknown",
        "dataset": "unknown"
    }
    uptime: str = "unknown"