"""
BlueRadar Fast Parallel Scraper
Microservice-style workers for real-time data collection
"""

import asyncio
import aiohttp
import json
import time
import random
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from queue import Queue
from threading import Thread, Lock
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try imports
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@dataclass
class ScrapedPost:
    """Lightweight post structure for speed"""
    id: str
    platform: str
    text: str
    author: str
    url: str
    image_urls: List[str]
    timestamp: str
    hashtags: List[str]
    engagement: Dict
    raw_score: float = 0.0

    def to_dict(self):
        return asdict(self)


class RapidAPITwitterScraper:
    """
    Twitter scraper using RapidAPI's Twitter241 API.

    IMPORTANT: Limited to 500 requests/month on free tier.
    Makes ONE batch request to fetch 50 tweets with comprehensive query.
    All filtering is done locally to minimize API calls.
    """

    API_URL = "https://twitter241.p.rapidapi.com/search"

    # Comprehensive ocean hazard query for India - fetches ALL relevant tweets in one request
    OCEAN_HAZARD_QUERY = (
        "(#HighWaves OR #RoughSea OR #SeaWaves OR #OceanWaves OR #WaveAlert OR "
        "#MarineHazard OR #RipCurrent OR #RipTide OR #StrongCurrents OR "
        "#DangerousCurrents OR #BeachSafety OR #StormSurge OR #Cyclone OR "
        "#CycloneAlert OR #CycloneWarning OR #HurricaneWaves OR #SevereWeather OR "
        "#OceanStorm OR #CoastalFlooding OR #FloodedCoastline OR #SeaLevelRise OR "
        "#FloodAlert OR #CoastalDisaster OR #BeachedWhale OR #BeachedDolphin OR "
        "#MarineRescue OR #StrandedAnimal OR #WildlifeRescue OR #OilSpill OR "
        "#OilLeak OR #MarinePollution OR #OceanPollution OR #EnvironmentalDisaster OR "
        "#GhostNets OR #FishingNets OR #MarineEntanglement OR #SaveMarineLife OR "
        "#OceanAnimals OR #ShipWreck OR #WreckedShip OR #MaritimeAccident OR "
        "#SeaAccident OR #OceanDisaster OR #ChemicalSpill OR #ToxicWater OR "
        "#HazardousLeak OR #PollutedSea OR #MarineContamination OR #PlasticPollution OR "
        "#OceanPlastic OR #SaveOurOceans OR #BeatPlasticPollution OR #PlasticWaste OR "
        "#IMDAlert OR #INCOIS OR #IndianOcean OR #BayOfBengal OR #ArabianSea OR "
        "#ChennaiFlood OR #MumbaiRain OR #KeralaFlood OR #OdishaCyclone OR "
        "#Tsunami OR #TsunamiWarning OR #TidalWave) "
        "place_country:IN"
    )

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            print("[WARNING] RAPIDAPI_KEY not found in environment variables")
        self.session = None
        self._cached_posts: List[ScrapedPost] = []
        self._cache_time: datetime = None
        self._cache_duration_minutes = 5  # Cache results for 5 minutes to avoid redundant calls

    async def create_session(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self.session:
            await self.session.close()

    async def fetch_all_tweets(self, count: int = 50) -> List[ScrapedPost]:
        """
        Fetch all tweets in ONE API call using comprehensive query.
        This is the main method - makes only 1 request to get all relevant tweets.
        """
        # Check cache first to minimize API calls
        if self._cached_posts and self._cache_time:
            cache_age = (datetime.now() - self._cache_time).total_seconds() / 60
            if cache_age < self._cache_duration_minutes:
                print(f"[Twitter] Using cached results ({len(self._cached_posts)} tweets, {cache_age:.1f}min old)")
                return self._cached_posts

        posts = []

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "twitter241.p.rapidapi.com"
        }

        params = {
            "query": self.OCEAN_HAZARD_QUERY,
            "type": "latest",
            "count": str(count)
        }

        try:
            print(f"[Twitter] Fetching {count} tweets via RapidAPI (1 request)...")
            async with self.session.get(self.API_URL, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = self._parse_response(data)
                    print(f"[Twitter] Fetched {len(posts)} tweets successfully")

                    # Cache the results
                    self._cached_posts = posts
                    self._cache_time = datetime.now()
                elif response.status == 429:
                    print("[Twitter] Rate limited - API quota may be exhausted")
                else:
                    print(f"[Twitter] API error: {response.status}")
        except Exception as e:
            print(f"[Twitter] Error: {e}")

        return posts

    async def search(self, keyword: str, max_results: int = 10) -> List[ScrapedPost]:
        """
        Search for keyword - filters from cached batch results.
        Does NOT make additional API calls - filters locally.
        """
        # Get all tweets (from cache or fresh fetch)
        all_posts = await self.fetch_all_tweets()

        # Filter locally by keyword
        keyword_lower = keyword.lower().replace("#", "")
        filtered = []

        for post in all_posts:
            text_lower = post.text.lower()
            hashtags_lower = [h.lower() for h in post.hashtags]

            if keyword_lower in text_lower or keyword_lower in hashtags_lower:
                filtered.append(post)
                if len(filtered) >= max_results:
                    break

        return filtered

    def _parse_response(self, data: dict) -> List[ScrapedPost]:
        """Parse RapidAPI Twitter response into ScrapedPost objects"""
        posts = []

        # Handle different response structures
        tweets = []

        # Try to extract tweets from response
        if isinstance(data, dict):
            # Standard response structure
            if "result" in data:
                result = data["result"]
                if isinstance(result, dict):
                    timeline = result.get("timeline", {})
                    instructions = timeline.get("instructions", [])
                    for instruction in instructions:
                        entries = instruction.get("entries", [])
                        for entry in entries:
                            content = entry.get("content", {})
                            item_content = content.get("itemContent", {})
                            tweet_results = item_content.get("tweet_results", {})
                            if tweet_results:
                                tweets.append(tweet_results.get("result", {}))

            # Alternative: direct tweets array
            elif "tweets" in data:
                tweets = data.get("tweets", [])

            # Try timeline entries
            elif "timeline" in data:
                timeline = data.get("timeline", {})
                for entry in timeline.get("entries", []):
                    tweet_data = entry.get("tweet", {})
                    if tweet_data:
                        tweets.append(tweet_data)

        # Parse each tweet
        for tweet in tweets:
            try:
                post = self._parse_tweet(tweet)
                if post:
                    posts.append(post)
            except Exception as e:
                continue

        return posts

    def _parse_tweet(self, tweet: dict) -> Optional[ScrapedPost]:
        """Parse a single tweet object"""
        if not tweet:
            return None

        # Handle nested structure
        legacy = tweet.get("legacy", tweet)
        core = tweet.get("core", {})
        user_results = core.get("user_results", {}).get("result", {})
        user_legacy = user_results.get("legacy", {})
        user_core = user_results.get("core", {})  # screen_name is in user_results.result.core

        # Get text
        text = legacy.get("full_text", "") or legacy.get("text", "")
        if not text:
            return None

        # Get tweet ID
        tweet_id = legacy.get("id_str", "") or tweet.get("rest_id", "")
        if not tweet_id:
            tweet_id = hashlib.md5(text[:50].encode()).hexdigest()[:12]

        # Get author - check multiple locations
        author = (
            user_core.get("screen_name", "") or  # Primary: user_results.result.core.screen_name
            user_legacy.get("screen_name", "") or  # Fallback: user_results.result.legacy.screen_name
            legacy.get("user", {}).get("screen_name", "")  # Old structure
        )

        # Get images
        images = []
        media = legacy.get("entities", {}).get("media", [])
        for m in media:
            media_url = m.get("media_url_https", "") or m.get("media_url", "")
            if media_url:
                images.append(media_url)

        # Get timestamp
        created_at = legacy.get("created_at", "")

        # Extract hashtags
        hashtag_entities = legacy.get("entities", {}).get("hashtags", [])
        hashtags = [h.get("text", "") for h in hashtag_entities]
        if not hashtags:
            hashtags = re.findall(r'#(\w+)', text)

        # Get engagement
        likes = legacy.get("favorite_count", 0)
        retweets = legacy.get("retweet_count", 0)
        replies = legacy.get("reply_count", 0)

        return ScrapedPost(
            id=tweet_id,
            platform="twitter",
            text=text,
            author=author,
            url=f"https://twitter.com/{author}/status/{tweet_id}" if author and tweet_id else "",
            image_urls=images,
            timestamp=created_at,
            hashtags=hashtags,
            engagement={"likes": likes, "retweets": retweets, "replies": replies}
        )


class FastYouTubeScraper:
    """
    Fast YouTube scraper using direct HTTP requests
    No Selenium needed for search results
    """

    def __init__(self):
        self.session = None

    async def create_session(self):
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })

    async def close(self):
        if self.session:
            await self.session.close()

    async def search(self, keyword: str, max_results: int = 10) -> List[ScrapedPost]:
        """Search YouTube via HTTP"""
        posts = []
        url = f"https://www.youtube.com/results?search_query={keyword}"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    posts = self._parse_youtube_html(html, keyword)[:max_results]
        except Exception as e:
            print(f"YouTube error: {e}")

        return posts

    def _parse_youtube_html(self, html: str, keyword: str) -> List[ScrapedPost]:
        """Extract video data from YouTube HTML"""
        posts = []

        # Find JSON data in HTML
        pattern = r'var ytInitialData = ({.*?});'
        match = re.search(pattern, html)

        if not match:
            # Try alternative pattern
            pattern = r'ytInitialData\s*=\s*({.*?});'
            match = re.search(pattern, html)

        if match:
            try:
                data = json.loads(match.group(1))
                contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {})
                primary = contents.get('primaryContents', {}).get('sectionListRenderer', {})

                for section in primary.get('contents', []):
                    items = section.get('itemSectionRenderer', {}).get('contents', [])

                    for item in items:
                        video = item.get('videoRenderer', {})
                        if not video:
                            continue

                        video_id = video.get('videoId', '')
                        title = video.get('title', {}).get('runs', [{}])[0].get('text', '')
                        channel = video.get('ownerText', {}).get('runs', [{}])[0].get('text', '')

                        # Get thumbnail
                        thumbnails = video.get('thumbnail', {}).get('thumbnails', [])
                        thumb_url = thumbnails[-1].get('url', '') if thumbnails else ""

                        # Get view count
                        view_text = video.get('viewCountText', {}).get('simpleText', '0')

                        # Get published time (e.g., "1 month ago", "2 days ago")
                        published_text = video.get('publishedTimeText', {}).get('simpleText', '')

                        posts.append(ScrapedPost(
                            id=video_id,
                            platform="youtube",
                            text=title,
                            author=channel,
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            image_urls=[thumb_url] if thumb_url else [],
                            timestamp=published_text,  # Store the relative time string for parsing
                            hashtags=re.findall(r'#(\w+)', title),
                            engagement={"views": view_text}
                        ))

            except json.JSONDecodeError:
                pass

        return posts


