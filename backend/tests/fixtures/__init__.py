"""
Test Fixtures Package
Contains reusable test data and fixtures for CoastGuardians tests.
"""

from .locations import COASTAL_LOCATIONS, INLAND_LOCATIONS, INTERNATIONAL_WATERS
from .hazard_data import HAZARD_DESCRIPTIONS, HAZARD_KEYWORDS, WEATHER_CONDITIONS
from .reporter_data import REPORTER_PROFILES

__all__ = [
    "COASTAL_LOCATIONS",
    "INLAND_LOCATIONS",
    "INTERNATIONAL_WATERS",
    "HAZARD_DESCRIPTIONS",
    "HAZARD_KEYWORDS",
    "WEATHER_CONDITIONS",
    "REPORTER_PROFILES"
]
