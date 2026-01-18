#!/usr/bin/env python3
"""
BlueRadar Intelligence Engine
Complete Social Media Intelligence System for Ocean Hazard Monitoring

Usage:
    python engine.py --mode demo
    python engine.py --mode full --platforms instagram twitter youtube
    python engine.py --mode setup
    python engine.py --mode realtime
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    OUTPUT_DIR, REPORTS_DIR, ALL_HASHTAGS, HAZARD_HASHTAGS,
    scraper_config
)
from utils.logging_config import setup_logging
from utils.image_downloader import ImageDownloader
from scrapers.session_manager import SessionManager
from scrapers.instagram_scraper import InstagramScraper
from scrapers.twitter_scraper import TwitterScraper
from scrapers.other_scrapers import (
    FacebookScraper, YouTubeScraper, NewsScraper, MultiPlatformScraper
)
from nlp.pipeline import NLPPipeline
from vision.pipeline import VisionPipeline

logger = setup_logging("blueradar_engine")


class BlueRadarEngine:
    """
    Main orchestrator for BlueRadar Intelligence System.

    Workflow:
    1. Scrape social media platforms (with session rotation)
    2. Download images
    3. Process text through NLP pipeline
    4. Classify images through vision pipeline
    5. Generate alerts and reports
    6. Output verified, scored data
    """

    def __init__(
        self,
        download_images: bool = True,
        use_ml: bool = True,
        headless: bool = True
    ):
        self.download_images = download_images
        self.use_ml = use_ml
        self.headless = headless

        # Initialize components
        self.session_manager = SessionManager()
        self.image_downloader = ImageDownloader()
        self.nlp_pipeline = NLPPipeline(use_ml=use_ml)
        self.vision_pipeline = VisionPipeline(use_ml=use_ml)

        # Results storage
        self.results = {
            "scan_info": {
                "started_at": None,
                "completed_at": None,
                "duration_seconds": 0,
                "status": "pending",
                "version": "2.0"
            },
            "platforms": {
                "instagram": [],
                "twitter": [],
                "facebook": [],
                "youtube": [],
                "news": []
            },
            "summary": {},
            "alerts": []
        }

        logger.info("="*60)
        logger.info("  BLUERADAR INTELLIGENCE ENGINE v2.0")
        logger.info("  Ocean Hazard Monitoring System")
        logger.info("="*60)

    def setup_instagram_cookies(self, session_ids: List[str]):
        """Setup Instagram session cookies"""
        self.session_manager.setup_instagram_cookies(session_ids)
        logger.info(f"Configured {len(session_ids)} Instagram sessions")

    def run_full_scan(
        self,
        hashtags: List[str] = None,
        keywords: List[str] = None,
        max_per_hashtag: int = 50,
        platforms: List[str] = None,
        time_filter_hours: int = 72
    ) -> Dict:
        """
        Run complete social media scan.

        Args:
            hashtags: Hashtags to search
            keywords: Keywords to search
            max_per_hashtag: Max posts per hashtag/keyword
            platforms: Platforms to scan
            time_filter_hours: Only include posts from last N hours
        """
        start_time = datetime.now()
        self.results["scan_info"]["started_at"] = start_time.isoformat()

        # Default configuration
        hashtags = hashtags or self._get_priority_hashtags()
        keywords = keywords or hashtags
        platforms = platforms or ["twitter", "youtube", "news"]

        logger.info(f"\nScan Configuration:")
        logger.info(f"   Hashtags: {len(hashtags)}")
        logger.info(f"   Platforms: {platforms}")
        logger.info(f"   Max per hashtag: {max_per_hashtag}")

        all_posts = []

        try:
            # =====================================================
            # PHASE 1: DATA COLLECTION
            # =====================================================
            logger.info("\n" + "="*60)
            logger.info("  PHASE 1: DATA COLLECTION")
            logger.info("="*60)

            # Instagram
            if "instagram" in platforms:
                posts = self._scan_instagram(hashtags, max_per_hashtag)
                self.results["platforms"]["instagram"] = posts
                all_posts.extend(posts)

            # Twitter
            if "twitter" in platforms:
                posts = self._scan_twitter(keywords, max_per_hashtag)
                self.results["platforms"]["twitter"] = posts
                all_posts.extend(posts)

            # Facebook
            if "facebook" in platforms:
                posts = self._scan_facebook(max_per_hashtag)
                self.results["platforms"]["facebook"] = posts
                all_posts.extend(posts)

            # YouTube
            if "youtube" in platforms:
                posts = self._scan_youtube(keywords[:10], max_per_hashtag)
                self.results["platforms"]["youtube"] = posts
                all_posts.extend(posts)

            # News
            if "news" in platforms:
                posts = self._scan_news(keywords[:10], max_per_hashtag)
                self.results["platforms"]["news"] = posts
                all_posts.extend(posts)

            logger.info(f"\nTotal posts collected: {len(all_posts)}")

            # =====================================================
            # PHASE 2: IMAGE DOWNLOADING
            # =====================================================
            if self.download_images and all_posts:
                logger.info("\n" + "="*60)
                logger.info("  PHASE 2: IMAGE DOWNLOADING")
                logger.info("="*60)

                all_posts = self.image_downloader.download_from_posts(all_posts)

            # =====================================================
            # PHASE 3: NLP PROCESSING
            # =====================================================
            logger.info("\n" + "="*60)
            logger.info("  PHASE 3: NLP ANALYSIS")
            logger.info("="*60)

            all_posts = self.nlp_pipeline.process(all_posts)

            # =====================================================
            # PHASE 4: VISION PROCESSING
            # =====================================================
            if self.download_images:
                logger.info("\n" + "="*60)
                logger.info("  PHASE 4: IMAGE ANALYSIS")
                logger.info("="*60)

                all_posts = self.vision_pipeline.process(all_posts)

            # =====================================================
            # PHASE 5: RESULTS COMPILATION
            # =====================================================
            logger.info("\n" + "="*60)
            logger.info("  PHASE 5: RESULTS COMPILATION")
            logger.info("="*60)

            # Update results with processed posts
            self._update_platform_results(all_posts)

            # Generate summary
            self._generate_summary(all_posts)

            # Generate alerts
            self._generate_alerts(all_posts)

            self.results["scan_info"]["status"] = "completed"

        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.results["scan_info"]["status"] = "error"
            self.results["scan_info"]["error"] = str(e)

        finally:
            end_time = datetime.now()
            self.results["scan_info"]["completed_at"] = end_time.isoformat()
            self.results["scan_info"]["duration_seconds"] = (end_time - start_time).total_seconds()

        # Save results
        output_path = self._save_results()

        # Print summary
        self._print_summary()

        return self.results

    def _get_priority_hashtags(self) -> List[str]:
        """Get priority hashtags for scanning"""
        priority = []

        # High priority categories
        high_priority = ["storms_cyclones", "flooding", "official_alerts"]

        for category in high_priority:
            cat_data = HAZARD_HASHTAGS.get(category, {})
            for subcat, tags in cat_data.items():
                if isinstance(tags, list):
                    priority.extend(tags[:5])

        # Add some from other categories
        for category, cat_data in HAZARD_HASHTAGS.items():
            if category not in high_priority:
                if isinstance(cat_data, dict):
                    for subcat, tags in cat_data.items():
                        if isinstance(tags, list):
                            priority.extend(tags[:3])

        return list(dict.fromkeys(priority))[:30]  # Dedupe and limit

    # =========================================================================
    # SCANNING METHODS
    # =========================================================================

    def _scan_instagram(self, hashtags: List[str], max_per: int) -> List[Dict]:
        """Scan Instagram"""
        logger.info("\nSCANNING INSTAGRAM")
        logger.info("-" * 40)

        try:
            with InstagramScraper(
                headless=self.headless,
                use_session=True
            ) as scraper:
                posts = scraper.scrape(hashtags, max_results=max_per)
                logger.info(f"Instagram: {len(posts)} posts")
                return posts
        except Exception as e:
            logger.error(f"Instagram error: {e}")
            return []

    def _scan_twitter(self, keywords: List[str], max_per: int) -> List[Dict]:
        """Scan Twitter"""
        logger.info("\nSCANNING TWITTER")
        logger.info("-" * 40)

        try:
            with TwitterScraper(headless=self.headless) as scraper:
                posts = scraper.scrape(keywords, max_results=max_per)
                logger.info(f"Twitter: {len(posts)} posts")
                return posts
        except Exception as e:
            logger.error(f"Twitter error: {e}")
            return []

    def _scan_facebook(self, max_per: int) -> List[Dict]:
        """Scan Facebook"""
        logger.info("\nSCANNING FACEBOOK")
        logger.info("-" * 40)

        try:
            with FacebookScraper(headless=self.headless) as scraper:
                posts = scraper.scrape(max_results=max_per)
                logger.info(f"Facebook: {len(posts)} posts")
                return posts
        except Exception as e:
            logger.error(f"Facebook error: {e}")
            return []

    def _scan_youtube(self, keywords: List[str], max_per: int) -> List[Dict]:
        """Scan YouTube"""
        logger.info("\nSCANNING YOUTUBE")
        logger.info("-" * 40)

        try:
            with YouTubeScraper(headless=self.headless) as scraper:
                posts = scraper.scrape(keywords, max_results=max_per)
                logger.info(f"YouTube: {len(posts)} posts")
                return posts
        except Exception as e:
            logger.error(f"YouTube error: {e}")
            return []

    def _scan_news(self, keywords: List[str], max_per: int) -> List[Dict]:
        """Scan News sources"""
        logger.info("\nSCANNING NEWS")
        logger.info("-" * 40)

        try:
            with NewsScraper(headless=self.headless) as scraper:
                posts = scraper.scrape(keywords, max_results=max_per)
                logger.info(f"News: {len(posts)} posts")
                return posts
        except Exception as e:
            logger.error(f"News error: {e}")
            return []

    # =========================================================================
    # RESULTS PROCESSING
    # =========================================================================

    def _update_platform_results(self, all_posts: List[Dict]):
        """Update platform-specific results"""
        for post in all_posts:
            platform = post.get("platform", "unknown")
            if platform in self.results["platforms"]:
                # Find and update existing post
                for i, existing in enumerate(self.results["platforms"][platform]):
                    if existing.get("id") == post.get("id"):
                        self.results["platforms"][platform][i] = post
                        break

    def _generate_summary(self, posts: List[Dict]):
        """Generate comprehensive summary"""
        # NLP summary
        nlp_summary = self.nlp_pipeline.get_summary(posts)

        # Platform counts
        platform_counts = {}
        for platform in ["instagram", "twitter", "facebook", "youtube", "news"]:
            platform_posts = self.results["platforms"].get(platform, [])
            platform_counts[platform] = {
                "total": len(platform_posts),
                "relevant": sum(
                    1 for p in platform_posts
                    if p.get("nlp", {}).get("is_relevant")
                ),
                "with_images": sum(
                    1 for p in platform_posts
                    if p.get("media", {}).get("local_paths")
                )
            }

        # Image stats
        image_stats = self.image_downloader.get_stats()

        self.results["summary"] = {
            "total_posts": len(posts),
            "by_platform": platform_counts,
            "nlp": nlp_summary,
            "images": image_stats,
            "generated_at": datetime.now().isoformat()
        }

    def _generate_alerts(self, posts: List[Dict]):
        """Generate alerts for critical posts"""
        alerts = []

        for post in posts:
            nlp = post.get("nlp", {})
            severity = nlp.get("severity", {})

            if severity.get("level") in ["CRITICAL", "HIGH"]:
                alert = {
                    "id": f"alert_{len(alerts)+1:03d}",
                    "type": "hazard_alert",
                    "severity": severity.get("level"),
                    "score": severity.get("score"),
                    "hazard": nlp.get("hazards", {}).get("primary_hazard"),
                    "location": nlp.get("locations", {}).get("primary_region"),
                    "relevance_score": nlp.get("relevance_score"),
                    "authenticity": nlp.get("authenticity", {}).get("score"),
                    "post_id": post.get("id"),
                    "platform": post.get("platform"),
                    "url": post.get("url"),
                    "text_preview": post.get("content", {}).get("text", "")[:150],
                    "generated_at": datetime.now().isoformat()
                }
                alerts.append(alert)

        # Sort by severity score
        alerts.sort(key=lambda x: x.get("score", 0), reverse=True)

        self.results["alerts"] = alerts

        if alerts:
            logger.warning(f"Generated {len(alerts)} alerts!")

    def _save_results(self) -> Path:
        """Save results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"blueradar_scan_{timestamp}.json"
        filepath = OUTPUT_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\nResults saved: {filepath}")

        # Also save alerts separately
        if self.results["alerts"]:
            alerts_file = OUTPUT_DIR / f"alerts_{timestamp}.json"
            with open(alerts_file, "w") as f:
                json.dump(self.results["alerts"], f, indent=2)
            logger.info(f"Alerts saved: {alerts_file}")

        return filepath

    def _print_summary(self):
        """Print formatted summary"""
        summary = self.results.get("summary", {})

        print("\n" + "="*60)
        print("SCAN SUMMARY")
        print("="*60)

        print(f"\nTotal posts: {summary.get('total_posts', 0)}")

        print("\nBy Platform:")
        for platform, data in summary.get("by_platform", {}).items():
            print(f"   {platform}: {data.get('total', 0)} total, {data.get('relevant', 0)} relevant")

        nlp = summary.get("nlp", {})
        print(f"\nRelevant posts: {nlp.get('relevant_count', 0)} ({nlp.get('relevance_rate', '0%')})")

        print("\nHazard Types:")
        for hazard, count in nlp.get("hazard_distribution", {}).items():
            print(f"   - {hazard}: {count}")

        print("\nSeverity Distribution:")
        for level, count in nlp.get("severity_distribution", {}).items():
            print(f"   - {level}: {count}")

        print("\nRegions:")
        for region, count in nlp.get("region_distribution", {}).items():
            print(f"   - {region}: {count}")

        images = summary.get("images", {})
        print(f"\nImages: {images.get('downloaded', 0)} downloaded ({images.get('total_mb', 0)} MB)")

        alerts = self.results.get("alerts", [])
        if alerts:
            print(f"\nALERTS: {len(alerts)} generated")
            for alert in alerts[:5]:
                print(f"   {alert['severity']}: {alert['hazard']} - {alert['location']}")

        print("\n" + "="*60)


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def quick_demo():
    """Run quick demo"""
    logger.info("\nRunning Quick Demo...")

    engine = BlueRadarEngine(
        download_images=True,
        use_ml=True,
        headless=True
    )

    demo_hashtags = [
        "CycloneAlert", "IndiaWeather", "IMDAlert",
        "MumbaiRains", "ChennaiFloods"
    ]

    return engine.run_full_scan(
        hashtags=demo_hashtags,
        max_per_hashtag=10,
        platforms=["twitter", "youtube", "news"]
    )