class FastGoogleNewsScraper:
    """
    Fast Google News scraper using aiohttp
    No Selenium needed - parses RSS feed
    """

    def __init__(self):
        self.session = None

    async def create_session(self):
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })

    async def close(self):
        if self.session:
            await self.session.close()

    async def search(self, keyword: str, max_results: int = 10) -> List[ScrapedPost]:
        """Search Google News via RSS"""
        posts = []
        # Use Google News RSS feed
        url = f"https://news.google.com/rss/search?q={keyword}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    xml = await response.text()
                    posts = self._parse_rss(xml, keyword)[:max_results]
        except Exception as e:
            print(f"Google News error: {e}")

        return posts

    def _parse_rss(self, xml: str, keyword: str) -> List[ScrapedPost]:
        """Parse Google News RSS feed"""
        posts = []

        if not BS4_AVAILABLE:
            return posts

        soup = BeautifulSoup(xml, 'xml')
        items = soup.find_all('item')

        for item in items:
            try:
                title = item.find('title')
                title_text = title.get_text(strip=True) if title else ""

                link = item.find('link')
                link_url = link.get_text(strip=True) if link else ""

                pub_date = item.find('pubDate')
                timestamp = pub_date.get_text(strip=True) if pub_date else ""

                source = item.find('source')
                source_name = source.get_text(strip=True) if source else "Google News"

                # Generate ID
                post_id = hashlib.md5(f"{title_text[:50]}".encode()).hexdigest()[:12]

                posts.append(ScrapedPost(
                    id=post_id,
                    platform="news",
                    text=title_text,
                    author=source_name,
                    url=link_url,
                    image_urls=[],
                    timestamp=timestamp,
                    hashtags=re.findall(r'#(\w+)', title_text),
                    engagement={}
                ))

            except Exception:
                continue

        return posts


