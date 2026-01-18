"""
BlueRadar Intelligence Engine - Complete Configuration
Full production settings with all keywords, platforms, and options
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = DATA_DIR / "output"
IMAGES_DIR = DATA_DIR / "images"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
REPORTS_DIR = DATA_DIR / "reports"

# Ensure directories exist
for dir_path in [OUTPUT_DIR, IMAGES_DIR, CACHE_DIR, LOGS_DIR, REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

for platform in ["instagram", "twitter", "facebook", "youtube", "news"]:
    (IMAGES_DIR / platform).mkdir(exist_ok=True)


# =============================================================================
# ENUMS
# =============================================================================

class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class HazardType(Enum):
    TSUNAMI = "tsunami"
    CYCLONE = "cyclone"
    FLOOD = "flood"
    STORM_SURGE = "storm_surge"
    HIGH_TIDE = "high_tide"
    ROUGH_SEA = "rough_sea"
    RIP_CURRENT = "rip_current"
    OIL_SPILL = "oil_spill"
    MARINE_POLLUTION = "marine_pollution"
    COASTAL_EROSION = "coastal_erosion"
    SHIPWRECK = "shipwreck"
    MARINE_RESCUE = "marine_rescue"
    UNKNOWN = "unknown"


class Platform(Enum):
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    GOOGLE_NEWS = "google_news"
    INDIAN_NEWS = "indian_news"


# =============================================================================
# SCRAPER CONFIGURATION
# =============================================================================

@dataclass
class ScraperConfig:
    """Complete scraper configuration"""
    # Rate limiting - Conservative for safety
    min_delay: float = 3.0
    max_delay: float = 8.0
    requests_per_session: int = 50
    cooldown_minutes: int = 30
    
    # Aggressive scraping (use with caution)
    aggressive_min_delay: float = 1.5
    aggressive_max_delay: float = 4.0
    
    # Scrolling behavior
    scroll_count: int = 8
    scroll_pause_min: float = 1.5
    scroll_pause_max: float = 3.5
    
    # Content limits
    max_posts_per_hashtag: int = 100
    max_posts_per_page: int = 50
    max_images_per_post: int = 10
    max_comments_per_post: int = 20
    
    # Browser settings
    headless: bool = True
    timeout: int = 45
    page_load_timeout: int = 60
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 5.0
    
    # Time filters (hours)
    max_post_age_hours: int = 72  # Only posts from last 72 hours


@dataclass
class CookieConfig:
    """Cookie rotation configuration"""
    rotation_strategy: str = "health_based"  # round_robin, health_based, random
    max_requests_per_cookie: int = 50
    cooldown_minutes: int = 30
    health_decrease_on_fail: int = 15
    health_decrease_on_rate_limit: int = 30
    health_recovery_rate: int = 5
    min_health_threshold: int = 20
    encryption_enabled: bool = True


@dataclass
class NLPConfig:
    """NLP Pipeline configuration"""
    # Models
    spam_model: str = "distilbert-base-uncased"
    classifier_model: str = "bert-base-multilingual-cased"
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    ner_model: str = "dslim/bert-base-NER"
    translation_model: str = "Helsinki-NLP/opus-mt-hi-en"
    zero_shot_model: str = "facebook/bart-large-mnli"
    
    # Indic language models
    indic_ner_model: str = "ai4bharat/indic-bert"
    
    # Thresholds
    spam_threshold: float = 0.6
    relevance_threshold: float = 0.3
    confidence_threshold: float = 0.5
    
    # Device (mps for M2 Mac, cuda for NVIDIA, cpu as fallback)
    device: str = "auto"  # auto-detect
    
    # Processing
    batch_size: int = 16
    max_length: int = 512
    
    # Language support
    supported_languages: List[str] = field(default_factory=lambda: [
        "en", "hi", "ta", "te", "ml", "kn", "mr", "bn", "gu", "or"
    ])


@dataclass
class VisionConfig:
    """Vision Pipeline configuration"""
    # Models
    classifier_model: str = "google/vit-base-patch16-224"
    damage_model: str = "microsoft/resnet-50"
    
    # Image settings
    image_size: int = 224
    max_images_per_post: int = 10
    
    # Processing
    batch_size: int = 8
    
    # Device
    device: str = "auto"
    
    # Classification thresholds
    hazard_threshold: float = 0.4
    damage_threshold: float = 0.5


# =============================================================================
# HASHTAG CONFIGURATION - COMPREHENSIVE
# =============================================================================

HAZARD_HASHTAGS = {
    "waves_currents": {
        "english": [
            "HighWaves", "RoughSea", "SeaWaves", "OceanWaves", "WaveAlert",
            "RipCurrent", "RipTide", "StrongCurrents", "DangerousCurrents",
            "MarineHazard", "BeachSafety", "SwellAlert", "SurfWarning",
            "TidalWaves", "OceanSwell", "CoastalWaves", "SeaConditions"
        ],
        "hindi": ["तेज़लहरें", "समुद्रीलहरें", "ऊंचीलहरें", "खतरनाकलहरें"],
        "tamil": ["கடல்அலை", "அலைஎச்சரிக்கை"],
        "telugu": ["అలలు", "సముద్రంఅలలు"]
    },
    
    "storms_cyclones": {
        "english": [
            "Cyclone", "CycloneAlert", "CycloneWarning", "CycloneUpdate",
            "TropicalStorm", "TropicalCyclone", "StormSurge", "StormAlert",
            "HurricaneWaves", "SevereWeather", "OceanStorm", "Typhoon",
            "CycloneLandfall", "EyeOfStorm", "CycloneTrack", "StormChasing"
        ],
        "india_specific": [
            "CycloneIndia", "CycloneMichaung", "CycloneBiparjoy", "CycloneTauktae",
            "CycloneAmphan", "CycloneFani", "CycloneYaas", "CycloneNisarga",
            "BayOfBengalCyclone", "ArabianSeaCyclone", "IMDCyclone"
        ],
        "hindi": ["चक्रवात", "तूफान", "आंधी", "चक्रवातचेतावनी"],
        "tamil": ["புயல்", "சூறாவளி", "புயல்எச்சரிக்கை"],
        "telugu": ["తుఫాను", "సైక్లోన్"]
    },
    
    "flooding": {
        "english": [
            "CoastalFlooding", "FloodAlert", "FloodWarning", "Flooding",
            "FlashFlood", "SeaLevelRise", "TidalFlooding", "UrbanFlooding",
            "FloodedStreets", "WaterLogging", "Inundation", "FloodRelief",
            "FloodRescue", "FloodDamage", "FloodVictims"
        ],
        "india_specific": [
            "MumbaiFloods", "ChennaiFloods", "KeralaFloods", "AssamFloods",
            "BiharFloods", "BengalFloods", "GujaratFloods", "MaharashtraFloods",
            "MumbaiRains", "ChennaiRains", "MonsoonFloods", "IndiaFloods"
        ],
        "hindi": ["बाढ़", "जलभराव", "बाढ़चेतावनी", "बाढ़राहत"],
        "tamil": ["வெள்ளம்", "வெள்ளஎச்சரிக்கை"],
        "telugu": ["వరదలు", "వరదహెచ్చరిక"]
    },
    
    "marine_incidents": {
        "english": [
            "OilSpill", "MarinePollution", "OceanPollution", "OilLeak",
            "ShipWreck", "MaritimeAccident", "SeaAccident", "BoatCapsize",
            "ShipSinking", "MarineDisaster", "OceanDisaster", "CargoSpill",
            "ChemicalSpill", "ToxicWater", "MarineContamination"
        ],
        "hindi": ["तेलरिसाव", "समुद्रीप्रदूषण", "जहाजदुर्घटना"],
        "tamil": ["எண்ணெய்கசிவு", "கடல்மாசு"],
        "telugu": ["చమురుచిందటం", "సముద్రకాలుష్యం"]
    },
    
    "marine_life": {
        "english": [
            "BeachedWhale", "BeachedDolphin", "MarineRescue", "StrandedAnimal",
            "WildlifeRescue", "SeaTurtle", "MarineMammal", "WhaleStranding",
            "DolphinRescue", "MarineConservation", "OceanWildlife"
        ],
        "hindi": ["समुद्रीजीवबचाव", "व्हेलबचाव"],
        "tamil": ["கடல்உயிர்காப்பு"],
        "telugu": ["సముద్రజీవిరక్షణ"]
    },
    
    "coastal_erosion": {
        "english": [
            "CoastalErosion", "BeachErosion", "ShorelineErosion", "SeaWallDamage",
            "CoastlineChange", "LandLoss", "ErodingCoast", "BeachReclamation"
        ],
        "hindi": ["तटीयकटाव", "समुद्रतटकटाव"],
        "tamil": ["கரையரிப்பு"],
        "telugu": ["తీరకోత"]
    },
    
    "official_alerts": {
        "india": [
            "IMDAlert", "IMDWarning", "IMDUpdate", "INCOIS", "INСOISAlert",
            "NDMAAlert", "NDMAIndia", "DisasterAlert", "WeatherWarning",
            "IndiaWeather", "IndianMet", "MetDept", "WeatherUpdate"
        ],
        "international": [
            "TsunamiWarning", "TsunamiAlert", "PTWC", "IOC", "UNESCO"
        ]
    },
    
    "geographic": {
        "india_coasts": [
            "BayOfBengal", "ArabianSea", "IndianOcean", "AndamanSea",
            "WestCoast", "EastCoast", "KonkanCoast", "MalabarCoast",
            "CoromandelCoast", "GujaratCoast", "MaharashtraCoast"
        ],
        "cities": [
            "MumbaiCoast", "ChennaiCoast", "KolkataCoast", "VisakhapatnamCoast",
            "GoaBeach", "KeralaCoast", "KochiCoast", "MangaloreCoast",
            "PuriBeach", "DighaBeach", "JuhuBeach", "MarinaBeach"
        ],
        "islands": [
            "Andaman", "Nicobar", "Lakshadweep", "PortBlair", "Kavaratti"
        ]
    }
}

# Flatten all hashtags for quick access
ALL_HASHTAGS = []
for category, subcategories in HAZARD_HASHTAGS.items():
    if isinstance(subcategories, dict):
        for subcat, tags in subcategories.items():
            ALL_HASHTAGS.extend(tags)
    else:
        ALL_HASHTAGS.extend(subcategories)

# Remove duplicates while preserving order
ALL_HASHTAGS = list(dict.fromkeys(ALL_HASHTAGS))


# =============================================================================
# LOCATION CONFIGURATION - COMPREHENSIVE INDIAN COASTAL
# =============================================================================

INDIAN_COASTAL_LOCATIONS = {
    "west_coast": {
        "gujarat": [
            "porbandar", "dwarka", "veraval", "diu", "daman", "surat", 
            "bharuch", "dahej", "mundra", "kandla", "okha", "mandvi"
        ],
        "maharashtra": [
            "mumbai", "thane", "raigad", "ratnagiri", "sindhudurg", 
            "alibaug", "murud", "harihareshwar", "ganpatipule", "malvan",
            "tarkarli", "vengurla"
        ],
        "goa": [
            "panaji", "vasco", "mormugao", "calangute", "baga", "anjuna",
            "vagator", "candolim", "palolem", "agonda", "colva", "benaulim"
        ],
        "karnataka": [
            "mangalore", "udupi", "karwar", "gokarna", "murudeshwar",
            "bhatkal", "kumta", "honnavar", "malpe", "padubidri"
        ],
        "kerala": [
            "thiruvananthapuram", "kovalam", "varkala", "kollam", "alappuzha",
            "kochi", "cherai", "munambam", "kozhikode", "kannur", "kasaragod",
            "bekal", "kappad", "marari", "kumarakom"
        ]
    },
    
    "east_coast": {
        "tamil_nadu": [
            "chennai", "marina", "mahabalipuram", "pondicherry", "puducherry",
            "cuddalore", "nagapattinam", "karaikal", "rameswaram", "dhanushkodi",
            "tuticorin", "kanyakumari", "kovalam", "velankanni"
        ],
        "andhra_pradesh": [
            "visakhapatnam", "vizag", "kakinada", "machilipatnam", 
            "krishnapatnam", "nellore", "srikakulam", "bheemunipatnam",
            "rushikonda", "yarada"
        ],
        "odisha": [
            "puri", "konark", "gopalpur", "chandipur", "paradip", 
            "dhamra", "chilika", "bhubaneswar", "cuttack", "balasore"
        ],
        "west_bengal": [
            "kolkata", "digha", "mandarmani", "shankarpur", "tajpur",
            "bakkhali", "gangasagar", "sagar", "haldia", "kakdwip",
            "sundarbans", "namkhana", "diamond_harbour"
        ]
    },
    
    "islands": {
        "andaman_nicobar": [
            "port_blair", "havelock", "neil", "baratang", "rangat",
            "mayabunder", "diglipur", "car_nicobar", "campbell_bay",
            "ross", "viper", "cellular_jail", "corbyn_cove", "radhanagar"
        ],
        "lakshadweep": [
            "kavaratti", "agatti", "bangaram", "kadmat", "kalpeni",
            "minicoy", "andrott", "amini", "kiltan"
        ]
    },
    
    "water_bodies": {
        "seas": [
            "bay_of_bengal", "arabian_sea", "indian_ocean", "andaman_sea",
            "laccadive_sea"
        ],
        "gulfs": [
            "gulf_of_kutch", "gulf_of_khambhat", "gulf_of_mannar",
            "palk_strait", "palk_bay"
        ]
    }
}

# Flatten locations for matching
ALL_LOCATIONS = []
for region, subregions in INDIAN_COASTAL_LOCATIONS.items():
    for subregion, locations in subregions.items():
        ALL_LOCATIONS.extend(locations)


# =============================================================================
# KEYWORD CONFIGURATION - HAZARD DETECTION
# =============================================================================

HAZARD_KEYWORDS = {
    "tsunami": {
        "english": ["tsunami", "tidal wave", "seismic wave", "harbor wave", "mega wave"],
        "hindi": ["सुनामी", "भूकंपीय लहर"],
        "tamil": ["சுனாமி", "ஆழிப்பேரலை"],
        "telugu": ["సునామీ", "భూకంపతరంగం"],
        "weight": 100  # Highest priority
    },
    
    "cyclone": {
        "english": ["cyclone", "hurricane", "typhoon", "tropical storm", "landfall", 
                   "eye wall", "storm track", "cyclonic", "depression"],
        "hindi": ["चक्रवात", "तूफान", "आंधी", "समुद्री तूफान"],
        "tamil": ["புயல்", "சூறாவளி", "காற்றழிவு"],
        "telugu": ["తుఫాను", "సైక్లోన్", "తీవ్రవాయుగుండం"],
        "weight": 95
    },
    
    "flood": {
        "english": ["flood", "flooding", "inundation", "submerged", "waterlogged",
                   "deluge", "flash flood", "overflow", "flooded"],
        "hindi": ["बाढ़", "जलभराव", "जलप्लावन", "डूबा"],
        "tamil": ["வெள்ளம்", "நீர்பெருக்கு"],
        "telugu": ["వరదలు", "ముంపు"],
        "weight": 85
    },
    
    "storm_surge": {
        "english": ["storm surge", "surge", "tidal surge", "coastal surge", 
                   "sea surge", "water surge"],
        "hindi": ["तूफानी लहर", "ज्वारीय उछाल"],
        "tamil": ["புயலெழுச்சி", "கடல்எழுச்சி"],
        "telugu": ["తుఫాను ఉప్పెన"],
        "weight": 90
    },
    
    "high_tide": {
        "english": ["high tide", "king tide", "spring tide", "tidal", "perigean tide",
                   "astronomical tide", "abnormal tide"],
        "hindi": ["ज्वार", "उच्च ज्वार", "भारी ज्वार"],
        "tamil": ["உயர்ந்தஅலை", "பேரலை"],
        "telugu": ["ఆటుపోట్లు", "అధికజ్వారం"],
        "weight": 70
    },
    
    "rough_sea": {
        "english": ["rough sea", "high waves", "choppy", "turbulent", "swell",
                   "heavy sea", "dangerous sea", "violent sea"],
        "hindi": ["उग्र समुद्र", "ऊंची लहरें", "खतरनाक लहरें"],
        "tamil": ["கொந்தளிப்பானகடல்", "அமைதியற்றகடல்"],
        "telugu": ["అల్లకల్లోలంసముద్రం"],
        "weight": 65
    },
    
    "rip_current": {
        "english": ["rip current", "rip tide", "undertow", "rip", "strong current"],
        "hindi": ["तेज धारा", "समुद्री धारा"],
        "tamil": ["நீரோட்டம்"],
        "telugu": ["ప్రవాహం"],
        "weight": 60
    },
    
    "oil_spill": {
        "english": ["oil spill", "oil leak", "petroleum spill", "crude oil", 
                   "oil slick", "bunker spill"],
        "hindi": ["तेल रिसाव", "तेल फैलाव"],
        "tamil": ["எண்ணெய்கசிவு"],
        "telugu": ["చమురుచిందటం"],
        "weight": 75
    },
    
    "marine_pollution": {
        "english": ["marine pollution", "ocean pollution", "sea pollution", 
                   "plastic pollution", "chemical spill", "toxic"],
        "hindi": ["समुद्री प्रदूषण", "जल प्रदूषण"],
        "tamil": ["கடல்மாசு"],
        "telugu": ["సముద్రకాలుష్యం"],
        "weight": 55
    },
    
    "coastal_erosion": {
        "english": ["erosion", "coastal erosion", "beach erosion", "shoreline erosion",
                   "land loss", "sea wall damage"],
        "hindi": ["तटीय कटाव", "भूमि कटाव"],
        "tamil": ["கரையரிப்பு"],
        "telugu": ["తీరకోత"],
        "weight": 50
    },
    
    "shipwreck": {
        "english": ["shipwreck", "boat capsize", "ship sinking", "vessel accident",
                   "maritime accident", "boat accident"],
        "hindi": ["जहाज दुर्घटना", "नाव पलटी"],
        "tamil": ["கப்பல்விபத்து"],
        "telugu": ["ఓడప్రమాదం"],
        "weight": 70
    }
}


# =============================================================================
# SEVERITY KEYWORDS
# =============================================================================

SEVERITY_KEYWORDS = {
    "critical": {
        "keywords": [
            "emergency", "evacuate", "evacuation", "deaths", "dead", "killed",
            "casualties", "catastrophic", "devastating", "life-threatening",
            "red alert", "extreme danger", "immediate danger", "fatal",
            "mass evacuation", "disaster declared", "state of emergency"
        ],
        "score": 100
    },
    "high": {
        "keywords": [
            "severe", "dangerous", "warning", "major", "significant",
            "damage", "destroyed", "injured", "missing", "rescue",
            "orange alert", "serious", "critical condition", "heavy damage",
            "widespread damage", "relief operations"
        ],
        "score": 75
    },
    "medium": {
        "keywords": [
            "moderate", "advisory", "caution", "alert", "expected",
            "likely", "possible", "monitor", "watch", "yellow alert",
            "prepare", "be alert", "stay vigilant"
        ],
        "score": 50
    },
    "low": {
        "keywords": [
            "minor", "slight", "low", "minimal", "normal", "routine",
            "green", "no threat", "stable", "improving"
        ],
        "score": 25
    }
}


# =============================================================================
# SPAM KEYWORDS
# =============================================================================

SPAM_KEYWORDS = {
    "promotional": [
        "buy now", "discount", "offer", "sale", "click here", "link in bio",
        "follow for follow", "f4f", "l4l", "dm for", "check bio", "giveaway",
        "promo code", "affiliate", "sponsored", "ad", "promotion"
    ],
    "crypto_forex": [
        "crypto", "bitcoin", "nft", "forex", "trading", "investment",
        "earn money", "make money", "passive income", "get rich"
    ],
    "health_scams": [
        "weight loss", "diet", "supplement", "miracle", "cure",
        "lose weight fast", "fat burning"
    ],
    "bot_patterns": [
        "follow back", "followback", "teamfollowback", "followtrain",
        "gainwithxtina", "like4like"
    ]
}

ALL_SPAM_KEYWORDS = []
for category, keywords in SPAM_KEYWORDS.items():
    ALL_SPAM_KEYWORDS.extend(keywords)


# =============================================================================
# USER AGENTS - LARGE POOL
# =============================================================================

USER_AGENTS = [
    # Chrome - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Chrome - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Chrome - Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # Mobile - Android
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    
    # Mobile - iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]


# =============================================================================
# NEWS SOURCES
# =============================================================================

NEWS_SOURCES = {
    "indian_news": {
        "times_of_india": {
            "base_url": "https://timesofindia.indiatimes.com",
            "search_url": "https://timesofindia.indiatimes.com/topic/",
            "sections": ["weather", "cyclone", "floods", "disaster"]
        },
        "ndtv": {
            "base_url": "https://www.ndtv.com",
            "search_url": "https://www.ndtv.com/search?searchtext=",
            "sections": ["india-news", "cities", "south"]
        },
        "the_hindu": {
            "base_url": "https://www.thehindu.com",
            "search_url": "https://www.thehindu.com/search/",
            "sections": ["news/national", "news/cities"]
        },
        "indian_express": {
            "base_url": "https://indianexpress.com",
            "search_url": "https://indianexpress.com/?s=",
            "sections": ["india", "cities"]
        },
        "hindustan_times": {
            "base_url": "https://www.hindustantimes.com",
            "search_url": "https://www.hindustantimes.com/search?q=",
            "sections": ["india-news"]
        }
    },
    
    "official_sources": {
        "imd": {
            "base_url": "https://mausam.imd.gov.in",
            "cyclone_url": "https://mausam.imd.gov.in/imd_latest/contents/cyclone.php"
        },
        "incois": {
            "base_url": "https://incois.gov.in",
            "alerts_url": "https://incois.gov.in/portal/osf/osf.jsp"
        }
    }
}


# =============================================================================
# FACEBOOK OFFICIAL PAGES
# =============================================================================

FACEBOOK_OFFICIAL_PAGES = [
    "IndiaMetDept",
    "ABORAP", 
    "INCOIS",
    "ndma.india",
    "DisasterMgmtIndia",
    "IndianCoastGuard",
    "IndianNavy",
    "PMOIndia",
    "MoaborIndia",
]


# =============================================================================
# IMAGE CLASSIFICATION LABELS
# =============================================================================

IMAGE_CLASSIFICATION_LABELS = {
    "hazard_positive": [
        "flooded area with water damage",
        "storm damage to buildings and infrastructure",
        "rough sea with high dangerous waves",
        "cyclone or storm clouds formation",
        "coastal erosion and beach damage",
        "rescue operation with boats or helicopters",
        "oil spill on water surface",
        "damaged ships or boats",
        "evacuation of people",
        "relief camp or shelter"
    ],
    
    "hazard_negative": [
        "normal beach scenery",
        "selfie or portrait photo",
        "food photography",
        "promotional or advertisement content",
        "meme or edited image",
        "indoor scene unrelated to disaster",
        "wildlife in normal conditions"
    ]
}


# =============================================================================
# GLOBAL CONFIG INSTANCES
# =============================================================================

scraper_config = ScraperConfig()
cookie_config = CookieConfig()
nlp_config = NLPConfig()
vision_config = VisionConfig()
