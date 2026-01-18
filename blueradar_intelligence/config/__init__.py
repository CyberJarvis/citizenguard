"""BlueRadar Configuration Package"""

from .settings import (
    # Paths
    BASE_DIR, DATA_DIR, MODELS_DIR, OUTPUT_DIR, IMAGES_DIR, CACHE_DIR, LOGS_DIR, REPORTS_DIR,
    
    # Enums
    SeverityLevel, HazardType, Platform,
    
    # Configs
    scraper_config, cookie_config, nlp_config, vision_config,
    ScraperConfig, CookieConfig, NLPConfig, VisionConfig,
    
    # Keywords and hashtags
    HAZARD_HASHTAGS, ALL_HASHTAGS, HAZARD_KEYWORDS, SEVERITY_KEYWORDS,
    SPAM_KEYWORDS, ALL_SPAM_KEYWORDS,
    
    # Locations
    INDIAN_COASTAL_LOCATIONS, ALL_LOCATIONS,
    
    # Platform configs
    USER_AGENTS, NEWS_SOURCES, FACEBOOK_OFFICIAL_PAGES,
    
    # Image labels
    IMAGE_CLASSIFICATION_LABELS,
)

__all__ = [
    "BASE_DIR", "DATA_DIR", "MODELS_DIR", "OUTPUT_DIR", "IMAGES_DIR", 
    "CACHE_DIR", "LOGS_DIR", "REPORTS_DIR",
    "SeverityLevel", "HazardType", "Platform",
    "scraper_config", "cookie_config", "nlp_config", "vision_config",
    "ScraperConfig", "CookieConfig", "NLPConfig", "VisionConfig",
    "HAZARD_HASHTAGS", "ALL_HASHTAGS", "HAZARD_KEYWORDS", "SEVERITY_KEYWORDS",
    "SPAM_KEYWORDS", "ALL_SPAM_KEYWORDS",
    "INDIAN_COASTAL_LOCATIONS", "ALL_LOCATIONS",
    "USER_AGENTS", "NEWS_SOURCES", "FACEBOOK_OFFICIAL_PAGES",
    "IMAGE_CLASSIFICATION_LABELS",
]
