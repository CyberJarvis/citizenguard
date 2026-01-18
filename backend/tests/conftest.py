"""
CoastGuardians Test Configuration
Shared fixtures and test setup for the verification system tests.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Generator
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import io
from PIL import Image

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "hazard_type(name): marks test for specific hazard type")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client for caching."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    return redis


# =============================================================================
# LOCATION FIXTURES
# =============================================================================

@pytest.fixture
def coastal_locations() -> Dict[str, Dict[str, Any]]:
    """Valid coastal locations within India's EEZ."""
    return {
        "mumbai_coast": {
            "latitude": 18.9388,
            "longitude": 72.8354,
            "name": "Mumbai Coast",
            "state": "Maharashtra"
        },
        "chennai_marina": {
            "latitude": 13.0499,
            "longitude": 80.2824,
            "name": "Chennai Marina Beach",
            "state": "Tamil Nadu"
        },
        "goa_beach": {
            "latitude": 15.2993,
            "longitude": 73.8278,
            "name": "Calangute Beach, Goa",
            "state": "Goa"
        },
        "kerala_coast": {
            "latitude": 8.8932,
            "longitude": 76.6141,
            "name": "Kovalam Beach, Kerala",
            "state": "Kerala"
        },
        "andaman_port_blair": {
            "latitude": 11.6234,
            "longitude": 92.7265,
            "name": "Port Blair, Andaman",
            "territory": "Andaman and Nicobar"
        },
        "vishakhapatnam": {
            "latitude": 17.6868,
            "longitude": 83.2185,
            "name": "Vishakhapatnam Coast",
            "state": "Andhra Pradesh"
        },
        "sundarbans": {
            "latitude": 21.9497,
            "longitude": 88.8950,
            "name": "Sundarbans Delta",
            "state": "West Bengal"
        },
        "lakshadweep": {
            "latitude": 10.5669,
            "longitude": 72.6411,
            "name": "Kavaratti, Lakshadweep",
            "territory": "Lakshadweep"
        }
    }


@pytest.fixture
def inland_locations() -> Dict[str, Dict[str, Any]]:
    """Invalid inland locations (outside coastal zone)."""
    return {
        "delhi": {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "name": "New Delhi",
            "state": "Delhi"
        },
        "jaipur": {
            "latitude": 26.9124,
            "longitude": 75.7873,
            "name": "Jaipur",
            "state": "Rajasthan"
        },
        "lucknow": {
            "latitude": 26.8467,
            "longitude": 80.9462,
            "name": "Lucknow",
            "state": "Uttar Pradesh"
        },
        "nagpur": {
            "latitude": 21.1458,
            "longitude": 79.0882,
            "name": "Nagpur",
            "state": "Maharashtra"
        }
    }


@pytest.fixture
def international_waters() -> Dict[str, Dict[str, Any]]:
    """Locations in international waters."""
    return {
        "mid_indian_ocean": {
            "latitude": 0.0,
            "longitude": 75.0,
            "name": "Mid Indian Ocean"
        },
        "near_maldives": {
            "latitude": 4.1755,
            "longitude": 73.5093,
            "name": "Near Maldives"
        }
    }


# =============================================================================
# REPORTER FIXTURES
# =============================================================================

