"""
BlueRadar Content Validator
Validates scraped content for misinformation, recency, and geographic relevance
"""

import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ValidationResult:
    """Result of content validation"""
    is_valid: bool
    rejection_reason: Optional[str] = None
    confidence: float = 1.0
    details: Dict = field(default_factory=dict)


# India indicators for smart context detection
INDIA_INDICATORS = [
    # Water bodies
    "bay of bengal", "arabian sea", "indian ocean",
    "andaman sea", "laccadive sea", "gulf of kutch",
    "gulf of khambhat", "gulf of mannar", "palk strait",

    # Government/Official sources
    "imd", "incois", "ndma", "indian meteorological",
    "india met department", "met department india",
    "national disaster management", "indian coast guard",

    # States (coastal)
    "tamil nadu", "tamilnadu", "kerala", "karnataka",
    "maharashtra", "gujarat", "odisha", "orissa",
    "west bengal", "andhra pradesh", "goa",

    # Major coastal cities
    "chennai", "mumbai", "kolkata", "visakhapatnam", "vizag",
    "kochi", "cochin", "mangalore", "mangaluru", "puducherry",
    "pondicherry", "puri", "paradip", "porbandar", "kandla",
    "thiruvananthapuram", "trivandrum", "kozhikode", "calicut",

    # Islands
    "andaman", "nicobar", "lakshadweep", "port blair",

    # Country reference
    "india", "indian", "bharat",

    # Hindi/Regional language indicators
    "चक्रवात", "बाढ़", "तूफान", "सुनामी",  # Hindi
    "புயல்", "வெள்ளம்",  # Tamil
    "తుఫాను", "వరద",  # Telugu
]

# International locations to block
INTERNATIONAL_BLOCKLIST = [
    # Countries with frequent cyclone news
    "philippines", "philippine", "manila", "luzon", "mindanao",
    "taiwan", "taipei",
    "japan", "japanese", "tokyo", "okinawa",
    "vietnam", "vietnamese", "hanoi", "ho chi minh",
    "bangladesh", "bangladeshi", "dhaka", "chittagong",
    "myanmar", "burma", "yangon",
    "thailand", "thai", "bangkok",
    "indonesia", "indonesian", "jakarta",
    "australia", "australian", "queensland", "darwin",
    "usa", "u.s.", "united states", "florida", "texas", "louisiana",
    "caribbean", "cuba", "puerto rico", "bahamas",
    "pacific", "hawaii", "guam",
    "china", "chinese", "hong kong", "guangdong",
    "malaysia", "kuala lumpur",
    "sri lanka", "colombo",  # Sometimes OK but often separate news

    # International water bodies
    "atlantic", "gulf of mexico", "south china sea",
    "pacific ocean", "caribbean sea",

    # International cyclone naming conventions (non-Indian)
    "super typhoon", "category 5 hurricane",
]


