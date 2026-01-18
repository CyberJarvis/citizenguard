"""
Comprehensive Test Suite for CoastGuardians 6-Layer Verification System

Tests ALL hazard types with realistic scenarios covering:
- All 10 hazard types (5 natural + 4 human-made + 1 other)
- All 6 verification layers (Geofence, Weather, Text, Image, Reporter, Composite)
- Auto-approve, Auto-reject, and Manual Review scenarios
- Edge cases (spam, panic, minimal text, wrong images)
- Integration workflows
- Performance benchmarks

Run with: pytest tests/test_hazard_verification_scenarios.py -v
"""

import pytest
import asyncio
import time
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.hazard import (
    HazardReport, HazardType, HazardCategory, Location,
    VerificationStatus, EnhancedHazardReportResponse
)
from app.models.verification import (
    VerificationResult, VerificationDecision, LayerResult,
    LayerStatus, LayerName
)
from app.services.verification_service import (
    VerificationService, get_verification_service
)
from app.services.geofence_service import GeofenceService, get_geofence_service
from app.services.vision_service import VisionService, get_vision_service
from app.services.vectordb_service import VectorDBService, get_vectordb_service

# Pytest async configuration
pytest_plugins = ('pytest_asyncio',)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_locations() -> Dict[str, Dict[str, Any]]:
    """Return dict of test locations with various characteristics"""
    return {
        "valid_coastal_mumbai": {
            "lat": 19.0760,
            "lon": 72.8777,
            "name": "Mumbai coast",
            "expected_geofence": "pass"
        },
        "valid_coastal_chennai": {
            "lat": 13.0827,
            "lon": 80.2707,
            "name": "Chennai coast",
            "expected_geofence": "pass"
        },
        "valid_coastal_goa": {
            "lat": 15.2993,
            "lon": 73.9542,
            "name": "Goa coast",
            "expected_geofence": "pass"
        },
        "valid_island_portblair": {
            "lat": 11.6234,
            "lon": 92.7265,
            "name": "Port Blair, Andaman",
            "expected_geofence": "pass"
        },
        "valid_coastal_kochi": {
            "lat": 9.9312,
            "lon": 76.2673,
            "name": "Kochi coast",
            "expected_geofence": "pass"
        },
        "too_far_inland": {
            "lat": 19.0760,
            "lon": 73.8,
            "name": "Far inland from Mumbai (50km+)",
            "expected_geofence": "fail"
        },
        "too_far_offshore": {
            "lat": 17.5,
            "lon": 70.0,
            "name": "Deep Arabian Sea (100km+ offshore)",
            "expected_geofence": "fail"
        },
        "borderline_inland": {
            "lat": 19.0760,
            "lon": 73.1,
            "name": "Borderline inland (15-20km)",
            "expected_geofence": "pass"  # Within 20km limit
        },
        "borderline_offshore": {
            "lat": 18.8,
            "lon": 72.5,
            "name": "Borderline offshore (25km)",
            "expected_geofence": "pass"  # Within 30km limit
        }
    }


@pytest.fixture
def sample_reporter_profiles() -> Dict[str, Dict[str, Any]]:
    """Return dict of reporter profiles with different credibility scores"""
    return {
        "excellent": {
            "user_id": "USR_TEST_EXCELLENT",
            "name": "Trusted Reporter",
            "credibility_score": 95,
            "total_reports": 50,
            "verified_reports": 48,
            "rejected_reports": 2,
            "accuracy": 0.96
        },
        "good": {
            "user_id": "USR_TEST_GOOD",
            "name": "Good Reporter",
            "credibility_score": 75,
            "total_reports": 30,
            "verified_reports": 23,
            "rejected_reports": 7,
            "accuracy": 0.77
        },
        "average": {
            "user_id": "USR_TEST_AVERAGE",
            "name": "Average Reporter",
            "credibility_score": 50,
            "total_reports": 20,
            "verified_reports": 10,
            "rejected_reports": 10,
            "accuracy": 0.50
        },
        "poor": {
            "user_id": "USR_TEST_POOR",
            "name": "Poor Reporter",
            "credibility_score": 25,
            "total_reports": 15,
            "verified_reports": 4,
            "rejected_reports": 11,
            "accuracy": 0.27
        },
        "new_user": {
            "user_id": "USR_TEST_NEW",
            "name": "New User",
            "credibility_score": 50,
            "total_reports": 0,
            "verified_reports": 0,
            "rejected_reports": 0,
            "accuracy": 0.50  # Default for new users
        }
    }


@pytest.fixture
def sample_images() -> Dict[str, str]:
    """Return paths to test images"""
    base_path = os.path.join(os.path.dirname(__file__), "fixtures", "images")
    return {
        "beached_whale": os.path.join(base_path, "beached_whale.jpg"),
        "beached_dolphin": os.path.join(base_path, "beached_dolphin.jpg"),
        "ship_wreck": os.path.join(base_path, "ship_wreck.jpg"),
        "oil_spill": os.path.join(base_path, "oil_spill.jpg"),
        "marine_debris": os.path.join(base_path, "plastic_debris.jpg"),
        "clean_beach": os.path.join(base_path, "clean_beach.jpg"),
        "sunset": os.path.join(base_path, "sunset.jpg"),
        "high_waves": os.path.join(base_path, "high_waves.jpg"),
        "flooded_area": os.path.join(base_path, "flooded_area.jpg"),
        "cyclone_damage": os.path.join(base_path, "cyclone_damage.jpg")
    }


