"""
Report Hazard Classifier Service
Classifies threat levels based on environmental data snapshot.
Returns: WARNING (currently occurring), ALERT (will occur soon), WATCH (possible), NO_THREAT
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pydantic import BaseModel

from app.models.hazard import (
    ThreatLevel, EnvironmentalSnapshot, HazardClassification,
    ExtendedWeatherData, MarineData, SeismicData, AstronomyData
)

logger = logging.getLogger(__name__)


class HazardThresholds(BaseModel):
    """Configurable thresholds for hazard classification."""

    # Tsunami thresholds (based on earthquake)
    tsunami_warning_magnitude: float = 7.5  # Magnitude for WARNING
    tsunami_alert_magnitude: float = 6.5    # Magnitude for ALERT
    tsunami_watch_magnitude: float = 5.5    # Magnitude for WATCH
    tsunami_depth_shallow_km: float = 70    # Shallow earthquakes more likely to cause tsunami
    tsunami_distance_critical_km: float = 200  # Distance for higher concern

    # High waves thresholds (based on marine data)
    waves_warning_height_m: float = 4.0     # Wave height for WARNING
    waves_alert_height_m: float = 3.0       # Wave height for ALERT
    waves_watch_height_m: float = 2.0       # Wave height for WATCH

    # Cyclone thresholds (based on weather)
    cyclone_warning_wind_kph: float = 119   # Hurricane force winds
    cyclone_alert_wind_kph: float = 89      # Tropical storm winds
    cyclone_watch_wind_kph: float = 62      # Strong winds
    cyclone_warning_pressure_mb: float = 980  # Very low pressure
    cyclone_alert_pressure_mb: float = 1000   # Low pressure

    # Rip current thresholds
    rip_warning_wind_kph: float = 40        # Strong onshore winds
    rip_warning_wave_m: float = 1.5         # Moderate waves + wind = danger

    # Coastal flood thresholds
    flood_warning_precip_mm: float = 50     # Heavy rain
    flood_alert_precip_mm: float = 30       # Significant rain
    flood_warning_tide_high: str = "HIGH"   # High tide concern


class ReportHazardClassifier:
    """
    Classifies hazard threat levels based on environmental data.
    Uses rule-based analysis of weather, marine, and seismic data.
    """

    def __init__(self, thresholds: Optional[HazardThresholds] = None):
        self.thresholds = thresholds or HazardThresholds()

    def classify(
        self,
        environmental_snapshot: EnvironmentalSnapshot,
        reported_hazard_type: Optional[str] = None
    ) -> HazardClassification:
        """
        Classify threat levels based on environmental data.

        Args:
            environmental_snapshot: Complete environmental data
            reported_hazard_type: Optional user-reported hazard type for context

        Returns:
            HazardClassification with threat levels and recommendations
        """
        # Individual hazard assessments
        tsunami_threat, tsunami_reason, tsunami_recs = self._assess_tsunami_threat(
            environmental_snapshot.seismic
        )

        cyclone_threat, cyclone_reason, cyclone_recs = self._assess_cyclone_threat(
            environmental_snapshot.weather
        )

        waves_threat, waves_reason, waves_recs = self._assess_high_waves_threat(
            environmental_snapshot.marine,
            environmental_snapshot.weather
        )

        flood_threat, flood_reason, flood_recs = self._assess_coastal_flood_threat(
            environmental_snapshot.weather,
            environmental_snapshot.marine
        )

        rip_threat, rip_reason, rip_recs = self._assess_rip_current_threat(
            environmental_snapshot.weather,
            environmental_snapshot.marine
        )

        # Determine overall threat level (highest among all)
        threats = [tsunami_threat, cyclone_threat, waves_threat, flood_threat, rip_threat]
        threat_order = [ThreatLevel.WARNING, ThreatLevel.ALERT, ThreatLevel.WATCH, ThreatLevel.NO_THREAT]
        overall_threat = ThreatLevel.NO_THREAT

        for level in threat_order:
            if level in threats:
                overall_threat = level
                break

        # Determine primary hazard type
        hazard_priority = [
            (tsunami_threat, "tsunami"),
            (cyclone_threat, "cyclone"),
            (waves_threat, "high_waves"),
            (flood_threat, "coastal_flood"),
            (rip_threat, "rip_current")
        ]

        primary_hazard = None
        for threat, hazard_type in hazard_priority:
            if threat == overall_threat and threat != ThreatLevel.NO_THREAT:
                primary_hazard = hazard_type
                break

        # Build reasoning
        reasons = []
        if tsunami_reason:
            reasons.append(f"Tsunami: {tsunami_reason}")
        if cyclone_reason:
            reasons.append(f"Cyclone: {cyclone_reason}")
        if waves_reason:
            reasons.append(f"Waves: {waves_reason}")
        if flood_reason:
            reasons.append(f"Flooding: {flood_reason}")
        if rip_reason:
            reasons.append(f"Rip Current: {rip_reason}")

        reasoning = "; ".join(reasons) if reasons else "No significant threats detected"

        # Compile recommendations
        all_recs = []
        if tsunami_recs:
            all_recs.extend(tsunami_recs)
        if cyclone_recs:
            all_recs.extend(cyclone_recs)
        if waves_recs:
            all_recs.extend(waves_recs)
        if flood_recs:
            all_recs.extend(flood_recs)
        if rip_recs:
            all_recs.extend(rip_recs)

        # Add default recommendation if none
        if not all_recs:
            all_recs.append("Normal conditions - exercise standard coastal safety")

        # Calculate confidence based on data availability
        confidence = self._calculate_confidence(environmental_snapshot)

        return HazardClassification(
            threat_level=overall_threat,
            hazard_type=primary_hazard,
            confidence=confidence,
            reasoning=reasoning,
            tsunami_threat=tsunami_threat,
            cyclone_threat=cyclone_threat,
            high_waves_threat=waves_threat,
            coastal_flood_threat=flood_threat,
            rip_current_threat=rip_threat,
            recommendations=all_recs[:5],  # Limit to top 5
            classified_at=datetime.now(timezone.utc),
            model_version="1.0"
        )

    def _assess_tsunami_threat(
        self,
        seismic: Optional[SeismicData]
    ) -> Tuple[ThreatLevel, str, List[str]]:
        """Assess tsunami threat based on seismic data."""
        if not seismic or seismic.magnitude is None:
            return ThreatLevel.NO_THREAT, "", []

        magnitude = seismic.magnitude
        depth = seismic.depth_km or 100
        distance = seismic.distance_km or 1000
        has_tsunami_flag = seismic.tsunami == 1

        # USGS already flagged tsunami threat
        if has_tsunami_flag:
            return (
                ThreatLevel.WARNING,
                f"USGS tsunami warning for M{magnitude} earthquake",
                [
                    "EVACUATE coastal areas immediately",
                    "Move to higher ground (30m+ elevation)",
                    "Stay away from beaches and harbors",
                    "Monitor official tsunami warnings"
                ]
            )

        # Strong shallow earthquake nearby
        is_shallow = depth < self.thresholds.tsunami_depth_shallow_km
        is_nearby = distance < self.thresholds.tsunami_distance_critical_km

        if magnitude >= self.thresholds.tsunami_warning_magnitude and is_shallow:
            return (
                ThreatLevel.WARNING,
                f"Major earthquake M{magnitude} at {depth}km depth - high tsunami risk",
                [
                    "EVACUATE coastal areas immediately",
                    "Move to higher ground",
                    "Do not return until official all-clear"
                ]
            )

        if magnitude >= self.thresholds.tsunami_alert_magnitude and is_shallow and is_nearby:
            return (
                ThreatLevel.ALERT,
                f"Strong earthquake M{magnitude} nearby ({distance:.0f}km) - tsunami possible",
                [
                    "Be prepared to evacuate",
                    "Move away from shoreline",
                    "Monitor official warnings closely"
                ]
            )

        if magnitude >= self.thresholds.tsunami_watch_magnitude:
            return (
                ThreatLevel.WATCH,
                f"Moderate earthquake M{magnitude} detected - monitoring situation",
                [
                    "Stay alert for updates",
                    "Know your evacuation route"
                ]
            )

        return ThreatLevel.NO_THREAT, "", []

    def _assess_cyclone_threat(
        self,
        weather: Optional[ExtendedWeatherData]
    ) -> Tuple[ThreatLevel, str, List[str]]:
        """Assess cyclone/storm threat based on weather data."""
        if not weather:
            return ThreatLevel.NO_THREAT, "", []

        wind_kph = weather.wind_kph or 0
        gust_kph = weather.gust_kph or 0
        pressure = weather.pressure_mb or 1013

        # Use higher of sustained wind or gust
        effective_wind = max(wind_kph, gust_kph * 0.8)

        # Hurricane force conditions
        if effective_wind >= self.thresholds.cyclone_warning_wind_kph or pressure < self.thresholds.cyclone_warning_pressure_mb:
            return (
                ThreatLevel.WARNING,
                f"Severe cyclonic conditions - winds {effective_wind:.0f}kph, pressure {pressure}mb",
                [
                    "SHELTER immediately in sturdy building",
                    "Stay away from windows and doors",
                    "Avoid coastal and low-lying areas",
                    "Do not attempt to travel"
                ]
            )

        # Tropical storm conditions
        if effective_wind >= self.thresholds.cyclone_alert_wind_kph or pressure < self.thresholds.cyclone_alert_pressure_mb:
            return (
                ThreatLevel.ALERT,
                f"Storm conditions developing - winds {effective_wind:.0f}kph, pressure {pressure}mb",
                [
                    "Seek shelter soon",
                    "Secure loose objects",
                    "Avoid unnecessary travel"
                ]
            )

        # Strong wind conditions
        if effective_wind >= self.thresholds.cyclone_watch_wind_kph:
            return (
                ThreatLevel.WATCH,
                f"Strong winds ({effective_wind:.0f}kph) - conditions may deteriorate",
                [
                    "Monitor weather updates",
                    "Prepare emergency supplies"
                ]
            )

        return ThreatLevel.NO_THREAT, "", []

    def _assess_high_waves_threat(
        self,
        marine: Optional[MarineData],
        weather: Optional[ExtendedWeatherData]
    ) -> Tuple[ThreatLevel, str, List[str]]:
        """Assess high wave threat based on marine and weather data."""
        if not marine:
            return ThreatLevel.NO_THREAT, "", []

        sig_height = marine.sig_ht_mt or 0
        swell_height = marine.swell_ht_mt or 0
        wave_height = max(sig_height, swell_height)

        # Factor in wind for wave growth
        wind_factor = 1.0
        if weather and weather.wind_kph:
            if weather.wind_kph > 50:
                wind_factor = 1.3
            elif weather.wind_kph > 30:
                wind_factor = 1.15

        effective_height = wave_height * wind_factor

        if effective_height >= self.thresholds.waves_warning_height_m:
            return (
                ThreatLevel.WARNING,
                f"Dangerous waves ({effective_height:.1f}m) - immediate coastal hazard",
                [
                    "AVOID all coastal areas",
                    "Do not enter the water",
                    "Stay off piers, jetties, and breakwaters",
                    "Keep safe distance from shore"
                ]
            )

        if effective_height >= self.thresholds.waves_alert_height_m:
            return (
                ThreatLevel.ALERT,
                f"High waves ({effective_height:.1f}m) - hazardous conditions",
                [
                    "Avoid beaches and rocky shores",
                    "Do not swim or surf",
                    "Keep children away from water"
                ]
            )

        if effective_height >= self.thresholds.waves_watch_height_m:
            return (
                ThreatLevel.WATCH,
                f"Elevated waves ({effective_height:.1f}m) - exercise caution",
                [
                    "Be cautious near water",
                    "Supervise children closely"
                ]
            )

        return ThreatLevel.NO_THREAT, "", []

    def _assess_coastal_flood_threat(
        self,
        weather: Optional[ExtendedWeatherData],
        marine: Optional[MarineData]
    ) -> Tuple[ThreatLevel, str, List[str]]:
        """
        Assess coastal flooding threat based on INCOIS thresholds.

        INCOIS Flooded Coastline Validation Thresholds:
        - WARNING: (Tide >2m AND rain >=20mm) OR (rain >=30mm AND visibility <=2km)
        - ALERT: (Tide 1.5-2m AND rain 10-19mm) OR rain 20-29mm
        - WATCH: Tide 0.8-1.5m OR rain 10-20mm
        - NO_THREAT: Otherwise
        """
        if not weather and not marine:
            return ThreatLevel.NO_THREAT, "", []

        precip = weather.precip_mm if weather else 0
        visibility = weather.vis_km if weather else 10  # Default good visibility
        tide_height = marine.tide_height_mt if marine and marine.tide_height_mt else 0

        # WARNING: (Tide >2m AND rain >=20mm) OR (rain >=30mm AND visibility <=2km)
        if (tide_height > 2.0 and precip >= 20) or (precip >= 30 and visibility <= 2):
            reason_parts = []
            if tide_height > 2.0 and precip >= 20:
                reason_parts.append(f"high tide ({tide_height:.1f}m) with heavy rain ({precip:.0f}mm)")
            if precip >= 30 and visibility <= 2:
                reason_parts.append(f"heavy rain ({precip:.0f}mm) with poor visibility ({visibility:.1f}km)")
            return (
                ThreatLevel.WARNING,
                f"Coastal flooding likely - {' and '.join(reason_parts)}",
                [
                    "AVOID low-lying coastal areas",
                    "Do not drive through flooded roads",
                    "Move valuables to higher ground",
                    "Be prepared to evacuate"
                ]
            )

        # ALERT: (Tide 1.5-2m AND rain 10-19mm) OR rain 20-29mm
        if (1.5 <= tide_height <= 2.0 and 10 <= precip < 20) or (20 <= precip < 30):
            if 1.5 <= tide_height <= 2.0 and 10 <= precip < 20:
                reason = f"moderate tide ({tide_height:.1f}m) with rain ({precip:.0f}mm)"
            else:
                reason = f"significant rainfall ({precip:.0f}mm)"
            return (
                ThreatLevel.ALERT,
                f"Flooding possible - {reason}",
                [
                    "Be aware of tidal flooding",
                    "Avoid low-lying areas near coast",
                    "Do not cross flooded areas"
                ]
            )

        # WATCH: Tide 0.8-1.5m OR rain 10-20mm
        if (0.8 <= tide_height <= 1.5) or (10 <= precip <= 20):
            if 0.8 <= tide_height <= 1.5 and 10 <= precip <= 20:
                reason = f"moderate tide ({tide_height:.1f}m) with light rain ({precip:.0f}mm)"
            elif 0.8 <= tide_height <= 1.5:
                reason = f"moderate tide ({tide_height:.1f}m)"
            else:
                reason = f"light to moderate rain ({precip:.0f}mm)"
            return (
                ThreatLevel.WATCH,
                f"Minor flooding possible - {reason}",
                ["Be aware of tidal conditions"]
            )

        # NO_THREAT: High tide alone (even >2m) without rain does NOT trigger alert
        # Normal tidal ranges in India are 3-5m which is expected behavior
        return ThreatLevel.NO_THREAT, "", []

    def _assess_rip_current_threat(
        self,
        weather: Optional[ExtendedWeatherData],
        marine: Optional[MarineData]
    ) -> Tuple[ThreatLevel, str, List[str]]:
        """Assess rip current threat."""
        if not weather or not marine:
            return ThreatLevel.NO_THREAT, "", []

        wind_kph = weather.wind_kph or 0
        wave_height = max(marine.sig_ht_mt or 0, marine.swell_ht_mt or 0)
        swell_period = marine.swell_period_secs or 0

        # Rip currents more likely with:
        # - Moderate to strong onshore winds
        # - 1-2m waves
        # - Longer swell periods
        is_rip_conditions = (
            wind_kph >= self.thresholds.rip_warning_wind_kph and
            wave_height >= self.thresholds.rip_warning_wave_m and
            swell_period > 8
        )

        if is_rip_conditions and wave_height >= 2.0:
            return (
                ThreatLevel.WARNING,
                f"High rip current risk - strong winds ({wind_kph}kph) with {wave_height}m waves",
                [
                    "DO NOT swim",
                    "Rip currents can pull swimmers out to sea",
                    "If caught in rip, swim parallel to shore",
                    "Always swim near lifeguards"
                ]
            )

        if is_rip_conditions:
            return (
                ThreatLevel.ALERT,
                f"Rip current conditions - winds {wind_kph}kph, waves {wave_height}m",
                [
                    "Use extreme caution when swimming",
                    "Know how to escape a rip current",
                    "Swim near lifeguards"
                ]
            )

        if wave_height >= 1.5 and swell_period > 10:
            return (
                ThreatLevel.WATCH,
                f"Moderate rip current potential - waves {wave_height}m",
                ["Be aware of rip current risks"]
            )

        return ThreatLevel.NO_THREAT, "", []

    def _calculate_confidence(self, snapshot: EnvironmentalSnapshot) -> float:
        """Calculate confidence score based on data availability."""
        score = 0.0
        total = 0.0

        # Weather data (most important for most hazards)
        total += 0.35
        if snapshot.weather:
            score += 0.35

        # Marine data (important for coastal hazards)
        total += 0.30
        if snapshot.marine:
            score += 0.30

        # Seismic data (important for tsunami)
        total += 0.25
        if snapshot.seismic is not None:  # None means no earthquakes, which is still data
            score += 0.25
        else:
            score += 0.15  # Partial credit for no earthquake data (likely means safe)

        # Astronomy data (less critical)
        total += 0.10
        if snapshot.astronomy:
            score += 0.10

        return round(score / total if total > 0 else 0.5, 2)


# Singleton instance
_classifier: Optional[ReportHazardClassifier] = None


def get_hazard_classifier() -> ReportHazardClassifier:
    """Get singleton instance of ReportHazardClassifier."""
    global _classifier
    if _classifier is None:
        _classifier = ReportHazardClassifier()
    return _classifier


def classify_hazard_threat(
    environmental_snapshot: EnvironmentalSnapshot,
    reported_hazard_type: Optional[str] = None
) -> HazardClassification:
    """
    Convenience function to classify hazard threat.
    Use this in the report submission pipeline.
    """
    classifier = get_hazard_classifier()
    return classifier.classify(environmental_snapshot, reported_hazard_type)
