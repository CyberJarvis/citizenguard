"""
BlueRadar - Image Downloader
Parallel downloading with deduplication and metadata
"""

import os
import time
import hashlib
import requests
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from utils.logging_config import setup_logging
from config import IMAGES_DIR

logger = setup_logging("image_downloader")


class ImageDownloader:
    """
    Production image downloader with:
    - Parallel downloading
    - Deduplication via hashing
    - Organized by platform
    - Metadata preservation
    - Retry logic
    - Rate limiting
    """
    
    def __init__(
        self,
        output_dir: Path = IMAGES_DIR,
        max_workers: int = 4,
        timeout: int = 30
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_workers = max_workers
        self.timeout = timeout
        
        # Create platform subdirs
        for platform in ["instagram", "twitter", "facebook", "youtube", "news"]:
            (self.output_dir / platform).mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            "downloaded": 0,
            "failed": 0,
            "duplicates": 0,
            "skipped": 0,
            "total_bytes": 0
        }
        
        # Deduplication
        self.seen_hashes: Set[str] = set()
        self.seen_urls: Set[str] = set()
        
        # Rate limiting
        self._last_request_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache"
        }
    
    def download_from_posts(
        self,
        posts: List[Dict],
        max_per_post: int = 5
    ) -> List[Dict]:
        """
        Download images from posts.
        Updates posts with local file paths.
        """
        # Collect download tasks
        tasks = []
        
        for post in posts:
            platform = post.get("platform", "unknown")
            image_urls = post.get("media", {}).get("urls", [])
            post_id = post.get("id", "unknown")
            
            for i, url in enumerate(image_urls[:max_per_post]):
                if url in self.seen_urls:
                    continue
                    
                tasks.append({
                    "url": url,
                    "platform": platform,
                    "post_id": post_id,
                    "index": i,
                    "post_ref": post
                })
                self.seen_urls.add(url)
        
        if not tasks:
            logger.info("No images to download")
            return posts
        
        logger.info(f"📥 Downloading {len(tasks)} images...")
        
        # Download in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_single, task): task
                for task in tasks
            }
            
            completed = 0
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    if result:
                        # Update post with local path
                        post = task["post_ref"]
                        if "local_paths" not in post.get("media", {}):
                            post["media"]["local_paths"] = []
                        post["media"]["local_paths"].append(result)
                        
                except Exception as e:
                    logger.debug(f"Download task failed: {e}")
                
                completed += 1
                if completed % 20 == 0:
                    logger.info(f"Progress: {completed}/{len(tasks)}")
        
        logger.info(
            f"✅ Downloads complete - "
            f"Success: {self.stats['downloaded']}, "
            f"Failed: {self.stats['failed']}, "
            f"Duplicates: {self.stats['duplicates']}"
        )
        
        return posts
    
    def _download_single(self, task: Dict, retry: int = 0) -> Optional[str]:
        """Download a single image"""
        url = task["url"]
        platform = task["platform"]
        post_id = task["post_id"]
        index = task["index"]
        
        if not self._is_valid_url(url):
            return None
        
        # Rate limiting
        self._rate_limit(platform)
        
        try:
            # Generate filename
            filename = self._generate_filename(url, platform, post_id, index)
            filepath = self.output_dir / platform / filename
            
            # Skip if exists
            if filepath.exists():
                self.stats["duplicates"] += 1
                return str(filepath)
            
            # Set referer based on platform
            headers = self.headers.copy()
            headers["Referer"] = self._get_referer(url, platform)
            
            # Download
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Verify content type
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return None
            
            # Read content
            content = response.content
            
            # Size check
            if len(content) < 1000:  # Too small
                return None
            
            # Duplicate check via hash
            content_hash = hashlib.md5(content).hexdigest()
            with self._lock:
                if content_hash in self.seen_hashes:
                    self.stats["duplicates"] += 1
                    return None
                self.seen_hashes.add(content_hash)
            
            # Save
            with open(filepath, "wb") as f:
                f.write(content)
            
            # Update stats
            with self._lock:
                self.stats["downloaded"] += 1
                self.stats["total_bytes"] += len(content)
            
            return str(filepath)
            
        except requests.exceptions.Timeout:
            if retry < 2:
                time.sleep(2)
                return self._download_single(task, retry + 1)
            self.stats["failed"] += 1
            return None
            
        except Exception as e:
            logger.debug(f"Download failed: {url} - {e}")
            self.stats["failed"] += 1
            return None
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL"""
        if not url or not isinstance(url, str):
            return False
        try:
            result = urlparse(url)
            return result.scheme in ["http", "https"] and bool(result.netloc)
        except:
            return False
    
    def _generate_filename(
        self,
        url: str,
        platform: str,
        post_id: str,
        index: int
    ) -> str:
        """Generate unique filename"""
        # Get extension from URL
        parsed = urlparse(url)
        path = parsed.path
        ext = Path(path).suffix.lower()
        
        if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            ext = ".jpg"
        
        # Hash URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        
        # Clean post_id
        safe_post_id = "".join(c for c in post_id if c.isalnum())[:20]
        
        return f"{platform}_{safe_post_id}_{index}_{url_hash}{ext}"
    
    def _get_referer(self, url: str, platform: str) -> str:
        """Get appropriate referer for request"""
        referers = {
            "instagram": "https://www.instagram.com/",
            "twitter": "https://twitter.com/",
            "facebook": "https://www.facebook.com/",
            "youtube": "https://www.youtube.com/",
            "news": "https://news.google.com/"
        }
        return referers.get(platform, "https://www.google.com/")
    
    def _rate_limit(self, platform: str):
        """Apply rate limiting"""
        min_interval = 0.3  # 300ms between requests per platform
        
        with self._lock:
            last_time = self._last_request_time.get(platform, 0)
            elapsed = time.time() - last_time
            
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            self._last_request_time[platform] = time.time()
    
    def get_stats(self) -> Dict:
        """Get download statistics"""
        return {
            **self.stats,
            "total_mb": round(self.stats["total_bytes"] / (1024 * 1024), 2),
            "success_rate": (
                f"{self.stats['downloaded'] / max(1, self.stats['downloaded'] + self.stats['failed']) * 100:.1f}%"
            )
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            "downloaded": 0,
            "failed": 0,
            "duplicates": 0,
            "skipped": 0,
            "total_bytes": 0
        }
        self.seen_hashes.clear()
        self.seen_urls.clear()
    
    def download_single(self, url: str, platform: str = "misc") -> Optional[str]:
        """Download a single image"""
        task = {
            "url": url,
            "platform": platform,
            "post_id": "single",
            "index": 0,
            "post_ref": {}
        }
        return self._download_single(task)


# Global instance
image_downloader = ImageDownloader()
