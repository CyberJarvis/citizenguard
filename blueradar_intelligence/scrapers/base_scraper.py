"""
BlueRadar - Base Scraper Class
Complete abstract base class for all platform scrapers
"""

import time
import json
import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    StaleElementReferenceException, WebDriverException
)
from bs4 import BeautifulSoup

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

from utils.logging_config import setup_logging
from config import scraper_config, IMAGES_DIR, HazardType, SeverityLevel
from scrapers.anti_detection import AntiDetection
from scrapers.session_manager import session_manager

logger = setup_logging("base_scraper")


class RateLimitError(Exception):
    """Raised when rate limit is detected"""
    pass


class LoginRequiredError(Exception):
    """Raised when login wall is detected"""
    pass


class ScraperError(Exception):
    """General scraper error"""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for all social media scrapers.
    
    Provides:
    - WebDriver management with stealth settings
    - Cookie-based authentication with rotation
    - Anti-detection measures
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - Data extraction helpers
    - Rate limit detection and handling
    """
    
    PLATFORM = "base"
    BASE_URL = ""
    
    def __init__(
        self,
        headless: bool = True,
        use_session: bool = False,
        max_retries: int = 3,
        timeout: int = 45
    ):
        self.headless = headless
        self.use_session = use_session
        self.max_retries = max_retries
        self.timeout = timeout
        
        self.driver: Optional[webdriver.Chrome] = None
        self.anti_detection = AntiDetection()
        self.current_account_id: Optional[str] = None
        self.logger = setup_logging(f"scraper.{self.PLATFORM}")
        
        # Statistics
        self.scraped_count = 0
        self.error_count = 0
        self.rate_limit_count = 0
        self.start_time = None
        
        # Content tracking (avoid duplicates)
        self.seen_urls = set()
        self.seen_hashes = set()
    
    # =========================================================================
    # DRIVER MANAGEMENT
    # =========================================================================
    
    def setup_driver(self):
        """Initialize Chrome WebDriver with stealth settings"""
        options = Options()
        
        # Headless mode
        if self.headless:
            options.add_argument("--headless=new")
        
        # Apply anti-detection settings
        options = self.anti_detection.configure_stealth_options(options)
        
        # Additional stability options
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--lang=en-US,en")
        
        # Memory optimization
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        try:
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise ScraperError(f"WebDriver initialization failed: {e}")
        
        # Configure timeouts
        self.driver.set_page_load_timeout(self.timeout)
        self.driver.implicitly_wait(10)
        
        # Apply fingerprint scripts
        self.anti_detection.set_driver(self.driver)
        
        self.start_time = datetime.now()
        self.logger.info(f"WebDriver initialized for {self.PLATFORM}")
    
    def close(self):
        """Clean up WebDriver and log statistics"""
        if self.driver:
            try:
                # Log session statistics
                duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
                self.logger.info(
                    f"Session ended - Scraped: {self.scraped_count}, "
                    f"Errors: {self.error_count}, "
                    f"Rate limits: {self.rate_limit_count}, "
                    f"Duration: {duration:.0f}s"
                )
                
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
    
    # =========================================================================
    # SESSION/COOKIE MANAGEMENT
    # =========================================================================
    
    def apply_session_cookie(self) -> bool:
        """Apply session cookie for authenticated access"""
        if not self.use_session:
            return False
        
        cookie_data = session_manager.get_session_cookie(self.PLATFORM)
        if not cookie_data:
            self.logger.warning(f"No session available for {self.PLATFORM}")
            return False
        
        try:
            # First visit the site to establish domain
            self.driver.get(self.BASE_URL or f"https://www.{self.PLATFORM}.com/")
            self.anti_detection.random_delay(2, 4)
            
            # Clear existing cookies
            self.driver.delete_all_cookies()
            
            # Add the session cookie
            self.driver.add_cookie(cookie_data["cookie"])
            self.current_account_id = cookie_data["account_id"]
            
            # Refresh to apply cookie
            self.driver.refresh()
            self.anti_detection.random_delay(2, 4)
            
            # Apply stealth scripts after navigation
            self.anti_detection.apply_fingerprint()
            
            self.logger.info(f"Applied session cookie: {self.current_account_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply session cookie: {e}")
            return False
    
    def rotate_session(self, reason: str = "") -> bool:
        """Rotate to a new session"""
        if not self.use_session or not self.current_account_id:
            return False
        
        new_session = session_manager.rotate_session(
            self.PLATFORM,
            self.current_account_id,
            reason
        )
        
        if new_session:
            self.current_account_id = new_session.id
            return self.apply_session_cookie()
        
        return False
    
    def record_request(self, success: bool = True, rate_limited: bool = False):
        """Record request for session management"""
        self.anti_detection.increment_request()
        
        if self.current_account_id:
            session_manager.record_request(
                self.PLATFORM,
                self.current_account_id,
                success,
                rate_limited
            )
        
        if rate_limited:
            self.rate_limit_count += 1
        elif not success:
            self.error_count += 1
        
        # Check if break needed
        if self.anti_detection.should_take_break():
            self.anti_detection.take_break(2, 4)
            
            # Rotate session after break
            if self.use_session:
                self.rotate_session("scheduled_break")
    
    # =========================================================================
    # PAGE NAVIGATION & INTERACTION
    # =========================================================================
    
    def get_page_safe(self, url: str, retry_count: int = 0) -> bool:
        """
        Safely navigate to URL with error handling and retries.
        """
        try:
            self.driver.get(url)
            self.anti_detection.random_delay(1, 3)
            
            # Check for common issues
            if self._detect_rate_limit():
                raise RateLimitError("Rate limit detected")
            
            if self._detect_login_required():
                raise LoginRequiredError("Login required")
            
            self.record_request(True)
            return True
            
        except RateLimitError:
            self.logger.warning(f"Rate limit hit on {url}")
            self.record_request(False, rate_limited=True)
            
            if retry_count < self.max_retries:
                if self.use_session:
                    self.rotate_session("rate_limit")
                self.anti_detection.random_delay(30, 60)
                return self.get_page_safe(url, retry_count + 1)
            return False
        
        except LoginRequiredError:
            self.logger.warning(f"Login required for {url}")
            
            if self.use_session and retry_count < 2:
                if self.rotate_session("login_required"):
                    return self.get_page_safe(url, retry_count + 1)
            return False
        
        except TimeoutException:
            self.logger.error(f"Timeout loading: {url}")
            self.record_request(False)
            
            if retry_count < self.max_retries:
                return self.get_page_safe(url, retry_count + 1)
            return False
        
        except WebDriverException as e:
            self.logger.error(f"WebDriver error loading {url}: {e}")
            self.record_request(False)
            return False
        
        except Exception as e:
            self.logger.error(f"Error loading {url}: {e}")
            self.record_request(False)
            return False
    
    def _detect_rate_limit(self) -> bool:
        """Detect if rate limited"""
        try:
            source = self.driver.page_source.lower()
            indicators = [
                "rate limit", "too many requests", "slow down",
                "temporarily blocked", "try again later",
                "unusual traffic", "automated behavior"
            ]
            return any(ind in source for ind in indicators)
        except:
            return False
    
    def _detect_login_required(self) -> bool:
        """Detect login wall"""
        try:
            source = self.driver.page_source.lower()
            indicators = [
                "log in to", "sign up to see", "create an account",
                "login to continue", "you must be logged in",
                "please log in", "sign in to"
            ]
            return any(ind in source for ind in indicators)
        except:
            return False
    
    def wait_for_element(
        self,
        by: By,
        selector: str,
        timeout: int = 10,
        condition: str = "presence"
    ) -> Optional[Any]:
        """Wait for element with configurable condition"""
        try:
            if condition == "presence":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
            elif condition == "visible":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, selector))
                )
            elif condition == "clickable":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, selector))
                )
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
            return element
        except TimeoutException:
            self.logger.debug(f"Timeout waiting for: {selector}")
            return None
    
    def safe_find_element(
        self,
        by: By,
        selector: str,
        parent=None,
        retry: bool = True
    ) -> Optional[Any]:
        """Safely find single element with optional retry"""
        try:
            root = parent or self.driver
            return root.find_element(by, selector)
        except (NoSuchElementException, StaleElementReferenceException):
            if retry:
                time.sleep(0.5)
                try:
                    root = parent or self.driver
                    return root.find_element(by, selector)
                except:
                    pass
            return None
    
    def safe_find_elements(
        self,
        by: By,
        selector: str,
        parent=None
    ) -> List:
        """Safely find multiple elements"""
        try:
            root = parent or self.driver
            return root.find_elements(by, selector)
        except (NoSuchElementException, StaleElementReferenceException):
            return []
    
    def safe_click(self, element, use_js: bool = False) -> bool:
        """Safely click an element"""
        try:
            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
            else:
                self.anti_detection.move_mouse_naturally(element, click=True)
            return True
        except Exception as e:
            self.logger.debug(f"Click failed: {e}")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def get_page_soup(self) -> BeautifulSoup:
        """Get BeautifulSoup object of current page"""
        return BeautifulSoup(self.driver.page_source, "html.parser")
    
    def scroll_page(
        self,
        count: int = None,
        pause_range: Tuple[float, float] = None
    ):
        """Scroll page with anti-detection"""
        count = count or scraper_config.scroll_count
        pause_range = pause_range or (
            scraper_config.scroll_pause_min,
            scraper_config.scroll_pause_max
        )
        self.anti_detection.human_scroll(count, pause_range)
    
    # =========================================================================
    # DATA EXTRACTION HELPERS
    # =========================================================================
    
    def extract_json_from_page(
        self,
        patterns: List[str] = None
    ) -> Optional[Dict]:
        """
        Extract JSON data embedded in page.
        Many platforms embed data in <script> tags.
        """
        soup = self.get_page_soup()
        
        # Try application/ld+json first
        json_scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if patterns:
                    if any(p in str(data) for p in patterns):
                        return data
                else:
                    return data
            except:
                continue
        
        # Try inline scripts with patterns
        patterns = patterns or ["window._sharedData", "window.__PRELOADED_STATE__"]
        
        for pattern in patterns:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and pattern in script.string:
                    try:
                        text = script.string
                        # Extract JSON from script
                        match = re.search(rf'{re.escape(pattern)}\s*=\s*({{\s*.*?\s*}});?', text, re.DOTALL)
                        if match:
                            return json.loads(match.group(1))
                    except:
                        continue
        
        return None
    
    def extract_text_safe(self, element, default: str = "") -> str:
        """Safely extract text from element"""
        if element is None:
            return default
        try:
            if hasattr(element, 'get_text'):
                return element.get_text(strip=True)
            elif hasattr(element, 'text'):
                return element.text.strip()
            return str(element).strip()
        except:
            return default
    
    def extract_attribute_safe(
        self,
        element,
        attribute: str,
        default: str = ""
    ) -> str:
        """Safely extract attribute from element"""
        if element is None:
            return default
        try:
            if hasattr(element, 'get'):
                return element.get(attribute, default)
            elif hasattr(element, 'get_attribute'):
                return element.get_attribute(attribute) or default
            return default
        except:
            return default
    
    def extract_urls_from_srcset(self, srcset: str) -> List[str]:
        """Extract URLs from srcset attribute"""
        urls = []
        if not srcset:
            return urls
        
        parts = srcset.split(',')
        for part in parts:
            part = part.strip()
            if part:
                url = part.split()[0]
                if url.startswith('http'):
                    urls.append(url)
        
        return urls
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        return re.findall(r'#(\w+)', text)
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text"""
        return re.findall(r'@(\w+)', text)
    
    # =========================================================================
    # POST CREATION
    # =========================================================================
    
    def create_post_entry(self, **kwargs) -> Dict[str, Any]:
        """Create standardized post entry"""
        post_id = kwargs.get("post_id") or self._generate_id()
        
        return {
            "id": post_id,
            "platform": self.PLATFORM,
            "scraped_at": datetime.now().isoformat(),
            "url": kwargs.get("url", ""),
            
            "author": {
                "username": kwargs.get("username", ""),
                "display_name": kwargs.get("display_name", ""),
                "profile_url": kwargs.get("profile_url", ""),
                "followers": kwargs.get("followers"),
                "following": kwargs.get("following"),
                "is_verified": kwargs.get("is_verified", False),
                "is_official": kwargs.get("is_official", False),
                "account_type": kwargs.get("account_type", "personal")
            },
            
            "content": {
                "text": kwargs.get("text", ""),
                "text_html": kwargs.get("text_html", ""),
                "hashtags": kwargs.get("hashtags", []),
                "mentions": kwargs.get("mentions", []),
                "language": kwargs.get("language", ""),
                "urls": kwargs.get("content_urls", [])
            },
            
            "media": {
                "type": kwargs.get("media_type", "none"),
                "urls": kwargs.get("image_urls", []),
                "local_paths": [],
                "thumbnails": kwargs.get("thumbnails", []),
                "count": len(kwargs.get("image_urls", [])),
                "video_url": kwargs.get("video_url"),
                "video_duration": kwargs.get("video_duration")
            },
            
            "engagement": {
                "likes": kwargs.get("likes", 0),
                "comments": kwargs.get("comments", 0),
                "shares": kwargs.get("shares", 0),
                "retweets": kwargs.get("retweets", 0),
                "views": kwargs.get("views", 0),
                "saves": kwargs.get("saves", 0),
                "reactions": kwargs.get("reactions", {})
            },
            
            "temporal": {
                "posted_at": kwargs.get("posted_at", ""),
                "posted_timestamp": kwargs.get("posted_timestamp"),
                "scraped_at": datetime.now().isoformat(),
                "age_hours": self._calculate_age_hours(kwargs.get("posted_at"))
            },
            
            "location": {
                "tagged": kwargs.get("location", ""),
                "coordinates": kwargs.get("coordinates"),
                "detected": None,
                "region": None
            },
            
            "context": {
                "search_hashtag": kwargs.get("search_hashtag", ""),
                "search_keyword": kwargs.get("search_keyword", ""),
                "search_page": kwargs.get("search_page"),
                "is_reply": kwargs.get("is_reply", False),
                "reply_to": kwargs.get("reply_to"),
                "is_repost": kwargs.get("is_repost", False),
                "original_url": kwargs.get("original_url")
            },
            
            "raw_data": kwargs.get("raw_data", {}),
            
            # Placeholder for NLP/Vision analysis
            "nlp": {},
            "vision": {}
        }
    
    def _generate_id(self) -> str:
        """Generate unique ID for post"""
        unique = f"{self.PLATFORM}_{datetime.now().isoformat()}_{self.scraped_count}_{random.random()}"
        return hashlib.md5(unique.encode()).hexdigest()[:16]
    
    def _calculate_age_hours(self, posted_at: str) -> Optional[float]:
        """Calculate post age in hours"""
        if not posted_at:
            return None
        
        try:
            # Try ISO format
            post_time = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
            age = datetime.now(post_time.tzinfo) - post_time
            return age.total_seconds() / 3600
        except:
            pass
        
        # Try parsing relative time
        try:
            posted_lower = posted_at.lower()
            
            if 'just now' in posted_lower or 'now' in posted_lower:
                return 0.1
            
            match = re.search(r'(\d+)\s*(minute|min|m)', posted_lower)
            if match:
                return int(match.group(1)) / 60
            
            match = re.search(r'(\d+)\s*(hour|hr|h)', posted_lower)
            if match:
                return int(match.group(1))
            
            match = re.search(r'(\d+)\s*(day|d)', posted_lower)
            if match:
                return int(match.group(1)) * 24
            
            match = re.search(r'(\d+)\s*(week|w)', posted_lower)
            if match:
                return int(match.group(1)) * 24 * 7
        except:
            pass
        
        return None
    
    def is_duplicate(self, url: str = None, content_hash: str = None) -> bool:
        """Check if post is duplicate"""
        if url and url in self.seen_urls:
            return True
        
        if content_hash and content_hash in self.seen_hashes:
            return True
        
        # Add to seen
        if url:
            self.seen_urls.add(url)
        if content_hash:
            self.seen_hashes.add(content_hash)
        
        return False
    
    def generate_content_hash(self, text: str, url: str = "") -> str:
        """Generate hash of content for deduplication"""
        content = f"{text[:100]}_{url}"
        return hashlib.md5(content.encode()).hexdigest()
    
    # =========================================================================
    # ABSTRACT METHODS
    # =========================================================================
    
    @abstractmethod
    def scrape(self, keywords: List[str], max_results: int = 20) -> List[Dict]:
        """
        Main scraping method. Must be implemented by subclasses.
        
        Args:
            keywords: List of keywords/hashtags to search
            max_results: Maximum results per keyword
            
        Returns:
            List of post dictionaries
        """
        pass
    
    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================
    
    def __enter__(self):
        self.setup_driver()
        if self.use_session:
            self.apply_session_cookie()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# Import random for _generate_id
import random
