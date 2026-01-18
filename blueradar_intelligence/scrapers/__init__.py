"""BlueRadar Scrapers Package"""

from .session_manager import SessionManager, session_manager
from .anti_detection import AntiDetection, anti_detection
from .base_scraper import BaseScraper
from .instagram_scraper import InstagramScraper
# TwitterScraper moved to services/fast_scraper.py (RapidAPITwitterScraper)
from .other_scrapers import (
    FacebookScraper, YouTubeScraper, NewsScraper, MultiPlatformScraper
)

__all__ = [
    "SessionManager", "session_manager",
    "AntiDetection", "anti_detection",
    "BaseScraper",
    "InstagramScraper",
    # "TwitterScraper" - Now using RapidAPITwitterScraper in services/fast_scraper.py
    "FacebookScraper",
    "YouTubeScraper",
    "NewsScraper",
    "MultiPlatformScraper"
]
