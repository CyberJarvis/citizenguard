"""
BlueRadar - Complete NLP Pipeline
Advanced text analysis with pre-trained ML models
Supports: English, Hindi, Tamil, Telugu, Malayalam
"""

import re
import json
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from collections import Counter
from dataclasses import dataclass

from utils.logging_config import setup_logging
from config import (
    nlp_config, HAZARD_KEYWORDS, SEVERITY_KEYWORDS,
    ALL_SPAM_KEYWORDS, INDIAN_COASTAL_LOCATIONS, ALL_LOCATIONS
)

logger = setup_logging("nlp_pipeline")

# =============================================================================
# CHECK AVAILABLE LIBRARIES
# =============================================================================

TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False
LANGDETECT_AVAILABLE = False
DEVICE = "cpu"

try:
    import torch
    TORCH_AVAILABLE = True
    
    # Detect best device
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        DEVICE = "mps"  # Apple Silicon
    elif torch.cuda.is_available():
        DEVICE = "cuda"
    else:
        DEVICE = "cpu"
    
    logger.info(f"PyTorch available, device: {DEVICE}")
except ImportError:
    logger.warning("PyTorch not available, using rule-based NLP only")

try:
    from transformers import (
        pipeline,
        AutoTokenizer,
        AutoModelForSequenceClassification,
        AutoModelForTokenClassification
    )
    TRANSFORMERS_AVAILABLE = True
    logger.info("Transformers library available")
except ImportError:
    logger.warning("Transformers not available")

try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    logger.warning("langdetect not available")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PreprocessingResult:
    original: str
    clean_text: str
    normalized: str
    language: str
    is_code_mixed: bool
    hashtags: List[str]
    mentions: List[str]
    urls: List[str]
    emojis: List[str]
    word_count: int


@dataclass
class SpamResult:
    spam_score: int
    is_spam: bool
    reasons: List[str]
    confidence: float


@dataclass
class HazardResult:
    types: Dict[str, Dict]
    primary_hazard: Optional[str]
    hazard_count: int
    confidence: float


@dataclass 
class LocationResult:
    locations: List[Dict]
    primary_region: Optional[str]
    is_india: bool
    coordinates: Optional[Dict]


@dataclass
class SentimentResult:
    sentiment: str
    score: float
    urgency: str
    urgency_score: float


@dataclass
class SeverityResult:
    level: str
    score: int
    reasons: List[str]
    confidence: float


@dataclass
class AuthenticityResult:
    score: int
    factors: Dict[str, int]
    confidence: str
    flags: List[str]


# =============================================================================
# NLP PIPELINE
# =============================================================================

