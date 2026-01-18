"""
Verification Service
6-Layer verification pipeline orchestrator for hazard report validation.

Layers:
1. Geofencing (20%): Validate coastal location
2. Weather (25%): Real-time environmental validation (natural hazards only)
3. Text Analysis (25%): VectorDB semantic analysis
4. Image Classification (20%): Vision Model validation (4 visual hazards only)
5. Reporter Score (10%): Historical credibility

Decision Thresholds (V2 - Hybrid Mode):
- >= 85%: Auto-Approve (verified) - ticket auto-created
- 75-85%: AI Recommended (ai_recommended) - needs authority/analyst confirmation
- 40-75%: Manual Review (needs_manual_review)
- < 40%: Recommend Reject (rejected)
- Geofence Fail: Auto-Reject (auto_rejected)
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.verification import (
    LayerResult, LayerStatus, LayerName, VerificationResult,
    VerificationDecision, VerificationAudit, ReporterLayerData,
    VerificationThresholds, AIRecommendation, VERIFICATION_THRESHOLDS
)
from app.models.hazard import HazardReport, HazardType, HazardCategory
from app.models.user import TrustEventType, calculate_trust_score
from app.services.geofence_service import get_geofence_service, GeofenceService
from app.services.vision_service import get_vision_service, VisionService
from app.services.vectordb_service import get_vectordb_service, VectorDBService

logger = logging.getLogger(__name__)


class VerificationService:
    """
    Main verification service orchestrating the 6-layer pipeline.

    Coordinates all verification layers and calculates composite scores
    with dynamic weight redistribution for skipped layers.
    """

    # Base weights for each layer
    BASE_WEIGHTS = {
        LayerName.GEOFENCE: 0.10,
        LayerName.WEATHER: 0.25,
        LayerName.TEXT: 0.25,
        LayerName.IMAGE: 0.35,
        LayerName.REPORTER: 0.05
    }

    # Decision thresholds (Simplified)
    AUTO_APPROVE_THRESHOLD = 85.0      # >= 85%: fully automated approval, ticket created
    MANUAL_REVIEW_THRESHOLD = 40.0     # 40-85%: needs manual review by analyst/authority
    # < 40%: auto-reject

    # Natural hazards that require weather validation
    NATURAL_HAZARDS = [
        "High Waves",
        "Rip Current",
        "Storm Surge/Cyclone Effects",
        "Flooded Coastline",
        "Tsunami",  # Added - Tsunami is a natural hazard requiring weather validation
    ]

    # Hazards that require image validation
    IMAGE_HAZARDS = [
        "Beached Aquatic Animal",
        "Ship Wreck",
        "Plastic Pollution",
        "Oil Spill",
    ]

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """Initialize verification service."""
        self.db = db
        self.geofence_service: Optional[GeofenceService] = None
        self.vision_service: Optional[VisionService] = None
        self.vectordb_service: Optional[VectorDBService] = None
        self._initialized = False

    async def initialize(self):
        """Initialize all sub-services."""
        if self._initialized:
            return

        try:
            # Initialize services
            self.geofence_service = get_geofence_service()
            self.vision_service = get_vision_service()
            self.vectordb_service = get_vectordb_service(self.db)

            # Initialize vectordb if needed
            if not self.vectordb_service._initialized:
                await self.vectordb_service.initialize()

            self._initialized = True
            logger.info("VerificationService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize VerificationService: {e}")
            raise

    def _is_natural_hazard(self, hazard_type: str) -> bool:
        """Check if hazard type is a natural hazard."""
        return hazard_type in self.NATURAL_HAZARDS

    def _requires_image_validation(self, hazard_type: str) -> bool:
        """Check if hazard type requires image validation."""
        return hazard_type in self.IMAGE_HAZARDS

    def _redistribute_weights(
        self,
        active_layers: List[LayerName],
        skipped_layers: List[LayerName]
    ) -> Dict[LayerName, float]:
        """
        Redistribute weights from skipped layers to active layers.

        Args:
            active_layers: Layers that are being applied
            skipped_layers: Layers that are being skipped

        Returns:
            Dictionary of layer name to adjusted weight
        """
        # Calculate total weight of skipped layers
        skipped_weight = sum(
            self.BASE_WEIGHTS[layer]
            for layer in skipped_layers
        )

        # Calculate total weight of active layers
        active_base_weight = sum(
            self.BASE_WEIGHTS[layer]
            for layer in active_layers
        )

        # Redistribute proportionally
        adjusted_weights = {}
        for layer in active_layers:
            base = self.BASE_WEIGHTS[layer]
            proportion = base / active_base_weight if active_base_weight > 0 else 0
            adjusted_weights[layer] = base + (skipped_weight * proportion)

        # Set skipped layers to 0
        for layer in skipped_layers:
            adjusted_weights[layer] = 0.0

        return adjusted_weights

    async def _run_geofence_layer(
        self,
        lat: float,
        lon: float
    ) -> LayerResult:
        """Run Layer 1: Geofence validation."""
        return await self.geofence_service.validate_location(lat, lon)

    async def _run_weather_layer(
        self,
        report: HazardReport,
        hazard_type: str
    ) -> LayerResult:
        """
        Run Layer 2: Weather validation.

        Uses existing environmental_snapshot and hazard_classification from report.
        """
        # Check if weather validation applies
        if not self._is_natural_hazard(hazard_type):
            return LayerResult(
                layer_name=LayerName.WEATHER,
                status=LayerStatus.SKIPPED,
                score=1.0,  # No penalty for skipped layers
                confidence=1.0,
                weight=0.25,
                reasoning=f"Weather validation not applicable for {hazard_type} (human-made hazard)",
                data={"hazard_type": hazard_type, "reason": "not_natural_hazard"},
                processed_at=datetime.now(timezone.utc)
            )

        try:
            # Use existing hazard classification if available
            if report.hazard_classification:
                classification = report.hazard_classification
                threat_level = classification.threat_level.value if hasattr(classification.threat_level, 'value') else str(classification.threat_level)

                # Map threat level to score
                threat_scores = {
                    "warning": 1.0,
                    "alert": 0.85,
                    "watch": 0.70,
                    "no_threat": 0.0
                }
                score = threat_scores.get(threat_level, 0.5)

                status = LayerStatus.PASS if score >= 0.5 else LayerStatus.FAIL

                return LayerResult(
                    layer_name=LayerName.WEATHER,
                    status=status,
                    score=score,
                    confidence=classification.confidence,
                    weight=0.25,
                    reasoning=f"Weather validation: {threat_level.upper()}. {classification.reasoning}",
                    data={
                        "threat_level": threat_level,
                        "hazard_type": hazard_type,
                        "confidence": classification.confidence,
                        "recommendations": classification.recommendations if classification.recommendations else []
                    },
                    processed_at=datetime.now(timezone.utc)
                )

            # No classification data - return partial score
            return LayerResult(
                layer_name=LayerName.WEATHER,
                status=LayerStatus.PASS,
                score=0.6,
                confidence=0.5,
                weight=0.25,
                reasoning="Weather validation: No environmental data available. Assigned moderate score.",
                data={"hazard_type": hazard_type, "reason": "no_environmental_data"},
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Weather layer error: {e}")
            return LayerResult(
                layer_name=LayerName.WEATHER,
                status=LayerStatus.FAIL,
                score=0.5,
                confidence=0.0,
                weight=0.25,
                reasoning=f"Weather validation failed: {str(e)}",
                data={"error": str(e)},
                processed_at=datetime.now(timezone.utc)
            )

    async def _run_text_layer(
        self,
        description: str,
        hazard_type: str
    ) -> LayerResult:
        """
        Run Layer 3: Text analysis.

        IMPORTANT: Missing or very short descriptions are heavily penalized because:
        - Legitimate hazard reports typically include descriptive text
        - Without text, we cannot verify the user's claim semantically
        - Empty reports are a common pattern in spam/fake submissions
        """
        text_length = len(description.strip()) if description else 0

        # No description at all - heavily penalize
        if not description or text_length == 0:
            return LayerResult(
                layer_name=LayerName.TEXT,
                status=LayerStatus.FAIL,
                score=0.0,  # Zero score for no description
                confidence=0.0,
                weight=0.25,
                reasoning="No description provided. Hazard reports require descriptive text for verification. This report cannot be validated without a description.",
                data={"reason": "no_description", "text_length": 0},
                processed_at=datetime.now(timezone.utc)
            )

        # Very short description (< 10 chars) - still penalize but less
        if text_length < 10:
            return LayerResult(
                layer_name=LayerName.TEXT,
                status=LayerStatus.FAIL,
                score=0.15,  # Very low score for too-short description
                confidence=0.1,
                weight=0.25,
                reasoning=f"Description too short ({text_length} characters). Please provide a meaningful description of the hazard (minimum 10 characters).",
                data={"reason": "description_too_short", "text_length": text_length},
                processed_at=datetime.now(timezone.utc)
            )

        # Short description (10-30 chars) - partial penalty
        if text_length < 30:
            # Still run analysis but apply penalty
            result = await self.vectordb_service.analyze_for_verification(
                description, hazard_type
            )
            # Apply penalty for short text
            result.score = result.score * 0.6  # 40% penalty
            result.reasoning = f"Short description ({text_length} chars). {result.reasoning}"
            return result

        return await self.vectordb_service.analyze_for_verification(
            description, hazard_type
        )

    async def _run_image_layer(
        self,
        image_path: str,
        hazard_type: str
    ) -> LayerResult:
        """Run Layer 4: Image classification."""
        return await self.vision_service.classify_image(image_path, hazard_type)

    async def _run_reporter_layer(
        self,
        user_id: str,
        db: AsyncIOMotorDatabase
    ) -> LayerResult:
        """
        Run Layer 5: Reporter credibility scoring.

        Fetches user's historical data and calculates credibility score.
        """
        try:
            # Fetch user from database
            user = await db.users.find_one({"user_id": user_id})

            if not user:
                # New or unknown user - give benefit of doubt
                return LayerResult(
                    layer_name=LayerName.REPORTER,
                    status=LayerStatus.PASS,
                    score=0.5,  # Default score for new users
                    confidence=0.5,
                    weight=0.10,
                    reasoning="New user - assigned default credibility score",
                    data=ReporterLayerData(
                        user_id=user_id,
                        total_reports=0,
                        verified_reports=0,
                        rejected_reports=0,
                        credibility_score=50,
                        historical_accuracy=0.0,
                        is_new_user=True
                    ).model_dump(),
                    processed_at=datetime.now(timezone.utc)
                )

            # Extract user statistics (using correct field names from User model)
            total_reports = user.get("total_reports", 0)
            verified_reports = user.get("verified_reports", 0)
            rejected_reports = user.get("rejected_reports", 0)
            credibility_score = user.get("credibility_score", 50)

            is_new_user = total_reports == 0

            # Calculate historical accuracy and final score
            # credibility_score now uses asymptotic trust formula (updated by AI layers & analyst decisions)
            if total_reports > 0:
                historical_accuracy = verified_reports / total_reports
                # Score = (accuracy * 40%) + (credibility/100 * 60%)
                # Higher weight on credibility since it incorporates AI layer feedback
                score = (historical_accuracy * 0.4) + (credibility_score / 100 * 0.6)
            else:
                historical_accuracy = 0.0
                # For new users, use credibility score directly (default 50 = 0.5)
                score = credibility_score / 100

            # Determine status based on score
            if score >= 0.6:
                status = LayerStatus.PASS
                reasoning = f"Trusted reporter: trust score {credibility_score}, {verified_reports}/{total_reports} verified ({historical_accuracy:.1%} accuracy)"
            elif score >= 0.4:
                status = LayerStatus.PASS
                reasoning = f"Moderate credibility: trust score {credibility_score}, {verified_reports}/{total_reports} verified ({historical_accuracy:.1%} accuracy)"
            else:
                status = LayerStatus.FAIL
                reasoning = f"Low credibility: trust score {credibility_score}, {verified_reports}/{total_reports} verified ({historical_accuracy:.1%} accuracy). Manual review recommended."

            return LayerResult(
                layer_name=LayerName.REPORTER,
                status=status,
                score=max(0.0, min(1.0, score)),
                confidence=min(1.0, total_reports / 10) if total_reports > 0 else 0.5,
                weight=0.10,
                reasoning=reasoning,
                data=ReporterLayerData(
                    user_id=user_id,
                    total_reports=total_reports,
                    verified_reports=verified_reports,
                    rejected_reports=rejected_reports,
                    credibility_score=credibility_score,
                    historical_accuracy=historical_accuracy,
                    is_new_user=is_new_user
                ).model_dump(),
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Reporter layer error: {e}")
            return LayerResult(
                layer_name=LayerName.REPORTER,
                status=LayerStatus.PASS,
                score=0.5,
                confidence=0.0,
                weight=0.10,
                reasoning=f"Reporter credibility check failed: {str(e)}. Assigned default score.",
                data={"error": str(e), "user_id": user_id},
                processed_at=datetime.now(timezone.utc)
            )

    def _calculate_composite_score(
        self,
        layer_results: List[LayerResult],
        weights: Dict[LayerName, float]
    ) -> float:
        """
        Calculate weighted composite score from all layer results.

        Args:
            layer_results: Results from all layers
            weights: Adjusted weights for each layer

        Returns:
            Composite score (0-100)
        """
        total_score = 0.0
        total_weight = 0.0

        for result in layer_results:
            if result.status != LayerStatus.SKIPPED:
                weight = weights.get(result.layer_name, result.weight)
                total_score += result.score * weight
                total_weight += weight

        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = 0.5

        return normalized_score * 100  # Convert to percentage

    def _determine_decision(
        self,
        composite_score: float,
        geofence_result: LayerResult,
        layer_results: List[LayerResult] = None
    ) -> Tuple[VerificationDecision, str]:
        """
        Determine verification decision based on composite score and layer results.

        Enhanced decision logic:
        - Auto-reject if geofence fails
        - Auto-reject if BOTH text AND image layers fail with very low scores
        - Auto-reject if image shows non-hazard content (selfie, portrait)
        - Apply standard thresholds for other cases

        Args:
            composite_score: Composite score (0-100)
            geofence_result: Result from geofence layer
            layer_results: All layer results for additional checks

        Returns:
            Tuple of (decision, reason)
        """
        # Geofence failure = auto-reject
        if geofence_result.status == LayerStatus.FAIL:
            return (
                VerificationDecision.AUTO_REJECTED,
                f"Location outside valid coastal area. {geofence_result.reasoning}"
            )

        # Check for critical layer failures (enhanced rejection logic)
        if layer_results:
            text_result = None
            image_result = None

            for result in layer_results:
                if result.layer_name == LayerName.TEXT:
                    text_result = result
                elif result.layer_name == LayerName.IMAGE:
                    image_result = result

            # Rule 1: Auto-reject if image shows selfie/portrait/non-hazard
            if image_result and image_result.status == LayerStatus.FAIL:
                data = image_result.data if isinstance(image_result.data, dict) else {}
                if data.get("rejection_type") == "pre_classification_check":
                    return (
                        VerificationDecision.AUTO_REJECTED,
                        f"Image rejected: {image_result.reasoning}"
                    )

            # Rule 2: Auto-reject if BOTH text and image fail with very low scores
            # This catches obvious spam/fake reports
            if (text_result and image_result and
                text_result.status == LayerStatus.FAIL and
                image_result.status == LayerStatus.FAIL):

                if text_result.score < 0.2 and image_result.score < 0.2:
                    return (
                        VerificationDecision.AUTO_REJECTED,
                        f"Report rejected: Both text analysis (score: {text_result.score:.1%}) "
                        f"and image validation (score: {image_result.score:.1%}) failed. "
                        f"This report does not appear to be a valid hazard report."
                    )

            # Rule 3: Auto-reject if no description AND image fails
            if (text_result and image_result and
                text_result.score == 0.0 and
                image_result.status == LayerStatus.FAIL):
                return (
                    VerificationDecision.AUTO_REJECTED,
                    f"Report rejected: No description provided and image validation failed. "
                    f"Please provide a detailed description and a clear photo of the hazard."
                )

        # Apply simplified thresholds (only 3 outcomes)
        if composite_score >= self.AUTO_APPROVE_THRESHOLD:
            return (
                VerificationDecision.AUTO_APPROVED,
                f"High confidence ({composite_score:.1f}%). Automatically verified and ticket created."
            )
        elif composite_score >= self.MANUAL_REVIEW_THRESHOLD:
            return (
                VerificationDecision.MANUAL_REVIEW,
                f"Score: {composite_score:.1f}%. Requires analyst/authority review before approval."
            )
        else:
            return (
                VerificationDecision.REJECTED,
                f"Low confidence ({composite_score:.1f}%). Recommended for rejection."
            )

    async def verify_report(
        self,
        report: HazardReport,
        image_path: Optional[str] = None,
        db: Optional[AsyncIOMotorDatabase] = None
    ) -> VerificationResult:
        """
        Run full 6-layer verification pipeline on a hazard report.

        Args:
            report: HazardReport to verify
            image_path: Path to the uploaded image
            db: Database connection for user lookups

        Returns:
            VerificationResult with all layer results and decision
        """
        start_time = time.time()
        verification_id = f"VRF_{uuid.uuid4().hex[:12].upper()}"

        # Use passed db or fall back to instance db (avoid bool() on Motor objects)
        db = db if db is not None else self.db

        # Ensure service is initialized
        if not self._initialized:
            await self.initialize()

        hazard_type = report.hazard_type.value if hasattr(report.hazard_type, 'value') else str(report.hazard_type)

        logger.info(f"Starting verification for report {report.report_id}, hazard type: {hazard_type}")

        # Determine which layers are applicable
        active_layers = [LayerName.GEOFENCE, LayerName.TEXT, LayerName.REPORTER]
        skipped_layers = []

        if self._is_natural_hazard(hazard_type):
            active_layers.append(LayerName.WEATHER)
        else:
            skipped_layers.append(LayerName.WEATHER)

        # ALWAYS include IMAGE layer - it runs pre-classification checks (face/selfie detection)
        # for ALL hazard types, even if CNN model doesn't apply to this hazard type.
        # The vision_service handles CNN skip logic internally.
        active_layers.append(LayerName.IMAGE)

        # Calculate adjusted weights
        weights = self._redistribute_weights(active_layers, skipped_layers)

        # Run Layer 1: Geofence (blocking)
        geofence_result = await self._run_geofence_layer(
            report.location.latitude,
            report.location.longitude
        )
        geofence_result.weight = weights[LayerName.GEOFENCE]

        # If geofence fails, return immediately
        if geofence_result.status == LayerStatus.FAIL:
            processing_time = int((time.time() - start_time) * 1000)

            return VerificationResult(
                verification_id=verification_id,
                report_id=report.report_id,
                composite_score=0.0,
                decision=VerificationDecision.AUTO_REJECTED,
                decision_reason=f"Location outside valid coastal area. {geofence_result.reasoning}",
                layer_results=[geofence_result],
                weights_used={k.value: v for k, v in weights.items()},
                applicable_layers=active_layers,
                skipped_layers=skipped_layers,
                processing_time_ms=processing_time,
                verified_at=datetime.now(timezone.utc)
            )

        # Run remaining layers in parallel
        layer_tasks = []

        # Weather layer
        layer_tasks.append(self._run_weather_layer(report, hazard_type))

        # Text layer
        description = report.description or ""
        layer_tasks.append(self._run_text_layer(description, hazard_type))

        # Image layer
        if image_path:
            layer_tasks.append(self._run_image_layer(image_path, hazard_type))
        else:
            # Create skipped result for image layer if no image provided
            async def skip_image():
                return LayerResult(
                    layer_name=LayerName.IMAGE,
                    status=LayerStatus.SKIPPED,
                    score=1.0,
                    confidence=1.0,
                    weight=weights.get(LayerName.IMAGE, 0),
                    reasoning="No image provided for classification",
                    data={"reason": "no_image"},
                    processed_at=datetime.now(timezone.utc)
                )
            layer_tasks.append(skip_image())

        # Reporter layer
        if db is not None:
            layer_tasks.append(self._run_reporter_layer(report.user_id, db))
        else:
            async def default_reporter():
                return LayerResult(
                    layer_name=LayerName.REPORTER,
                    status=LayerStatus.PASS,
                    score=0.5,
                    confidence=0.5,
                    weight=weights.get(LayerName.REPORTER, 0.10),
                    reasoning="Database not available - assigned default credibility",
                    data={"reason": "no_database"},
                    processed_at=datetime.now(timezone.utc)
                )
            layer_tasks.append(default_reporter())

        # Execute all layers in parallel
        layer_results = await asyncio.gather(*layer_tasks)

        # Update weights in results
        all_results = [geofence_result] + list(layer_results)
        for result in all_results:
            if result.layer_name in weights:
                result.weight = weights[result.layer_name]

        # Calculate composite score
        composite_score = self._calculate_composite_score(all_results, weights)

        # Update user trust score based on AI layer results (text and image)
        if db is not None and report.user_id:
            await self.update_user_trust_from_ai_layers(
                user_id=report.user_id,
                layer_results=all_results,
                db=db
            )

        # Determine decision (now with enhanced rejection rules)
        decision, reason = self._determine_decision(composite_score, geofence_result, all_results)

        processing_time = int((time.time() - start_time) * 1000)

        # Simplified: Only manual review requires human confirmation
        ai_recommendation = self._get_ai_recommendation(composite_score, decision)
        requires_confirmation = decision == VerificationDecision.MANUAL_REVIEW

        logger.info(
            f"Verification complete for {report.report_id}: "
            f"score={composite_score:.1f}%, decision={decision.value}, "
            f"time={processing_time}ms"
        )

        return VerificationResult(
            verification_id=verification_id,
            report_id=report.report_id,
            composite_score=composite_score,
            decision=decision,
            decision_reason=reason,
            layer_results=all_results,
            weights_used={k.value: v for k, v in weights.items()},
            applicable_layers=active_layers,
            skipped_layers=skipped_layers,
            processing_time_ms=processing_time,
            verified_at=datetime.now(timezone.utc),
            # V2 fields
            ai_recommendation=ai_recommendation,
            requires_authority_confirmation=requires_confirmation,
            authority_confirmation=None
        )

    def _get_ai_recommendation(
        self,
        composite_score: float,
        decision: VerificationDecision
    ) -> str:
        """
        Get AI recommendation string based on score and decision (simplified).

        Args:
            composite_score: Composite score (0-100)
            decision: The verification decision

        Returns:
            AI recommendation string (approve, review, reject)
        """
        if decision == VerificationDecision.AUTO_REJECTED:
            return AIRecommendation.REJECT.value
        elif composite_score >= self.AUTO_APPROVE_THRESHOLD:
            return AIRecommendation.APPROVE.value
        elif composite_score >= self.MANUAL_REVIEW_THRESHOLD:
            return AIRecommendation.REVIEW.value
        else:
            return AIRecommendation.REJECT.value

    async def update_user_trust_from_ai_layers(
        self,
        user_id: str,
        layer_results: List[LayerResult],
        db: AsyncIOMotorDatabase
    ) -> Optional[int]:
        """
        Update user's trust score based on AI layer results (text and image).

        Uses asymptotic formula for gradual trust changes:
        - Text pass/fail: α=0.025 (low impact)
        - Image pass/fail: α=0.05 (moderate impact)

        Args:
            user_id: ID of the user who submitted the report
            layer_results: Results from all verification layers
            db: Database connection

        Returns:
            New trust score if updated, None if failed
        """
        if db is None:
            logger.warning("Cannot update trust: no database connection")
            return None

        try:
            # Get current user
            user = await db.users.find_one({"user_id": user_id})
            if not user:
                logger.warning(f"Cannot update trust: user {user_id} not found")
                return None

            current_score = user.get("credibility_score", 50)
            new_score = current_score

            # Process text layer result
            for result in layer_results:
                if result.layer_name == LayerName.TEXT and result.status != LayerStatus.SKIPPED:
                    text_passed = result.status == LayerStatus.PASS and result.score >= 0.5
                    event_type = TrustEventType.AI_TEXT_PASS if text_passed else TrustEventType.AI_TEXT_FAIL
                    new_score = calculate_trust_score(new_score, event_type)
                    logger.debug(f"Text layer {'pass' if text_passed else 'fail'}: trust {current_score} -> {new_score}")

                elif result.layer_name == LayerName.IMAGE and result.status != LayerStatus.SKIPPED:
                    image_passed = result.status == LayerStatus.PASS and result.score >= 0.5
                    event_type = TrustEventType.AI_IMAGE_PASS if image_passed else TrustEventType.AI_IMAGE_FAIL
                    new_score = calculate_trust_score(new_score, event_type)
                    logger.debug(f"Image layer {'pass' if image_passed else 'fail'}: trust -> {new_score}")

            # Update in database if changed
            if int(new_score) != current_score:
                await db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"credibility_score": int(new_score)}}
                )
                logger.info(f"Updated trust for user {user_id}: {current_score} -> {int(new_score)}")

            return int(new_score)

        except Exception as e:
            logger.error(f"Error updating user trust: {e}")
            return None

    async def create_audit(
        self,
        verification_result: VerificationResult
    ) -> VerificationAudit:
        """
        Create an audit record for a verification.

        Args:
            verification_result: The verification result to audit

        Returns:
            VerificationAudit record
        """
        return VerificationAudit(
            audit_id=f"AUD_{uuid.uuid4().hex[:12].upper()}",
            verification_id=verification_result.verification_id,
            report_id=verification_result.report_id,
            original_decision=verification_result.decision,
            original_score=verification_result.composite_score,
            layer_results=verification_result.layer_results,
            was_overridden=False,
            created_at=datetime.now(timezone.utc)
        )


# Singleton instance
_verification_service: Optional[VerificationService] = None


def get_verification_service(db: Optional[AsyncIOMotorDatabase] = None) -> VerificationService:
    """Get or create verification service singleton."""
    global _verification_service
    if _verification_service is None:
        _verification_service = VerificationService(db)
    return _verification_service


async def initialize_verification_service(db: AsyncIOMotorDatabase) -> VerificationService:
    """Initialize verification service."""
    service = get_verification_service(db)
    await service.initialize()
    return service
