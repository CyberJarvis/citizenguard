"""
Coast Guardian Analysis Service
Integrates LLM analysis, FAISS vector similarity, priority scoring, and credibility assessment
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re

from llm_client import CoastGuardianLLM
from api.models import (
    SocialMediaPost, DisasterAnalysis, ProcessedPost, MisinformationAnalysis,
    DisasterType, UrgencyLevel, SentimentType
)
from api.misinformation_service import CoastGuardianMisinformationDetector
from api.enhanced_nlp_service import get_enhanced_nlp_service, SentimentAnalysis, EmotionAnalysis
from api.vector_service import get_vector_db, CoastGuardianVectorDB

class CoastGuardianAnalysisService:
    """Advanced analysis service for social media posts"""

    def __init__(self):
        self.llm = CoastGuardianLLM()
        self.misinformation_detector = CoastGuardianMisinformationDetector()
        self.enhanced_nlp = get_enhanced_nlp_service()

        # Initialize vector database (will be lazy-loaded)
        self.vector_db: Optional[CoastGuardianVectorDB] = None

        # Enhanced priority scoring weights for marine disaster response (with NLP)
        self.priority_weights = {
            'relevance_score': 0.16,         # LLM relevance (reduced to make room for emotions)
            'vector_relevance': 0.07,        # Vector similarity relevance
            'urgency_multiplier': 0.18,      # Disaster urgency (reduced)
            'emotional_urgency': 0.12,       # NEW: Emotional urgency from NLP
            'credibility_score': 0.11,       # Source credibility
            'misinformation_penalty': 0.11,  # Misinformation risk adjustment
            'location_specificity': 0.09,    # Coastal/specific location
            'time_sensitivity': 0.07,        # Recency of post
            'platform_credibility': 0.05,    # Platform reliability
            'user_verification': 0.02,       # Verified/official accounts
            'social_engagement': 0.02        # Likes, shares, comments
        }

        # Platform credibility scores for marine disaster reporting
        self.platform_credibility = {
            'news': 0.9,        # Official news outlets
            'twitter': 0.7,     # Real-time updates but mixed reliability
            'facebook': 0.6,    # Community reports but algorithm concerns
            'instagram': 0.5,   # Visual evidence but less text context
            'reddit': 0.4,      # Community driven but anonymous
            'youtube': 0.4      # Video evidence but processing time
        }

        # Credibility indicators
        self.credibility_indicators = {
            'positive': [
                'official_source', 'verified_account', 'location_specific',
                'multiple_sources', 'contact_info', 'government_handle',
                'news_outlet', 'emergency_service'
            ],
            'negative': [
                'anonymous_source', 'vague_location', 'sensational_language',
                'no_evidence', 'conspiracy_language', 'clickbait_style'
            ]
        }

        # Enhanced Indian coastal locations with priority weights
        self.coastal_locations = {
            # Major ports (highest priority)
            'mumbai': 1.0, 'chennai': 1.0, 'kolkata': 1.0, 'visakhapatnam': 1.0,
            'kochi': 1.0, 'kandla': 1.0, 'paradip': 1.0,

            # Important coastal cities
            'mangalore': 0.9, 'tuticorin': 0.9, 'haldia': 0.9, 'marmagao': 0.9,
            'ennore': 0.8, 'bhavnagar': 0.8, 'kakinada': 0.8,

            # Popular coastal areas
            'marina beach': 0.8, 'juhu': 0.7, 'baga': 0.7, 'puri': 0.8,
            'mahabalipuram': 0.7, 'kovalam': 0.7, 'calicut': 0.8,

            # Coastal states/islands
            'andaman': 0.9, 'lakshadweep': 0.9, 'goa': 0.8,
            'kerala': 0.7, 'tamil nadu': 0.7, 'odisha': 0.7,
            'west bengal': 0.7, 'karnataka': 0.7, 'gujarat': 0.8,
            'andhra pradesh': 0.7, 'maharashtra': 0.7,

            # Additional critical coastal locations
            'dwarka': 0.8, 'somnath': 0.7, 'rameswaram': 0.8, 'puducherry': 0.7,
            'diu': 0.6, 'daman': 0.6, 'mamallapuram': 0.7, 'cuddalore': 0.7
        }

        # High-risk marine disaster zones (for enhanced prioritization)
        self.high_risk_zones = {
            'cyclone': ['odisha', 'west bengal', 'andhra pradesh', 'tamil nadu'],
            'tsunami': ['kerala', 'tamil nadu', 'andhra pradesh', 'odisha', 'andaman'],
            'oil_spill': ['mumbai', 'kandla', 'chennai', 'visakhapatnam', 'kochi'],
            'flooding': ['mumbai', 'kolkata', 'chennai', 'kochi'],
            'earthquake': ['andaman', 'gujarat', 'maharashtra']
        }

    def _get_vector_db(self) -> Optional[CoastGuardianVectorDB]:
        """Lazy-load vector database"""
        if self.vector_db is None:
            try:
                self.vector_db = get_vector_db()
                if self.vector_db is None:
                    from api.vector_service import initialize_vector_db
                    self.vector_db = initialize_vector_db()
            except Exception as e:
                print(f"❌ Vector DB initialization failed: {e}")
                self.vector_db = None
        return self.vector_db

    def analyze_post(self, post: SocialMediaPost) -> ProcessedPost:
        """Complete analysis of a social media post with LLM + Vector similarity"""
        start_time = time.time()

        try:
            # Use improved fallback analysis with basic keyword detection
            text_lower = post.text.lower()

            # Basic disaster detection
            relevance_score = 0.0
            disaster_type = 'none'
            urgency = 'low'
            keywords = []

            # Tsunami detection
            if any(word in text_lower for word in ['tsunami', 'wave', 'waves', 'evacuate', 'evacuation']):
                relevance_score = 8.0
                disaster_type = 'tsunami'
                urgency = 'critical' if any(word in text_lower for word in ['urgent', 'immediately', 'evacuate']) else 'high'
                keywords = ['tsunami', 'waves', 'evacuation']

            # Cyclone detection
            elif any(word in text_lower for word in ['cyclone', 'storm', 'hurricane', 'typhoon', 'wind speed']):
                relevance_score = 7.0
                disaster_type = 'cyclone'
                urgency = 'high' if any(word in text_lower for word in ['severe', 'danger', 'warning']) else 'medium'
                keywords = ['cyclone', 'storm', 'wind']

            # Oil spill detection
            elif any(word in text_lower for word in ['oil spill', 'oil leak', 'crude oil', 'tanker accident']):
                relevance_score = 7.5
                disaster_type = 'oil_spill'
                urgency = 'high'
                keywords = ['oil', 'spill', 'environmental']

            # Flooding detection
            elif any(word in text_lower for word in ['flood', 'flooding', 'waterlogged', 'heavy rain']):
                relevance_score = 6.0
                disaster_type = 'flooding'
                urgency = 'medium'
                keywords = ['flood', 'rain', 'water']

            # General marine/coastal content
            elif any(word in text_lower for word in ['coast', 'beach', 'port', 'marine', 'sea', 'ocean']):
                relevance_score = 2.0
                keywords = ['coastal', 'marine']

            # Sentiment analysis
            sentiment = 'negative' if any(word in text_lower for word in ['panic', 'scared', 'emergency', 'disaster', 'danger']) else 'neutral'

            llm_analysis = {
                'relevance_score': relevance_score,
                'disaster_type': disaster_type,
                'urgency': urgency,
                'sentiment': sentiment,
                'keywords': keywords,
                'confidence_score': 0.8 if relevance_score > 5 else 0.5
            }

            # Skip vector analysis for performance (disabled temporarily)
            vector_enhancement = None

            # Combine both analyses
            enhanced_analysis = self._enhance_analysis(post, llm_analysis, vector_enhancement)

            # Additional safety check for disaster_type before creating DisasterAnalysis
            enhanced_analysis['disaster_type'] = self._normalize_disaster_type(enhanced_analysis.get('disaster_type', 'none'))

            # Create disaster analysis object
            disaster_analysis = DisasterAnalysis(**enhanced_analysis)

            # Perform misinformation detection
            misinformation_analysis = self._perform_misinformation_analysis(post, disaster_analysis)

            # Calculate priority level (now includes vector data and misinformation risk)
            priority_level = self._calculate_priority(disaster_analysis, post, vector_enhancement, misinformation_analysis)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Create processed post with comprehensive analysis
            processed_post = ProcessedPost(
                original_post=post,
                analysis=disaster_analysis,
                misinformation_analysis=misinformation_analysis,
                processing_time_ms=processing_time,
                priority_level=priority_level
            )

            # Add processed post to vector database for learning
            self._update_vector_db(post, disaster_analysis)

            return processed_post

        except Exception as e:
            print(f"❌ Analysis error: {e}")
            print(f"🔧 Enhanced analysis data: {enhanced_analysis if 'enhanced_analysis' in locals() else 'Not created yet'}")
            # Return minimal analysis on error
            return self._create_fallback_analysis(post, start_time)

    def _get_vector_analysis(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Get vector similarity analysis for the post"""
        vector_db = self._get_vector_db()

        if not vector_db:
            return {"error": "Vector database not available"}

        try:
            return vector_db.enhance_post_analysis(post)
        except Exception as e:
            print(f"❌ Vector analysis error: {e}")
            return {"error": str(e)}

    def _update_vector_db(self, post: SocialMediaPost, analysis: DisasterAnalysis):
        """Update vector database with new analysis for learning"""
        vector_db = self._get_vector_db()

        if not vector_db:
            return

        try:
            # Add post to vector database for future similarity matching
            metadata = {
                "platform": post.platform,
                "language": post.language,
                "location": post.location,
                "relevance_score": analysis.relevance_score,
                "urgency": analysis.urgency,
                "confidence": analysis.confidence_score,
                "source": "analyzed_post"
            }

            vector_db.add_text(post.text, analysis.disaster_type, metadata)

        except Exception as e:
            print(f"❌ Vector DB update error: {e}")

    def _perform_misinformation_analysis(self, post: SocialMediaPost, analysis: DisasterAnalysis) -> MisinformationAnalysis:
        """Perform comprehensive misinformation detection"""
        try:
            # Detect misinformation using the dedicated service
            flags = self.misinformation_detector.detect_misinformation(post, analysis)

            # Generate comprehensive report
            report = self.misinformation_detector.generate_misinformation_report(post, analysis, flags)

            # Create MisinformationAnalysis object
            return MisinformationAnalysis(
                risk_level=report["misinformation_assessment"]["risk_level"],
                confidence_score=flags.confidence_score,
                suspicious_language_flags=flags.suspicious_language,
                credibility_concerns=flags.credibility_issues,
                fact_check_warnings=flags.fact_check_warnings,
                source_reliability=flags.source_reliability,
                verification_suggestions=report["verification_suggestions"],
                recommendation=report["misinformation_assessment"]["recommendation"]
            )

        except Exception as e:
            print(f"❌ Misinformation analysis error: {e}")
            # Return minimal analysis on error
            return MisinformationAnalysis(
                risk_level="minimal_misinformation_risk",
                confidence_score=0.1,
                suspicious_language_flags=[],
                credibility_concerns=["analysis_error"],
                fact_check_warnings=[],
                source_reliability="very_low_reliability",
                verification_suggestions=["Manual verification required due to analysis error"],
                recommendation="Unable to assess misinformation risk due to technical error"
            )

    def _normalize_disaster_type(self, disaster_type) -> str:
        """Normalize disaster type to match expected enum values"""
        if not disaster_type:
            return "none"

        # Handle various input types
        if isinstance(disaster_type, list):
            if not disaster_type:
                return "none"
            disaster_type = disaster_type[0] if disaster_type else "none"

        # Convert to string and lowercase
        disaster_type = str(disaster_type).lower().strip()

        # Handle empty strings
        if not disaster_type or disaster_type in ['', 'null', 'none']:
            return "none"

        # Mapping of common variations to expected values
        type_mapping = {
            'flood': 'flooding',
            'floods': 'flooding',
            'tornado': 'none',  # Not in our expected types
            'hurricane': 'cyclone',
            'typhoon': 'cyclone',
            'storm': 'cyclone',
            'oil': 'oil_spill',
            'spill': 'oil_spill',
            'quake': 'earthquake',
            'seismic': 'earthquake'
        }

        # Apply mapping if found
        if disaster_type in type_mapping:
            return type_mapping[disaster_type]

        # Valid disaster types
        valid_types = ['tsunami', 'cyclone', 'oil_spill', 'flooding', 'earthquake', 'none']

        # Return if already valid
        if disaster_type in valid_types:
            return disaster_type

        # Default fallback
        return "none"

    def _enhance_analysis(self, post: SocialMediaPost, llm_analysis: Dict[str, Any], vector_enhancement: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhance LLM analysis with additional processing including advanced NLP"""

        # Simplified NLP analysis (skip expensive operations for performance)
        class SimpleObject:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        sentiment_analysis = SimpleObject(
            sentiment=llm_analysis.get('sentiment', 'neutral'),
            polarity_score=0.0,
            confidence=0.5,
            subjectivity_score=0.5,
            emotion_scores={}
        )
        emotion_analysis = SimpleObject(
            primary_emotion='neutral',
            emotion_intensity=0.5,
            panic_level=0.0,
            urgency_emotion='none',
            fear_indicators=[],
            stress_indicators=[],
            hope_indicators=[]
        )
        entity_extraction = SimpleObject(
            locations=[],
            organizations=[],
            persons=[],
            timestamps=[],
            quantities=[],
            marine_entities=[]
        )
        enhanced_keywords_nlp = []
        emotional_urgency = SimpleObject(emotional_urgency=0.5, panic_level=0.0)

        # Enhanced location detection (combine existing + NLP entities)
        location_mentioned = self._extract_location(post.text)
        if not location_mentioned and post.location:
            location_mentioned = post.location

        # Use NLP-extracted locations if none found
        if not location_mentioned and entity_extraction.locations:
            location_mentioned = entity_extraction.locations[0]['name']

        # Enhanced credibility assessment
        credibility_score, credibility_indicators = self._assess_credibility(post)

        # Enhanced keyword extraction (combine existing + NLP)
        enhanced_keywords = self._extract_enhanced_keywords(post.text, llm_analysis.get('keywords', []))

        # Add NLP keywords
        nlp_keywords = [kw['keyword'] for kw in enhanced_keywords_nlp[:10]]
        enhanced_keywords.extend(nlp_keywords)
        enhanced_keywords = list(set(enhanced_keywords))[:15]  # Remove duplicates, limit

        # Enhanced confidence calculation
        confidence_score = self._calculate_confidence(post, llm_analysis)

        # Integrate vector analysis if available
        vector_relevance_score = 0
        vector_disaster_type = self._normalize_disaster_type(llm_analysis.get('disaster_type', 'none'))

        if vector_enhancement and 'vector_classification' in vector_enhancement:
            vector_class = vector_enhancement['vector_classification']

            # Use vector score if higher than LLM score
            if 'relevance_score' in vector_class:
                vector_relevance_score = vector_class['relevance_score']

            # Use vector disaster type if confidence is high
            if 'predicted_disaster_type' in vector_class and vector_class.get('confidence', 0) > 0.6:
                vector_disaster_type = self._normalize_disaster_type(vector_class['predicted_disaster_type'])

            # Merge vector keywords
            if 'vector_keywords' in vector_enhancement:
                enhanced_keywords.extend(vector_enhancement['vector_keywords'])
                enhanced_keywords = list(set(enhanced_keywords))[:10]  # Remove duplicates, limit

        # Final relevance score (weighted average of LLM and Vector)
        llm_relevance = llm_analysis.get('relevance_score', 0)
        if vector_relevance_score > 0:
            # Weight: 70% LLM, 30% Vector
            final_relevance_score = (0.7 * llm_relevance) + (0.3 * vector_relevance_score)
        else:
            final_relevance_score = llm_relevance

        return {
            'relevance_score': round(final_relevance_score, 1),
            'disaster_type': self._normalize_disaster_type(vector_disaster_type),
            'urgency': llm_analysis.get('urgency', 'low'),
            'sentiment': sentiment_analysis.sentiment,  # Use enhanced sentiment instead of LLM
            'keywords': enhanced_keywords,
            'credibility_indicators': credibility_indicators,
            'location_mentioned': location_mentioned,
            'language_detected': post.language,
            'confidence_score': confidence_score,
            # Store vector insights for priority calculation
            '_vector_relevance': vector_relevance_score,
            '_vector_confidence': vector_enhancement.get('vector_classification', {}).get('confidence', 0) if vector_enhancement else 0,

            # Enhanced NLP data
            '_enhanced_sentiment': {
                'sentiment': sentiment_analysis.sentiment,
                'polarity_score': sentiment_analysis.polarity_score,
                'confidence': sentiment_analysis.confidence,
                'subjectivity': sentiment_analysis.subjectivity_score,
                'emotion_scores': sentiment_analysis.emotion_scores
            },
            '_emotion_analysis': {
                'primary_emotion': emotion_analysis.primary_emotion,
                'emotion_intensity': emotion_analysis.emotion_intensity,
                'panic_level': emotion_analysis.panic_level,
                'urgency_emotion': emotion_analysis.urgency_emotion,
                'fear_indicators': emotion_analysis.fear_indicators,
                'stress_indicators': emotion_analysis.stress_indicators,
                'hope_indicators': emotion_analysis.hope_indicators
            },
            '_entity_extraction': {
                'locations': entity_extraction.locations,
                'organizations': entity_extraction.organizations,
                'persons': entity_extraction.persons,
                'timestamps': entity_extraction.timestamps,
                'quantities': entity_extraction.quantities,
                'marine_entities': entity_extraction.marine_entities
            },
            '_emotional_urgency': emotional_urgency,
            '_enhanced_keywords': enhanced_keywords_nlp
        }

    def _extract_location(self, text: str) -> str:
        """Extract location mentions from text"""
        text_lower = text.lower()

        # Check for coastal locations
        for location in self.coastal_locations:
            if location in text_lower:
                return location.title()

        # Extract patterns like "near [location]", "at [location]", "in [location]"
        location_patterns = [
            r'(?:near|at|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:coast|beach|port|harbor)'
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]

        return None

    def _assess_credibility(self, post: SocialMediaPost) -> tuple[float, List[str]]:
        """Assess post credibility based on multiple factors"""
        credibility_score = 0.5  # Base credibility
        indicators = []

        # User credibility factors
        if post.user:
            if post.user.verified:
                credibility_score += 0.3
                indicators.append('verified_account')

            if post.user.follower_count > 10000:
                credibility_score += 0.1
                indicators.append('high_followers')

            # Check for official/government handles
            username_lower = post.user.username.lower()
            if any(term in username_lower for term in ['govt', 'official', 'police', 'emergency', 'coast']):
                credibility_score += 0.2
                indicators.append('official_source')

        # Content credibility factors
        text_lower = post.text.lower()

        # Positive indicators
        if any(indicator in text_lower for indicator in ['official', 'confirmed', 'authorities']):
            credibility_score += 0.1
            indicators.append('official_language')

        if re.search(r'\d{1,2}:\d{2}', post.text):  # Time mentions
            credibility_score += 0.05
            indicators.append('specific_time')

        # Location specificity
        if self._extract_location(post.text):
            credibility_score += 0.1
            indicators.append('location_specific')

        # Negative indicators
        if any(term in text_lower for term in ['rumor', 'unconfirmed', 'fake']):
            credibility_score -= 0.2
            indicators.append('uncertainty_language')

        # Excessive caps or exclamation marks
        if len(re.findall(r'[A-Z]{3,}', post.text)) > 2:
            credibility_score -= 0.1
            indicators.append('excessive_caps')

        if post.text.count('!') > 5:
            credibility_score -= 0.1
            indicators.append('excessive_exclamation')

        return max(0.0, min(1.0, credibility_score)), indicators

    def _extract_enhanced_keywords(self, text: str, base_keywords: List[str]) -> List[str]:
        """Extract enhanced keywords including location and urgency terms"""
        enhanced_keywords = base_keywords.copy()

        # Disaster-specific keywords
        disaster_keywords = {
            'tsunami': ['wave', 'surge', 'seismic', 'evacuation'],
            'cyclone': ['storm', 'wind', 'hurricane', 'landfall'],
            'oil_spill': ['pollution', 'leak', 'contamination', 'cleanup'],
            'flooding': ['flood', 'inundation', 'waterlogging', 'overflow'],
            'earthquake': ['tremor', 'quake', 'aftershock', 'magnitude']
        }

        # Extract disaster-related terms
        text_lower = text.lower()
        for disaster_type, keywords in disaster_keywords.items():
            for keyword in keywords:
                if keyword in text_lower and keyword not in enhanced_keywords:
                    enhanced_keywords.append(keyword)

        # Extract urgency keywords
        urgency_keywords = ['emergency', 'urgent', 'immediate', 'critical', 'alert', 'warning']
        for keyword in urgency_keywords:
            if keyword in text_lower and keyword not in enhanced_keywords:
                enhanced_keywords.append(keyword)

        return enhanced_keywords[:10]  # Limit to top 10 keywords

    def _calculate_confidence(self, post: SocialMediaPost, llm_analysis: Dict[str, Any]) -> float:
        """Calculate overall confidence in the analysis"""
        confidence = 0.7  # Base confidence

        # Language confidence
        if post.language in ['english', 'hindi', 'tamil']:  # Well-supported languages
            confidence += 0.1

        # Platform reliability
        if post.platform in ['news', 'twitter']:
            confidence += 0.1

        # Content length (more content = potentially more reliable analysis)
        if len(post.text) > 50:
            confidence += 0.05

        # Location specificity
        if self._extract_location(post.text):
            confidence += 0.05

        return min(1.0, confidence)

    def _calculate_priority(self, analysis: DisasterAnalysis, post: SocialMediaPost, vector_enhancement: Dict[str, Any] = None, misinformation_analysis: MisinformationAnalysis = None) -> str:
        """Calculate priority level (P0-P4) based on analysis"""

        priority_score = 0.0

        # LLM Relevance score weight
        priority_score += (analysis.relevance_score / 10) * self.priority_weights['relevance_score']

        # Vector relevance score weight (if available)
        if vector_enhancement and 'vector_classification' in vector_enhancement:
            vector_relevance = vector_enhancement['vector_classification'].get('relevance_score', 0)
            priority_score += (vector_relevance / 10) * self.priority_weights['vector_relevance']

        # Urgency multiplier
        urgency_multipliers = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.2}
        priority_score += urgency_multipliers[analysis.urgency] * self.priority_weights['urgency_multiplier']

        # Emotional urgency (NEW: from enhanced NLP)
        emotional_urgency_score = 0.0
        if hasattr(analysis, '_emotional_urgency') or '_emotional_urgency' in analysis.__dict__:
            emotional_urgency = getattr(analysis, '_emotional_urgency', analysis.__dict__.get('_emotional_urgency', {}))
            if emotional_urgency:
                emotional_urgency_score = emotional_urgency.get('emotional_urgency', 0.0)
        priority_score += emotional_urgency_score * self.priority_weights['emotional_urgency']

        # Credibility score weight
        priority_score += analysis.confidence_score * self.priority_weights['credibility_score']

        # Enhanced location specificity with coastal priority weighting
        location_boost = 0.0
        if analysis.location_mentioned:
            location_text = analysis.location_mentioned.lower()

            # Check for specific coastal locations
            for location, weight in self.coastal_locations.items():
                if location in location_text:
                    location_boost = max(location_boost, weight)

            # Check for high-risk zones for specific disaster types
            if analysis.disaster_type != 'none' and analysis.disaster_type in self.high_risk_zones:
                for risk_location in self.high_risk_zones[analysis.disaster_type]:
                    if risk_location.lower() in location_text:
                        location_boost = max(location_boost, 0.9)  # High risk zone bonus

            priority_score += location_boost * self.priority_weights['location_specificity']

        # Misinformation risk adjustment
        if misinformation_analysis:
            # High misinformation risk reduces priority
            misinformation_penalties = {
                "high_misinformation_risk": -0.3,
                "moderate_misinformation_risk": -0.15,
                "low_misinformation_risk": -0.05,
                "minimal_misinformation_risk": 0.0
            }
            penalty = misinformation_penalties.get(misinformation_analysis.risk_level, 0.0)
            priority_score += penalty * self.priority_weights['misinformation_penalty']

            # Very low source reliability also reduces priority
            reliability_penalties = {
                "very_low_reliability": -0.2,
                "low_reliability": -0.1,
                "moderate_reliability": 0.0,
                "high_reliability": 0.05
            }
            reliability_penalty = reliability_penalties.get(misinformation_analysis.source_reliability, 0.0)
            priority_score += reliability_penalty * self.priority_weights['misinformation_penalty']

        # Platform credibility weighting
        platform_cred = self.platform_credibility.get(post.platform, 0.5)
        priority_score += platform_cred * self.priority_weights['platform_credibility']

        # User verification status (higher priority for verified/official accounts)
        if post.user:
            user_boost = 0.0
            if post.user.verified:
                user_boost = 1.0  # Verified accounts get full boost
            elif post.user.follower_count > 10000:
                user_boost = 0.6  # High follower accounts get moderate boost
            elif post.user.follower_count > 1000:
                user_boost = 0.3  # Medium follower accounts get small boost

            priority_score += user_boost * self.priority_weights['user_verification']

        # Social engagement factor (more engagement indicates importance)
        engagement_score = 0.0
        if hasattr(post, 'likes') and hasattr(post, 'shares') and hasattr(post, 'comments'):
            total_engagement = (post.likes or 0) + (post.shares or 0) + (post.comments or 0)
            if total_engagement > 100:
                engagement_score = 1.0
            elif total_engagement > 50:
                engagement_score = 0.7
            elif total_engagement > 10:
                engagement_score = 0.4
            elif total_engagement > 1:
                engagement_score = 0.2

            priority_score += engagement_score * self.priority_weights['social_engagement']

        # Time sensitivity (recent posts get higher priority)
        if post.timestamp:
            time_diff = (datetime.now(timezone.utc) - post.timestamp).total_seconds() / 3600  # Hours
            time_factor = max(0, 1 - (time_diff / 24))  # Decay over 24 hours
            priority_score += time_factor * self.priority_weights['time_sensitivity']

        # Ensure priority score is within bounds
        priority_score = max(0.0, min(1.0, priority_score))

        # Convert to priority levels (adjusted thresholds for misinformation)
        if priority_score >= 0.75:
            return "P0"  # Critical
        elif priority_score >= 0.55:
            return "P1"  # High
        elif priority_score >= 0.35:
            return "P2"  # Medium
        elif priority_score >= 0.15:
            return "P3"  # Low
        else:
            return "P4"  # Minimal

    def _get_priority_breakdown(self, analysis: DisasterAnalysis, post: SocialMediaPost, misinformation_analysis: MisinformationAnalysis = None) -> Dict[str, Any]:
        """Get detailed priority scoring breakdown for analysis"""
        breakdown = {}

        # LLM Relevance score
        relevance_contribution = (analysis.relevance_score / 10) * self.priority_weights['relevance_score']
        breakdown['relevance_score'] = {
            'value': analysis.relevance_score,
            'weight': self.priority_weights['relevance_score'],
            'contribution': round(relevance_contribution, 3)
        }

        # Urgency multiplier
        urgency_multipliers = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.2}
        urgency_contribution = urgency_multipliers[analysis.urgency] * self.priority_weights['urgency_multiplier']
        breakdown['urgency'] = {
            'value': analysis.urgency,
            'multiplier': urgency_multipliers[analysis.urgency],
            'weight': self.priority_weights['urgency_multiplier'],
            'contribution': round(urgency_contribution, 3)
        }

        # Credibility score
        credibility_contribution = analysis.confidence_score * self.priority_weights['credibility_score']
        breakdown['credibility'] = {
            'value': analysis.confidence_score,
            'weight': self.priority_weights['credibility_score'],
            'contribution': round(credibility_contribution, 3)
        }

        # Enhanced location specificity
        location_boost = 0.0
        if analysis.location_mentioned:
            location_text = analysis.location_mentioned.lower()
            for location, weight in self.coastal_locations.items():
                if location in location_text:
                    location_boost = max(location_boost, weight)

        location_contribution = location_boost * self.priority_weights['location_specificity']
        breakdown['location_specificity'] = {
            'mentioned_location': analysis.location_mentioned,
            'coastal_relevance': location_boost,
            'weight': self.priority_weights['location_specificity'],
            'contribution': round(location_contribution, 3)
        }

        # Platform credibility
        platform_cred = self.platform_credibility.get(post.platform, 0.5)
        platform_contribution = platform_cred * self.priority_weights['platform_credibility']
        breakdown['platform_credibility'] = {
            'platform': post.platform,
            'credibility_score': platform_cred,
            'weight': self.priority_weights['platform_credibility'],
            'contribution': round(platform_contribution, 3)
        }

        # User verification
        user_boost = 0.0
        if post.user:
            if post.user.verified:
                user_boost = 1.0
            elif post.user.follower_count > 10000:
                user_boost = 0.6
            elif post.user.follower_count > 1000:
                user_boost = 0.3

        user_contribution = user_boost * self.priority_weights['user_verification']
        breakdown['user_verification'] = {
            'verified': post.user.verified if post.user else False,
            'follower_count': post.user.follower_count if post.user else 0,
            'verification_boost': user_boost,
            'weight': self.priority_weights['user_verification'],
            'contribution': round(user_contribution, 3)
        }

        # Social engagement
        total_engagement = (post.likes or 0) + (post.shares or 0) + (post.comments or 0)
        engagement_score = 0.0
        if total_engagement > 100:
            engagement_score = 1.0
        elif total_engagement > 50:
            engagement_score = 0.7
        elif total_engagement > 10:
            engagement_score = 0.4
        elif total_engagement > 1:
            engagement_score = 0.2

        engagement_contribution = engagement_score * self.priority_weights['social_engagement']
        breakdown['social_engagement'] = {
            'total_engagement': total_engagement,
            'engagement_score': engagement_score,
            'weight': self.priority_weights['social_engagement'],
            'contribution': round(engagement_contribution, 3)
        }

        # Time sensitivity
        time_factor = 0.0
        if post.timestamp:
            time_diff = (datetime.now(timezone.utc) - post.timestamp).total_seconds() / 3600
            time_factor = max(0, 1 - (time_diff / 24))

        time_contribution = time_factor * self.priority_weights['time_sensitivity']
        breakdown['time_sensitivity'] = {
            'hours_old': round(time_diff, 2) if post.timestamp else None,
            'time_factor': round(time_factor, 3),
            'weight': self.priority_weights['time_sensitivity'],
            'contribution': round(time_contribution, 3)
        }

        # Misinformation impact
        misinformation_contribution = 0.0
        penalty = 0.0
        if misinformation_analysis:
            misinformation_penalties = {
                "high_misinformation_risk": -0.3,
                "moderate_misinformation_risk": -0.15,
                "low_misinformation_risk": -0.05,
                "minimal_misinformation_risk": 0.0
            }
            penalty = misinformation_penalties.get(misinformation_analysis.risk_level, 0.0)
            misinformation_contribution = penalty * self.priority_weights['misinformation_penalty']

        breakdown['misinformation_penalty'] = {
            'risk_level': misinformation_analysis.risk_level if misinformation_analysis else 'not_analyzed',
            'penalty_factor': penalty,
            'weight': self.priority_weights['misinformation_penalty'],
            'contribution': round(misinformation_contribution, 3)
        }

        # Calculate total score
        total_score = sum([
            relevance_contribution, urgency_contribution, credibility_contribution,
            location_contribution, platform_contribution, user_contribution,
            engagement_contribution, time_contribution, misinformation_contribution
        ])

        breakdown['total_score'] = round(total_score, 3)
        breakdown['priority_thresholds'] = {
            'P0_critical': 0.75,
            'P1_high': 0.55,
            'P2_medium': 0.35,
            'P3_low': 0.15,
            'P4_minimal': 0.0
        }

        return breakdown

    def _create_fallback_analysis(self, post: SocialMediaPost, start_time: float) -> ProcessedPost:
        """Create fallback analysis when main analysis fails"""
        processing_time = (time.time() - start_time) * 1000

        fallback_analysis = DisasterAnalysis(
            relevance_score=0.0,
            disaster_type="none",
            urgency="low",
            sentiment="neutral",
            keywords=[],
            credibility_indicators=["analysis_error"],
            location_mentioned=post.location,
            language_detected=post.language,
            confidence_score=0.1
        )

        return ProcessedPost(
            original_post=post,
            analysis=fallback_analysis,
            processing_time_ms=processing_time,
            priority_level="P4"
        )

    def batch_analyze(self, posts: List[SocialMediaPost]) -> List[ProcessedPost]:
        """Analyze multiple posts in batch"""
        results = []
        for post in posts:
            try:
                result = self.analyze_post(post)
                results.append(result)
            except Exception as e:
                print(f"❌ Batch analysis error for post: {e}")
                continue

        return results