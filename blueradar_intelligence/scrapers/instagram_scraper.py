"""
BlueRadar - Complete Instagram Scraper
Production-ready scraper with session rotation and comprehensive data extraction
"""

import re
import json
import time
from typing import List, Dict, Optional, Set
from datetime import datetime
from urllib.parse import quote_plus, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, LoginRequiredError, RateLimitError
from scrapers.session_manager import session_manager
from utils.logging_config import setup_logging

logger = setup_logging("instagram_scraper")


class InstagramScraper(BaseScraper):
    """
    Complete Instagram scraper with:
    - Session cookie rotation
    - Multiple extraction methods (JSON, GraphQL, DOM)
    - Hashtag, profile, and post scraping
    - Full image extraction including carousels
    - Comment extraction
    - Engagement metrics
    """
    
    PLATFORM = "instagram"
    BASE_URL = "https://www.instagram.com"
    
    # Login indicators
    LOGIN_INDICATORS = [
        "log in to instagram",
        "sign up to see photos",
        "create an account",
        "login to continue",
        "to see this",
        "this page isn't available"
    ]
    
    # Rate limit indicators
    RATE_LIMIT_INDICATORS = [
        "please wait a few minutes",
        "try again later",
        "temporarily blocked",
        "action blocked"
    ]
    
    def __init__(
        self,
        headless: bool = True,
        use_session: bool = True,
        max_retries: int = 3
    ):
        super().__init__(
            headless=headless,
            use_session=use_session,
            max_retries=max_retries
        )
        
        # Instagram-specific tracking
        self.scraped_post_ids: Set[str] = set()
        
    def scrape(
        self,
        hashtags: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """
        Scrape Instagram hashtags for posts.
        
        Args:
            hashtags: List of hashtags (with or without #)
            max_results: Max posts per hashtag
            
        Returns:
            List of post dictionaries
        """
        self.setup_driver()
        
        if self.use_session:
            if not self.apply_session_cookie():
                self.logger.warning("No session available, attempting public access")
        
        all_posts = []
        
        for hashtag in hashtags:
            hashtag = hashtag.lstrip("#").strip()
            if not hashtag:
                continue
                
            self.logger.info(f"🔍 Scraping #{hashtag}")
            
            try:
                posts = self._scrape_hashtag(hashtag, max_results)
                all_posts.extend(posts)
                self.logger.info(f"✅ Found {len(posts)} posts for #{hashtag}")
            except LoginRequiredError:
                self.logger.warning(f"Login required for #{hashtag}")
                if self.use_session:
                    if self.rotate_session("login_required"):
                        posts = self._scrape_hashtag(hashtag, max_results)
                        all_posts.extend(posts)
            except RateLimitError:
                self.logger.warning(f"Rate limited on #{hashtag}")
                if self.use_session:
                    self.rotate_session("rate_limit")
                self.anti_detection.take_break(2, 4)
            except Exception as e:
                self.logger.error(f"Error scraping #{hashtag}: {e}")
            
            # Delay between hashtags
            self.anti_detection.random_delay(4, 8)
        
        self.close()
        return all_posts
    
    def _scrape_hashtag(self, hashtag: str, max_results: int) -> List[Dict]:
        """Scrape a single hashtag"""
        url = f"{self.BASE_URL}/explore/tags/{hashtag}/"
        
        if not self.get_page_safe(url):
            return []
        
        # Check for issues
        if self._is_login_required():
            raise LoginRequiredError(f"Login required for #{hashtag}")
        
        if self._is_rate_limited():
            raise RateLimitError(f"Rate limited on #{hashtag}")
        
        self.anti_detection.random_delay(2, 4)
        
        # Scroll to load more posts
        self.scroll_page(count=5)
        
        # Get post links
        post_links = self._get_post_links(max_results)
        self.logger.info(f"Found {len(post_links)} post links")
        
        # Scrape each post
        posts = []
        for i, link in enumerate(post_links):
            if link in self.seen_urls:
                continue
                
            try:
                post_data = self._scrape_post(link, hashtag)
                if post_data:
                    posts.append(post_data)
                    self.scraped_count += 1
                    self.seen_urls.add(link)
                    
                    # Progress log
                    if (i + 1) % 10 == 0:
                        self.logger.info(f"Progress: {i + 1}/{len(post_links)} posts")
                        
            except Exception as e:
                self.logger.debug(f"Error scraping post: {e}")
                self.error_count += 1
            
            # Delay between posts
            self.anti_detection.random_delay(2, 5)
            
            # Check for break
            if self.anti_detection.should_take_break():
                self.anti_detection.take_break(1, 3)
        
        return posts
    
    def _is_login_required(self) -> bool:
        """Check if login wall is shown"""
        try:
            source = self.driver.page_source.lower()
            return any(ind in source for ind in self.LOGIN_INDICATORS)
        except:
            return False
    
    def _is_rate_limited(self) -> bool:
        """Check if rate limited"""
        try:
            source = self.driver.page_source.lower()
            return any(ind in source for ind in self.RATE_LIMIT_INDICATORS)
        except:
            return False
    
    def _get_post_links(self, max_count: int) -> List[str]:
        """Extract post links from hashtag page"""
        soup = self.get_page_soup()
        links = []
        seen = set()
        
        # Find all post links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/p/" in href or "/reel/" in href:
                # Normalize URL
                if href.startswith("/"):
                    full_url = f"{self.BASE_URL}{href}"
                else:
                    full_url = href
                
                # Remove query params
                full_url = full_url.split("?")[0]
                
                if full_url not in seen and full_url not in self.seen_urls:
                    seen.add(full_url)
                    links.append(full_url)
                    
                    if len(links) >= max_count:
                        break
        
        return links
    
    def _scrape_post(self, url: str, search_context: str) -> Optional[Dict]:
        """Scrape a single Instagram post"""
        if not self.get_page_safe(url):
            return None
        
        self.anti_detection.random_delay(1, 3)
        
        # Try multiple extraction methods
        post_data = None
        
        # Method 1: JSON extraction (most reliable)
        post_data = self._extract_from_json(url, search_context)
        
        # Method 2: GraphQL data
        if not post_data:
            post_data = self._extract_from_graphql(url, search_context)
        
        # Method 3: DOM parsing (fallback)
        if not post_data:
            post_data = self._extract_from_dom(url, search_context)
        
        return post_data
    
    def _extract_from_json(self, url: str, search_context: str) -> Optional[Dict]:
        """Extract post data from embedded JSON (ld+json)"""
        soup = self.get_page_soup()
        
        # Find JSON-LD scripts
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)
                
                # Check if this is post data
                if data.get("@type") in ["ImageObject", "VideoObject", "MediaObject"]:
                    return self._parse_ld_json(data, url, search_context)
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                self.logger.debug(f"JSON parse error: {e}")
        
        return None
    
    def _parse_ld_json(self, data: Dict, url: str, search_context: str) -> Dict:
        """Parse ld+json format"""
        # Extract post ID from URL
        post_id_match = re.search(r'/p/([A-Za-z0-9_-]+)', url)
        post_id = post_id_match.group(1) if post_id_match else ""
        
        # Get author info
        author = data.get("author", {})
        author_id = author.get("identifier", {})
        
        # Get caption
        caption = data.get("caption", "")
        if isinstance(caption, dict):
            caption = caption.get("text", "") or caption.get("@value", "")
        
        # Get image URLs
        image_urls = []
        
        # Main content URL
        if data.get("contentUrl"):
            image_urls.append(data["contentUrl"])
        
        # Thumbnail
        if data.get("thumbnailUrl"):
            thumb = data["thumbnailUrl"]
            if isinstance(thumb, list):
                image_urls.extend(thumb)
            else:
                image_urls.append(thumb)
        
        # Remove duplicates while preserving order
        image_urls = list(dict.fromkeys(image_urls))
        
        # Extract hashtags and mentions
        hashtags = self.extract_hashtags(caption)
        mentions = self.extract_mentions(caption)
        
        # Determine media type
        media_type = "image"
        if data.get("@type") == "VideoObject":
            media_type = "video"
        elif len(image_urls) > 1:
            media_type = "carousel"
        
        return self.create_post_entry(
            post_id=post_id,
            url=url,
            username=author_id.get("value", "") if isinstance(author_id, dict) else "",
            display_name=author.get("name", ""),
            profile_url=author.get("url", ""),
            text=caption,
            hashtags=hashtags,
            mentions=mentions,
            image_urls=image_urls,
            media_type=media_type,
            posted_at=data.get("dateCreated", data.get("uploadDate", "")),
            search_hashtag=search_context,
            raw_data=data
        )
    
    def _extract_from_graphql(self, url: str, search_context: str) -> Optional[Dict]:
        """Extract from window._sharedData or similar"""
        soup = self.get_page_soup()
        
        # Look for shared data
        for script in soup.find_all("script"):
            if not script.string:
                continue
                
            text = script.string
            
            # Try window._sharedData
            if "window._sharedData" in text:
                try:
                    match = re.search(r'window\._sharedData\s*=\s*({.*?});', text, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        return self._parse_shared_data(data, url, search_context)
                except:
                    pass
            
            # Try window.__additionalDataLoaded
            if "__additionalDataLoaded" in text:
                try:
                    match = re.search(r'__additionalDataLoaded\([^,]+,\s*({.*?})\)', text, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        return self._parse_additional_data(data, url, search_context)
                except:
                    pass
        
        return None
    
    def _parse_shared_data(self, data: Dict, url: str, search_context: str) -> Optional[Dict]:
        """Parse window._sharedData format"""
        try:
            # Navigate to post data
            post_page = data.get("entry_data", {}).get("PostPage", [{}])[0]
            media = post_page.get("graphql", {}).get("shortcode_media", {})
            
            if not media:
                return None
            
            return self._parse_media_object(media, url, search_context)
            
        except Exception as e:
            self.logger.debug(f"Error parsing shared data: {e}")
            return None
    
    def _parse_additional_data(self, data: Dict, url: str, search_context: str) -> Optional[Dict]:
        """Parse __additionalDataLoaded format"""
        try:
            media = data.get("graphql", {}).get("shortcode_media", {})
            
            if not media:
                # Try alternate path
                media = data.get("items", [{}])[0] if data.get("items") else {}
            
            if media:
                return self._parse_media_object(media, url, search_context)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error parsing additional data: {e}")
            return None
    
    def _parse_media_object(self, media: Dict, url: str, search_context: str) -> Dict:
        """Parse Instagram media object (common format)"""
        owner = media.get("owner", {})
        
        # Get caption
        caption_edges = media.get("edge_media_to_caption", {}).get("edges", [])
        caption = caption_edges[0]["node"]["text"] if caption_edges else ""
        
        # Get images
        image_urls = []
        
        # Main image
        if media.get("display_url"):
            image_urls.append(media["display_url"])
        
        # Carousel images
        carousel = media.get("edge_sidecar_to_children", {}).get("edges", [])
        for edge in carousel:
            node = edge.get("node", {})
            if node.get("display_url"):
                image_urls.append(node["display_url"])
        
        # Thumbnails
        thumbnails = []
        resources = media.get("display_resources", [])
        for res in resources:
            if res.get("src"):
                thumbnails.append(res["src"])
        
        # Determine media type
        type_name = media.get("__typename", "").lower()
        if "video" in type_name:
            media_type = "video"
        elif "sidecar" in type_name or len(carousel) > 0:
            media_type = "carousel"
        else:
            media_type = "image"
        
        # Extract hashtags and mentions
        hashtags = self.extract_hashtags(caption)
        mentions = self.extract_mentions(caption)
        
        # Get engagement
        likes = media.get("edge_media_preview_like", {}).get("count", 0)
        comments = media.get("edge_media_to_comment", {}).get("count", 0)
        views = media.get("video_view_count", 0)
        
        # Get timestamp
        timestamp = media.get("taken_at_timestamp", 0)
        posted_at = datetime.fromtimestamp(timestamp).isoformat() if timestamp else ""
        
        # Get location
        location_data = media.get("location", {}) or {}
        location = location_data.get("name", "")
        
        return self.create_post_entry(
            post_id=media.get("shortcode", ""),
            url=url,
            username=owner.get("username", ""),
            display_name=owner.get("full_name", ""),
            profile_url=f"{self.BASE_URL}/{owner.get('username', '')}/",
            followers=owner.get("edge_followed_by", {}).get("count"),
            is_verified=owner.get("is_verified", False),
            text=caption,
            hashtags=hashtags,
            mentions=mentions,
            image_urls=image_urls,
            thumbnails=thumbnails,
            media_type=media_type,
            video_url=media.get("video_url"),
            video_duration=media.get("video_duration"),
            likes=likes,
            comments=comments,
            views=views,
            posted_at=posted_at,
            posted_timestamp=timestamp,
            location=location,
            search_hashtag=search_context,
            raw_data=media
        )
    
    def _extract_from_dom(self, url: str, search_context: str) -> Optional[Dict]:
        """Fallback: Extract from DOM elements"""
        soup = self.get_page_soup()
        
        # Post ID from URL
        post_id_match = re.search(r'/p/([A-Za-z0-9_-]+)', url)
        post_id = post_id_match.group(1) if post_id_match else ""
        
        # Username - try multiple selectors
        username = ""
        username_selectors = [
            "header a[href^='/']",
            "a[role='link'][tabindex='0']",
            "span a[href^='/']"
        ]
        
        for selector in username_selectors:
            elem = soup.select_one(selector)
            if elem:
                href = elem.get("href", "")
                if href.startswith("/") and "/p/" not in href and "/explore/" not in href:
                    username = href.strip("/").split("/")[0]
                    if username and not username.startswith("explore"):
                        break
        
        # Caption
        caption = ""
        
        # Method 1: Meta description
        meta = soup.find("meta", {"property": "og:description"})
        if meta:
            caption = meta.get("content", "")
        
        # Method 2: Find in article
        if not caption or len(caption) < 20:
            article = soup.find("article")
            if article:
                # Look for caption spans
                for span in article.find_all("span"):
                    text = span.get_text(strip=True)
                    if len(text) > 50:
                        caption = text
                        break
        
        # Images
        image_urls = []
        
        # Method 1: og:image meta
        og_image = soup.find("meta", {"property": "og:image"})
        if og_image and og_image.get("content"):
            image_urls.append(og_image["content"])
        
        # Method 2: img tags with srcset
        for img in soup.find_all("img", {"srcset": True}):
            srcset = img.get("srcset", "")
            urls = self.extract_urls_from_srcset(srcset)
            if urls:
                # Get largest (last one)
                image_urls.append(urls[-1])
        
        # Method 3: Direct img src
        for img in soup.find_all("img", {"src": True}):
            src = img.get("src", "")
            # Filter out small images
            if "instagram" in src and all(skip not in src for skip in ["150x150", "s320x320", "44x44"]):
                if src not in image_urls:
                    image_urls.append(src)
        
        # Timestamp
        timestamp = ""
        time_elem = soup.find("time", {"datetime": True})
        if time_elem:
            timestamp = time_elem.get("datetime", "")
        
        # Extract hashtags and mentions
        hashtags = self.extract_hashtags(caption)
        mentions = self.extract_mentions(caption)
        
        if not caption and not image_urls:
            return None
        
        return self.create_post_entry(
            post_id=post_id,
            url=url,
            username=username,
            profile_url=f"{self.BASE_URL}/{username}/" if username else "",
            text=caption,
            hashtags=hashtags,
            mentions=mentions,
            image_urls=image_urls[:10],  # Limit
            media_type="image" if image_urls else "none",
            posted_at=timestamp,
            search_hashtag=search_context
        )
    
    # =========================================================================
    # ADDITIONAL SCRAPING METHODS
    # =========================================================================
    
    def scrape_profile(self, username: str, max_posts: int = 20) -> List[Dict]:
        """Scrape posts from a user profile"""
        self.setup_driver()
        
        if self.use_session:
            self.apply_session_cookie()
        
        username = username.lstrip("@").strip()
        url = f"{self.BASE_URL}/{username}/"
        
        if not self.get_page_safe(url):
            self.close()
            return []
        
        if self._is_login_required():
            self.logger.warning("Login required for profile")
            self.close()
            return []
        
        self.scroll_page(count=4)
        
        post_links = self._get_post_links(max_posts)
        
        posts = []
        for link in post_links:
            try:
                post_data = self._scrape_post(link, f"@{username}")
                if post_data:
                    posts.append(post_data)
            except Exception as e:
                self.logger.debug(f"Error: {e}")
            
            self.anti_detection.random_delay(2, 4)
        
        self.close()
        return posts
    
    def scrape_single_post(self, url: str) -> Optional[Dict]:
        """Scrape a single post by URL"""
        self.setup_driver()
        
        if self.use_session:
            self.apply_session_cookie()
        
        post_data = self._scrape_post(url, "direct")
        
        self.close()
        return post_data
    
    def scrape_posts_with_comments(
        self,
        hashtags: List[str],
        max_results: int = 20,
        max_comments: int = 10
    ) -> List[Dict]:
        """Scrape posts including top comments"""
        posts = self.scrape(hashtags, max_results)
        
        # Comments would be extracted during post scraping
        # This is a placeholder for enhanced comment extraction
        
        return posts
