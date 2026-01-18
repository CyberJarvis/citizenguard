"""
Verification System Models
6-Layer verification pipeline data models for hazard report validation.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from app.utils.timezone import to_ist_isoformat


class VerificationDecision(str, Enum):
    """Final verification decision"""
    AUTO_APPROVED = "auto_approved"      # Score >= 85%: fully automated approval
    MANUAL_REVIEW = "manual_review"      # Score 40-85%: needs manual review
    REJECTED = "rejected"                # Score < 40%: auto-rejected
    AUTO_REJECTED = "auto_rejected"      # Geofence failed: auto-rejected
    AI_RECOMMENDED = "ai_recommended"    # Legacy - treated same as MANUAL_REVIEW


class AIRecommendation(str, Enum):
    """AI recommendation (simplified)"""
    APPROVE = "approve"              # Score ≥85% - auto-approve and create ticket
    RECOMMEND_APPROVE = "recommend"  # Legacy - treated same as REVIEW
    REVIEW = "review"                # Score 40-85% - needs manual review
    REJECT = "reject"                # Score <40% - auto-reject


# Simplified Verification Thresholds
VERIFICATION_THRESHOLDS = {
    "auto_approve_min": 85,      # >= 85%: fully automated approval
    "manual_review_min": 40,     # 40-85%: needs manual review
    "auto_reject_max": 40        # < 40%: auto-reject
}


class LayerStatus(str, Enum):
    """Individual layer verification status"""
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class LayerName(str, Enum):
    """Verification layer names"""
    GEOFENCE = "geofence"
    WEATHER = "weather"
    TEXT = "text"
    IMAGE = "image"
    REPORTER = "reporter"


# =============================================================================
# LAYER RESULT MODELS
# =============================================================================

class GeofenceLayerData(BaseModel):
    """Data specific to geofence layer"""
    latitude: float
    longitude: float
    distance_to_coast_km: float
    is_inland: bool
    is_offshore: bool
    nearest_coastline_point: Optional[Dict[str, Any]] = None  # Can contain lat, lon (float) and name (str)
    region: Optional[str] = None


class WeatherLayerData(BaseModel):
    """Data specific to weather validation layer"""
    hazard_type: str
    is_natural_hazard: bool
    threat_level: str  # warning, alert, watch, no_threat
    weather_conditions: Optional[Dict[str, Any]] = None
    marine_conditions: Optional[Dict[str, Any]] = None
    seismic_conditions: Optional[Dict[str, Any]] = None
    matching_indicators: List[str] = []


class TextLayerData(BaseModel):
    """Data specific to text analysis layer"""
    description: str
    predicted_hazard_type: str
    classification_confidence: float
    similarity_score: float
    panic_level: float  # 0-1
    is_spam: bool
    spam_keywords_found: List[str] = []
    top_matches: List[Dict[str, Any]] = []


class ImageLayerData(BaseModel):
    """Data specific to image classification layer"""
    image_path: str
    reported_hazard_type: str
    predicted_class: str
    prediction_confidence: float
    is_match: bool
    all_predictions: Dict[str, float] = {}  # class -> probability


class ReporterLayerData(BaseModel):
    """Data specific to reporter credibility layer"""
    user_id: str
    total_reports: int
    verified_reports: int
    rejected_reports: int
    credibility_score: int  # 0-100
    historical_accuracy: float  # 0-1
    is_new_user: bool


class LayerResult(BaseModel):
    """Result from a single verification layer"""
    layer_name: LayerName = Field(..., description="Name of the verification layer")
    status: LayerStatus = Field(..., description="Layer status (pass/fail/skipped)")
    score: float = Field(..., ge=0.0, le=1.0, description="Layer score (0.0 to 1.0)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the result")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight after redistribution")
    reasoning: str = Field(..., description="Human-readable explanation")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Layer-specific details")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When layer was processed"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }


# =============================================================================
# VERIFICATION RESULT MODELS
# =============================================================================

class VerificationResult(BaseModel):
    """Complete verification result for a hazard report"""
    verification_id: str = Field(..., description="Unique verification ID")
    report_id: str = Field(..., description="Associated hazard report ID")

    # Scores and decision
    composite_score: float = Field(..., ge=0.0, le=100.0, description="Final composite score (0-100)")
    decision: VerificationDecision = Field(..., description="Verification decision")
    decision_reason: str = Field(..., description="Explanation for the decision")

    # Layer results
    layer_results: List[LayerResult] = Field(..., description="Results from each layer")
    weights_used: Dict[str, float] = Field(..., description="Weights used for each layer")

    # Layers that were applicable
    applicable_layers: List[LayerName] = Field(..., description="Layers that were applied")
    skipped_layers: List[LayerName] = Field(default=[], description="Layers that were skipped")

    # Processing metadata
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When verification was completed"
    )

    # V2: Hybrid Mode Fields
    ai_recommendation: Optional[str] = Field(
        default=None,
        description="V2: AI recommendation - approve, recommend, review, reject"
    )
    requires_authority_confirmation: bool = Field(
        default=False,
        description="V2: True if score is 75-85% and needs authority/analyst to confirm"
    )
    authority_confirmation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="V2: Authority confirmation details if AI recommended"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }

    def get_ai_recommendation(self) -> str:
        """Get AI recommendation based on score (simplified 3-tier)"""
        if self.ai_recommendation:
            return self.ai_recommendation

        score = self.composite_score
        if self.decision == VerificationDecision.AUTO_REJECTED:
            return AIRecommendation.REJECT.value
        elif score >= VERIFICATION_THRESHOLDS["auto_approve_min"]:  # >= 85%
            return AIRecommendation.APPROVE.value
        elif score >= VERIFICATION_THRESHOLDS["manual_review_min"]:  # 40-85%
            return AIRecommendation.REVIEW.value
        else:  # < 40%
            return AIRecommendation.REJECT.value


class VerificationAudit(BaseModel):
    """Audit trail for verification decisions"""
    audit_id: str = Field(..., description="Unique audit ID")
    verification_id: str = Field(..., description="Associated verification ID")
    report_id: str = Field(..., description="Associated hazard report ID")

    # Original verification
    original_decision: VerificationDecision = Field(..., description="Original automated decision")
    original_score: float = Field(..., description="Original composite score")
    layer_results: List[LayerResult] = Field(..., description="Layer results at time of verification")

    # Override information (if analyst overrode)
    was_overridden: bool = Field(default=False, description="Whether decision was overridden")
    override_decision: Optional[VerificationDecision] = Field(default=None, description="Override decision if any")
    override_by: Optional[str] = Field(default=None, description="User ID of analyst who overrode")
    override_by_name: Optional[str] = Field(default=None, description="Name of analyst who overrode")
    override_reason: Optional[str] = Field(default=None, description="Reason for override")
    override_at: Optional[datetime] = Field(default=None, description="When override was made")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When audit was created"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }


# =============================================================================
# API REQUEST/RESPONSE MODELS
# =============================================================================

class VerificationQueueItem(BaseModel):
    """Item in the manual review queue"""
    report_id: str
    verification_id: str
    hazard_type: str
    location_name: Optional[str]
    composite_score: float
    decision: VerificationDecision
    layer_summary: Dict[str, str]  # layer_name -> status
    reporter_name: Optional[str]
    created_at: datetime
    time_in_queue_minutes: int


class AnalystDecisionRequest(BaseModel):
    """Request for analyst to make a decision"""
    decision: VerificationDecision = Field(..., description="Analyst's decision")
    reason: str = Field(..., min_length=10, description="Reason for the decision")
    credibility_impact: int = Field(default=5, ge=-20, le=20, description="Credibility score impact")


class VerificationStatsResponse(BaseModel):
    """Verification statistics"""
    total_verifications: int
    auto_approved_count: int
    manual_review_count: int
    rejected_count: int
    auto_rejected_count: int
    avg_composite_score: float
    avg_processing_time_ms: float
    layer_pass_rates: Dict[str, float]  # layer_name -> pass rate
    period_start: datetime
    period_end: datetime


class VerificationThresholds(BaseModel):
    """Configurable verification thresholds"""
    auto_approve_threshold: float = Field(default=85.0, ge=0, le=100)
    manual_review_threshold: float = Field(default=40.0, ge=0, le=100)
    geofence_inland_limit_km: float = Field(default=20.0, ge=0)
    geofence_offshore_limit_km: float = Field(default=30.0, ge=0)

    # Layer weights
    weight_geofence: float = Field(default=0.20, ge=0, le=1)
    weight_weather: float = Field(default=0.25, ge=0, le=1)
    weight_text: float = Field(default=0.25, ge=0, le=1)
    weight_image: float = Field(default=0.20, ge=0, le=1)
    weight_reporter: float = Field(default=0.10, ge=0, le=1)


# =============================================================================
# ENHANCED VERIFICATION STATUS FOR HAZARD REPORT
# =============================================================================

class EnhancedVerificationStatus(str, Enum):
    """Enhanced verification status with more granular states"""
    PENDING = "pending"                    # Not yet verified
    VERIFIED = "verified"                  # Auto-approved or manually approved
    REJECTED = "rejected"                  # Manually rejected
    AUTO_REJECTED = "auto_rejected"        # Failed geofence
    NEEDS_MANUAL_REVIEW = "needs_manual_review"  # Awaiting analyst decision


# =============================================================================
# VISION CLASSIFICATION RESULT (for storing in HazardReport)
# =============================================================================

class VisionClassificationResult(BaseModel):
    """Result from Vision Model image classification"""
    trash: int = Field(default=0, ge=0, le=1, description="Trash/marine debris detected")
    oil_spill: int = Field(default=0, ge=0, le=1, description="Oil spill detected")
    marine_animal: int = Field(default=0, ge=0, le=1, description="Marine animal detected")
    shipwreck: int = Field(default=0, ge=0, le=1, description="Shipwreck detected")
    clean: int = Field(default=0, ge=0, le=1, description="Clean/no hazard")

    confidence_scores: Dict[str, float] = Field(
        default={},
        description="Raw probability scores for each class"
    )

    predicted_class: str = Field(default="clean", description="Primary predicted class")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When image was processed"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: to_ist_isoformat(v)
        }
