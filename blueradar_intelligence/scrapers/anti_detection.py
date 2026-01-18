"""
BlueRadar - Advanced Anti-Detection Module
Comprehensive bot detection avoidance system
"""

import random
import time
import math
import json
from typing import Tuple, List, Optional, Dict
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys

from utils.logging_config import setup_logging
from config import USER_AGENTS

logger = setup_logging("anti_detection")


class BezierCurve:
    """Bezier curve for natural mouse movement"""
    
    @staticmethod
    def generate_points(
        start: Tuple[int, int],
        end: Tuple[int, int],
        num_points: int = 50
    ) -> List[Tuple[int, int]]:
        """Generate bezier curve points for mouse movement"""
        
        # Control points for natural curve
        control1 = (
            start[0] + random.randint(-50, 50),
            start[1] + random.randint(-50, 50)
        )
        control2 = (
            end[0] + random.randint(-50, 50),
            end[1] + random.randint(-50, 50)
        )
        
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Cubic bezier formula
            x = (
                (1 - t) ** 3 * start[0] +
                3 * (1 - t) ** 2 * t * control1[0] +
                3 * (1 - t) * t ** 2 * control2[0] +
                t ** 3 * end[0]
            )
            y = (
                (1 - t) ** 3 * start[1] +
                3 * (1 - t) ** 2 * t * control1[1] +
                3 * (1 - t) * t ** 2 * control2[1] +
                t ** 3 * end[1]
            )
            
            points.append((int(x), int(y)))
        
        return points


class HumanBehavior:
    """Simulates human-like behavior patterns"""
    
    @staticmethod
    def get_typing_delay() -> float:
        """Get human-like typing delay between characters"""
        # Human typing speed varies: 150-400ms per character
        base_delay = random.gauss(0.15, 0.05)
        
        # Occasionally pause longer (thinking)
        if random.random() < 0.1:
            base_delay += random.uniform(0.3, 0.8)
        
        return max(0.05, base_delay)
    
    @staticmethod
    def get_reading_time(text_length: int) -> float:
        """Estimate time to read content"""
        # Average reading speed: 200-250 words per minute
        words = text_length / 5  # Rough word estimate
        minutes = words / random.uniform(200, 250)
        return minutes * 60  # Convert to seconds
    
    @staticmethod
    def should_make_typo() -> bool:
        """Determine if a typo should be made"""
        return random.random() < 0.05  # 5% chance
    
    @staticmethod
    def get_scroll_behavior() -> Dict:
        """Get randomized scroll behavior parameters"""
        return {
            "distance": random.randint(300, 800),
            "duration": random.uniform(0.5, 1.5),
            "pause_after": random.uniform(0.5, 2.0),
            "scroll_up_chance": 0.15,
            "scroll_up_distance": random.randint(50, 200)
        }


class BrowserFingerprint:
    """Browser fingerprint randomization"""
    
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (1600, 900), (1280, 800), (1024, 768),
        (2560, 1440), (1920, 1200)
    ]
    
    TIMEZONES = [
        "Asia/Kolkata", "Asia/Mumbai", "Asia/Delhi",
        "America/New_York", "America/Los_Angeles",
        "Europe/London", "Europe/Paris"
    ]
    
    LANGUAGES = [
        ["en-US", "en"], ["en-IN", "en"], ["hi-IN", "hi", "en"],
        ["ta-IN", "ta", "en"], ["te-IN", "te", "en"]
    ]
    
    PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]
    
    @classmethod
    def generate(cls) -> Dict:
        """Generate random browser fingerprint"""
        resolution = random.choice(cls.SCREEN_RESOLUTIONS)
        
        return {
            "screen_width": resolution[0],
            "screen_height": resolution[1],
            "available_width": resolution[0],
            "available_height": resolution[1] - random.randint(40, 100),
            "color_depth": random.choice([24, 32]),
            "timezone": random.choice(cls.TIMEZONES),
            "languages": random.choice(cls.LANGUAGES),
            "platform": random.choice(cls.PLATFORMS),
            "hardware_concurrency": random.choice([2, 4, 8, 12, 16]),
            "device_memory": random.choice([2, 4, 8, 16]),
            "user_agent": random.choice(USER_AGENTS)
        }