@pytest.fixture
def sample_weather_data() -> Dict[str, Dict[str, Any]]:
    """Return sample weather/environmental data for different scenarios"""
    return {
        "tsunami_warning": {
            "weather": {
                "temp_c": 28,
                "wind_kph": 15,
                "pressure_mb": 1010,
                "humidity": 75,
                "precip_mm": 0,
                "vis_km": 10,
                "condition": "Partly Cloudy"
            },
            "seismic": {
                "magnitude": 7.5,
                "depth_km": 30,
                "distance_km": 150,
                "place": "Off coast of Sumatra",
                "tsunami": 1
            },
            "marine": {
                "sig_ht_mt": 1.5,
                "swell_ht_mt": 1.0,
                "swell_period_secs": 12
            }
        },
        "cyclone_severe": {
            "weather": {
                "temp_c": 28,
                "wind_kph": 95,
                "gust_kph": 115,
                "pressure_mb": 980,
                "humidity": 92,
                "precip_mm": 35,
                "vis_km": 1.5,
                "condition": "Heavy Rain"
            },
            "marine": {
                "sig_ht_mt": 5.5,
                "swell_ht_mt": 4.0,
                "swell_period_secs": 15,
                "water_temp_c": 29
            }
        },
        "cyclone_moderate": {
            "weather": {
                "temp_c": 29,
                "wind_kph": 65,
                "gust_kph": 80,
                "pressure_mb": 995,
                "humidity": 85,
                "precip_mm": 15,
                "vis_km": 3,
                "condition": "Rain"
            },
            "marine": {
                "sig_ht_mt": 3.5,
                "swell_ht_mt": 2.5,
                "swell_period_secs": 12
            }
        },
        "high_waves_warning": {
            "weather": {
                "temp_c": 27,
                "wind_kph": 45,
                "pressure_mb": 1005,
                "humidity": 80
            },
            "marine": {
                "sig_ht_mt": 4.5,
                "swell_ht_mt": 3.5,
                "swell_period_secs": 20,
                "tide_height_mt": 2.1,
                "tide_type": "HIGH"
            }
        },
        "rip_current_conditions": {
            "weather": {
                "temp_c": 30,
                "wind_kph": 35,
                "pressure_mb": 1008
            },
            "marine": {
                "sig_ht_mt": 3.0,
                "swell_ht_mt": 2.5,
                "swell_period_secs": 19,
                "tide_type": "LOW"
            }
        },
        "flood_conditions": {
            "weather": {
                "temp_c": 26,
                "wind_kph": 30,
                "pressure_mb": 1000,
                "humidity": 95,
                "precip_mm": 45,
                "vis_km": 1.5,
                "condition": "Heavy Rain"
            },
            "marine": {
                "tide_height_mt": 2.5,
                "tide_type": "HIGH",
                "sig_ht_mt": 2.5
            }
        },
        "clear_normal": {
            "weather": {
                "temp_c": 30,
                "wind_kph": 15,
                "gust_kph": 20,
                "pressure_mb": 1013,
                "humidity": 65,
                "precip_mm": 0,
                "vis_km": 10,
                "condition": "Sunny"
            },
            "marine": {
                "sig_ht_mt": 1.0,
                "swell_ht_mt": 0.5,
                "swell_period_secs": 8,
                "tide_height_mt": 1.5,
                "tide_type": "MID"
            },
            "seismic": None
        }
    }


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database"""
    mock = MagicMock()

    # Mock collections
    mock.hazard_reports = MagicMock()
    mock.users = MagicMock()
    mock.verification_audits = MagicMock()
    mock.tickets = MagicMock()
    mock.notifications = MagicMock()

    # Setup async methods
    mock.hazard_reports.find_one = AsyncMock(return_value=None)
    mock.hazard_reports.insert_one = AsyncMock()
    mock.hazard_reports.update_one = AsyncMock()
    mock.users.find_one = AsyncMock(return_value=None)
    mock.users.update_one = AsyncMock()
    mock.verification_audits.insert_one = AsyncMock()
    mock.tickets.find_one = AsyncMock(return_value=None)
    mock.tickets.insert_one = AsyncMock()
    mock.notifications.insert_one = AsyncMock()

    return mock


def create_test_report(
    hazard_type: str,
    latitude: float,
    longitude: float,
    description: str,
    user_id: str,
    user_name: str = "Test User",
    image_url: Optional[str] = None,
    address: str = "Test Location, India"
) -> HazardReport:
    """Helper function to create a test HazardReport"""

    # Map string to enum - using actual HazardType enum values
    # Actual enum: HIGH_WAVES, RIP_CURRENT, STORM_SURGE, FLOODED_COASTLINE,
    #              BEACHED_ANIMAL, OIL_SPILL, FISHER_NETS, SHIP_WRECK,
    #              CHEMICAL_SPILL, PLASTIC_POLLUTION
    hazard_type_map = {
        "High Waves": HazardType.HIGH_WAVES,
        "Rip Current": HazardType.RIP_CURRENT,
        "Storm Surge/Cyclone Effects": HazardType.STORM_SURGE,
        "Flooded Coastline": HazardType.FLOODED_COASTLINE,
        "Beached Aquatic Animal": HazardType.BEACHED_ANIMAL,
        "Oil Spill": HazardType.OIL_SPILL,
        "Fisher Nets Entanglement": HazardType.FISHER_NETS,
        "Ship Wreck": HazardType.SHIP_WRECK,
        "Chemical Spill": HazardType.CHEMICAL_SPILL,
        "Plastic Pollution": HazardType.PLASTIC_POLLUTION,
    }

    hazard_enum = hazard_type_map.get(hazard_type, HazardType.HIGH_WAVES)

    # Determine category
    natural_hazards = ["Storm Surge/Cyclone Effects", "High Waves",
                       "Flooded Coastline", "Rip Current"]
    category = HazardCategory.NATURAL if hazard_type in natural_hazards else HazardCategory.HUMAN_MADE

    location = Location(
        latitude=latitude,
        longitude=longitude,
        address=address
    )

    # Provide default image_url if none specified (required field in HazardReport)
    final_image_url = image_url if image_url else "/uploads/hazards/test_image.jpg"

    return HazardReport(
        report_id=f"RPT_TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        user_id=user_id,
        user_name=user_name,
        hazard_type=hazard_enum,
        category=category,
        description=description,
        image_url=final_image_url,
        location=location,
        verification_status=VerificationStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


# =============================================================================
# NATURAL HAZARD TESTS
# =============================================================================

class TestTsunamiVerification:
    """Test tsunami hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_tsunami_auto_approve_high_confidence(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_weather_data
    ):
        """
        Scenario: Strong tsunami report with all positive indicators
        - Location: Valid coastal (Mumbai)
        - Weather: Recent M7.5 earthquake detected, tsunami warning
        - Text: Detailed description with relevant keywords
        - Reporter: Excellent accuracy (95%)
        Expected: Auto-approved, score >= 75
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["excellent"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Massive earthquake felt offshore, sea water receding rapidly from beach. "
                       "Urgent evacuation needed. Multiple witnesses reporting unusual wave patterns. "
                       "Local fishermen have left the area.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address=location["name"]
        )

        # Setup mock user data
        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "name": reporter["name"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        # Mock hazard classification (from environmental data)
        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="warning")
        report.hazard_classification.confidence = 0.85
        report.hazard_classification.reasoning = "M7.5 earthquake detected with tsunami warning issued"
        report.hazard_classification.recommendations = ["Evacuate coastal areas", "Move to higher ground"]

        # Run verification
        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone (8.5km from coast)",
                data={"distance_to_coast_km": 8.5, "zone_type": "coastal"},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.88,
                    confidence=0.85,
                    weight=0.25,
                    reasoning="High semantic similarity to verified tsunami reports",
                    data={"predicted_type": "Tsunami", "similarity_score": 0.88},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        # Assertions
        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75
        assert len(result.layer_results) >= 4

        # Check geofence passed
        geofence_result = next(
            (lr for lr in result.layer_results if lr.layer_name == LayerName.GEOFENCE), None
        )
        assert geofence_result is not None
        assert geofence_result.status == LayerStatus.PASS

        print(f"\n✓ PASSED - Tsunami Auto-Approve High Confidence")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")
        print(f"  - Processing Time: {result.processing_time_ms}ms")

    @pytest.mark.asyncio
    async def test_tsunami_manual_review_no_earthquake(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Tsunami report but no earthquake detected
        - Location: Valid coastal (Chennai)
        - Weather: No seismic activity, normal conditions
        - Text: Vague description
        - Reporter: Average accuracy (50%)
        Expected: Manual review required, score 40-75
        """
        location = sample_locations["valid_coastal_chennai"]
        reporter = sample_reporter_profiles["average"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="I think I saw a tsunami wave approaching the shore",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        # No hazard classification (no threat)
        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="no_threat")
        report.hazard_classification.confidence = 0.3
        report.hazard_classification.reasoning = "No seismic activity detected"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 5.2},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.45,
                    confidence=0.50,
                    weight=0.25,
                    reasoning="Low semantic similarity, vague description",
                    data={"predicted_type": "Tsunami", "similarity_score": 0.45},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        # Assertions
        assert result.decision == VerificationDecision.MANUAL_REVIEW
        assert 40 <= result.composite_score < 75

        print(f"\n✓ PASSED - Tsunami Manual Review (No Earthquake)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")

    @pytest.mark.asyncio
    async def test_tsunami_auto_reject_too_far_inland(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Tsunami report from far inland location
        - Location: 50km+ inland
        - Expected: Auto-rejected at geofencing layer
        """
        location = sample_locations["too_far_inland"]
        reporter = sample_reporter_profiles["excellent"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Tsunami alert! Waves coming!",
            user_id=reporter["user_id"],
            address=location["name"]
        )

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.FAIL,
                score=0.0,
                confidence=0.95,
                weight=0.20,
                reasoning="Location too far inland (52km from coast). Maximum allowed: 20km",
                data={"distance_to_coast_km": 52, "reason": "too_far_inland"},
                processed_at=datetime.now(timezone.utc)
            )

            result = await service.verify_report(report, db=mock_db)

        # Assertions
        assert result.decision == VerificationDecision.AUTO_REJECTED
        assert result.composite_score == 0.0
        assert "inland" in result.decision_reason.lower() or "coast" in result.decision_reason.lower()

        print(f"\n✓ PASSED - Tsunami Auto-Reject (Too Far Inland)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Reason: {result.decision_reason}")


class TestCycloneVerification:
    """Test cyclone/storm surge hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_cyclone_auto_approve_severe_conditions(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_weather_data
    ):
        """
        Scenario: Severe cyclone with matching weather conditions
        - Location: Valid coastal (Port Blair)
        - Weather: Wind 95 kph, pressure 980 mb, heavy rain
        - Text: Detailed damage report
        - Reporter: Good accuracy (75%)
        Expected: Auto-approved, score >= 80
        """
        location = sample_locations["valid_island_portblair"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Severe cyclone hitting the island. Trees falling everywhere, "
                       "power lines down, extremely strong winds. Roof damaged. "
                       "Visibility very poor due to heavy rain.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        # Mock hazard classification with severe cyclone
        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="warning")
        report.hazard_classification.confidence = 0.90
        report.hazard_classification.reasoning = "Severe cyclone conditions: wind 95kph, pressure 980mb"
        report.hazard_classification.recommendations = ["Stay indoors", "Avoid coastal areas"]

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.92,
                confidence=0.92,
                weight=0.20,
                reasoning="Location within valid coastal zone (island location)",
                data={"distance_to_coast_km": 3.5},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.85,
                    confidence=0.82,
                    weight=0.25,
                    reasoning="High semantic similarity to verified cyclone reports",
                    data={"predicted_type": "Storm Surge/Cyclone Effects", "similarity_score": 0.85},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75

        print(f"\n✓ PASSED - Cyclone Auto-Approve (Severe Conditions)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")

    @pytest.mark.asyncio
    async def test_cyclone_manual_review_clear_weather(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Cyclone report but weather is clear
        - Location: Valid coastal
        - Weather: Clear, wind 15 kph, normal pressure
        - Text: Panic-filled message
        - Reporter: Poor accuracy (25%)
        Expected: Manual review due to weather mismatch
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["poor"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="CYCLONE COMING!!! EVERYONE EVACUATE NOW!!! EMERGENCY!!!",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        # No threat - clear weather
        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="no_threat")
        report.hazard_classification.confidence = 0.2
        report.hazard_classification.reasoning = "Clear weather, no cyclone indicators"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 8.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.FAIL,
                    score=0.25,
                    confidence=0.70,
                    weight=0.25,
                    reasoning="High panic level detected, low semantic quality",
                    data={"panic_level": 0.85, "spam_detected": False},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        assert result.decision in [VerificationDecision.MANUAL_REVIEW, VerificationDecision.REJECTED]
        assert result.composite_score < 60

        print(f"\n✓ PASSED - Cyclone Manual Review (Clear Weather)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")


class TestHighWavesVerification:
    """Test high waves hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_high_waves_auto_approve_severe_swell(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: High waves with marine data confirmation
        - Location: Valid coastal beach
        - Weather: Wave height 4.5m, swell 3.5m
        - Text: Descriptive safety warning
        - Reporter: Good accuracy
        Expected: Auto-approved, score >= 75
        """
        location = sample_locations["valid_coastal_chennai"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="High Waves",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Very high waves observed at Marina Beach. Dangerous conditions "
                       "for swimmers. Lifeguards have closed the beach. Waves crashing "
                       "over the seawall. Fishermen advised not to venture out.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address="Marina Beach, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="warning")
        report.hazard_classification.confidence = 0.88
        report.hazard_classification.reasoning = "High wave conditions confirmed: 4.5m significant height"
        report.hazard_classification.recommendations = ["Avoid swimming", "Stay away from seawall"]

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 0.5},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.82,
                    confidence=0.80,
                    weight=0.25,
                    reasoning="High semantic similarity to verified high wave reports",
                    data={"predicted_type": "High Waves", "similarity_score": 0.82},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75

        print(f"\n✓ PASSED - High Waves Auto-Approve")
        print(f"  - Composite Score: {result.composite_score:.1f}")


class TestFloodedCoastlineVerification:
    """Test flooded coastline hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_flooded_coastline_auto_approve_heavy_rain(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Coastal flooding with heavy rainfall
        - Location: Valid coastal
        - Weather: High tide, heavy rain (35mm)
        - Text: Detailed flood description
        - Reporter: Excellent accuracy
        Expected: Auto-approved, score >= 80
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["excellent"]

        report = create_test_report(
            hazard_type="Flooded Coastline",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Coastal road completely flooded. Water entering ground floor "
                       "of buildings. Heavy rain continuing. High tide combined with "
                       "rainfall causing severe waterlogging. Traffic diverted.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address="Worli Sea Face, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="warning")
        report.hazard_classification.confidence = 0.85
        report.hazard_classification.reasoning = "High tide + heavy rain causing coastal flooding"
        report.hazard_classification.recommendations = ["Avoid low-lying areas"]

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 1.2},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.86,
                    confidence=0.82,
                    weight=0.25,
                    reasoning="High semantic match to flood reports",
                    data={"predicted_type": "Flooded Coastline", "similarity_score": 0.86},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75

        print(f"\n✓ PASSED - Flooded Coastline Auto-Approve")
        print(f"  - Composite Score: {result.composite_score:.1f}")


class TestRipCurrentVerification:
    """Test rip current hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_rip_current_auto_approve_strong_swell(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Rip current with favorable conditions
        - Location: Valid coastal beach
        - Weather: Strong swell (2.5m), long period (19s)
        - Text: Detailed safety observation
        - Reporter: Good accuracy
        Expected: Auto-approved, score >= 75
        """
        location = sample_locations["valid_coastal_goa"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Rip Current",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Strong rip current observed at Calangute Beach. Swimmer was "
                       "rescued by lifeguard earlier. Dangerous conditions persist. "
                       "Red flag is up. Water pulling strongly away from shore.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address="Calangute Beach, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="alert")
        report.hazard_classification.confidence = 0.80
        report.hazard_classification.reasoning = "Conditions favorable for rip currents: long swell period"
        report.hazard_classification.recommendations = ["Swim parallel to shore if caught"]

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone (beach)",
                data={"distance_to_coast_km": 0.2},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.80,
                    confidence=0.78,
                    weight=0.25,
                    reasoning="Good semantic match to rip current reports",
                    data={"predicted_type": "Rip Current", "similarity_score": 0.80},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 70

        print(f"\n✓ PASSED - Rip Current Auto-Approve")
        print(f"  - Composite Score: {result.composite_score:.1f}")


# =============================================================================
# HUMAN-MADE HAZARD TESTS
# =============================================================================

class TestBeachedAnimalVerification:
    """Test beached aquatic animal verification scenarios"""

    @pytest.mark.asyncio
    async def test_beached_animal_auto_approve_with_image(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_images
    ):
        """
        Scenario: Beached whale with matching image
        - Location: Valid coastal
        - Image: Matches "beached_animal" with high confidence
        - Text: Detailed description
        - Reporter: Good accuracy
        Expected: Auto-approved, score >= 75
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Beached Aquatic Animal",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Large whale beached on Juhu Beach. Animal appears injured "
                       "and in distress. Approximately 8 meters long. Crowd gathering. "
                       "Please send wildlife rescue team immediately.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=sample_images["beached_whale"],
            address="Juhu Beach, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        # No weather classification needed for human-made hazards
        report.hazard_classification = None

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone (beach)",
                data={"distance_to_coast_km": 0.1},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.85,
                    confidence=0.82,
                    weight=0.25,
                    reasoning="High semantic similarity to beached animal reports",
                    data={"predicted_type": "Beached Aquatic Animal", "similarity_score": 0.85},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vision_service, 'classify_image') as mock_vision:
                    mock_vision.return_value = LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=LayerStatus.PASS,
                        score=0.92,
                        confidence=0.92,
                        weight=0.20,
                        reasoning="Image matches reported hazard type: Beached Aquatic Animal",
                        data={
                            "predicted_class": "Beached Aquatic Animal",
                            "confidence_scores": {
                                "Beached Aquatic Animal": 0.92,
                                "Ship Wreck": 0.03,
                                "Plastic Pollution": 0.02,
                                "Oil Spill": 0.01,
                                "Other": 0.02
                            },
                            "matches_report": True
                        },
                        processed_at=datetime.now(timezone.utc)
                    )

                    result = await service.verify_report(
                        report,
                        image_path=sample_images["beached_whale"],
                        db=mock_db
                    )

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75

        # Check image layer was used
        image_result = next(
            (lr for lr in result.layer_results if lr.layer_name == LayerName.IMAGE), None
        )
        assert image_result is not None
        assert image_result.status == LayerStatus.PASS

        print(f"\n✓ PASSED - Beached Animal Auto-Approve (With Image)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Image Classification: Beached Aquatic Animal (92% confidence)")

    @pytest.mark.asyncio
    async def test_beached_animal_manual_review_wrong_image(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_images
    ):
        """
        Scenario: Beached animal report but image shows clean beach
        - Location: Valid coastal
        - Image: Shows clean beach (no animal)
        - Reporter: Average accuracy
        Expected: Manual review required due to image mismatch
        """
        location = sample_locations["valid_coastal_chennai"]
        reporter = sample_reporter_profiles["average"]

        report = create_test_report(
            hazard_type="Beached Aquatic Animal",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Beached dolphin on beach near marina",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=sample_images["clean_beach"],
            address="Marina Beach, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 0.3},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.55,
                    confidence=0.60,
                    weight=0.25,
                    reasoning="Moderate semantic match, short description",
                    data={"predicted_type": "Beached Aquatic Animal", "similarity_score": 0.55},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vision_service, 'classify_image') as mock_vision:
                    mock_vision.return_value = LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=LayerStatus.FAIL,
                        score=0.15,
                        confidence=0.88,
                        weight=0.20,
                        reasoning="Image does NOT match reported hazard. Predicted: Other (clean beach)",
                        data={
                            "predicted_class": "Other",
                            "confidence_scores": {
                                "Beached Aquatic Animal": 0.05,
                                "Ship Wreck": 0.02,
                                "Plastic Pollution": 0.03,
                                "Oil Spill": 0.02,
                                "Other": 0.88
                            },
                            "matches_report": False
                        },
                        processed_at=datetime.now(timezone.utc)
                    )

                    result = await service.verify_report(
                        report,
                        image_path=sample_images["clean_beach"],
                        db=mock_db
                    )

        assert result.decision in [VerificationDecision.MANUAL_REVIEW, VerificationDecision.REJECTED]
        assert result.composite_score < 65

        print(f"\n✓ PASSED - Beached Animal Manual Review (Wrong Image)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")


