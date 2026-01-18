"""
BlueRadar - Additional Platform Scrapers
Facebook, YouTube, Google News, and Indian News Sites
"""

import re
import time
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote_plus, urljoin

from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from config import FACEBOOK_OFFICIAL_PAGES, NEWS_SOURCES
from utils.logging_config import setup_logging

logger = setup_logging("other_scrapers")


# =============================================================================
# FACEBOOK SCRAPER
# =============================================================================

class FacebookScraper(BaseScraper):
    """
    Facebook scraper for public pages.
    Uses mobile site (m.facebook.com) for better access.
    """
    
    PLATFORM = "facebook"
    BASE_URL = "https://m.facebook.com"
    DESKTOP_URL = "https://www.facebook.com"
    
    def __init__(
        self,
        headless: bool = True,
        use_session: bool = False
    ):
        super().__init__(headless=headless, use_session=use_session)
        self.official_pages = FACEBOOK_OFFICIAL_PAGES
    
    def scrape(
        self,
        pages: List[str] = None,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Scrape Facebook pages.
        
        Args:
            pages: List of page names/IDs (default: official disaster pages)
            max_results: Max posts per page
        """
        pages = pages or self.official_pages
        
        self.setup_driver()
        
        if self.use_session:
            self.apply_session_cookie()
        
        all_posts = []
        
        for page in pages:
            self.logger.info(f"📘 Scraping Facebook page: {page}")
            
            try:
                posts = self._scrape_page(page, max_results)
                all_posts.extend(posts)
                self.logger.info(f"✅ Found {len(posts)} posts from {page}")
            except Exception as e:
                self.logger.error(f"Error scraping {page}: {e}")
            
            self.anti_detection.random_delay(5, 10)
        
        self.close()
        return all_posts
    
    def _scrape_page(self, page_name: str, max_results: int) -> List[Dict]:
        """Scrape a single Facebook page"""
        # Try mobile URL first (less restrictive)
        url = f"{self.BASE_URL}/{page_name}"
        
        if not self.get_page_safe(url):
            return []
        
        # Check for login wall
        if self._is_login_required():
            self.logger.warning(f"Login required for {page_name}")
            return []
        
        self.anti_detection.random_delay(2, 4)
        self.scroll_page(count=3)
        
        soup = self.get_page_soup()
        posts = []
        
        # Find post containers
        article_selectors = [
            "article",
            "div[data-ft]",
            "div[role='article']",
            ".story_body_container",
            ".userContent"
        ]
        
        for selector in article_selectors:
            articles = soup.select(selector)
            if articles:
                break
        else:
            articles = []
        
        for article in articles[:max_results]:
            try:
                post_data = self._extract_post(article, page_name)
                if post_data:
                    posts.append(post_data)
                    self.scraped_count += 1
            except Exception as e:
                self.logger.debug(f"Error extracting post: {e}")
        
        return posts
    
    def _is_login_required(self) -> bool:
        """Check for login wall"""
        source = self.driver.page_source.lower()
        indicators = [
            "log in", "sign up", "create account",
            "you must log in", "please log in"
        ]
        return any(ind in source for ind in indicators)
    
    def _extract_post(self, article, page_name: str) -> Optional[Dict]:
        """Extract post data from article element"""
        # Text content
        text = ""
        for p in article.select("p, span, div.userContent"):
            t = p.get_text(strip=True)
            if len(t) > 50:
                text = t
                break
        
        # Images
        image_urls = []
        for img in article.select("img[src*='fbcdn']"):
            src = img.get("src", "")
            if src and self._is_content_image(src):
                image_urls.append(src)
        
        # Post URL
        post_url = ""
        link_elem = article.select_one("a[href*='/story'], a[href*='/posts/'], a[href*='/permalink/']")
        if link_elem:
            href = link_elem.get("href", "")
            if href:
                if href.startswith("/"):
                    post_url = f"https://facebook.com{href}"
                else:
                    post_url = href
        
        # Timestamp
        timestamp = ""
        time_elem = article.select_one("abbr, time")
        if time_elem:
            timestamp = time_elem.get("data-utime", "") or time_elem.get("title", "")
        
        if not text and not image_urls:
            return None
        
        return self.create_post_entry(
            url=post_url,
            username=page_name,
            display_name=page_name,
            profile_url=f"{self.DESKTOP_URL}/{page_name}",
            is_official=page_name in self.official_pages,
            text=text,
            hashtags=self.extract_hashtags(text),
            mentions=self.extract_mentions(text),
            image_urls=image_urls,
            media_type="image" if image_urls else "none",
            posted_at=timestamp,
            search_keyword=f"page:{page_name}"
        )
    
    def _is_content_image(self, url: str) -> bool:
        """Filter out icons and avatars"""
        skip_patterns = [
            "emoji", "static", "rsrc", "icon", "logo",
            "50x50", "32x32", "64x64", "profile"
        ]
        return not any(s in url.lower() for s in skip_patterns)


# =============================================================================
# YOUTUBE SCRAPER
# =============================================================================

class YouTubeScraper(BaseScraper):
    """
    YouTube scraper for hazard-related videos.
    Extracts video metadata, thumbnails, and descriptions.
    """
    
    PLATFORM = "youtube"
    BASE_URL = "https://www.youtube.com"
    SEARCH_URL = "https://www.youtube.com/results"
    
    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, use_session=False)
    
    def scrape(
        self,
        keywords: List[str],
        max_results: int = 20
    ) -> List[Dict]:
        """Search YouTube for videos"""
        self.setup_driver()
        
        all_posts = []
        
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
                
            self.logger.info(f"🎬 Searching YouTube for: {keyword}")
            
            try:
                posts = self._search_keyword(keyword, max_results)
                all_posts.extend(posts)
                self.logger.info(f"✅ Found {len(posts)} videos for '{keyword}'")
            except Exception as e:
                self.logger.error(f"Error searching: {e}")
            
            self.anti_detection.random_delay(3, 6)
        
        self.close()
        return all_posts
    
    def _search_keyword(self, keyword: str, max_results: int) -> List[Dict]:
        """Search for videos"""
        query = quote_plus(keyword)
        url = f"{self.SEARCH_URL}?search_query={query}"
        
        if not self.get_page_safe(url):
            return []
        
        # Wait for results to load
        self.wait_for_element(
            By.CSS_SELECTOR,
            "ytd-video-renderer, ytd-video-with-context-renderer",
            timeout=15
        )
        
        self.scroll_page(count=3)
        
        soup = self.get_page_soup()
        
        # Find video elements
        videos = soup.select("ytd-video-renderer, ytd-video-with-context-renderer")
        
        posts = []
        for video in videos[:max_results]:
            try:
                post_data = self._extract_video(video, keyword)
                if post_data:
                    posts.append(post_data)
                    self.scraped_count += 1
            except Exception as e:
                self.logger.debug(f"Error extracting video: {e}")
        
        return posts
    
    def _extract_video(self, video_elem, keyword: str) -> Optional[Dict]:
        """Extract video data"""
        # Title and URL
        title_elem = video_elem.select_one("#video-title, a#video-title")
        if not title_elem:
            return None
        
        title = self.extract_text_safe(title_elem)
        video_url = title_elem.get("href", "")
        
        if video_url and not video_url.startswith("http"):
            video_url = f"{self.BASE_URL}{video_url}"
        
        # Channel name
        channel_elem = video_elem.select_one(
            "#channel-name a, #channel-name yt-formatted-string, .ytd-channel-name a"
        )
        channel = self.extract_text_safe(channel_elem)
        
        # Channel URL
        channel_url = ""
        if channel_elem and channel_elem.get("href"):
            href = channel_elem.get("href")
            channel_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
        
        # Metadata (views, time)
        meta_elem = video_elem.select_one("#metadata-line, #metadata")
        views = ""
        upload_time = ""
        
        if meta_elem:
            spans = meta_elem.select("span")
            for span in spans:
                text = span.get_text(strip=True).lower()
                if "view" in text:
                    views = text
                elif any(t in text for t in ["ago", "hour", "day", "week", "month", "year"]):
                    upload_time = text
        
        # Description snippet
        description = ""
        desc_elem = video_elem.select_one(".metadata-snippet-text, #description-text")
        if desc_elem:
            description = self.extract_text_safe(desc_elem)
        
        # Thumbnail
        thumbnail = ""
        thumb_elem = video_elem.select_one("img#img, img.yt-img-shadow")
        if thumb_elem:
            thumbnail = thumb_elem.get("src", "")
        
        # Duration
        duration = ""
        duration_elem = video_elem.select_one(
            "#overlays ytd-thumbnail-overlay-time-status-renderer, .ytd-thumbnail-overlay-time-status-renderer"
        )
        if duration_elem:
            duration = self.extract_text_safe(duration_elem)
        
        if not title:
            return None
        
        return self.create_post_entry(
            url=video_url,
            username=channel,
            display_name=channel,
            profile_url=channel_url,
            text=f"{title}\n\n{description}".strip(),
            hashtags=self.extract_hashtags(title + " " + description),
            image_urls=[thumbnail] if thumbnail else [],
            thumbnails=[thumbnail] if thumbnail else [],
            media_type="video",
            views=self._parse_views(views),
            video_duration=duration,
            posted_at=upload_time,
            search_keyword=keyword
        )
    
    def _parse_views(self, views_str: str) -> int:
        """Parse view count"""
        if not views_str:
            return 0
        
        views_str = views_str.lower().replace(",", "").replace(" views", "").replace(" view", "")
        
        multiplier = 1
        if "k" in views_str:
            multiplier = 1000
            views_str = views_str.replace("k", "")
        elif "m" in views_str:
            multiplier = 1000000
            views_str = views_str.replace("m", "")
        elif "b" in views_str:
            multiplier = 1000000000
            views_str = views_str.replace("b", "")
        
        try:
            return int(float(views_str.strip()) * multiplier)
        except:
            return 0
    
    def scrape_channel(self, channel_id: str, max_videos: int = 20) -> List[Dict]:
        """Scrape videos from a YouTube channel"""
        self.setup_driver()
        
        url = f"{self.BASE_URL}/channel/{channel_id}/videos"
        
        if not self.get_page_safe(url):
            self.close()
            return []
        
        self.scroll_page(count=3)
        
        soup = self.get_page_soup()
        videos = soup.select("ytd-grid-video-renderer, ytd-rich-item-renderer")
        
        posts = []
        for video in videos[:max_videos]:
            try:
                post_data = self._extract_video(video, f"channel:{channel_id}")
                if post_data:
                    posts.append(post_data)
            except:
                continue
        
        self.close()
        return posts


# =============================================================================
# NEWS SCRAPER
# =============================================================================

class NewsScraper(BaseScraper):
    """
    Scraper for news sources:
    - Google News
    - Indian news sites (TOI, NDTV, The Hindu)
    """
    
    PLATFORM = "news"
    
    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, use_session=False)
        self.sources = NEWS_SOURCES
    
    def scrape(
        self,
        keywords: List[str],
        max_results: int = 30,
        sources: List[str] = None
    ) -> List[Dict]:
        """
        Scrape news articles.
        
        Args:
            keywords: Search terms
            max_results: Max articles per keyword
            sources: Specific sources to search (default: all)
        """
        self.setup_driver()
        
        all_posts = []
        
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
            
            self.logger.info(f"📰 Searching news for: {keyword}")
            
            # Google News
            try:
                posts = self._search_google_news(keyword, max_results // 2)
                all_posts.extend(posts)
            except Exception as e:
                self.logger.error(f"Google News error: {e}")
            
            # Indian news sites
            try:
                posts = self._search_indian_news(keyword, max_results // 2)
                all_posts.extend(posts)
            except Exception as e:
                self.logger.error(f"Indian news error: {e}")
            
            self.anti_detection.random_delay(3, 5)
        
        self.close()
        return all_posts
    
    def _search_google_news(self, keyword: str, max_results: int) -> List[Dict]:
        """Search Google News"""
        query = quote_plus(keyword)
        url = f"https://news.google.com/search?q={query}&hl=en-IN&gl=IN"
        
        if not self.get_page_safe(url):
            return []
        
        self.anti_detection.random_delay(2, 4)
        self.scroll_page(count=2)
        
        soup = self.get_page_soup()
        
        # Find article elements
        articles = soup.select("article, [jslog]")
        
        posts = []
        for article in articles[:max_results]:
            try:
                # Title
                title_elem = article.select_one("h3, h4, a[href*='articles']")
                title = self.extract_text_safe(title_elem)
                
                if not title:
                    continue
                
                # URL
                link_elem = article.select_one("a[href*='articles'], a[href*='./articles']")
                article_url = ""
                if link_elem:
                    href = link_elem.get("href", "")
                    if href.startswith("./"):
                        article_url = f"https://news.google.com{href[1:]}"
                    elif href.startswith("/"):
                        article_url = f"https://news.google.com{href}"
                    else:
                        article_url = href
                
                # Source
                source_elem = article.select_one("time + a, .source-name")
                source = self.extract_text_safe(source_elem) or "Google News"
                
                # Time
                time_elem = article.select_one("time")
                timestamp = ""
                if time_elem:
                    timestamp = time_elem.get("datetime", "") or time_elem.get_text(strip=True)
                
                # Image
                image_urls = []
                img_elem = article.select_one("img[src*='http']")
                if img_elem:
                    image_urls.append(img_elem.get("src", ""))
                
                posts.append(self.create_post_entry(
                    url=article_url,
                    username=source,
                    display_name=source,
                    is_official=True,
                    account_type="news",
                    text=title,
                    hashtags=self.extract_hashtags(title),
                    image_urls=image_urls,
                    media_type="article",
                    posted_at=timestamp,
                    search_keyword=keyword
                ))
                self.scraped_count += 1
                
            except Exception as e:
                self.logger.debug(f"Error extracting article: {e}")
        
        return posts
    
    def _search_indian_news(self, keyword: str, max_results: int) -> List[Dict]:
        """Search Indian news sites"""
        posts = []
        
        indian_sources = self.sources.get("indian_news", {})
        
        for source_name, source_config in indian_sources.items():
            if len(posts) >= max_results:
                break
            
            try:
                source_posts = self._search_single_source(
                    source_name,
                    source_config,
                    keyword,
                    max_results // len(indian_sources)
                )
                posts.extend(source_posts)
            except Exception as e:
                self.logger.debug(f"Error searching {source_name}: {e}")
            
            self.anti_detection.random_delay(2, 4)
        
        return posts[:max_results]
    
    def _search_single_source(
        self,
        source_name: str,
        config: Dict,
        keyword: str,
        max_results: int
    ) -> List[Dict]:
        """Search a single news source"""
        search_url = config.get("search_url", "")
        base_url = config.get("base_url", "")
        
        if not search_url:
            return []
        
        query = quote_plus(keyword)
        url = f"{search_url}{query}"
        
        if not self.get_page_safe(url):
            return []
        
        self.anti_detection.random_delay(1, 3)
        
        soup = self.get_page_soup()
        
        # Generic article selectors
        article_selectors = [
            "article", ".story", ".article-item", ".news-item",
            ".search-result", ".listing-item", "li[class*='story']"
        ]
        
        articles = []
        for selector in article_selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        posts = []
        for article in articles[:max_results]:
            try:
                # Title
                title_elem = article.select_one("h2, h3, h4, .title, a.title")
                title = self.extract_text_safe(title_elem)
                
                if not title or len(title) < 20:
                    continue
                
                # URL
                link_elem = article.select_one("a[href]")
                article_url = ""
                if link_elem:
                    href = link_elem.get("href", "")
                    if href.startswith("http"):
                        article_url = href
                    elif href.startswith("/"):
                        article_url = f"{base_url}{href}"
                
                # Description
                desc_elem = article.select_one("p, .summary, .description")
                description = self.extract_text_safe(desc_elem)
                
                # Image
                image_urls = []
                img_elem = article.select_one("img[src*='http']")
                if img_elem:
                    image_urls.append(img_elem.get("src", ""))
                
                # Time
                time_elem = article.select_one("time, .date, .timestamp")
                timestamp = self.extract_text_safe(time_elem)
                
                posts.append(self.create_post_entry(
                    url=article_url,
                    username=source_name,
                    display_name=source_name.replace("_", " ").title(),
                    profile_url=base_url,
                    is_official=True,
                    account_type="news",
                    text=f"{title}\n\n{description}".strip(),
                    hashtags=self.extract_hashtags(title),
                    image_urls=image_urls,
                    media_type="article",
                    posted_at=timestamp,
                    search_keyword=keyword
                ))
                self.scraped_count += 1
                
            except Exception as e:
                self.logger.debug(f"Error: {e}")
        
        return posts


# =============================================================================
# COMBINED SCRAPER
# =============================================================================

class MultiPlatformScraper:
    """
    Convenience class to scrape multiple platforms at once.
    """
    
    def __init__(self, headless: bool = True, use_instagram_session: bool = True):
        self.headless = headless
        self.use_instagram_session = use_instagram_session
        self.logger = setup_logging("multi_scraper")
    
    def scrape_all(
        self,
        keywords: List[str],
        platforms: List[str] = None,
        max_per_platform: int = 30
    ) -> Dict[str, List[Dict]]:
        """
        Scrape all specified platforms.
        
        Args:
            keywords: Search terms
            platforms: List of platforms (default: all)
            max_per_platform: Max results per platform per keyword
            
        Returns:
            Dictionary of platform -> posts
        """
        platforms = platforms or ["twitter", "youtube", "news"]
        results = {}
        
        for platform in platforms:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Scraping {platform.upper()}")
            self.logger.info(f"{'='*50}")
            
            try:
                if platform == "instagram":
                    with InstagramScraper(
                        headless=self.headless,
                        use_session=self.use_instagram_session
                    ) as scraper:
                        results[platform] = scraper.scrape(keywords, max_per_platform)
                
                elif platform == "twitter":
                    with TwitterScraper(headless=self.headless) as scraper:
                        results[platform] = scraper.scrape(keywords, max_per_platform)
                
                elif platform == "facebook":
                    with FacebookScraper(headless=self.headless) as scraper:
                        results[platform] = scraper.scrape(max_results=max_per_platform)
                
                elif platform == "youtube":
                    with YouTubeScraper(headless=self.headless) as scraper:
                        results[platform] = scraper.scrape(keywords, max_per_platform)
                
                elif platform == "news":
                    with NewsScraper(headless=self.headless) as scraper:
                        results[platform] = scraper.scrape(keywords, max_per_platform)
                
                self.logger.info(f"✅ {platform}: {len(results.get(platform, []))} posts")
                
            except Exception as e:
                self.logger.error(f"❌ {platform} failed: {e}")
                results[platform] = []
        
        return results


# Import for Instagram reference
from scrapers.instagram_scraper import InstagramScraper