@pytest.fixture
def reporter_profiles() -> Dict[str, Dict[str, Any]]:
    """Different reporter profile types."""
    return {
        "verified_authority": {
            "id": str(uuid.uuid4()),
            "role": "authority",
            "verified": True,
            "reports_count": 50,
            "verified_reports": 45,
            "spam_reports": 0,
            "trust_score": 0.95,
            "email": "authority@coastguard.gov.in"
        },
        "trusted_analyst": {
            "id": str(uuid.uuid4()),
            "role": "analyst",
            "verified": True,
            "reports_count": 100,
            "verified_reports": 85,
            "spam_reports": 2,
            "trust_score": 0.85,
            "email": "analyst@example.com"
        },
        "experienced_citizen": {
            "id": str(uuid.uuid4()),
            "role": "citizen",
            "verified": True,
            "reports_count": 20,
            "verified_reports": 15,
            "spam_reports": 1,
            "trust_score": 0.75,
            "email": "citizen@example.com"
        },
        "new_citizen": {
            "id": str(uuid.uuid4()),
            "role": "citizen",
            "verified": True,
            "reports_count": 2,
            "verified_reports": 1,
            "spam_reports": 0,
            "trust_score": 0.5,
            "email": "newuser@example.com"
        },
        "unverified_user": {
            "id": str(uuid.uuid4()),
            "role": "citizen",
            "verified": False,
            "reports_count": 0,
            "verified_reports": 0,
            "spam_reports": 0,
            "trust_score": 0.3,
            "email": "unverified@example.com"
        },
        "suspected_spammer": {
            "id": str(uuid.uuid4()),
            "role": "citizen",
            "verified": True,
            "reports_count": 15,
            "verified_reports": 2,
            "spam_reports": 10,
            "trust_score": 0.1,
            "email": "spammer@example.com"
        }
    }


# =============================================================================
# WEATHER FIXTURES
# =============================================================================

@pytest.fixture
def weather_conditions() -> Dict[str, Dict[str, Any]]:
    """Various weather condition scenarios."""
    return {
        "tsunami_conditions": {
            "wave_height": 8.5,
            "wind_speed": 45,
            "sea_state": "very rough",
            "pressure": 990,
            "visibility": 5000,
            "alerts": ["TSUNAMI_WARNING"],
            "temperature": 28,
            "humidity": 85
        },
        "cyclone_conditions": {
            "wave_height": 6.0,
            "wind_speed": 120,
            "sea_state": "phenomenal",
            "pressure": 960,
            "visibility": 2000,
            "alerts": ["CYCLONE_WARNING", "STORM_SURGE"],
            "temperature": 26,
            "humidity": 95
        },
        "high_wave_conditions": {
            "wave_height": 4.5,
            "wind_speed": 35,
            "sea_state": "rough",
            "pressure": 1005,
            "visibility": 8000,
            "alerts": ["HIGH_WAVE_ALERT"],
            "temperature": 29,
            "humidity": 75
        },
        "flood_conditions": {
            "wave_height": 2.5,
            "wind_speed": 25,
            "sea_state": "moderate",
            "pressure": 1000,
            "visibility": 4000,
            "alerts": ["FLOOD_WARNING"],
            "temperature": 27,
            "humidity": 90,
            "rainfall_24h": 150
        },
        "rip_current_conditions": {
            "wave_height": 2.0,
            "wind_speed": 20,
            "sea_state": "moderate",
            "pressure": 1010,
            "visibility": 10000,
            "alerts": ["RIP_CURRENT_RISK"],
            "temperature": 30,
            "humidity": 70
        },
        "calm_conditions": {
            "wave_height": 0.5,
            "wind_speed": 8,
            "sea_state": "calm",
            "pressure": 1015,
            "visibility": 15000,
            "alerts": [],
            "temperature": 31,
            "humidity": 65
        },
        "monsoon_conditions": {
            "wave_height": 3.0,
            "wind_speed": 40,
            "sea_state": "rough",
            "pressure": 995,
            "visibility": 3000,
            "alerts": ["MONSOON_ACTIVE"],
            "temperature": 25,
            "humidity": 95,
            "rainfall_24h": 100
        }
    }


# =============================================================================
# HAZARD-SPECIFIC TEXT FIXTURES
# =============================================================================