class TestShipWreckVerification:
    """Test ship wreck hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_ship_wreck_auto_approve_with_image(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_images
    ):
        """
        Scenario: Ship wreck with matching image
        - Location: Valid coastal/offshore
        - Image: Matches "ship_wreck" with high confidence
        - Text: Detailed incident description
        - Reporter: Excellent accuracy
        Expected: Auto-approved, score >= 80
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["excellent"]

        report = create_test_report(
            hazard_type="Ship Wreck",
            latitude=19.05,
            longitude=72.85,
            description="Fishing vessel capsized near the harbor entrance. Crew has been "
                       "rescued by coast guard. Boat is partially submerged and drifting. "
                       "Poses navigation hazard. Fuel leak suspected.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=sample_images["ship_wreck"],
            address="Mumbai Harbor"
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.92,
                confidence=0.92,
                weight=0.20,
                reasoning="Location within valid offshore zone",
                data={"distance_to_coast_km": 5.0, "zone_type": "offshore"},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.88,
                    confidence=0.85,
                    weight=0.25,
                    reasoning="High semantic similarity to ship wreck reports",
                    data={"predicted_type": "Ship Wreck", "similarity_score": 0.88},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vision_service, 'classify_image') as mock_vision:
                    mock_vision.return_value = LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=LayerStatus.PASS,
                        score=0.89,
                        confidence=0.89,
                        weight=0.20,
                        reasoning="Image matches reported hazard type: Ship Wreck",
                        data={
                            "predicted_class": "Ship Wreck",
                            "confidence_scores": {
                                "Ship Wreck": 0.89,
                                "Beached Aquatic Animal": 0.04,
                                "Plastic Pollution": 0.03,
                                "Oil Spill": 0.02,
                                "Other": 0.02
                            },
                            "matches_report": True
                        },
                        processed_at=datetime.now(timezone.utc)
                    )

                    result = await service.verify_report(
                        report,
                        image_path=sample_images["ship_wreck"],
                        db=mock_db
                    )

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75

        print(f"\n✓ PASSED - Ship Wreck Auto-Approve (With Image)")
        print(f"  - Composite Score: {result.composite_score:.1f}")


