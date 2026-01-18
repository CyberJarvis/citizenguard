"""
BlueRadar Services Module
Fast microservices for scraping and NLP
"""

from .fast_scraper import (
    ParallelScraperManager,
    RapidAPITwitterScraper,
    FastYouTubeScraper,
    RapidAPIInstagramScraper,  # Replaced Selenium-based scraper with RapidAPI
    ScrapedPost
)
from .fast_nlp import FastNLPProcessor, FastNLPResult

__all__ = [
    "ParallelScraperManager",
    "RapidAPITwitterScraper",
    "FastYouTubeScraper",
    "RapidAPIInstagramScraper",
    "ScrapedPost",
    "FastNLPProcessor",
    "FastNLPResult"
]
