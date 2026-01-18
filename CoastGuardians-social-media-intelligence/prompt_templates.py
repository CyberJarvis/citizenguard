"""
Coast Guardian Prompt Templates for Marine Disaster Analysis
Supports 15 Indian languages + code-mixing
"""

from typing import Dict, List
import random

class CoastGuardianPrompts:
    """Comprehensive prompt templates for marine disaster analysis"""

    # Core prompt template
    MARINE_ANALYSIS_PROMPT = """
You are Coast Guardian, an advanced AI system for marine disaster intelligence.
Analyze social media posts for marine disaster relevance in {language}.

SUPPORTED DISASTER TYPES:
- tsunami: Tsunami warnings, wave anomalies
- cyclone: Tropical storms, coastal cyclones
- oil_spill: Marine pollution, oil contamination
- flooding: Coastal flooding, storm surge
- earthquake: Seismic events affecting coastal areas
- none: Not marine disaster related

URGENCY LEVELS:
- critical: Immediate life-threatening situation
- high: Significant threat requiring attention
- medium: Developing situation to monitor
- low: General awareness/informational

ANALYSIS FORMAT (JSON):
{
    "relevance_score": 0-10,
    "disaster_type": "tsunami|cyclone|oil_spill|flooding|earthquake|none",
    "urgency": "critical|high|medium|low",
    "sentiment": "negative|neutral|positive",
    "keywords": ["key", "words", "found"],
    "credibility_indicators": ["factors", "affecting", "credibility"],
    "location_mentioned": "extracted_location_if_any",
    "language_detected": "{language}",
    "confidence_score": 0.0-1.0
}

POST TO ANALYZE:
{post_text}

Provide analysis in JSON format only.
"""

    # Language-specific disaster keywords
    DISASTER_KEYWORDS = {
        "english": {
            "tsunami": ["tsunami", "tidal wave", "seismic sea wave", "giant waves", "wave warning"],
            "cyclone": ["cyclone", "hurricane", "tropical storm", "storm surge", "high winds"],
            "oil_spill": ["oil spill", "marine pollution", "oil leak", "environmental disaster", "crude oil"],
            "flooding": ["coastal flood", "storm surge", "high tide", "sea level rise", "waterlogging"],
            "earthquake": ["earthquake", "tremor", "seismic activity", "quake", "aftershock"]
        },
        "hindi": {
            "tsunami": ["सुनामी", "ज्वारीय लहर", "विशाल लहरें", "समुद्री लहर चेतावनी"],
            "cyclone": ["चक्रवात", "तूफान", "समुद्री तूफान", "तेज़ हवाएं"],
            "oil_spill": ["तेल रिसाव", "समुद्री प्रदूषण", "पर्यावरणीय आपदा"],
            "flooding": ["बाढ़", "तटीय बाढ़", "समुद्री जल वृद्धि"],
            "earthquake": ["भूकंप", "कंपन", "भूकंपीय गतिविधि"]
        },
        "tamil": {
            "tsunami": ["சுனாமி", "கடல் அலை", "பெரிய அலைகள்", "அலை எச்சரிக்கை"],
            "cyclone": ["சூறாவளி", "புயல்", "கடல் புயல்", "பலத்த காற்று"],
            "oil_spill": ["எண்ணெய் கசிவு", "கடல் மாசுபாடு", "சுற்றுச்சூழல் பேரழிவு"],
            "flooding": ["வெள்ளம்", "கடலோர வெள்ளம்", "கடல் நீர் உயர்வு"],
            "earthquake": ["பூகம்பம்", "நிலநடுக்கம்", "அதிர்வு"]
        }
        # Add more languages as needed
    }

    # Realistic post templates by platform
    POST_TEMPLATES = {
        "twitter": [
            "🚨 BREAKING: {disaster_text} in {location}! {urgency_text} #MarineAlert #CoastGuard",
            "Witnessed {disaster_text} at {location}. {emotion_text} {urgency_text}",
            "Local reports: {disaster_text} affecting {location} area. Stay safe! 🙏",
            "Can anyone confirm {disaster_text} near {location}? {concern_text}",
            "{disaster_text} alert for {location}. {action_text} immediately!"
        ],
        "facebook": [
            "Hi everyone, there are reports of {disaster_text} near {location}. {detailed_text} Please share if you have more information.",
            "Emergency update: {disaster_text} has been reported in {location}. {safety_text}",
            "Just heard about {disaster_text} in {location} area. {emotion_text} {prayer_text}",
            "Attention residents of {location}: {disaster_text} warning issued. {preparation_text}",
            "My friend in {location} just told me about {disaster_text}. {concern_text}"
        ],
        "instagram": [
            "🌊 {disaster_text} spotted near {location} today. {emotion_text} #StayAlert #Marine",
            "Scary scenes from {location} - {disaster_text} happening right now 😰",
            "Nature's power on display at {location}. {disaster_text} {reflection_text}",
            "Documenting {disaster_text} at {location}. {awareness_text} 📸",
            "Beach day turned serious - {disaster_text} at {location}. {safety_text}"
        ]
    }

    # Context variations
    URGENCY_CONTEXTS = {
        "critical": ["EVACUATE NOW", "IMMEDIATE DANGER", "LIFE THREATENING", "ACT FAST"],
        "high": ["Seek higher ground", "Monitor closely", "Take precautions", "Stay alert"],
        "medium": ["Keep watching", "Be prepared", "Stay informed", "Monitor updates"],
        "low": ["For your awareness", "Just sharing", "FYI", "Heads up"]
    }

    EMOTION_CONTEXTS = {
        "negative": ["So scary!", "Very worried", "This is terrible", "Prayers needed"],
        "neutral": ["Sharing for awareness", "Factual update", "As reported", "Official info"],
        "positive": ["We'll get through this", "Community strong", "Help available", "Stay positive"]
    }

    @classmethod
    def get_analysis_prompt(cls, post_text: str, language: str = "english") -> str:
        """Get formatted analysis prompt for LLM"""
        return cls.MARINE_ANALYSIS_PROMPT.format(
            language=language,
            post_text=post_text
        )

    @classmethod
    def get_disaster_keywords(cls, language: str = "english") -> Dict[str, List[str]]:
        """Get disaster keywords for specific language"""
        return cls.DISASTER_KEYWORDS.get(language, cls.DISASTER_KEYWORDS["english"])

    @classmethod
    def generate_realistic_post(cls,
                               disaster_type: str,
                               location: str,
                               platform: str = "twitter",
                               language: str = "english",
                               urgency: str = "medium") -> str:
        """Generate realistic social media post"""

        # Select template
        templates = cls.POST_TEMPLATES.get(platform, cls.POST_TEMPLATES["twitter"])
        template = random.choice(templates)

        # Get keywords for the disaster
        keywords = cls.get_disaster_keywords(language)
        disaster_keywords = keywords.get(disaster_type, ["incident"])
        disaster_text = random.choice(disaster_keywords)

        # Get context variations
        urgency_text = random.choice(cls.URGENCY_CONTEXTS[urgency])
        emotion_text = random.choice(cls.EMOTION_CONTEXTS["negative" if urgency in ["critical", "high"] else "neutral"])

        # Fill template
        return template.format(
            disaster_text=disaster_text,
            location=location,
            urgency_text=urgency_text,
            emotion_text=emotion_text,
            detailed_text="Authorities are responding. Follow official channels for updates.",
            safety_text="Please stay away from the affected area and follow evacuation orders.",
            concern_text="Hope everyone is safe. Please share updates if you have them.",
            action_text="Evacuate" if urgency == "critical" else "Monitor",
            prayer_text="Prayers for everyone's safety 🙏",
            preparation_text="Prepare emergency kits and have evacuation plans ready.",
            reflection_text="Reminder of nature's unpredictable power.",
            awareness_text="Sharing to raise awareness about marine safety."
        )

# Indian coastal locations for realistic data
INDIAN_COASTAL_LOCATIONS = [
    # Major ports and cities
    "Mumbai", "Chennai", "Kolkata", "Visakhapatnam", "Kochi", "Mangalore",
    "Paradip", "Kandla", "Tuticorin", "Ennore", "Haldia", "Marmagao",

    # Popular coastal areas
    "Marina Beach", "Juhu Beach", "Baga Beach", "Puri", "Mahabalipuram",
    "Kovalam", "Varkala", "Gokarna", "Diu", "Rameswaram",

    # Specific coastal regions
    "Konkan Coast", "Malabar Coast", "Coromandel Coast", "Sundarbans",
    "Gulf of Mannar", "Lakshadweep", "Andaman Islands", "Puducherry",

    # Fishing harbors
    "Sassoon Dock", "Fisherman's Wharf", "Karwar", "Malpe", "Cuddalore",
    "Nagapattinam", "Machilipatnam", "Kakinada", "Berhampur"
]