@pytest.fixture
def hazard_descriptions() -> Dict[str, Dict[str, str]]:
    """Text descriptions for each hazard type with quality levels."""
    return {
        "tsunami": {
            "high_quality": """URGENT: Massive tsunami wave approaching! Witnessed huge water
            withdrawal from shore followed by 10+ meter wall of water. Destruction along
            2km of coastline. Multiple buildings damaged. Immediate evacuation needed!
            Location: Marina Beach, Chennai. Time: 14:30 IST. Many people trapped.""",

            "medium_quality": """Big wave came and flooded the beach area. Lot of water
            came very fast. Some boats damaged. People running away.""",

            "low_quality": """wave big water bad help"""
        },
        "cyclone": {
            "high_quality": """EMERGENCY: Category 4 cyclone making landfall! Winds exceeding
            180 km/h. Heavy rainfall, storm surge of 4 meters expected. Trees uprooted,
            power lines down. Roof of several houses blown away. District: Puri, Odisha.
            Evacuation shelters full. Need immediate rescue operations.""",

            "medium_quality": """Very strong storm hitting coastal area. Strong winds
            damaging houses. Heavy rain. Many trees fallen on roads.""",

            "low_quality": """storm wind rain bad"""
        },
        "high_waves": {
            "high_quality": """WARNING: Abnormally high waves of 5-6 meters observed at
            Kovalam Beach. Several tourists caught off-guard. One person swept away.
            Fishermen advised not to venture into sea. Coast guard patrolling area.
            Expected to continue for next 6 hours due to distant storm system.""",

            "medium_quality": """Very big waves at beach today. Higher than normal.
            Some people got wet. Dangerous to swim.""",

            "low_quality": """waves big water"""
        },
        "flooded_coastline": {
            "high_quality": """ALERT: Severe coastal flooding in Sundarbans area.
            Embankments breached in 3 locations. Saltwater inundation affecting
            5 villages. Estimated 2000 hectares of farmland submerged.
            Relief camps being set up. Fresh water shortage reported.""",

            "medium_quality": """Water flooding into village from sea side. Many houses
            have water inside. Roads not passable. People moving to higher ground.""",

            "low_quality": """water everywhere flood"""
        },
        "rip_current": {
            "high_quality": """DANGER: Strong rip current identified at Palolem Beach,
            Goa. Width approximately 10 meters, extending 100 meters offshore.
            Two swimmers rescued this morning. Lifeguards on alert. Red flags deployed.
            Current strongest during low tide, between 2-5 PM.""",

            "medium_quality": """Dangerous water current at beach pulling people out.
            Swimmers getting dragged away. Lifeguard made rescue.""",

            "low_quality": """water pulling strong"""
        },
        "beached_animal": {
            "high_quality": """WILDLIFE EMERGENCY: Pod of 15 pilot whales stranded at
            Tiruchendur Beach, Tamil Nadu. 8 adults, 7 juveniles. Most still alive
            but stressed. Marine biologists contacted. Volunteers keeping whales wet.
            Immediate help needed for refloating operation before high tide at 18:00.""",

            "medium_quality": """Found big whale on beach. It's still breathing but
            can't move. Some other dolphins also nearby. Please send help.""",

            "low_quality": """big fish beach help"""
        },
        "ship_wreck": {
            "high_quality": """MARITIME EMERGENCY: Cargo vessel MV Ocean Star capsized
            near Mandvi Port, Gujarat. 12 crew members, 5 rescued, 7 missing.
            Vessel carrying 500 tons of cargo, possible fuel leak detected.
            Coast Guard and Navy dispatched. Coordinates: 22.8408°N, 69.3520°E.
            Weather deteriorating, rescue operations challenging.""",

            "medium_quality": """Ship sinking near port area. Can see it tilting badly.
            Some people in water. Rescue boats going. Oil visible in water.""",

            "low_quality": """boat sink water people"""
        },
        "marine_debris": {
            "high_quality": """POLLUTION ALERT: Massive plastic debris accumulation at
            Versova Beach, Mumbai. Estimated 50 tons of plastic waste washed ashore
            after monsoon. Includes fishing nets, plastic bottles, medical waste.
            Wildlife entanglement reported - 3 sea turtles affected. Beach cleanup
            drive organized for weekend. Marine ecosystem severely impacted.""",

            "medium_quality": """Lots of plastic and garbage on beach. Dead fish also
            seen. Smell is very bad. Need cleanup soon.""",

            "low_quality": """garbage beach dirty"""
        },
        "oil_spill": {
            "high_quality": """ENVIRONMENTAL EMERGENCY: Major oil spill detected 15km
            off Mumbai coast. Source: Suspected tanker leak. Oil slick spreading,
            currently 3km x 500m. Tar balls reaching Juhu Beach. Strong petroleum odor.
            Marine life affected - dead fish washing up. Immediate containment required.
            ONGC and Coast Guard notified.""",

            "medium_quality": """Oil in water near beach. Black sticky substance on
            sand. Bad smell. Some dead fish. People complaining of smell.""",

            "low_quality": """black water oil bad"""
        },
        "other": {
            "high_quality": """UNUSUAL SIGHTING: Large unidentified floating structure
            spotted 5km off Kochi coast. Appears to be abandoned fishing platform.
            Approximately 20x15 meters. Partially submerged, navigation hazard.
            No visible markings or ownership indicators. Drifting towards shore.""",

            "medium_quality": """Something strange floating in sea near beach.
            Looks like some kind of structure. Could be dangerous for boats.""",

            "low_quality": """strange thing water"""
        }
    }