class ContentValidator:
    """
    Validates scraped content for:
    - Recency (max 48 hours by default)
    - Geographic relevance (India-only with smart detection)
    - Source credibility
    - Duplicate detection
    """

    def __init__(self, config: Dict = None):
        config = config or {}

        # Recency settings
        self.max_age_hours = config.get("max_age_hours", 48)

        # Geographic settings
        self.geo_mode = config.get("geo_mode", "smart")  # strict, moderate, smart
        self.blocked_regions = config.get("blocked_regions", INTERNATIONAL_BLOCKLIST)
        self.india_indicators = config.get("india_indicators", INDIA_INDICATORS)

        # Duplicate detection
        self.enable_duplicate_detection = config.get("enable_duplicate_detection", True)
        self.duplicate_window_hours = config.get("duplicate_window_hours", 24)
        self.seen_content: deque = deque(maxlen=1000)  # Rolling window of content hashes

        # Stats
        self.stats = {
            "total_validated": 0,
            "accepted": 0,
            "rejected_old": 0,
            "rejected_international": 0,
            "rejected_duplicate": 0,
            "rejected_low_relevance": 0,
        }

    def validate(self, post: Dict, nlp_result: Dict = None) -> ValidationResult:
        """
        Validate a post for inclusion as an alert.

        Args:
            post: Scraped post data
            nlp_result: NLP processing result (optional)

        Returns:
            ValidationResult with is_valid flag and details
        """
        self.stats["total_validated"] += 1
        nlp_result = nlp_result or {}

        # Step 1: Recency check
        recency_result = self._check_recency(post)
        if not recency_result.is_valid:
            self.stats["rejected_old"] += 1
            return recency_result

        # Step 2: Geographic check
        geo_result = self._check_geography(post, nlp_result)
        if not geo_result.is_valid:
            self.stats["rejected_international"] += 1
            return geo_result

        # Step 3: Duplicate check
        if self.enable_duplicate_detection:
            dup_result = self._check_duplicate(post)
            if not dup_result.is_valid:
                self.stats["rejected_duplicate"] += 1
                return dup_result

        # All checks passed
        self.stats["accepted"] += 1
        return ValidationResult(
            is_valid=True,
            confidence=1.0,
            details={
                "age_hours": recency_result.details.get("age_hours"),
                "is_india_relevant": True,
                "checks_passed": ["recency", "geography", "duplicate"]
            }
        )

    def _check_recency(self, post: Dict) -> ValidationResult:
        """Check if post is within acceptable time window"""
        age_hours = self._calculate_age_hours(post)

        if age_hours is None:
            # Can't determine age - REJECT to avoid old content
            return ValidationResult(
                is_valid=False,
                rejection_reason="timestamp_unknown",
                confidence=0.8,
                details={"age_hours": None, "reason": "cannot_determine_age"}
            )

        if age_hours > self.max_age_hours:
            return ValidationResult(
                is_valid=False,
                rejection_reason="content_too_old",
                confidence=1.0,
                details={
                    "age_hours": age_hours,
                    "max_allowed": self.max_age_hours
                }
            )

        return ValidationResult(
            is_valid=True,
            confidence=1.0,
            details={"age_hours": age_hours}
        )

    def _calculate_age_hours(self, post: Dict) -> Optional[float]:
        """Calculate post age in hours from various timestamp formats"""
        timestamp = post.get("timestamp") or post.get("posted_at") or ""

        if not timestamp:
            return None

        now = datetime.now()

        # Try ISO format
        try:
            if "T" in timestamp or timestamp.endswith("Z"):
                post_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00").replace("+00:00", ""))
                return (now - post_time).total_seconds() / 3600
        except:
            pass

        # Try RFC 2822 format (from RSS feeds)
        try:
            from email.utils import parsedate_to_datetime
            post_time = parsedate_to_datetime(timestamp)
            # Convert to naive datetime for comparison
            post_time = post_time.replace(tzinfo=None)
            return (now - post_time).total_seconds() / 3600
        except:
            pass

        # Try relative time parsing
        timestamp_lower = timestamp.lower()

        relative_patterns = [
            (r"(\d+)\s*min", lambda m: int(m.group(1)) / 60),
            (r"(\d+)\s*hour", lambda m: int(m.group(1))),
            (r"(\d+)\s*day", lambda m: int(m.group(1)) * 24),
            (r"(\d+)\s*week", lambda m: int(m.group(1)) * 24 * 7),
            (r"(\d+)\s*month", lambda m: int(m.group(1)) * 24 * 30),
            (r"(\d+)\s*year", lambda m: int(m.group(1)) * 24 * 365),
            (r"just\s*now", lambda m: 0.1),
            (r"(\d+)\s*sec", lambda m: int(m.group(1)) / 3600),
            (r"stream", lambda m: 0.1),  # Live streams are current
        ]

        for pattern, converter in relative_patterns:
            match = re.search(pattern, timestamp_lower)
            if match:
                try:
                    return converter(match)
                except:
                    pass

        return None

    def _check_geography(self, post: Dict, nlp_result: Dict) -> ValidationResult:
        """Check if post is India-relevant using smart detection"""
        text = post.get("text", "") or ""
        text_lower = text.lower()

        # Also check title if available
        title = post.get("title", "") or ""
        combined_text = f"{title} {text}".lower()

        # Step 1: Check for international blocklist (reject immediately)
        for blocked in self.blocked_regions:
            if blocked in combined_text:
                # Exception: If also mentions India explicitly, allow it
                if self._has_strong_india_indicator(combined_text):
                    continue

                return ValidationResult(
                    is_valid=False,
                    rejection_reason="international_content",
                    confidence=0.9,
                    details={
                        "blocked_term": blocked,
                        "mode": self.geo_mode
                    }
                )

        # Step 2: Check for India indicators (smart mode)
        india_score = self._calculate_india_score(combined_text, nlp_result)

        if self.geo_mode == "strict":
            # Require explicit India mention
            if india_score < 0.5:
                return ValidationResult(
                    is_valid=False,
                    rejection_reason="no_india_reference",
                    confidence=0.8,
                    details={"india_score": india_score, "mode": "strict"}
                )
        elif self.geo_mode == "smart":
            # Allow if no international indicators and has some relevance
            if india_score < 0.2:
                return ValidationResult(
                    is_valid=False,
                    rejection_reason="not_india_relevant",
                    confidence=0.7,
                    details={"india_score": india_score, "mode": "smart"}
                )
        # moderate mode: just check blocklist (already done)

        return ValidationResult(
            is_valid=True,
            confidence=min(1.0, india_score + 0.5),
            details={"india_score": india_score}
        )

    def _has_strong_india_indicator(self, text: str) -> bool:
        """Check for strong India indicators"""
        strong_indicators = [
            "india", "indian", "imd", "incois",
            "chennai", "mumbai", "kolkata", "kerala",
            "tamil nadu", "bay of bengal", "arabian sea"
        ]
        return any(ind in text for ind in strong_indicators)

    def _calculate_india_score(self, text: str, nlp_result: Dict) -> float:
        """Calculate India relevance score (0-1)"""
        score = 0.0
        matches = []

        # Check India indicators
        for indicator in self.india_indicators:
            if indicator in text:
                score += 0.15
                matches.append(indicator)
                if score >= 1.0:
                    break

        # Check NLP-extracted locations
        locations = nlp_result.get("locations", [])
        if isinstance(locations, dict):
            locations = locations.get("locations", [])

        for loc in locations:
            if isinstance(loc, dict):
                if loc.get("type") == "indian_coast":
                    score += 0.3
                elif loc.get("region") in ["west_coast", "east_coast", "islands"]:
                    score += 0.25

        # Check if primary region is set
        primary_region = nlp_result.get("primary_region")
        if primary_region in ["west_coast", "east_coast", "islands"]:
            score += 0.2

        return min(1.0, score)

    def _check_duplicate(self, post: Dict) -> ValidationResult:
        """Check if similar content was seen recently"""
        content_hash = self._generate_content_hash(post)

        if content_hash in self.seen_content:
            return ValidationResult(
                is_valid=False,
                rejection_reason="duplicate_content",
                confidence=0.95,
                details={"hash": content_hash[:16]}
            )

        # Add to seen content
        self.seen_content.append(content_hash)

        return ValidationResult(is_valid=True)

    def _generate_content_hash(self, post: Dict) -> str:
        """Generate hash for duplicate detection"""
        text = post.get("text", "") or ""

        # Normalize text for comparison
        normalized = text.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        normalized = re.sub(r'\s+', ' ', normalized).strip()  # Normalize whitespace

        # Use first 200 chars for hashing (titles/headlines)
        normalized = normalized[:200]

        return hashlib.md5(normalized.encode()).hexdigest()

    def get_stats(self) -> Dict:
        """Get validation statistics"""
        total = self.stats["total_validated"]
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "acceptance_rate": self.stats["accepted"] / total,
            "rejection_rate": (total - self.stats["accepted"]) / total,
        }

    def reset_stats(self):
        """Reset statistics"""
        for key in self.stats:
            self.stats[key] = 0


# Convenience function for quick validation
def validate_post(post: Dict, nlp_result: Dict = None, config: Dict = None) -> ValidationResult:
    """Quick validation of a single post"""
    validator = ContentValidator(config)
    return validator.validate(post, nlp_result)


# Default configuration
DEFAULT_VALIDATION_CONFIG = {
    "max_age_hours": 48,
    "geo_mode": "smart",
    "enable_duplicate_detection": True,
    "duplicate_window_hours": 24,
}