class RapidAPIInstagramScraper:
    """
    Instagram scraper using RapidAPI's Instagram-Data1 API.
    Uses hashtag/feed/v2 endpoint for fetching posts by hashtag.
    """

    # Using the instagram-data1 API (correct endpoint is /hashtag/feed, not /v2)
    API_URL = "https://instagram-data1.p.rapidapi.com/hashtag/feed"
    API_HOST = "instagram-data1.p.rapidapi.com"

    # Ocean hazard hashtags for Instagram
    HAZARD_HASHTAGS = [
        "HighWaves", "RoughSea", "SeaWaves", "OceanWaves", "WaveAlert", "MarineHazard",
        "RipCurrent", "RipTide", "StrongCurrents", "DangerousCurrents", "BeachSafety",
        "StormSurge", "Cyclone", "CycloneAlert", "CycloneWarning", "HurricaneWaves",
        "SevereWeather", "OceanStorm", "CoastalFlooding", "FloodedCoastline",
        "SeaLevelRise", "FloodAlert", "CoastalDisaster", "BeachedWhale", "BeachedDolphin",
        "MarineRescue", "StrandedAnimal", "WildlifeRescue", "OilSpill", "OilLeak",
        "MarinePollution", "OceanPollution", "EnvironmentalDisaster", "GhostNets",
        "FishingNets", "MarineEntanglement", "SaveMarineLife", "OceanAnimals",
        "ShipWreck", "WreckedShip", "MaritimeAccident", "SeaAccident", "OceanDisaster",
        "ChemicalSpill", "ToxicWater", "HazardousLeak", "PollutedSea", "MarineContamination",
        "PlasticPollution", "OceanPlastic", "SaveOurOceans", "BeatPlasticPollution", "PlasticWaste"
    ]

    # India-related keywords for filtering
    INDIA_KEYWORDS = [
        "india", "bharat", "in", "tamil nadu", "kerala", "goa", "mumbai", "kochi",
        "chennai", "gujarat", "odisha", "andhra", "pondicherry", "karnataka", "vizag",
        "maharashtra", "bengal", "kolkata", "west bengal", "bay of bengal", "arabian sea",
        "indian ocean", "imd", "incois"
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_INSTAGRAM_KEY") or os.getenv("RAPIDAPI_KEY")
        if not self.api_key:
            print("[WARNING] RAPIDAPI_INSTAGRAM_KEY not found in environment variables")
        self.session = None
        self._cached_posts: List[ScrapedPost] = []
        self._cache_time: datetime = None
        self._cache_duration_minutes = 5

    async def create_session(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self.session:
            await self.session.close()

    def _is_india_related(self, text: str) -> bool:
        """Check if post is India-related"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.INDIA_KEYWORDS)

    async def fetch_hashtag_posts(self, hashtag: str) -> List[ScrapedPost]:
        """Fetch posts for a single hashtag using Instagram120 RapidAPI"""
        posts = []

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.API_HOST
        }

        # Instagram120 uses 'hashtag' parameter (without #)
        params = {"hashtag": hashtag.replace("#", "")}

        try:
            print(f"[Instagram] Fetching #{hashtag}...")
            async with self.session.get(self.API_URL, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = self._parse_response(data, hashtag)
                elif response.status == 429:
                    print(f"[Instagram] Rate limited on #{hashtag}")
                else:
                    print(f"[Instagram] API error {response.status} for #{hashtag}")
        except Exception as e:
            print(f"[Instagram] Error fetching #{hashtag}: {e}")

        return posts

    async def fetch_all_posts(self, hashtags: List[str] = None, max_per_hashtag: int = 10) -> List[ScrapedPost]:
        """
        Fetch posts from multiple hashtags.
        Filters for India-related content.
        """
        # Check cache first
        if self._cached_posts and self._cache_time:
            cache_age = (datetime.now() - self._cache_time).total_seconds() / 60
            if cache_age < self._cache_duration_minutes:
                print(f"[Instagram] Using cached results ({len(self._cached_posts)} posts, {cache_age:.1f}min old)")
                return self._cached_posts

        hashtags = hashtags or self.HAZARD_HASHTAGS[:10]  # Limit to first 10 to save API calls
        all_posts = []
        seen_ids = set()

        for hashtag in hashtags:
            posts = await self.fetch_hashtag_posts(hashtag)

            # Filter for India-related and deduplicate
            for post in posts[:max_per_hashtag]:
                if post.id not in seen_ids:
                    # Apply India filter
                    if self._is_india_related(post.text):
                        all_posts.append(post)
                        seen_ids.add(post.id)

            # Small delay between requests
            await asyncio.sleep(0.3)

        print(f"[Instagram] Fetched {len(all_posts)} India-related posts from {len(hashtags)} hashtags")

        # Cache results
        self._cached_posts = all_posts
        self._cache_time = datetime.now()

        return all_posts

    async def search(self, keyword: str, max_results: int = 10) -> List[ScrapedPost]:
        """
        Search for keyword - filters from cached results or fetches fresh.
        """
        all_posts = await self.fetch_all_posts()

        # Filter locally by keyword
        keyword_lower = keyword.lower().replace("#", "")
        filtered = []

        for post in all_posts:
            text_lower = post.text.lower()
            hashtags_lower = [h.lower() for h in post.hashtags]

            if keyword_lower in text_lower or keyword_lower in hashtags_lower:
                filtered.append(post)
                if len(filtered) >= max_results:
                    break

        return filtered

    def _parse_response(self, data: dict, hashtag: str) -> List[ScrapedPost]:
        """Parse RapidAPI Instagram-Data1 response into ScrapedPost objects"""
        posts = []

        # Handle instagram-data1 API response structure
        # Response format: {"count": N, "collector": [...], "has_more": bool, ...}
        items = []

        if isinstance(data, dict):
            # instagram-data1 uses 'collector' array
            items = data.get("collector", [])
            if not items:
                # Fallback to other common structures
                items = data.get("data", {}).get("items", [])
            if not items:
                items = data.get("items", [])

        for item in items:
            try:
                post = self._parse_post(item, hashtag)
                if post:
                    posts.append(post)
            except Exception:
                continue

        return posts

    def _parse_post(self, item: dict, hashtag: str) -> Optional[ScrapedPost]:
        """Parse a single Instagram post from instagram-data1 API"""
        if not item:
            return None

        # Get post ID - instagram-data1 uses 'id' or 'shortcode'
        post_id = item.get("id", "") or item.get("shortcode", "") or item.get("pk", "")
        if not post_id:
            return None

        # Get caption/text - instagram-data1 uses 'description'
        text = item.get("description", "") or ""
        if not text:
            caption = item.get("caption", {})
            if isinstance(caption, dict):
                text = caption.get("text", "")
            else:
                text = str(caption) if caption else ""

        # Get author - instagram-data1 uses 'owner' object with 'username'
        owner = item.get("owner", {})
        if isinstance(owner, dict):
            author = owner.get("username", "") or owner.get("full_name", "")
        else:
            author = str(owner) if owner else ""
        if not author:
            user = item.get("user", {})
            author = user.get("username", "") or user.get("full_name", "")

        # Get shortcode for URL
        shortcode = item.get("shortcode", "") or item.get("code", "")
        url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""

        # Get images - instagram-data1 uses 'displayUrl' or 'thumbnail'
        images = []
        if item.get("displayUrl"):
            images.append(item.get("displayUrl"))
        elif item.get("thumbnail"):
            images.append(item.get("thumbnail"))
        elif item.get("display_url"):
            images.append(item.get("display_url"))
        elif item.get("thumbnail_url"):
            images.append(item.get("thumbnail_url"))

        # Get timestamp - instagram-data1 uses 'taken_at_timestamp'
        taken_at = item.get("taken_at_timestamp", 0) or item.get("taken_at", 0)
        if taken_at:
            timestamp = datetime.fromtimestamp(taken_at).isoformat()
        else:
            timestamp = datetime.now().isoformat()

        # Extract hashtags from text
        hashtags_list = re.findall(r'#(\w+)', text)
        if hashtag not in hashtags_list:
            hashtags_list.append(hashtag)

        # Get engagement - instagram-data1 uses 'likesCount', 'commentsCount'
        likes = item.get("likesCount", 0) or item.get("like_count", 0) or 0
        comments = item.get("commentsCount", 0) or item.get("comment_count", 0) or 0

        return ScrapedPost(
            id=str(post_id),
            platform="instagram",
            text=text,
            author=author,
            url=url,
            image_urls=images,
            timestamp=timestamp,
            hashtags=hashtags_list,
            engagement={"likes": likes, "comments": comments}
        )


class ParallelScraperManager:
    """
    Manages multiple scrapers running in parallel
    Collects results into a shared queue for processing
    """

    def __init__(self, instagram_sessions: List[str] = None):
        self.result_queue = Queue()
        self.instagram_sessions = instagram_sessions or []
        self.running = False
        self.workers = []

        # Callbacks for real-time updates
        self.on_post_found: Optional[Callable] = None
        self.on_alert: Optional[Callable] = None

    async def scrape_twitter_async(self, keywords: List[str], max_per: int = 10):
        """
        Async Twitter scraping using RapidAPI.

        IMPORTANT: This makes only ONE API request to fetch all tweets,
        then filters locally. This preserves API quota (500/month).
        """
        scraper = RapidAPITwitterScraper()
        await scraper.create_session()

        try:
            # Fetch ALL tweets in one API call (uses comprehensive query)
            all_posts = await scraper.fetch_all_tweets(count=50)

            # Add all posts to queue - they're already filtered for India ocean hazards
            for post in all_posts:
                self.result_queue.put(post)
                if self.on_post_found:
                    self.on_post_found(post)

            print(f"[Twitter] Added {len(all_posts)} tweets to pipeline")
        finally:
            await scraper.close()

    async def scrape_youtube_async(self, keywords: List[str], max_per: int = 10):
        """Async YouTube scraping"""
        scraper = FastYouTubeScraper()
        await scraper.create_session()

        try:
            for keyword in keywords:
                posts = await scraper.search(keyword, max_per)
                for post in posts:
                    self.result_queue.put(post)
                    if self.on_post_found:
                        self.on_post_found(post)
                await asyncio.sleep(0.5)
        finally:
            await scraper.close()

    async def scrape_instagram_async(self, keywords: List[str], max_per: int = 10):
        """
        Async Instagram scraping using RapidAPI.
        No longer requires session IDs - uses API key from environment.
        """
        scraper = RapidAPIInstagramScraper()
        await scraper.create_session()

        try:
            # Fetch all posts from hazard hashtags
            all_posts = await scraper.fetch_all_posts(max_per_hashtag=max_per)

            # Add all posts to queue
            for post in all_posts:
                self.result_queue.put(post)
                if self.on_post_found:
                    self.on_post_found(post)

            print(f"[Instagram] Added {len(all_posts)} posts to pipeline")
        finally:
            await scraper.close()

    async def scrape_news_async(self, keywords: List[str], max_per: int = 10):
        """Async Google News scraping"""
        scraper = FastGoogleNewsScraper()
        await scraper.create_session()

        try:
            for keyword in keywords:
                posts = await scraper.search(keyword, max_per)
                for post in posts:
                    self.result_queue.put(post)
                    if self.on_post_found:
                        self.on_post_found(post)
                await asyncio.sleep(0.5)
        finally:
            await scraper.close()

    async def run_parallel_scrape(
        self,
        keywords: List[str],
        platforms: List[str] = None,
        max_per: int = 10
    ) -> List[ScrapedPost]:
        """
        Run all scrapers in parallel
        Returns collected posts
        """
        platforms = platforms or ["twitter", "youtube", "instagram"]

        tasks = []

        # Async tasks for Twitter, YouTube, News, and Instagram
        if "twitter" in platforms:
            tasks.append(self.scrape_twitter_async(keywords, max_per))

        if "youtube" in platforms:
            tasks.append(self.scrape_youtube_async(keywords, max_per))

        if "news" in platforms:
            tasks.append(self.scrape_news_async(keywords, max_per))

        # Instagram is now async via RapidAPI (no more Selenium/sessions needed)
        if "instagram" in platforms:
            tasks.append(self.scrape_instagram_async(keywords, max_per))

        # Run all async tasks in parallel
        if tasks:
            await asyncio.gather(*tasks)

        # Collect all results
        posts = []
        while not self.result_queue.empty():
            posts.append(self.result_queue.get())

        return posts

    def start_continuous_scraping(
        self,
        keywords: List[str],
        interval_seconds: int = 300,  # 5 minutes
        platforms: List[str] = None
    ):
        """
        Start continuous background scraping
        Runs in separate thread
        """
        self.running = True

        def worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while self.running:
                try:
                    posts = loop.run_until_complete(
                        self.run_parallel_scrape(keywords, platforms)
                    )
                    print(f"[{datetime.now()}] Scraped {len(posts)} posts")

                    # Wait for next interval
                    time.sleep(interval_seconds)

                except Exception as e:
                    print(f"Scraping error: {e}")
                    time.sleep(60)  # Wait before retry

            loop.close()

        thread = Thread(target=worker, daemon=True)
        thread.start()
        self.workers.append(thread)

        return thread

    def stop(self):
        """Stop all workers"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)


# Quick test
async def test_fast_scraper():
    """Test the fast scraper"""
    print("Testing Fast Parallel Scraper...")

    manager = ParallelScraperManager()

    keywords = ["cyclone", "flood", "storm"]

    start = time.time()
    posts = await manager.run_parallel_scrape(
        keywords,
        platforms=["twitter", "youtube"],  # Skip Instagram for quick test
        max_per=5
    )
    elapsed = time.time() - start

    print(f"\nResults:")
    print(f"  Posts collected: {len(posts)}")
    print(f"  Time taken: {elapsed:.2f} seconds")
    print(f"  Speed: {len(posts)/elapsed:.1f} posts/second")

    for post in posts[:5]:
        print(f"\n  [{post.platform}] {post.text[:80]}...")

    return posts


if __name__ == "__main__":
    asyncio.run(test_fast_scraper())