# =============================================================================
# IMAGE GENERATION FIXTURES
# =============================================================================

@pytest.fixture
def create_test_image():
    """Factory to create test images with specific characteristics."""
    def _create_image(
        width: int = 1920,
        height: int = 1080,
        color: tuple = (100, 150, 200),
        format: str = "JPEG",
        add_noise: bool = False
    ) -> bytes:
        """Create a test image and return as bytes."""
        img = Image.new('RGB', (width, height), color)

        if add_noise:
            import random
            pixels = img.load()
            for i in range(0, width, 10):
                for j in range(0, height, 10):
                    r = min(255, max(0, color[0] + random.randint(-20, 20)))
                    g = min(255, max(0, color[1] + random.randint(-20, 20)))
                    b = min(255, max(0, color[2] + random.randint(-20, 20)))
                    pixels[i, j] = (r, g, b)

        buffer = io.BytesIO()
        img.save(buffer, format=format, quality=85)
        buffer.seek(0)
        return buffer.getvalue()

    return _create_image


@pytest.fixture
def hazard_image_colors() -> Dict[str, tuple]:
    """Color schemes representing different hazard types."""
    return {
        "tsunami": (50, 80, 120),      # Dark blue-gray
        "cyclone": (80, 80, 90),       # Dark gray (stormy)
        "high_waves": (70, 130, 180),  # Steel blue
        "flooded_coastline": (139, 90, 43),  # Brown muddy water
        "rip_current": (65, 105, 225), # Royal blue
        "beached_animal": (210, 180, 140),  # Sandy beach
        "ship_wreck": (47, 79, 79),    # Dark slate gray
        "marine_debris": (169, 169, 169),   # Gray (garbage)
        "oil_spill": (25, 25, 25),     # Near black
        "other": (128, 128, 128)       # Neutral gray
    }


# =============================================================================
# MOCK SERVICE FIXTURES
# =============================================================================

@pytest.fixture
def mock_weather_service():
    """Mock weather service."""
    service = MagicMock()
    service.get_weather_data = AsyncMock()
    service.check_alerts = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_vision_service():
    """Mock vision/image analysis service."""
    service = MagicMock()
    service.analyze_image = AsyncMock(return_value={
        "hazard_detected": True,
        "confidence": 0.85,
        "detected_objects": ["water", "waves", "coast"]
    })
    service.validate_image = AsyncMock(return_value={
        "is_valid": True,
        "is_coastal": True,
        "quality_score": 0.9
    })
    return service


