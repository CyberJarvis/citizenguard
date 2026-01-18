#!/usr/bin/env python3
"""
Enhanced NLP Service for BlueRadar Social Intelligence
Provides advanced sentiment analysis, emotion detection, and enhanced disaster detection
"""

import re
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import statistics

from api.models import SocialMediaPost, DisasterAnalysis


@dataclass
class SentimentAnalysis:
    """Comprehensive sentiment analysis results"""
    sentiment: str  # positive, negative, neutral
    confidence: float  # 0.0 to 1.0
    polarity_score: float  # -1.0 (most negative) to 1.0 (most positive)
    subjectivity_score: float  # 0.0 (objective) to 1.0 (subjective)
    emotion_scores: Dict[str, float]  # fear, anger, sadness, joy, surprise, disgust


@dataclass
class EmotionAnalysis:
    """Detailed emotion analysis for disaster contexts"""
    primary_emotion: str
    emotion_intensity: float  # 0.0 to 1.0
    panic_level: float  # 0.0 to 1.0
    urgency_emotion: float  # 0.0 to 1.0
    fear_indicators: List[str]
    stress_indicators: List[str]
    hope_indicators: List[str]


@dataclass
class EnhancedEntityExtraction:
    """Named entity recognition for marine disasters"""
    locations: List[Dict[str, Any]]  # [{'name': str, 'confidence': float, 'type': str}]
    organizations: List[Dict[str, Any]]
    persons: List[Dict[str, Any]]
    timestamps: List[Dict[str, Any]]
    quantities: List[Dict[str, Any]]  # wave height, wind speed, casualties
    marine_entities: List[Dict[str, Any]]  # ships, ports, equipment