class NLPPipeline:
    """
    Complete NLP pipeline for hazard post analysis:
    
    Stages:
    1. Preprocessing (cleaning, language detection, translation)
    2. Spam Detection (rule-based + ML)
    3. Hazard Classification (multi-label)
    4. Named Entity Recognition (locations)
    5. Sentiment Analysis
    6. Severity Classification
    7. Authenticity Scoring
    8. Final Relevance Scoring
    """
    
    def __init__(self, use_ml: bool = True, device: str = "auto"):
        self.use_ml = use_ml and TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE
        self.device = DEVICE if device == "auto" else device
        
        # Model pipelines (lazy loaded)
        self.sentiment_pipe = None
        self.ner_pipe = None
        self.zero_shot_pipe = None
        self.translation_pipe = None
        
        self.models_loaded = False
        
        # Compile regex patterns
        self._compile_patterns()
        
        if self.use_ml:
            self._load_models()
        
        logger.info(f"NLP Pipeline initialized (ML: {self.use_ml}, Device: {self.device})")
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        self.url_pattern = re.compile(r'https?://\S+')
        self.hashtag_pattern = re.compile(r'#(\w+)')
        self.mention_pattern = re.compile(r'@(\w+)')
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        self.number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
    
    def _load_models(self):
        """Load ML models"""
        try:
            logger.info("Loading NLP models...")
            
            # Device index for transformers
            device_idx = 0 if self.device == "cuda" else -1
            
            # Sentiment Analysis
            try:
                self.sentiment_pipe = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    device=device_idx,
                    truncation=True,
                    max_length=512
                )
                logger.info("[OK] Sentiment model loaded")
            except Exception as e:
                logger.warning(f"Sentiment model failed: {e}")
            
            # NER for location extraction
            try:
                self.ner_pipe = pipeline(
                    "ner",
                    model="dslim/bert-base-NER",
                    device=device_idx,
                    aggregation_strategy="simple"
                )
                logger.info("[OK] NER model loaded")
            except Exception as e:
                logger.warning(f"NER model failed: {e}")
            
            # Zero-shot classification for hazard types
            try:
                self.zero_shot_pipe = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=device_idx
                )
                logger.info("[OK] Zero-shot classifier loaded")
            except Exception as e:
                logger.warning(f"Zero-shot model failed: {e}")
            
            self.models_loaded = True
            logger.info("NLP models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.use_ml = False
    
    # =========================================================================
    # MAIN PROCESSING
    # =========================================================================
    
    def process(self, posts: List[Dict]) -> List[Dict]:
        """
        Process list of posts through complete NLP pipeline.
        """
        logger.info(f"Processing {len(posts)} posts through NLP pipeline")
        
        processed = []
        
        for i, post in enumerate(posts):
            try:
                enriched = self._process_single(post)
                processed.append(enriched)
                
                if (i + 1) % 25 == 0:
                    logger.info(f"Progress: {i + 1}/{len(posts)} posts")
                    
            except Exception as e:
                logger.debug(f"Error processing post: {e}")
                post["nlp"] = self._get_default_nlp_result()
                processed.append(post)
        
        logger.info(f"[OK] Processed {len(processed)} posts")
        return processed
    
    def _process_single(self, post: Dict) -> Dict:
        """Process a single post through all stages"""
        # Get text content
        text = post.get("content", {}).get("text", "")
        
        if not text or len(text.strip()) < 5:
            post["nlp"] = self._get_default_nlp_result()
            return post
        
        # Stage 1: Preprocessing
        preprocessing = self._preprocess(text)
        
        # Stage 2: Spam Detection
        spam = self._detect_spam(preprocessing)
        
        # Skip further processing if spam
        if spam.is_spam:
            post["nlp"] = {
                "preprocessing": self._to_dict(preprocessing),
                "spam": self._to_dict(spam),
                "hazards": {"types": {}, "primary_hazard": None, "hazard_count": 0},
                "locations": {"locations": [], "primary_region": None, "is_india": False},
                "sentiment": {"sentiment": "neutral", "score": 0, "urgency": "low"},
                "severity": {"level": "LOW", "score": 0, "reasons": []},
                "authenticity": {"score": 30, "factors": {}, "confidence": "low"},
                "relevance_score": 0,
                "is_relevant": False,
                "is_spam": True,
                "processed_at": datetime.now().isoformat()
            }
            return post
        
        # Stage 3: Hazard Classification
        hazards = self._classify_hazards(preprocessing)
        
        # Stage 4: Location Extraction
        locations = self._extract_locations(preprocessing)
        
        # Stage 5: Sentiment Analysis
        sentiment = self._analyze_sentiment(preprocessing)
        
        # Stage 6: Severity Classification
        severity = self._classify_severity(preprocessing, hazards, sentiment)
        
        # Stage 7: Authenticity Scoring
        authenticity = self._score_authenticity(post, preprocessing)
        
        # Stage 8: Final Relevance Score
        relevance_score = self._calculate_relevance(
            hazards, locations, spam, severity, authenticity
        )
        
        # Compile results
        post["nlp"] = {
            "preprocessing": self._to_dict(preprocessing),
            "spam": self._to_dict(spam),
            "hazards": self._to_dict(hazards),
            "locations": self._to_dict(locations),
            "sentiment": self._to_dict(sentiment),
            "severity": self._to_dict(severity),
            "authenticity": self._to_dict(authenticity),
            "relevance_score": relevance_score,
            "is_relevant": relevance_score >= 40,
            "is_spam": False,
            "processed_at": datetime.now().isoformat()
        }
        
        return post
    
    def _to_dict(self, obj) -> Dict:
        """Convert dataclass to dict"""
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items()}
        return obj
    
    # =========================================================================
    # STAGE 1: PREPROCESSING
    # =========================================================================
    
    def _preprocess(self, text: str) -> PreprocessingResult:
        """Clean and preprocess text"""
        original = text
        
        # Extract components before cleaning
        urls = self.url_pattern.findall(text)
        hashtags = self.hashtag_pattern.findall(text)
        mentions = self.mention_pattern.findall(text)
        emojis = self.emoji_pattern.findall(text)
        
        # Clean text
        clean = text
        clean = self.url_pattern.sub('', clean)
        clean = self.hashtag_pattern.sub(r'\1', clean)  # Keep hashtag text
        clean = self.mention_pattern.sub(r'\1', clean)  # Keep mention text
        clean = self.emoji_pattern.sub(' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Normalize
        normalized = clean.lower()
        
        # Detect language
        language = "en"
        is_code_mixed = False
        
        if LANGDETECT_AVAILABLE and len(clean) > 10:
            try:
                langs = detect_langs(clean)
                if langs:
                    language = langs[0].lang
                    # Check for code-mixing
                    if len(langs) > 1 and langs[1].prob > 0.2:
                        is_code_mixed = True
            except LangDetectException:
                pass
        
        return PreprocessingResult(
            original=original,
            clean_text=clean,
            normalized=normalized,
            language=language,
            is_code_mixed=is_code_mixed,
            hashtags=hashtags,
            mentions=mentions,
            urls=urls,
            emojis=emojis,
            word_count=len(clean.split())
        )
    
    # =========================================================================
    # STAGE 2: SPAM DETECTION
    # =========================================================================
    
    def _detect_spam(self, prep: PreprocessingResult) -> SpamResult:
        """Detect spam/promotional content"""
        text_lower = prep.normalized
        score = 0
        reasons = []
        
        # Check spam keywords
        for keyword in ALL_SPAM_KEYWORDS:
            if keyword.lower() in text_lower:
                score += 15
                reasons.append(f"spam_keyword:{keyword}")
        
        # Excessive hashtags
        if len(prep.hashtags) > 10:
            score += 20
            reasons.append("excessive_hashtags")
        
        # Excessive URLs
        if len(prep.urls) > 3:
            score += 20
            reasons.append("excessive_urls")
        
        # All caps ratio
        if prep.clean_text:
            caps_ratio = sum(1 for c in prep.clean_text if c.isupper()) / len(prep.clean_text)
            if caps_ratio > 0.6:
                score += 15
                reasons.append("excessive_caps")
        
        # Very short text with links
        if prep.word_count < 10 and prep.urls:
            score += 15
            reasons.append("short_with_links")
        
        # Bot-like patterns
        bot_patterns = [
            r'follow.*follow',
            r'dm.*for',
            r'link.*bio',
            r'check.*profile'
        ]
        for pattern in bot_patterns:
            if re.search(pattern, text_lower):
                score += 20
                reasons.append("bot_pattern")
                break
        
        is_spam = score >= 50
        confidence = min(1.0, score / 100)
        
        return SpamResult(
            spam_score=min(100, score),
            is_spam=is_spam,
            reasons=reasons,
            confidence=confidence
        )
    
    # =========================================================================
    # STAGE 3: HAZARD CLASSIFICATION
    # =========================================================================
    
    def _classify_hazards(self, prep: PreprocessingResult) -> HazardResult:
        """Classify hazard types"""
        text_lower = prep.normalized
        detected = {}
        
        # Rule-based classification
        for hazard_type, hazard_data in HAZARD_KEYWORDS.items():
            score = 0
            matched_keywords = []
            weight = hazard_data.get("weight", 50)
            
            # Check all language keywords
            for lang_key in ["english", "hindi", "tamil", "telugu"]:
                keywords = hazard_data.get(lang_key, [])
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        score += weight * 0.5
                        matched_keywords.append(keyword)
            
            if score > 0:
                detected[hazard_type] = {
                    "confidence": min(1.0, score / 100),
                    "keywords": matched_keywords,
                    "weight": weight
                }
        
        # ML-based classification (zero-shot)
        if self.use_ml and self.zero_shot_pipe and len(prep.clean_text) > 20:
            try:
                labels = list(HAZARD_KEYWORDS.keys())
                result = self.zero_shot_pipe(
                    prep.clean_text[:500],
                    labels,
                    multi_label=True
                )
                
                for label, score in zip(result["labels"], result["scores"]):
                    if score > 0.3:
                        if label in detected:
                            detected[label]["confidence"] = max(
                                detected[label]["confidence"],
                                score
                            )
                            detected[label]["ml_score"] = score
                        else:
                            detected[label] = {
                                "confidence": score,
                                "keywords": [],
                                "ml_score": score
                            }
                            
            except Exception as e:
                logger.debug(f"Zero-shot classification failed: {e}")
        
        # Sort by confidence
        sorted_hazards = sorted(
            detected.items(),
            key=lambda x: x[1].get("confidence", 0),
            reverse=True
        )
        
        primary = sorted_hazards[0][0] if sorted_hazards else None
        overall_confidence = sorted_hazards[0][1].get("confidence", 0) if sorted_hazards else 0
        
        return HazardResult(
            types=dict(sorted_hazards),
            primary_hazard=primary,
            hazard_count=len(detected),
            confidence=overall_confidence
        )
    
    # =========================================================================
    # STAGE 4: LOCATION EXTRACTION
    # =========================================================================
    
    def _extract_locations(self, prep: PreprocessingResult) -> LocationResult:
        """Extract location entities"""
        text_lower = prep.normalized
        locations = []
        
        # Rule-based: Check Indian coastal locations
        for region, subregions in INDIAN_COASTAL_LOCATIONS.items():
            for subregion, cities in subregions.items():
                for city in cities:
                    city_lower = city.lower().replace("_", " ")
                    if city_lower in text_lower:
                        locations.append({
                            "text": city,
                            "normalized": city.replace("_", " ").title(),
                            "region": region,
                            "subregion": subregion,
                            "type": "indian_coast",
                            "confidence": 0.9
                        })
        
        # ML-based NER
        if self.use_ml and self.ner_pipe and len(prep.clean_text) > 10:
            try:
                entities = self.ner_pipe(prep.clean_text[:500])
                
                for entity in entities:
                    if entity["entity_group"] in ["LOC", "GPE"]:
                        entity_text = entity["word"].lower().replace("##", "")
                        
                        # Skip if already found
                        if any(loc["text"].lower() == entity_text for loc in locations):
                            continue
                        
                        # Check if it's an Indian location
                        is_indian = entity_text in ALL_LOCATIONS
                        
                        locations.append({
                            "text": entity["word"],
                            "normalized": entity["word"].title(),
                            "region": "india" if is_indian else "unknown",
                            "subregion": None,
                            "type": "ner_extracted",
                            "confidence": entity["score"]
                        })
                        
            except Exception as e:
                logger.debug(f"NER failed: {e}")
        
        # Determine primary region
        indian_locations = [loc for loc in locations if loc["type"] == "indian_coast"]
        
        if indian_locations:
            regions = [loc["region"] for loc in indian_locations]
            primary_region = Counter(regions).most_common(1)[0][0]
        else:
            primary_region = None
        
        return LocationResult(
            locations=locations,
            primary_region=primary_region,
            is_india=len(indian_locations) > 0,
            coordinates=None
        )
    
    # =========================================================================
    # STAGE 5: SENTIMENT ANALYSIS
    # =========================================================================
    
    def _analyze_sentiment(self, prep: PreprocessingResult) -> SentimentResult:
        """Analyze sentiment and urgency"""
        sentiment = "neutral"
        score = 0.0
        
        # ML-based sentiment
        if self.use_ml and self.sentiment_pipe and len(prep.clean_text) > 10:
            try:
                result = self.sentiment_pipe(prep.clean_text[:512])[0]
                label = result["label"].lower()
                conf = result["score"]
                
                if "positive" in label:
                    sentiment = "positive"
                    score = conf
                elif "negative" in label:
                    sentiment = "negative"
                    score = -conf
                else:
                    sentiment = "neutral"
                    score = 0
                    
            except Exception as e:
                logger.debug(f"Sentiment analysis failed: {e}")
        
        # Urgency detection (rule-based)
        text_lower = prep.normalized
        urgency = "low"
        urgency_score = 0.0
        
        urgency_keywords = {
            "critical": [
                "emergency", "evacuate", "immediately", "now", "critical",
                "urgent", "life threatening", "danger", "hurry"
            ],
            "high": [
                "warning", "alert", "severe", "dangerous", "major",
                "serious", "significant", "damage"
            ],
            "medium": [
                "advisory", "caution", "attention", "watch", "expected",
                "likely", "possible", "monitor"
            ]
        }
        
        for level, keywords in urgency_keywords.items():
            if any(kw in text_lower for kw in keywords):
                urgency = level
                urgency_score = {"critical": 1.0, "high": 0.75, "medium": 0.5}.get(level, 0.25)
                break
        
        return SentimentResult(
            sentiment=sentiment,
            score=score,
            urgency=urgency,
            urgency_score=urgency_score
        )
    
    # =========================================================================
    # STAGE 6: SEVERITY CLASSIFICATION
    # =========================================================================
    
    def _classify_severity(
        self,
        prep: PreprocessingResult,
        hazards: HazardResult,
        sentiment: SentimentResult
    ) -> SeverityResult:
        """Classify severity level"""
        text_lower = prep.normalized
        score = 0
        reasons = []
        
        # Check severity keywords
        for level, level_data in SEVERITY_KEYWORDS.items():
            keywords = level_data.get("keywords", [])
            level_score = level_data.get("score", 50)
            
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += level_score * 0.4
                    reasons.append(f"{level}:{keyword}")
                    break  # One match per level
        
        # Hazard type contribution
        high_risk_hazards = ["tsunami", "cyclone"]
        medium_risk_hazards = ["flood", "storm_surge"]
        
        if hazards.primary_hazard in high_risk_hazards:
            score += 25
            reasons.append(f"high_risk_hazard:{hazards.primary_hazard}")
        elif hazards.primary_hazard in medium_risk_hazards:
            score += 15
            reasons.append(f"medium_risk_hazard:{hazards.primary_hazard}")
        
        # Urgency contribution
        if sentiment.urgency == "critical":
            score += 25
            reasons.append("urgency:critical")
        elif sentiment.urgency == "high":
            score += 15
            reasons.append("urgency:high")
        
        # Negative sentiment contribution
        if sentiment.sentiment == "negative":
            score += 10
        
        # Casualty/damage mentions
        casualty_keywords = ["death", "dead", "killed", "injured", "missing", "trapped", "stranded"]
        if any(kw in text_lower for kw in casualty_keywords):
            score += 30
            reasons.append("casualty_mention")
        
        # Determine level
        score = min(100, score)
        
        if score >= 70:
            level = "CRITICAL"
        elif score >= 50:
            level = "HIGH"
        elif score >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        confidence = min(1.0, score / 100)
        
        return SeverityResult(
            level=level,
            score=int(score),
            reasons=reasons[:5],  # Limit reasons
            confidence=confidence
        )
    
    # =========================================================================
    # STAGE 7: AUTHENTICITY SCORING
    # =========================================================================
    
    def _score_authenticity(
        self,
        post: Dict,
        prep: PreprocessingResult
    ) -> AuthenticityResult:
        """Score post authenticity"""
        score = 50  # Base score
        factors = {}
        flags = []
        
        # Author factors
        author = post.get("author", {})
        
        # Verified account
        if author.get("is_verified"):
            score += 25
            factors["verified_account"] = 25
        
        # Official account
        if author.get("is_official"):
            score += 30
            factors["official_account"] = 30
        
        # Follower count
        followers = author.get("followers")
        if followers:
            if followers > 100000:
                score += 20
                factors["very_high_followers"] = 20
            elif followers > 10000:
                score += 15
                factors["high_followers"] = 15
            elif followers > 1000:
                score += 10
                factors["medium_followers"] = 10
            elif followers < 50:
                score -= 10
                factors["low_followers"] = -10
                flags.append("suspicious_low_followers")
        
        # Content factors
        content = post.get("content", {})
        
        # Has specific location
        location = post.get("location", {})
        if location.get("tagged"):
            score += 10
            factors["location_tagged"] = 10
        
        # Has media
        media = post.get("media", {})
        if media.get("count", 0) > 0:
            score += 10
            factors["has_media"] = 10
        
        # Temporal factors
        temporal = post.get("temporal", {})
        age_hours = temporal.get("age_hours")
        
        if age_hours is not None:
            if age_hours < 1:
                score += 15
                factors["very_recent"] = 15
            elif age_hours < 24:
                score += 10
                factors["recent"] = 10
            elif age_hours > 72:
                score -= 10
                factors["old_post"] = -10
        
        # Text quality
        if prep.word_count > 20:
            score += 5
            factors["detailed_content"] = 5
        
        # Determine confidence
        score = max(0, min(100, score))
        
        if score >= 70:
            confidence = "high"
        elif score >= 50:
            confidence = "medium"
        else:
            confidence = "low"
        
        return AuthenticityResult(
            score=score,
            factors=factors,
            confidence=confidence,
            flags=flags
        )
    
    # =========================================================================
    # STAGE 8: RELEVANCE SCORING
    # =========================================================================
    
    def _calculate_relevance(
        self,
        hazards: HazardResult,
        locations: LocationResult,
        spam: SpamResult,
        severity: SeverityResult,
        authenticity: AuthenticityResult
    ) -> int:
        """Calculate final relevance score"""
        score = 0
        
        # Hazard detection (max 40)
        if hazards.hazard_count > 0:
            score += int(hazards.confidence * 40)
        
        # Location relevance (max 30)
        if locations.is_india:
            score += 30
        elif locations.locations:
            score += 15
        
        # Severity bonus (max 20)
        if severity.level == "CRITICAL":
            score += 20
        elif severity.level == "HIGH":
            score += 15
        elif severity.level == "MEDIUM":
            score += 10
        elif severity.level == "LOW":
            score += 5
        
        # Authenticity bonus (max 10)
        if authenticity.score >= 70:
            score += 10
        elif authenticity.score >= 50:
            score += 5
        
        # Spam penalty
        if spam.is_spam:
            score = 0
        elif spam.spam_score > 30:
            score = max(0, score - 20)
        
        return min(100, score)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _get_default_nlp_result(self) -> Dict:
        """Default NLP result for empty/failed processing"""
        return {
            "preprocessing": {
                "clean_text": "",
                "language": "unknown",
                "word_count": 0
            },
            "spam": {"spam_score": 0, "is_spam": False, "reasons": []},
            "hazards": {"types": {}, "primary_hazard": None, "hazard_count": 0},
            "locations": {"locations": [], "primary_region": None, "is_india": False},
            "sentiment": {"sentiment": "neutral", "score": 0, "urgency": "low"},
            "severity": {"level": "LOW", "score": 0, "reasons": []},
            "authenticity": {"score": 50, "factors": {}, "confidence": "low"},
            "relevance_score": 0,
            "is_relevant": False,
            "is_spam": False,
            "processed_at": datetime.now().isoformat()
        }
    
    def get_summary(self, posts: List[Dict]) -> Dict:
        """Generate summary statistics"""
        total = len(posts)
        
        if total == 0:
            return {"total_processed": 0}
        
        relevant = [p for p in posts if p.get("nlp", {}).get("is_relevant")]
        spam = [p for p in posts if p.get("nlp", {}).get("is_spam")]
        
        # Hazard distribution
        hazard_counts = Counter()
        for post in relevant:
            primary = post.get("nlp", {}).get("hazards", {}).get("primary_hazard")
            if primary:
                hazard_counts[primary] += 1
        
        # Severity distribution
        severity_counts = Counter()
        for post in relevant:
            level = post.get("nlp", {}).get("severity", {}).get("level", "LOW")
            severity_counts[level] += 1
        
        # Region distribution
        region_counts = Counter()
        for post in relevant:
            region = post.get("nlp", {}).get("locations", {}).get("primary_region")
            if region:
                region_counts[region] += 1
        
        # Language distribution
        lang_counts = Counter()
        for post in posts:
            lang = post.get("nlp", {}).get("preprocessing", {}).get("language", "unknown")
            lang_counts[lang] += 1
        
        return {
            "total_processed": total,
            "relevant_count": len(relevant),
            "spam_count": len(spam),
            "relevance_rate": f"{len(relevant)/total*100:.1f}%" if total > 0 else "0%",
            "hazard_distribution": dict(hazard_counts.most_common()),
            "severity_distribution": dict(severity_counts),
            "region_distribution": dict(region_counts.most_common()),
            "language_distribution": dict(lang_counts.most_common()),
            "critical_count": severity_counts.get("CRITICAL", 0),
            "high_count": severity_counts.get("HIGH", 0)
        }
    
    def process_single(self, text: str) -> Dict:
        """Process a single text (for testing)"""
        post = {"content": {"text": text}}
        processed = self._process_single(post)
        return processed.get("nlp", {})


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

nlp_pipeline = NLPPipeline(use_ml=True)