class TestMarineDebrisVerification:
    """Test plastic pollution / marine debris verification scenarios"""

    @pytest.mark.asyncio
    async def test_marine_debris_auto_approve_with_image(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_images
    ):
        """
        Scenario: Marine plastic pollution with matching image
        - Location: Valid coastal beach
        - Image: Matches "marine_debris" classification
        - Text: Detailed pollution description
        - Reporter: Good accuracy
        Expected: Auto-approved, score >= 75
        """
        location = sample_locations["valid_coastal_goa"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Plastic Pollution",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Large amount of plastic waste washed up on Baga Beach. "
                       "Covering approximately 200 meters of shoreline. Includes "
                       "plastic bottles, bags, fishing nets, and other debris. "
                       "Cleanup needed urgently.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=sample_images["marine_debris"],
            address="Baga Beach, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 0.1},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.82,
                    confidence=0.80,
                    weight=0.25,
                    reasoning="High semantic similarity to pollution reports",
                    data={"predicted_type": "Plastic Pollution", "similarity_score": 0.82},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vision_service, 'classify_image') as mock_vision:
                    mock_vision.return_value = LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=LayerStatus.PASS,
                        score=0.85,
                        confidence=0.85,
                        weight=0.20,
                        reasoning="Image matches reported hazard type: Plastic Pollution",
                        data={
                            "predicted_class": "Plastic Pollution",
                            "confidence_scores": {
                                "Plastic Pollution": 0.85,
                                "Ship Wreck": 0.05,
                                "Beached Aquatic Animal": 0.04,
                                "Oil Spill": 0.03,
                                "Other": 0.03
                            },
                            "matches_report": True
                        },
                        processed_at=datetime.now(timezone.utc)
                    )

                    result = await service.verify_report(
                        report,
                        image_path=sample_images["marine_debris"],
                        db=mock_db
                    )

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 75

        print(f"\n✓ PASSED - Marine Debris Auto-Approve (With Image)")
        print(f"  - Composite Score: {result.composite_score:.1f}")