class EnhancedNLPService:
    """Enhanced NLP service with advanced sentiment and emotion analysis"""

    def __init__(self):
        # Emotion lexicons for Indian coastal languages
        self.emotion_lexicons = {
            'fear': {
                'english': ['afraid', 'scared', 'terrified', 'panic', 'frightened', 'horror', 'dread', 'anxiety'],
                'tamil': ['பயம்', 'அச்சம்', 'நடுக்கம்', 'பீதி'],
                'telugu': ['భయం', 'డర', 'పీచు', 'కంపనలు'],
                'malayalam': ['ഭയം', 'പേടി', 'ഭീതി', 'നടുക്കം'],
                'hindi': ['डर', 'भय', 'घबराहट', 'हड़बड़ाहट'],
                'bengali': ['ভয়', 'আতঙ্ক', 'ভীতি', 'শংকা'],
                'gujarati': ['ડર', 'ભય', 'ત્રાસ', 'ગભરાહટ'],
                'marathi': ['भीती', 'घाबरणे', 'भय', 'धास्ती']
            },
            'anger': {
                'english': ['angry', 'furious', 'rage', 'outraged', 'mad', 'livid', 'annoyed', 'frustrated'],
                'tamil': ['கோபம்', 'எரிச்சல்', 'ராகம்'],
                'telugu': ['కోపం', 'ఆగ్రహం', 'రగవు'],
                'malayalam': ['കോപം', 'ദേഷ്യം', 'ക്രോധം'],
                'hindi': ['गुस्सा', 'क्रोध', 'गुर्राहट'],
                'bengali': ['রাগ', 'ক্রোধ', 'গোস্সা'],
                'gujarati': ['ગુસ્સો', 'કોપ', 'રોષ'],
                'marathi': ['राग', 'क्रोध', 'रिसावणे']
            },
            'sadness': {
                'english': ['sad', 'depressed', 'heartbroken', 'devastated', 'grief', 'sorrow', 'despair'],
                'tamil': ['துக்கம்', 'வருत्तम்', 'சோகம்'],
                'telugu': ['దుఃఖం', 'శోకం', 'వేదన'],
                'malayalam': ['ദുഃഖം', 'വിഷാദം', 'സങ്കടം'],
                'hindi': ['दुख', 'शोक', 'गम'],
                'bengali': ['দুঃখ', 'শোক', 'কষ্ট'],
                'gujarati': ['દુઃખ', 'શોક', 'ઉદાસી'],
                'marathi': ['दुःख', 'शोक', 'मन खराब']
            },
            'joy': {
                'english': ['happy', 'joyful', 'excited', 'elated', 'cheerful', 'delighted', 'pleased'],
                'tamil': ['மகிழ்ச்சி', 'சந்தோषம்', 'ஆனंதம்'],
                'telugu': ['సంతోషం', 'ఆనందం', 'ఖుషी'],
                'malayalam': ['സന്തോഷം', 'ആനന്ദം', 'ഹർഷം'],
                'hindi': ['खुशी', 'आनंद', 'प्रसन्नता'],
                'bengali': ['খুশি', 'আনন্দ', 'হর্ষ'],
                'gujarati': ['ખુશી', 'આનંદ', 'હર્ષ'],
                'marathi': ['आनंद', 'खूष', 'प्रसन्नता']
            }
        }

        # Urgency indicators for disaster contexts
        self.urgency_indicators = {
            'critical': ['immediate', 'urgent', 'emergency', 'now', 'asap', 'critical', 'evacuate'],
            'high': ['soon', 'quickly', 'fast', 'hurry', 'important', 'alert'],
            'medium': ['warning', 'caution', 'watch', 'monitor', 'prepare'],
            'low': ['notice', 'advisory', 'update', 'information']
        }

        # Marine disaster specific vocabulary
        self.marine_vocabulary = {
            'tsunami': {
                'severity_indicators': ['wave height', 'surge', 'inundation', 'retreat', 'aftershock'],
                'action_words': ['evacuate', 'move inland', 'higher ground', 'emergency shelter'],
                'measurement_patterns': [r'(\d+(?:\.\d+)?)\s*(?:m|meter|metre|feet|ft)', r'magnitude\s+(\d+(?:\.\d+)?)']
            },
            'cyclone': {
                'severity_indicators': ['wind speed', 'landfall', 'eye wall', 'storm surge', 'category'],
                'action_words': ['take shelter', 'secure', 'board up', 'stock supplies'],
                'measurement_patterns': [r'(\d+)\s*(?:kmph|km/h|mph)', r'category\s+(\d+)']
            },
            'oil_spill': {
                'severity_indicators': ['tonnes', 'gallons', 'contamination', 'slick', 'cleanup'],
                'action_words': ['contain', 'cleanup', 'avoid contact', 'report'],
                'measurement_patterns': [r'(\d+(?:,\d+)?)\s*(?:tonnes|tons|gallons|litres?)']
            },
            'flooding': {
                'severity_indicators': ['water level', 'overflow', 'breach', 'inundation'],
                'action_words': ['evacuate', 'move higher', 'avoid roads', 'emergency'],
                'measurement_patterns': [r'(\d+(?:\.\d+)?)\s*(?:m|meter|metre|feet|ft)\s*(?:above|over)']
            }
        }

        # Language detection patterns for sentiment analysis
        self.language_patterns = {
            'tamil': re.compile(r'[\u0B80-\u0BFF]+'),
            'telugu': re.compile(r'[\u0C00-\u0C7F]+'),
            'malayalam': re.compile(r'[\u0D00-\u0D7F]+'),
            'hindi': re.compile(r'[\u0900-\u097F]+'),
            'bengali': re.compile(r'[\u0980-\u09FF]+'),
            'gujarati': re.compile(r'[\u0A80-\u0AFF]+'),
            'marathi': re.compile(r'[\u0900-\u097F]+'),  # Same as Hindi script
            'kannada': re.compile(r'[\u0C80-\u0CFF]+'),
            'odia': re.compile(r'[\u0B00-\u0B7F]+')
        }

    def analyze_sentiment_and_emotion(self, text: str, language: str = 'english') -> Tuple[SentimentAnalysis, EmotionAnalysis]:
        """
        Comprehensive sentiment and emotion analysis for social media posts
        """
        # Sentiment analysis
        sentiment_analysis = self._analyze_sentiment(text, language)

        # Emotion analysis
        emotion_analysis = self._analyze_emotions(text, language)

        return sentiment_analysis, emotion_analysis

    def _analyze_sentiment(self, text: str, language: str) -> SentimentAnalysis:
        """Advanced sentiment analysis with cultural context"""
        text_lower = text.lower()

        # Initialize scores
        positive_score = 0
        negative_score = 0
        emotion_scores = {'fear': 0, 'anger': 0, 'sadness': 0, 'joy': 0, 'surprise': 0, 'disgust': 0}

        # Check for emotion words in text
        for emotion, language_dict in self.emotion_lexicons.items():
            words = language_dict.get(language, language_dict.get('english', []))

            for word in words:
                if word.lower() in text_lower:
                    emotion_scores[emotion] += 1

                    # Weight sentiment based on emotion
                    if emotion in ['fear', 'anger', 'sadness', 'disgust']:
                        negative_score += 1
                    elif emotion == 'joy':
                        positive_score += 1

        # Disaster-specific sentiment modifiers
        disaster_negative_words = [
            'disaster', 'emergency', 'crisis', 'danger', 'threat', 'risk', 'damage', 'destruction',
            'casualty', 'death', 'injured', 'trapped', 'missing', 'evacuation', 'warning'
        ]

        disaster_positive_words = [
            'safe', 'rescued', 'relief', 'help', 'support', 'recovery', 'restored', 'cleared',
            'contained', 'under control', 'evacuated successfully', 'no casualties'
        ]

        for word in disaster_negative_words:
            if word in text_lower:
                negative_score += 2  # Higher weight for disaster context

        for word in disaster_positive_words:
            if word in text_lower:
                positive_score += 2

        # Calculate polarity (-1 to 1)
        total_score = positive_score + negative_score
        if total_score > 0:
            polarity_score = (positive_score - negative_score) / total_score
        else:
            polarity_score = 0.0

        # Determine sentiment category
        if polarity_score > 0.1:
            sentiment = 'positive'
            confidence = min(0.9, abs(polarity_score) + 0.1)
        elif polarity_score < -0.1:
            sentiment = 'negative'
            confidence = min(0.9, abs(polarity_score) + 0.1)
        else:
            sentiment = 'neutral'
            confidence = max(0.1, 1.0 - abs(polarity_score))

        # Calculate subjectivity (presence of emotion words indicates subjectivity)
        total_emotion_words = sum(emotion_scores.values())
        text_words = len(text.split())
        subjectivity_score = min(1.0, total_emotion_words / max(1, text_words) * 5)

        # Normalize emotion scores
        max_emotion_score = max(emotion_scores.values()) if any(emotion_scores.values()) else 1
        normalized_emotions = {k: v/max_emotion_score for k, v in emotion_scores.items()}

        return SentimentAnalysis(
            sentiment=sentiment,
            confidence=confidence,
            polarity_score=polarity_score,
            subjectivity_score=subjectivity_score,
            emotion_scores=normalized_emotions
        )

    def _analyze_emotions(self, text: str, language: str) -> EmotionAnalysis:
        """Detailed emotion analysis for disaster contexts"""
        text_lower = text.lower()

        # Calculate emotion scores
        emotion_scores = {}
        for emotion, language_dict in self.emotion_lexicons.items():
            words = language_dict.get(language, language_dict.get('english', []))
            score = sum(1 for word in words if word.lower() in text_lower)
            emotion_scores[emotion] = score

        # Determine primary emotion
        primary_emotion = max(emotion_scores, key=emotion_scores.get) if any(emotion_scores.values()) else 'neutral'
        emotion_intensity = min(1.0, emotion_scores[primary_emotion] / 3.0)  # Normalize to 0-1

        # Calculate panic level (fear + urgency indicators)
        panic_indicators = ['panic', 'terrified', 'emergency', 'evacuate', 'run', 'escape', 'help']
        panic_score = sum(1 for indicator in panic_indicators if indicator in text_lower)
        panic_level = min(1.0, panic_score / 5.0)

        # Calculate urgency emotion
        urgency_score = 0
        for level, indicators in self.urgency_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    if level == 'critical':
                        urgency_score += 4
                    elif level == 'high':
                        urgency_score += 3
                    elif level == 'medium':
                        urgency_score += 2
                    else:
                        urgency_score += 1

        urgency_emotion = min(1.0, urgency_score / 10.0)

        # Extract specific indicators
        fear_indicators = self._extract_fear_indicators(text_lower)
        stress_indicators = self._extract_stress_indicators(text_lower)
        hope_indicators = self._extract_hope_indicators(text_lower)

        return EmotionAnalysis(
            primary_emotion=primary_emotion,
            emotion_intensity=emotion_intensity,
            panic_level=panic_level,
            urgency_emotion=urgency_emotion,
            fear_indicators=fear_indicators,
            stress_indicators=stress_indicators,
            hope_indicators=hope_indicators
        )

    def _extract_fear_indicators(self, text: str) -> List[str]:
        """Extract fear-related indicators from text"""
        fear_patterns = [
            'scared', 'terrified', 'afraid', 'panic', 'frightened', 'worried',
            'anxious', 'nervous', 'concerned', 'alarmed', 'distressed'
        ]
        return [pattern for pattern in fear_patterns if pattern in text]

    def _extract_stress_indicators(self, text: str) -> List[str]:
        """Extract stress-related indicators from text"""
        stress_patterns = [
            'stressed', 'overwhelmed', 'can\'t handle', 'breaking down', 'too much',
            'exhausted', 'tired', 'burned out', 'pressure', 'tension'
        ]
        return [pattern for pattern in stress_patterns if pattern in text]

    def _extract_hope_indicators(self, text: str) -> List[str]:
        """Extract hope-related indicators from text"""
        hope_patterns = [
            'hope', 'optimistic', 'better', 'improving', 'recovering', 'healing',
            'positive', 'confident', 'faith', 'trust', 'believe', 'overcome'
        ]
        return [pattern for pattern in hope_patterns if pattern in text]

    def extract_enhanced_entities(self, text: str, language: str = 'english') -> EnhancedEntityExtraction:
        """Enhanced named entity recognition for marine disasters"""

        # Extract locations with coastal focus
        locations = self._extract_locations(text)

        # Extract organizations (emergency services, agencies)
        organizations = self._extract_organizations(text)

        # Extract persons (officials, victims)
        persons = self._extract_persons(text)

        # Extract timestamps and time references
        timestamps = self._extract_timestamps(text)

        # Extract quantities (wave heights, wind speeds, casualties)
        quantities = self._extract_quantities(text)

        # Extract marine-specific entities
        marine_entities = self._extract_marine_entities(text)

        return EnhancedEntityExtraction(
            locations=locations,
            organizations=organizations,
            persons=persons,
            timestamps=timestamps,
            quantities=quantities,
            marine_entities=marine_entities
        )

    def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """Extract location entities with confidence scores"""
        locations = []

        # Indian coastal locations (from existing analysis service)
        coastal_locations = [
            'mumbai', 'chennai', 'kolkata', 'visakhapatnam', 'kochi', 'kandla', 'paradip',
            'mangalore', 'tuticorin', 'haldia', 'marmagao', 'ennore', 'bhavnagar', 'kakinada',
            'marina beach', 'juhu', 'baga', 'puri', 'mahabalipuram', 'kovalam', 'calicut'
        ]

        text_lower = text.lower()
        for location in coastal_locations:
            if location in text_lower:
                # Calculate confidence based on context
                confidence = 0.8
                if any(word in text_lower for word in ['coast', 'port', 'harbor', 'beach']):
                    confidence = 0.9

                locations.append({
                    'name': location.title(),
                    'confidence': confidence,
                    'type': 'coastal_location'
                })

        # Extract other location patterns
        location_patterns = [
            r'(?:near|at|in|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:coast|beach|port|harbor|district)',
            r'(?:state of|province of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match.lower() not in [loc['name'].lower() for loc in locations]:
                    locations.append({
                        'name': match,
                        'confidence': 0.6,
                        'type': 'general_location'
                    })

        return locations

    def _extract_organizations(self, text: str) -> List[Dict[str, Any]]:
        """Extract organization entities"""
        organizations = []

        org_patterns = [
            r'(Coast Guard|Navy|NDRF|SDRF|IMD|INCOIS)',
            r'([A-Z][a-z]+\s+(?:Police|Fire|Emergency|Rescue|Department|Authority|Commission))',
            r'(National\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'(Indian\s+[A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]

        for pattern in org_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                organizations.append({
                    'name': match,
                    'confidence': 0.8,
                    'type': 'emergency_organization'
                })

        return organizations

    def _extract_persons(self, text: str) -> List[Dict[str, Any]]:
        """Extract person entities"""
        persons = []

        # Simple person extraction (can be enhanced with NER models)
        person_patterns = [
            r'(?:Mr\.|Mrs\.|Dr\.|Chief|Director|Officer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+said|\s+stated|\s+reported)'
        ]

        for pattern in person_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                persons.append({
                    'name': match,
                    'confidence': 0.7,
                    'type': 'person'
                })

        return persons

    def _extract_timestamps(self, text: str) -> List[Dict[str, Any]]:
        """Extract time references"""
        timestamps = []

        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',
            r'(today|tomorrow|yesterday|tonight)',
            r'(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
        ]

        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                timestamps.append({
                    'value': match,
                    'confidence': 0.8,
                    'type': 'time_reference'
                })

        return timestamps

    def _extract_quantities(self, text: str) -> List[Dict[str, Any]]:
        """Extract numerical quantities relevant to disasters"""
        quantities = []

        quantity_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:m|meter|metre|feet|ft)(?:\s+(?:high|tall|above|over))?', 'height'),
            (r'(\d+)\s*(?:kmph|km/h|mph|knots)', 'wind_speed'),
            (r'magnitude\s+(\d+(?:\.\d+)?)', 'earthquake_magnitude'),
            (r'(\d+(?:,\d+)?)\s*(?:tonnes|tons|gallons|litres?)', 'volume'),
            (r'(\d+)\s*(?:people|persons|casualties|deaths|injured)', 'casualties'),
            (r'(\d+)\s*(?:houses|buildings|structures)', 'structures')
        ]

        for pattern, quantity_type in quantity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                quantities.append({
                    'value': match,
                    'type': quantity_type,
                    'confidence': 0.9
                })

        return quantities

    def _extract_marine_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract marine-specific entities"""
        marine_entities = []

        marine_patterns = [
            (r'(?:ship|vessel|boat|tanker|cargo|ferry)\s+([A-Z][a-zA-Z0-9\s]+)', 'vessel'),
            (r'([A-Z][a-z]+\s+(?:Port|Harbor|Harbour|Terminal))', 'port_facility'),
            (r'(oil rig|platform|drilling platform|offshore platform)', 'offshore_facility'),
            (r'(Coast Guard|Navy|Marine Police|Port Authority)', 'marine_authority'),
            (r'(lighthouse|beacon|buoy|navigation aid)', 'navigation_aid')
        ]

        for pattern, entity_type in marine_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                marine_entities.append({
                    'name': match,
                    'type': entity_type,
                    'confidence': 0.8
                })

        return marine_entities

    def enhanced_keyword_extraction(self, text: str, disaster_type: str = None, language: str = 'english') -> List[Dict[str, Any]]:
        """Extract enhanced keywords with weights and context"""
        keywords = []
        text_lower = text.lower()

        # Disaster-specific keyword extraction
        if disaster_type and disaster_type in self.marine_vocabulary:
            vocab = self.marine_vocabulary[disaster_type]

            for keyword in vocab['severity_indicators']:
                if keyword in text_lower:
                    keywords.append({
                        'keyword': keyword,
                        'weight': 0.9,
                        'context': 'severity_indicator'
                    })

            for keyword in vocab['action_words']:
                if keyword in text_lower:
                    keywords.append({
                        'keyword': keyword,
                        'weight': 0.8,
                        'context': 'action_required'
                    })

        # Urgency keywords
        for urgency_level, indicators in self.urgency_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    weight = {'critical': 1.0, 'high': 0.8, 'medium': 0.6, 'low': 0.4}[urgency_level]
                    keywords.append({
                        'keyword': indicator,
                        'weight': weight,
                        'context': f'urgency_{urgency_level}'
                    })

        # Emotion keywords
        for emotion, language_dict in self.emotion_lexicons.items():
            words = language_dict.get(language, language_dict.get('english', []))
            for word in words:
                if word.lower() in text_lower:
                    keywords.append({
                        'keyword': word,
                        'weight': 0.7,
                        'context': f'emotion_{emotion}'
                    })

        # Remove duplicates and sort by weight
        unique_keywords = []
        seen_keywords = set()

        for kw in keywords:
            if kw['keyword'] not in seen_keywords:
                unique_keywords.append(kw)
                seen_keywords.add(kw['keyword'])

        # Sort by weight (highest first)
        unique_keywords.sort(key=lambda x: x['weight'], reverse=True)

        return unique_keywords[:15]  # Return top 15 keywords

    def calculate_emotional_urgency_score(self, text: str, language: str = 'english') -> Dict[str, float]:
        """Calculate overall emotional urgency for priority scoring"""
        sentiment_analysis, emotion_analysis = self.analyze_sentiment_and_emotion(text, language)

        # Calculate composite urgency score
        emotional_urgency = (
            emotion_analysis.panic_level * 0.4 +
            emotion_analysis.urgency_emotion * 0.3 +
            emotion_analysis.emotion_intensity * 0.2 +
            (1 - sentiment_analysis.confidence if sentiment_analysis.sentiment == 'negative' else 0) * 0.1
        )

        return {
            'emotional_urgency': min(1.0, emotional_urgency),
            'panic_level': emotion_analysis.panic_level,
            'sentiment_polarity': sentiment_analysis.polarity_score,
            'fear_intensity': emotion_analysis.emotion_intensity if emotion_analysis.primary_emotion == 'fear' else 0,
            'overall_negativity': 1 - sentiment_analysis.polarity_score if sentiment_analysis.polarity_score < 0 else 0
        }


# Global instance
enhanced_nlp_service = EnhancedNLPService()

def get_enhanced_nlp_service() -> EnhancedNLPService:
    """Get the global enhanced NLP service instance"""
    return enhanced_nlp_service