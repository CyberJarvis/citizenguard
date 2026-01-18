"""
BlueRadar Fast NLP Processor
Lightweight rule-based NLP for real-time classification
Falls back to ML only for uncertain cases
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


# Hazard keywords with weights
HAZARD_PATTERNS = {
    "cyclone": {
        "keywords": [
            ("cyclone", 100), ("hurricane", 100), ("typhoon", 100),
            ("storm", 60), ("landfall", 80), ("eye of storm", 90),
            ("चक्रवात", 100), ("புயல்", 100), ("తుఫాను", 100),
            ("cyclonic", 70), ("super cyclone", 100), ("severe cyclonic", 90)
        ],
        "severity_boost": 20
    },
    "tsunami": {
        "keywords": [
            ("tsunami", 100), ("tidal wave", 90), ("seismic sea", 80),
            ("सुनामी", 100), ("சுனாமி", 100)
        ],
        "severity_boost": 30
    },
    "flood": {
        "keywords": [
            ("flood", 80), ("flooding", 80), ("submerged", 70),
            ("waterlogged", 60), ("inundated", 70), ("deluge", 80),
            ("बाढ़", 80), ("வெள்ளம்", 80), ("water level", 50),
            ("flash flood", 90), ("urban flood", 70)
        ],
        "severity_boost": 15
    },
    "storm_surge": {
        "keywords": [
            ("storm surge", 90), ("coastal surge", 85), ("tidal surge", 80),
            ("sea surge", 75), ("high tide", 60)
        ],
        "severity_boost": 20
    },
    "rough_sea": {
        "keywords": [
            ("rough sea", 70), ("high waves", 70), ("choppy", 50),
            ("turbulent", 50), ("swell", 40), ("strong current", 60),
            ("rip current", 70), ("dangerous waves", 80)
        ],
        "severity_boost": 10
    },
    "oil_spill": {
        "keywords": [
            ("oil spill", 90), ("oil leak", 80), ("petroleum", 60),
            ("crude oil", 70), ("marine pollution", 60)
        ],
        "severity_boost": 15
    }
}

# Severity indicators
SEVERITY_PATTERNS = {
    "critical": {
        "keywords": [
            ("emergency", 100), ("evacuate", 100), ("evacuation", 100),
            ("deaths", 100), ("dead", 90), ("killed", 90), ("casualties", 100),
            ("catastrophic", 100), ("devastating", 90), ("life-threatening", 100),
            ("red alert", 100), ("extreme danger", 100), ("mayday", 100)
        ],
        "level": "CRITICAL",
        "score": 100
    },
    "high": {
        "keywords": [
            ("severe", 80), ("dangerous", 80), ("warning", 70),
            ("major", 70), ("significant", 60), ("damage", 70),
            ("destroyed", 80), ("injured", 80), ("missing", 80),
            ("rescue", 70), ("orange alert", 80), ("trapped", 85)
        ],
        "level": "HIGH",
        "score": 75
    },
    "medium": {
        "keywords": [
            ("moderate", 50), ("advisory", 50), ("caution", 40),
            ("alert", 40), ("expected", 40), ("likely", 40),
            ("possible", 30), ("monitor", 30), ("watch", 30),
            ("yellow alert", 50)
        ],
        "level": "MEDIUM",
        "score": 50
    },
    "low": {
        "keywords": [
            ("minor", 20), ("slight", 20), ("low", 20),
            ("minimal", 20), ("normal", 10), ("routine", 10)
        ],
        "level": "LOW",
        "score": 25
    }
}

# Indian coastal locations
INDIAN_LOCATIONS = {
    "west_coast": [
        "mumbai", "goa", "mangalore", "kochi", "kozhikode", "kannur",
        "thiruvananthapuram", "porbandar", "dwarka", "diu", "daman",
        "ratnagiri", "karwar", "udupi", "kasaragod", "alappuzha",
        "mumbai coast", "arabian sea", "konkan"
    ],
    "east_coast": [
        "chennai", "visakhapatnam", "vizag", "puri", "digha", "kolkata",
        "paradip", "gopalpur", "machilipatnam", "kakinada", "pondicherry",
        "puducherry", "cuddalore", "nagapattinam", "rameswaram", "tuticorin",
        "bay of bengal", "coromandel", "odisha coast", "tamil nadu coast"
    ],
    "islands": [
        "andaman", "nicobar", "lakshadweep", "port blair", "kavaratti"
    ]
}

# Spam patterns
SPAM_PATTERNS = [
    r"buy\s*now", r"discount", r"offer", r"sale", r"click\s*here",
    r"link\s*in\s*bio", r"follow\s*for\s*follow", r"f4f", r"dm\s*for",
    r"giveaway", r"crypto", r"nft", r"forex", r"trading", r"earn\s*money",
    r"make\s*money", r"weight\s*loss", r"diet", r"promo\s*code"
]


@dataclass
class FastNLPResult:
    """Result of fast NLP analysis"""
    is_relevant: bool
    relevance_score: float
    hazard_type: Optional[str]
    hazard_confidence: float
    severity: str
    severity_score: float
    locations: List[str]
    primary_region: Optional[str]
    is_spam: bool
    is_alert_worthy: bool
    processing_time_ms: float

    def to_dict(self) -> Dict:
        return {
            "is_relevant": self.is_relevant,
            "relevance_score": self.relevance_score,
            "hazard_type": self.hazard_type,
            "hazard_confidence": self.hazard_confidence,
            "severity": self.severity,
            "severity_score": self.severity_score,
            "locations": self.locations,
            "primary_region": self.primary_region,
            "is_spam": self.is_spam,
            "is_alert_worthy": self.is_alert_worthy,
            "processing_time_ms": self.processing_time_ms
        }


class FastNLPProcessor:
    """
    Ultra-fast NLP processor using rule-based matching
    Designed for real-time alert generation
    """

    def __init__(self):
        # Compile regex patterns for speed
        self.spam_patterns = [re.compile(p, re.IGNORECASE) for p in SPAM_PATTERNS]

        # Build location lookup
        self.location_lookup = {}
        for region, locations in INDIAN_LOCATIONS.items():
            for loc in locations:
                self.location_lookup[loc.lower()] = region

    def process(self, text: str, platform: str = "unknown") -> FastNLPResult:
        """
        Process text and return classification
        Optimized for speed - typically <5ms
        """
        start_time = datetime.now()

        text_lower = text.lower()

        # 1. Spam check (fast exit)
        is_spam = self._check_spam(text_lower)
        if is_spam:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return FastNLPResult(
                is_relevant=False,
                relevance_score=0,
                hazard_type=None,
                hazard_confidence=0,
                severity="LOW",
                severity_score=0,
                locations=[],
                primary_region=None,
                is_spam=True,
                is_alert_worthy=False,
                processing_time_ms=elapsed
            )

        # 2. Hazard detection
        hazard_type, hazard_score = self._detect_hazard(text_lower)

        # 3. Severity classification (now considers hazard context)
        severity, severity_score = self._classify_severity(text_lower, hazard_score)

        # 4. Location extraction
        locations, primary_region = self._extract_locations(text_lower)

        # 5. Calculate relevance score
        relevance_score = self._calculate_relevance(
            hazard_score, severity_score, len(locations), platform
        )

        # 6. Determine if alert-worthy (include MEDIUM alerts)
        is_alert_worthy = (
            relevance_score >= 50 and
            severity in ["CRITICAL", "HIGH", "MEDIUM"] and
            hazard_type is not None
        )

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        return FastNLPResult(
            is_relevant=relevance_score >= 40,
            relevance_score=relevance_score,
            hazard_type=hazard_type,
            hazard_confidence=hazard_score / 100,
            severity=severity,
            severity_score=severity_score,
            locations=locations,
            primary_region=primary_region,
            is_spam=False,
            is_alert_worthy=is_alert_worthy,
            processing_time_ms=elapsed
        )

    def _check_spam(self, text: str) -> bool:
        """Fast spam check"""
        for pattern in self.spam_patterns:
            if pattern.search(text):
                return True
        return False

    def _detect_hazard(self, text: str) -> Tuple[Optional[str], float]:
        """Detect hazard type and confidence"""
        best_hazard = None
        best_score = 0

        for hazard_type, config in HAZARD_PATTERNS.items():
            score = 0
            for keyword, weight in config["keywords"]:
                if keyword.lower() in text:
                    score = max(score, weight)

            if score > best_score:
                best_score = score
                best_hazard = hazard_type

        return best_hazard, best_score

    def _classify_severity(self, text: str, hazard_score: float = 0) -> Tuple[str, float]:
        """
        Classify severity level based on keyword matching and hazard score.
        Now considers hazard context to avoid false positives.
        """
        best_severity = "LOW"
        best_score = 0

        for level, config in SEVERITY_PATTERNS.items():
            for keyword, weight in config["keywords"]:
                if keyword.lower() in text:
                    if weight > best_score:
                        best_score = weight
                        best_severity = config["level"]

        # Severity adjustment based on hazard context:
        # If no hazard detected or very weak hazard, cap severity at MEDIUM
        # This prevents false positives where a post mentions "alert" or "watch"
        # but isn't actually about a disaster
        if hazard_score < 40 and best_severity in ["CRITICAL", "HIGH"]:
            # Downgrade to MEDIUM if no real hazard detected
            best_severity = "MEDIUM"
            best_score = min(best_score, 50)

        if hazard_score < 20 and best_severity == "MEDIUM":
            # Downgrade to LOW if almost no hazard keywords found
            best_severity = "LOW"
            best_score = min(best_score, 25)

        return best_severity, best_score

    def _extract_locations(self, text: str) -> Tuple[List[str], Optional[str]]:
        """Extract Indian coastal locations"""
        locations = []
        regions = {}

        for location, region in self.location_lookup.items():
            if location in text:
                locations.append(location)
                regions[region] = regions.get(region, 0) + 1

        # Get primary region
        primary_region = None
        if regions:
            primary_region = max(regions, key=regions.get)

        return locations, primary_region

    def _calculate_relevance(
        self,
        hazard_score: float,
        severity_score: float,
        location_count: int,
        platform: str
    ) -> float:
        """Calculate overall relevance score"""
        score = 0

        # Hazard contribution (max 40)
        score += min(40, hazard_score * 0.4)

        # Severity contribution (max 30)
        score += min(30, severity_score * 0.3)

        # Location contribution (max 20)
        if location_count > 0:
            score += min(20, location_count * 10)

        # Platform trust bonus (max 10)
        platform_bonus = {
            "twitter": 8,
            "youtube": 6,
            "instagram": 5,
            "facebook": 4,
            "news": 10
        }
        score += platform_bonus.get(platform, 5)

        return min(100, score)

    def process_batch(self, posts: List[Dict]) -> List[Dict]:
        """Process multiple posts quickly"""
        results = []

        for post in posts:
            text = post.get("text", "") or post.get("content", "")
            platform = post.get("platform", "unknown")

            nlp_result = self.process(text, platform)

            post["nlp"] = nlp_result.to_dict()
            post["is_alert"] = nlp_result.is_alert_worthy

            results.append(post)

        return results

    def get_alerts_only(self, posts: List[Dict]) -> List[Dict]:
        """Filter to only alert-worthy posts"""
        processed = self.process_batch(posts)
        return [p for p in processed if p.get("is_alert", False)]


# Singleton instance
fast_nlp = FastNLPProcessor()


def test_fast_nlp():
    """Test the fast NLP processor"""
    processor = FastNLPProcessor()

    test_texts = [
        "BREAKING: Cyclone Michaung makes landfall near Chennai coast with 120 kmph winds. Red alert issued. Evacuations underway.",
        "Severe flooding in Mumbai after heavy rains. Multiple areas submerged. Rescue operations ongoing.",
        "Beautiful sunset at Goa beach today! #travel #beach #vacation",
        "Buy now! Discount 50% on all products. Click here!",
        "Storm surge warning for Odisha coast. High waves expected. Fishermen advised not to venture into sea.",
        "Minor earthquake tremors felt in Andaman islands. No tsunami warning.",
    ]

    print("Fast NLP Processor Test")
    print("=" * 60)

    total_time = 0
    for text in test_texts:
        result = processor.process(text)
        total_time += result.processing_time_ms

        print(f"\nText: {text[:60]}...")
        print(f"  Relevant: {result.is_relevant}")
        print(f"  Hazard: {result.hazard_type} ({result.hazard_confidence:.0%})")
        print(f"  Severity: {result.severity}")
        print(f"  Locations: {result.locations}")
        print(f"  Alert Worthy: {result.is_alert_worthy}")
        print(f"  Time: {result.processing_time_ms:.2f}ms")

    print(f"\n{'=' * 60}")
    print(f"Total time: {total_time:.2f}ms")
    print(f"Average: {total_time/len(test_texts):.2f}ms per text")


if __name__ == "__main__":
    test_fast_nlp()