def setup_cookies():
    """Interactive cookie setup"""
    print("\nSession Cookie Setup")
    print("="*50)
    print("\nHow to get Instagram session ID:")
    print("1. Login to Instagram in browser")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application -> Cookies -> instagram.com")
    print("4. Copy the 'sessionid' value")
    print("\nEnter session IDs (one per line, empty to finish):")

    session_ids = []
    while True:
        try:
            sid = input(f"Session {len(session_ids)+1}: ").strip()
            if not sid:
                break
            session_ids.append(sid)
        except EOFError:
            break

    if session_ids:
        sm = SessionManager()
        sm.setup_instagram_cookies(session_ids)
        print(f"\nSaved {len(session_ids)} session cookies!")
    else:
        print("\nNo cookies provided")


def show_status():
    """Show session status"""
    sm = SessionManager()
    status = sm.get_status()
    print(json.dumps(status, indent=2))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BlueRadar Intelligence Engine - Ocean Hazard Monitoring"
    )

    parser.add_argument(
        "--mode",
        choices=["full", "demo", "setup", "status", "realtime"],
        default="demo",
        help="Run mode"
    )

    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["twitter", "youtube", "news"],
        help="Platforms to scan"
    )

    parser.add_argument(
        "--hashtags",
        nargs="+",
        help="Hashtags to search"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=30,
        help="Max results per hashtag"
    )

    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image downloading"
    )

    parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Disable ML models"
    )

    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window"
    )

    args = parser.parse_args()

    if args.mode == "setup":
        setup_cookies()
        return

    if args.mode == "status":
        show_status()
        return

    if args.mode == "demo":
        quick_demo()
        return

    # Full scan
    engine = BlueRadarEngine(
        download_images=not args.no_images,
        use_ml=not args.no_ml,
        headless=not args.visible
    )

    engine.run_full_scan(
        hashtags=args.hashtags,
        max_per_hashtag=args.max_results,
        platforms=args.platforms
    )


if __name__ == "__main__":
    main()