@pytest.fixture
def mock_geofence_service():
    """Mock geofence service."""
    service = MagicMock()
    service.validate_location = AsyncMock(return_value={
        "is_valid": True,
        "is_coastal": True,
        "nearest_coast_km": 0.5,
        "eez_zone": "India"
    })
    return service


@pytest.fixture
def mock_ticket_service():
    """Mock ticket service."""
    service = MagicMock()
    service.create_ticket = AsyncMock(return_value={
        "id": str(uuid.uuid4()),
        "status": "open",
        "created_at": datetime.utcnow().isoformat()
    })
    service.update_ticket = AsyncMock(return_value=True)
    return service


# =============================================================================
# TEST REPORT FACTORY
# =============================================================================

@pytest.fixture
def create_test_report(coastal_locations, reporter_profiles, hazard_descriptions):
    """Factory to create test hazard reports."""
    def _create_report(
        hazard_type: str,
        location_key: str = "mumbai_coast",
        reporter_key: str = "experienced_citizen",
        description_quality: str = "high_quality",
        include_image: bool = True,
        custom_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a test report with configurable parameters."""
        location = coastal_locations.get(location_key, coastal_locations["mumbai_coast"])
        reporter = reporter_profiles.get(reporter_key, reporter_profiles["experienced_citizen"])

        descriptions = hazard_descriptions.get(hazard_type, hazard_descriptions.get("other", {}))
        description = descriptions.get(description_quality, descriptions.get("medium_quality", "Test hazard report"))

        report = {
            "id": str(uuid.uuid4()),
            "hazard_type": hazard_type,
            "description": description,
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "location_name": location.get("name", "Unknown Location"),
            "reporter_id": reporter["id"],
            "reporter_role": reporter["role"],
            "reporter_trust_score": reporter["trust_score"],
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "has_image": include_image,
            "image_path": f"/uploads/hazards/{uuid.uuid4()}.jpg" if include_image else None
        }

        if custom_data:
            report.update(custom_data)

        return report

    return _create_report


# =============================================================================
# VERIFICATION RESULT FIXTURES
# =============================================================================

@pytest.fixture
def expected_verification_results() -> Dict[str, Dict[str, Any]]:
    """Expected verification outcomes for different scenarios."""
    return {
        "auto_approve": {
            "status": "verified",
            "final_score": 0.75,  # Minimum for auto-approve
            "decision": "auto_approved",
            "requires_manual_review": False
        },
        "manual_review": {
            "status": "pending_review",
            "final_score": 0.55,  # Between 40-75%
            "decision": "manual_review",
            "requires_manual_review": True
        },
        "auto_reject": {
            "status": "rejected",
            "final_score": 0.35,  # Below 40%
            "decision": "auto_rejected",
            "requires_manual_review": False
        },
        "geofence_fail": {
            "status": "rejected",
            "final_score": 0.0,
            "decision": "auto_rejected",
            "requires_manual_review": False,
            "rejection_reason": "outside_coastal_zone"
        }
    }


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup any test files after each test."""
    yield
    # Cleanup logic if needed
    import glob
    test_uploads = glob.glob("/tmp/test_uploads/*")
    for f in test_uploads:
        try:
            os.remove(f)
        except:
            pass


# =============================================================================
# PERFORMANCE TRACKING
# =============================================================================

@pytest.fixture
def performance_tracker():
    """Track test performance metrics."""
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.metrics = {}

        def start(self):
            self.start_time = datetime.now()

        def stop(self):
            self.end_time = datetime.now()

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return None

        def record(self, name: str, value: Any):
            self.metrics[name] = value

        def assert_under(self, max_seconds: float):
            assert self.duration is not None, "Timer not started/stopped"
            assert self.duration < max_seconds, f"Took {self.duration}s, expected < {max_seconds}s"

    return PerformanceTracker()