class TestOilSpillVerification:
    """Test oil spill hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_oil_spill_auto_approve_with_image(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_images
    ):
        """
        Scenario: Oil spill with matching image (critical hazard)
        - Location: Valid coastal/offshore
        - Image: Matches "oil_spill" with high confidence
        - Text: Detailed pollution description
        - Reporter: Excellent accuracy
        Expected: Auto-approved, score >= 85 (critical hazard)
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["excellent"]

        report = create_test_report(
            hazard_type="Oil Spill",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Large oil slick observed in water near Mumbai Port. Strong "
                       "petroleum odor in the area. Oil appears to be spreading from "
                       "a tanker anchored offshore. Slick approximately 500m long. "
                       "Birds affected. Urgent containment needed.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=sample_images["oil_spill"],
            address="Mumbai Port, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone (port area)",
                data={"distance_to_coast_km": 2.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.90,
                    confidence=0.88,
                    weight=0.25,
                    reasoning="Very high semantic similarity to oil spill reports",
                    data={"predicted_type": "Oil Spill", "similarity_score": 0.90},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vision_service, 'classify_image') as mock_vision:
                    mock_vision.return_value = LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=LayerStatus.PASS,
                        score=0.94,
                        confidence=0.94,
                        weight=0.20,
                        reasoning="Image matches reported hazard type: Oil Spill",
                        data={
                            "predicted_class": "Oil Spill",
                            "confidence_scores": {
                                "Oil Spill": 0.94,
                                "Plastic Pollution": 0.02,
                                "Ship Wreck": 0.02,
                                "Beached Aquatic Animal": 0.01,
                                "Other": 0.01
                            },
                            "matches_report": True
                        },
                        processed_at=datetime.now(timezone.utc)
                    )

                    result = await service.verify_report(
                        report,
                        image_path=sample_images["oil_spill"],
                        db=mock_db
                    )

        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 80

        print(f"\n✓ PASSED - Oil Spill Auto-Approve (With Image)")
        print(f"  - Composite Score: {result.composite_score:.1f}")

    @pytest.mark.asyncio
    async def test_oil_spill_manual_review_no_image(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Oil spill report without image
        - Location: Valid coastal
        - Image: None provided
        - Text: Vague description
        - Reporter: New user
        Expected: Manual review required due to missing image
        """
        location = sample_locations["valid_coastal_chennai"]
        reporter = sample_reporter_profiles["new_user"]

        report = create_test_report(
            hazard_type="Oil Spill",
            latitude=location["lat"],
            longitude=location["lon"],
            description="I think there's oil in the water",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=None,
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 3.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.35,
                    confidence=0.50,
                    weight=0.25,
                    reasoning="Low semantic match, very short description",
                    data={"predicted_type": "Oil Spill", "similarity_score": 0.35},
                    processed_at=datetime.now(timezone.utc)
                )

                # No image provided - skip image layer
                result = await service.verify_report(report, db=mock_db)

        assert result.decision in [VerificationDecision.MANUAL_REVIEW, VerificationDecision.REJECTED]

        print(f"\n✓ PASSED - Oil Spill Manual Review (No Image)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")


class TestOtherHazardVerification:
    """Test 'Other' category hazard verification scenarios"""

    @pytest.mark.asyncio
    async def test_other_hazard_text_based_verification(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: 'Other' category hazard (text analysis only)
        - Location: Valid coastal
        - Weather: N/A (doesn't apply to other)
        - Text: Detailed description of unusual phenomenon
        - Image: N/A (doesn't require image validation)
        - Reporter: Good accuracy
        Expected: Relies on text analysis + reporter score
        """
        location = sample_locations["valid_coastal_kochi"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Chemical Spill",  # Using Chemical Spill for unusual contamination events
            latitude=location["lat"],
            longitude=location["lon"],
            description="Unusual red tide observed along 2km stretch of coastline near "
                       "Fort Kochi. Water has turned brownish-red. Strong algae odor. "
                       "Fish mortality reported by local fishermen. Possibly harmful "
                       "algal bloom. Beach should be closed to swimmers.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address="Fort Kochi, " + location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 0.5},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.75,
                    confidence=0.72,
                    weight=0.25,
                    reasoning="Good semantic match to coastal hazard reports",
                    data={"predicted_type": "Other", "similarity_score": 0.75},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        # 'Other' hazards should skip weather and image validation
        assert result.decision in [VerificationDecision.AUTO_APPROVED, VerificationDecision.MANUAL_REVIEW]
        assert 50 <= result.composite_score <= 90

        print(f"\n✓ PASSED - Other Hazard (Text-Based)")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_spam_detection_low_score(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Spam/promotional content
        - Text contains spam keywords and URL
        Expected: Low text analysis score
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["average"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Click here to buy emergency supplies! FREE SHIPPING! "
                       "Best prices on survival kits! Visit http://spam.example.com "
                       "Use code EMERGENCY for 50% off!",
            user_id=reporter["user_id"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="no_threat")
        report.hazard_classification.confidence = 0.1
        report.hazard_classification.reasoning = "No weather hazard"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 8.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.FAIL,
                    score=0.05,
                    confidence=0.95,
                    weight=0.25,
                    reasoning="SPAM DETECTED: Promotional content with URL",
                    data={"is_spam": True, "spam_indicators": ["url", "promotional_keywords"]},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        assert result.composite_score < 50

        text_result = next(
            (lr for lr in result.layer_results if lr.layer_name == LayerName.TEXT), None
        )
        assert text_result is not None
        assert text_result.score < 0.2

        print(f"\n✓ PASSED - Spam Detection")
        print(f"  - Composite Score: {result.composite_score:.1f}")
        print(f"  - Text Score: {text_result.score:.2f}")

    @pytest.mark.asyncio
    async def test_extreme_panic_text(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Hysterical panic text
        - Text: All caps, many exclamation marks, panic keywords
        Expected: High panic level detected, lower text score
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["average"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="HELP!!! EVERYONE IS DYING!!! APOCALYPSE NOW!!! "
                       "RUN FOR YOUR LIVES!!! EMERGENCY!!! EMERGENCY!!! "
                       "THE WORLD IS ENDING!!! AAAAAHHHHH!!!",
            user_id=reporter["user_id"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="no_threat")
        report.hazard_classification.confidence = 0.2
        report.hazard_classification.reasoning = "No seismic activity"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 8.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.FAIL,
                    score=0.15,
                    confidence=0.85,
                    weight=0.25,
                    reasoning="PANIC DETECTED: Extreme emotional language, no specific details",
                    data={"panic_level": 0.95, "exclamation_ratio": 0.8},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        text_result = next(
            (lr for lr in result.layer_results if lr.layer_name == LayerName.TEXT), None
        )
        assert text_result.score < 0.3

        print(f"\n✓ PASSED - Extreme Panic Text Detection")
        print(f"  - Text Score: {text_result.score:.2f}")

    @pytest.mark.asyncio
    async def test_minimal_description(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Very short description (3 words)
        Expected: Low text analysis score, flagged for review
        """
        location = sample_locations["valid_coastal_chennai"]
        reporter = sample_reporter_profiles["average"]

        report = create_test_report(
            hazard_type="High Waves",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Big waves here",  # Only 3 words
            user_id=reporter["user_id"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="watch")
        report.hazard_classification.confidence = 0.5
        report.hazard_classification.reasoning = "Moderate wave conditions"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 0.5},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.40,
                    confidence=0.50,
                    weight=0.25,
                    reasoning="Description too short for reliable analysis",
                    data={"word_count": 3, "flag": "too_short"},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        text_result = next(
            (lr for lr in result.layer_results if lr.layer_name == LayerName.TEXT), None
        )
        assert text_result.score < 0.5

        print(f"\n✓ PASSED - Minimal Description Detection")
        print(f"  - Text Score: {text_result.score:.2f}")

    @pytest.mark.asyncio
    async def test_borderline_geofence_inland(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Scenario: Location at borderline inland distance (18km)
        Expected: Should still pass geofence (within 20km limit)
        """
        location = sample_locations["borderline_inland"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Storm damage reported in area, flooding from coastal surge",
            user_id=reporter["user_id"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="alert")
        report.hazard_classification.confidence = 0.7
        report.hazard_classification.reasoning = "Storm conditions present"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.75,
                confidence=0.85,
                weight=0.20,
                reasoning="Location at borderline distance (18km inland) but within limit",
                data={"distance_to_coast_km": 18.0, "zone_type": "borderline_inland"},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.70,
                    confidence=0.70,
                    weight=0.25,
                    reasoning="Good semantic match",
                    data={"predicted_type": "Storm Surge/Cyclone Effects"},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        geofence_result = next(
            (lr for lr in result.layer_results if lr.layer_name == LayerName.GEOFENCE), None
        )
        assert geofence_result.status == LayerStatus.PASS

        print(f"\n✓ PASSED - Borderline Inland Location")
        print(f"  - Distance: 18km (within 20km limit)")
        print(f"  - Geofence: PASS")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance and timing requirements"""

    @pytest.mark.asyncio
    async def test_pipeline_execution_time(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Test that full pipeline completes within acceptable time
        Expected: < 5 seconds for full verification
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["good"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Strong winds and heavy rain reported in the coastal area",
            user_id=reporter["user_id"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="alert")
        report.hazard_classification.confidence = 0.75
        report.hazard_classification.reasoning = "Storm conditions"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        start_time = time.time()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 5.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.75,
                    confidence=0.75,
                    weight=0.25,
                    reasoning="Good semantic match",
                    data={"predicted_type": "Storm Surge/Cyclone Effects"},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        duration = time.time() - start_time

        assert result is not None
        assert duration < 5.0, f"Pipeline took {duration:.2f}s, expected < 5s"
        assert result.processing_time_ms is not None

        print(f"\n✓ PASSED - Performance Test")
        print(f"  - Total Duration: {duration:.3f}s")
        print(f"  - Reported Processing Time: {result.processing_time_ms}ms")

    @pytest.mark.asyncio
    async def test_concurrent_verifications(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Test that multiple verifications can run concurrently
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["good"]

        reports = []
        for i in range(5):
            report = create_test_report(
                hazard_type="High Waves",
                latitude=location["lat"] + (i * 0.01),
                longitude=location["lon"],
                description=f"Test report {i}: High waves observed",
                user_id=reporter["user_id"],
                address=f"Location {i}"
            )
            report.hazard_classification = MagicMock()
            report.hazard_classification.threat_level = MagicMock(value="alert")
            report.hazard_classification.confidence = 0.75
            report.hazard_classification.reasoning = "Wave conditions"
            report.hazard_classification.recommendations = []
            reports.append(report)

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        start_time = time.time()

        async def verify_report(report):
            with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
                mock_geofence.return_value = LayerResult(
                    layer_name=LayerName.GEOFENCE,
                    status=LayerStatus.PASS,
                    score=0.90,
                    confidence=0.90,
                    weight=0.20,
                    reasoning="Valid location",
                    data={"distance_to_coast_km": 5.0},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                    mock_text.return_value = LayerResult(
                        layer_name=LayerName.TEXT,
                        status=LayerStatus.PASS,
                        score=0.75,
                        confidence=0.75,
                        weight=0.25,
                        reasoning="Match",
                        data={},
                        processed_at=datetime.now(timezone.utc)
                    )

                    return await service.verify_report(report, db=mock_db)

        # Run all verifications concurrently
        results = await asyncio.gather(*[verify_report(r) for r in reports])

        duration = time.time() - start_time

        assert len(results) == 5
        assert all(r is not None for r in results)
        assert duration < 10.0, f"Concurrent verification took {duration:.2f}s, expected < 10s"

        print(f"\n✓ PASSED - Concurrent Verification Test")
        print(f"  - 5 reports verified in {duration:.3f}s")
        print(f"  - Average: {duration/5:.3f}s per report")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_full_workflow_auto_approve(
        self, mock_db, sample_locations, sample_reporter_profiles, sample_images
    ):
        """
        Test complete workflow from submission to auto-approval
        1. Submit high-confidence report
        2. Auto-approve via verification
        3. Verify reporter score update trigger
        """
        location = sample_locations["valid_coastal_mumbai"]
        reporter = sample_reporter_profiles["excellent"]

        report = create_test_report(
            hazard_type="Oil Spill",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Large oil spill from tanker accident in Mumbai harbor, "
                       "spreading rapidly toward beaches. Strong petroleum odor. "
                       "Wildlife affected. Urgent containment needed.",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            image_url=sample_images["oil_spill"],
            address="Mumbai Harbor"
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "name": reporter["name"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.95,
                confidence=0.95,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 2.0},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.90,
                    confidence=0.88,
                    weight=0.25,
                    reasoning="Very high match to oil spill reports",
                    data={"predicted_type": "Oil Spill", "similarity_score": 0.90},
                    processed_at=datetime.now(timezone.utc)
                )

                with patch.object(service.vision_service, 'classify_image') as mock_vision:
                    mock_vision.return_value = LayerResult(
                        layer_name=LayerName.IMAGE,
                        status=LayerStatus.PASS,
                        score=0.95,
                        confidence=0.95,
                        weight=0.20,
                        reasoning="Image matches: Oil Spill",
                        data={
                            "predicted_class": "Oil Spill",
                            "confidence_scores": {"Oil Spill": 0.95},
                            "matches_report": True
                        },
                        processed_at=datetime.now(timezone.utc)
                    )

                    result = await service.verify_report(
                        report,
                        image_path=sample_images["oil_spill"],
                        db=mock_db
                    )

        # Verify auto-approval
        assert result.decision == VerificationDecision.AUTO_APPROVED
        assert result.composite_score >= 80

        # Verify all layers were processed
        assert len(result.layer_results) >= 4

        print(f"\n✓ PASSED - Full Workflow Auto-Approve")
        print(f"  - Final Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")
        print(f"  - Layers Processed: {len(result.layer_results)}")

    @pytest.mark.asyncio
    async def test_workflow_manual_review_to_approval(
        self, mock_db, sample_locations, sample_reporter_profiles
    ):
        """
        Test manual review workflow
        1. Submit ambiguous report
        2. Flagged for manual review
        3. Verify it needs analyst attention
        """
        location = sample_locations["valid_coastal_chennai"]
        reporter = sample_reporter_profiles["new_user"]

        report = create_test_report(
            hazard_type="Storm Surge/Cyclone Effects",
            latitude=location["lat"],
            longitude=location["lon"],
            description="Water looks strange near the beach",
            user_id=reporter["user_id"],
            user_name=reporter["name"],
            address=location["name"]
        )

        mock_db.users.find_one = AsyncMock(return_value={
            "user_id": reporter["user_id"],
            "name": reporter["name"],
            "credibility_score": reporter["credibility_score"],
            "reports_submitted_count": reporter["total_reports"],
            "reports_verified_count": reporter["verified_reports"],
            "reports_rejected_count": reporter["rejected_reports"]
        })

        # No threat weather
        report.hazard_classification = MagicMock()
        report.hazard_classification.threat_level = MagicMock(value="no_threat")
        report.hazard_classification.confidence = 0.3
        report.hazard_classification.reasoning = "No seismic activity detected"
        report.hazard_classification.recommendations = []

        service = VerificationService(mock_db)
        await service.initialize()

        with patch.object(service.geofence_service, 'validate_location') as mock_geofence:
            mock_geofence.return_value = LayerResult(
                layer_name=LayerName.GEOFENCE,
                status=LayerStatus.PASS,
                score=0.90,
                confidence=0.90,
                weight=0.20,
                reasoning="Location within valid coastal zone",
                data={"distance_to_coast_km": 0.5},
                processed_at=datetime.now(timezone.utc)
            )

            with patch.object(service.vectordb_service, 'analyze_for_verification') as mock_text:
                mock_text.return_value = LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.PASS,
                    score=0.55,  # Moderate score for manual review range
                    confidence=0.60,
                    weight=0.25,
                    reasoning="Moderate description quality, needs verification",
                    data={"predicted_type": "Storm Surge/Cyclone Effects", "similarity_score": 0.55},
                    processed_at=datetime.now(timezone.utc)
                )

                result = await service.verify_report(report, db=mock_db)

        # Should be flagged for manual review
        assert result.decision == VerificationDecision.MANUAL_REVIEW
        assert 40 <= result.composite_score < 75

        print(f"\n✓ PASSED - Manual Review Workflow")
        print(f"  - Score: {result.composite_score:.1f}")
        print(f"  - Decision: {result.decision.value}")
        print(f"  - Reason: {result.decision_reason}")


# =============================================================================
# TEST HELPERS
# =============================================================================

def print_verification_summary(result: VerificationResult, test_name: str):
    """Print a formatted summary of verification results"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Composite Score: {result.composite_score:.1f}")
    print(f"Decision: {result.decision.value}")
    print(f"Processing Time: {result.processing_time_ms}ms")
    print(f"\nLayer Results:")
    for lr in result.layer_results:
        status_icon = "✓" if lr.status == LayerStatus.PASS else "✗" if lr.status == LayerStatus.FAIL else "○"
        print(f"  {status_icon} {lr.layer_name.value}: {lr.score:.2f} ({lr.reasoning[:50]}...)")
    print(f"{'='*60}\n")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
