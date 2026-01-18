"""
BlueRadar - Twitter Scraper
Uses RapidAPI Twitter241 for reliable access
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from scrapers.base_scraper import BaseScraper
from services.fast_scraper import RapidAPITwitterScraper
from utils.logging_config import setup_logging

logger = setup_logging("twitter_scraper")


class TwitterScraper(BaseScraper):
    """
    Twitter scraper for ocean hazard monitoring.
    Uses RapidAPI's Twitter241 API internally for reliable access.

    Note: Twitter/X is heavily protected against selenium scraping,
    so this uses the RapidAPI-based scraper for actual data fetching.
    """

    PLATFORM = "twitter"
    BASE_URL = "https://twitter.com"

    def __init__(
        self,
        headless: bool = True,
        use_session: bool = False
    ):
        super().__init__(headless=headless, use_session=use_session)
        self._api_scraper = RapidAPITwitterScraper()

    def scrape(
        self,
        keywords: List[str] = None,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Scrape Twitter for ocean hazard related posts.

        Args:
            keywords: List of keywords to search (used for local filtering)
            max_results: Maximum number of results to return

        Returns:
            List of post dictionaries
        """
        self.logger.info(f"Scraping Twitter for ocean hazard posts...")

        try:
            # Run the async scraper in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                posts = loop.run_until_complete(
                    self._api_scraper.search_ocean_hazards(max_results=max_results)
                )
            finally:
                loop.close()

            # Convert ScrapedPost objects to dicts if needed
            results = []
            for post in posts:
                if hasattr(post, 'to_dict'):
                    results.append(post.to_dict())
                elif isinstance(post, dict):
                    results.append(post)
                else:
                    # Convert dataclass to dict
                    results.append({
                        'platform': getattr(post, 'platform', 'twitter'),
                        'post_id': getattr(post, 'post_id', ''),
                        'username': getattr(post, 'username', ''),
                        'text': getattr(post, 'text', ''),
                        'timestamp': getattr(post, 'timestamp', datetime.now().isoformat()),
                        'url': getattr(post, 'url', ''),
                        'image_urls': getattr(post, 'image_urls', []),
                        'engagement': getattr(post, 'engagement', {}),
                        'location': getattr(post, 'location', None),
                        'hashtags': getattr(post, 'hashtags', []),
                    })

            # Filter by keywords if provided
            if keywords:
                keywords_lower = [k.lower() for k in keywords]
                filtered = []
                for post in results:
                    text = post.get('text', '').lower()
                    if any(kw in text for kw in keywords_lower):
                        filtered.append(post)
                results = filtered

            self.logger.info(f"Found {len(results)} Twitter posts")
            return results[:max_results]

        except Exception as e:
            self.logger.error(f"Twitter scraping error: {e}")
            return []

    def setup_driver(self):
        """Override - not needed for API-based scraping"""
        pass

    def close(self):
        """Override - not needed for API-based scraping"""
        pass