class AntiDetection:
    """
    Comprehensive anti-detection system:
    - Human-like delays with natural distribution
    - Mouse movement with bezier curves
    - Scroll patterns with natural pauses
    - Browser fingerprint randomization
    - Request pattern obfuscation
    - Automatic break scheduling
    """
    
    def __init__(self, driver: WebDriver = None):
        self.driver = driver
        self.request_count = 0
        self.session_start = time.time()
        self.fingerprint = BrowserFingerprint.generate()
        
        # Tracking for pattern analysis
        self.request_history: List[datetime] = []
        self.scroll_history: List[float] = []
        self.delay_history: List[float] = []
        
        logger.debug("Anti-detection system initialized")
    
    def set_driver(self, driver: WebDriver):
        """Set the WebDriver instance"""
        self.driver = driver
        self.apply_fingerprint()
    
    def apply_fingerprint(self):
        """Apply fingerprint to browser"""
        if not self.driver:
            return
        
        scripts = [
            # Override navigator.webdriver
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Override plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {name: 'Chrome PDF Plugin'},
                        {name: 'Chrome PDF Viewer'},
                        {name: 'Native Client'}
                    ];
                }
            })
            """,
            
            # Override languages
            f"""
            Object.defineProperty(navigator, 'languages', {{
                get: () => {json.dumps(self.fingerprint['languages'])}
            }})
            """,
            
            # Override platform
            f"""
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{self.fingerprint['platform']}'
            }})
            """,
            
            # Override hardware concurrency
            f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {self.fingerprint['hardware_concurrency']}
            }})
            """,
            
            # Override device memory
            f"""
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {self.fingerprint['device_memory']}
            }})
            """,
            
            # Override permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,
            
            # Hide automation indicators
            """
            window.chrome = {runtime: {}};
            """,
            
            # Override toString for functions
            """
            const originalFunction = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === Function.prototype.toString) {
                    return 'function toString() { [native code] }';
                }
                return originalFunction.call(this);
            };
            """
        ]
        
        for script in scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.debug(f"Fingerprint script failed: {e}")
    
    def random_delay(
        self,
        min_sec: float = 2.0,
        max_sec: float = 6.0,
        distribution: str = "normal"
    ) -> float:
        """
        Generate human-like random delay.
        
        Args:
            min_sec: Minimum delay
            max_sec: Maximum delay
            distribution: 'normal', 'uniform', or 'exponential'
        """
        if distribution == "normal":
            mean = (min_sec + max_sec) / 2
            std = (max_sec - min_sec) / 4
            delay = random.gauss(mean, std)
        elif distribution == "exponential":
            delay = random.expovariate(1 / ((min_sec + max_sec) / 2))
        else:  # uniform
            delay = random.uniform(min_sec, max_sec)
        
        # Clamp to range
        delay = max(min_sec, min(max_sec, delay))
        
        # Occasionally add longer pauses (human distraction)
        if random.random() < 0.08:
            delay += random.uniform(2, 5)
            logger.debug("Added distraction pause")
        
        # Record for pattern analysis
        self.delay_history.append(delay)
        if len(self.delay_history) > 100:
            self.delay_history.pop(0)
        
        time.sleep(delay)
        return delay
    
    def human_scroll(
        self,
        scroll_count: int = 5,
        pause_range: Tuple[float, float] = (1.5, 3.5)
    ):
        """
        Simulate human-like scrolling behavior.
        """
        if not self.driver:
            return
        
        viewport_height = self.driver.execute_script("return window.innerHeight")
        page_height = self.driver.execute_script("return document.body.scrollHeight")
        current_pos = 0
        
        for i in range(scroll_count):
            behavior = HumanBehavior.get_scroll_behavior()
            
            # Calculate scroll distance (not always full viewport)
            scroll_amount = int(viewport_height * random.uniform(0.3, 0.9))
            
            # Smooth scroll
            self._smooth_scroll(scroll_amount, behavior["duration"])
            current_pos += scroll_amount
            
            # Record scroll
            self.scroll_history.append(scroll_amount)
            
            # Pause (reading/looking)
            time.sleep(random.uniform(*pause_range))
            
            # Occasionally scroll up (re-reading)
            if random.random() < behavior["scroll_up_chance"]:
                scroll_up = behavior["scroll_up_distance"]
                self._smooth_scroll(-scroll_up, 0.3)
                current_pos -= scroll_up
                time.sleep(random.uniform(0.5, 1.5))
            
            # Check if reached bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            current_scroll = self.driver.execute_script("return window.pageYOffset")
            
            if current_scroll + viewport_height >= new_height - 100:
                logger.debug("Reached page bottom")
                break
    
    def _smooth_scroll(self, distance: int, duration: float = 1.0):
        """Perform smooth scroll animation"""
        if not self.driver:
            return
        
        steps = max(10, int(duration * 30))  # ~30 FPS
        step_distance = distance / steps
        step_delay = duration / steps
        
        for _ in range(steps):
            self.driver.execute_script(f"window.scrollBy(0, {step_distance})")
            time.sleep(step_delay + random.uniform(-0.01, 0.01))
    
    def move_mouse_naturally(self, element, click: bool = False):
        """
        Move mouse to element using bezier curves.
        """
        if not self.driver:
            return
        
        try:
            actions = ActionChains(self.driver)
            
            # Get current position (approximate)
            current_x = random.randint(100, 500)
            current_y = random.randint(100, 500)
            
            # Get element position
            location = element.location
            size = element.size
            
            # Random point within element
            target_x = location['x'] + random.randint(5, max(6, size['width'] - 5))
            target_y = location['y'] + random.randint(5, max(6, size['height'] - 5))
            
            # Generate bezier path
            points = BezierCurve.generate_points(
                (current_x, current_y),
                (target_x, target_y),
                num_points=random.randint(20, 40)
            )
            
            # Move through points
            for point in points:
                actions.move_by_offset(
                    point[0] - current_x,
                    point[1] - current_y
                )
                current_x, current_y = point
                time.sleep(random.uniform(0.005, 0.015))
            
            # Small pause before click
            if click:
                time.sleep(random.uniform(0.1, 0.3))
                actions.click()
            
            actions.perform()
            
        except Exception as e:
            logger.debug(f"Mouse movement failed: {e}")
            # Fallback to simple move
            try:
                ActionChains(self.driver).move_to_element(element).perform()
                if click:
                    element.click()
            except:
                pass
    
    def human_type(self, element, text: str):
        """Type text with human-like speed and occasional typos"""
        if not self.driver:
            return
        
        element.clear()
        
        for char in text:
            # Occasionally make and correct typo
            if HumanBehavior.should_make_typo():
                wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                element.send_keys(wrong_char)
                time.sleep(HumanBehavior.get_typing_delay() * 2)
                element.send_keys(Keys.BACKSPACE)
                time.sleep(HumanBehavior.get_typing_delay())
            
            element.send_keys(char)
            time.sleep(HumanBehavior.get_typing_delay())
    
    def random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(USER_AGENTS)
    
    def should_take_break(self) -> bool:
        """Determine if scraper should take a longer break"""
        elapsed = time.time() - self.session_start
        
        # Take break every 15-25 minutes
        if elapsed > random.randint(900, 1500):
            return True
        
        # Or every 30-50 requests
        if self.request_count > random.randint(30, 50):
            return True
        
        # Check request rate
        if len(self.request_history) >= 5:
            recent = self.request_history[-5:]
            if len(recent) >= 5:
                time_span = (recent[-1] - recent[0]).total_seconds()
                if time_span < 30:  # 5 requests in < 30 seconds
                    logger.warning("Request rate too high, forcing break")
                    return True
        
        return False
    
    def take_break(self, min_minutes: float = 2, max_minutes: float = 5):
        """Take a longer break to avoid detection"""
        break_time = random.uniform(min_minutes * 60, max_minutes * 60)
        logger.info(f"Taking break for {break_time/60:.1f} minutes")
        
        # Occasionally move mouse during break
        if self.driver and random.random() < 0.3:
            try:
                for _ in range(random.randint(1, 3)):
                    time.sleep(random.uniform(10, 30))
                    self.driver.execute_script(
                        f"window.scrollBy(0, {random.randint(-100, 100)})"
                    )
            except:
                pass
        
        time.sleep(break_time)
        
        # Reset counters
        self.request_count = 0
        self.session_start = time.time()
        self.request_history.clear()
    
    def increment_request(self):
        """Track request count"""
        self.request_count += 1
        self.request_history.append(datetime.now())
        
        # Keep only last 50 requests
        if len(self.request_history) > 50:
            self.request_history.pop(0)
    
    def get_random_viewport(self) -> Tuple[int, int]:
        """Get random viewport size"""
        return random.choice(BrowserFingerprint.SCREEN_RESOLUTIONS)
    
    def configure_stealth_options(self, options):
        """Configure Chrome options for stealth"""
        
        # Basic stealth settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        
        # Random viewport
        width, height = self.fingerprint["screen_width"], self.fingerprint["screen_height"]
        options.add_argument(f"--window-size={width},{height}")
        
        # Random user agent
        options.add_argument(f"user-agent={self.fingerprint['user_agent']}")
        
        # Language
        lang = self.fingerprint["languages"][0]
        options.add_argument(f"--lang={lang}")
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Preferences
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
    
    def add_decoy_requests(self, driver: WebDriver, platform: str):
        """
        Make decoy requests to look more natural.
        Visit unrelated pages to mix up pattern.
        """
        decoy_urls = {
            "instagram": [
                "https://www.instagram.com/explore/",
                "https://www.instagram.com/reels/",
            ],
            "twitter": [
                "https://twitter.com/explore",
            ],
            "facebook": [
                "https://m.facebook.com/watch/",
            ]
        }
        
        urls = decoy_urls.get(platform, [])
        if urls and random.random() < 0.2:  # 20% chance
            decoy_url = random.choice(urls)
            try:
                driver.get(decoy_url)
                self.random_delay(1, 3)
                logger.debug(f"Made decoy request to {decoy_url}")
            except:
                pass
    
    def get_stats(self) -> Dict:
        """Get anti-detection statistics"""
        avg_delay = sum(self.delay_history) / len(self.delay_history) if self.delay_history else 0
        
        return {
            "requests_in_session": self.request_count,
            "session_duration_minutes": (time.time() - self.session_start) / 60,
            "average_delay": avg_delay,
            "fingerprint": {
                "screen": f"{self.fingerprint['screen_width']}x{self.fingerprint['screen_height']}",
                "platform": self.fingerprint['platform'],
                "languages": self.fingerprint['languages']
            }
        }


# Global anti-detection instance
anti_detection = AntiDetection()
