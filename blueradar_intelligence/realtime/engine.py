"""
BlueRadar Real-Time Engine
Main orchestrator for real-time ocean hazard monitoring
"""

import asyncio
import json
import sys
import signal
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from threading import Thread
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.fast_scraper import ParallelScraperManager, ScrapedPost
from services.fast_nlp import FastNLPProcessor, FastNLPResult
from services.content_validator import ContentValidator, DEFAULT_VALIDATION_CONFIG
from realtime.websocket_server import WebSocketServer, AlertBroadcaster, Alert


# Default keywords for ocean hazards
DEFAULT_KEYWORDS = [
    # Cyclone/Storm
    "cyclone", "CycloneAlert", "CycloneIndia", "hurricane", "storm",
    "TropicalStorm", "IMDAlert", "StormSurge",

    # Flood
    "flood", "flooding", "MumbaiFloods", "ChennaiFloods", "KeralaFloods",
    "CoastalFlooding", "FloodAlert",

    # Sea conditions
    "HighWaves", "RoughSea", "RipCurrent", "TidalFlooding",

    # India specific
    "IndiaWeather", "BayOfBengal", "ArabianSea", "INCOIS"
]


class RealTimeEngine:
    """
    Real-time monitoring engine that:
    1. Runs parallel scrapers in background
    2. Processes posts through fast NLP
    3. Broadcasts alerts via WebSocket
    4. Provides REST API for dashboard
    """

    def __init__(
        self,
        ws_port: int = 8765,
        scrape_interval: int = 300  # 5 minutes
    ):
        self.ws_port = ws_port
        self.scrape_interval = scrape_interval

        # Initialize components (Instagram now uses RapidAPI, no sessions needed)
        self.scraper = ParallelScraperManager()
        self.nlp = FastNLPProcessor()
        self.validator = ContentValidator(DEFAULT_VALIDATION_CONFIG)
        self.ws_server = WebSocketServer(port=ws_port)
        self.broadcaster = AlertBroadcaster(self.ws_server)

        # State
        self.running = False
        self.stats = {
            "started_at": None,
            "posts_scraped": 0,
            "alerts_generated": 0,
            "posts_rejected": 0,
            "rejected_old": 0,
            "rejected_international": 0,
            "rejected_duplicate": 0,
            "last_scrape": None
        }

        # NOTE: Removed on_post_found callback to ensure ALL posts go through
        # the validation pipeline in _scrape_loop (recency, geography, duplicate checks)

    async def _scrape_loop(self, keywords: List[str], platforms: List[str]):
        """Continuous scraping loop"""
        while self.running:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting scrape cycle...")

                posts = await self.scraper.run_parallel_scrape(
                    keywords,
                    platforms,
                    max_per=10
                )

                self.stats["last_scrape"] = datetime.now().isoformat()
                self.stats["posts_scraped"] += len(posts)

                print(f"  Scraped {len(posts)} posts")

                # Process each post
                alerts_this_cycle = 0
                rejected_this_cycle = 0
                for post in posts:
                    nlp_result = self.nlp.process(post.text, post.platform)
                    post_dict = post.to_dict()

                    # Validate content (recency, geography, duplicates)
                    validation = self.validator.validate(post_dict, nlp_result.to_dict())

                    if not validation.is_valid:
                        self.stats["posts_rejected"] += 1
                        rejected_this_cycle += 1
                        # Track rejection reason
                        if validation.rejection_reason in ["content_too_old", "timestamp_unknown"]:
                            self.stats["rejected_old"] += 1
                        elif validation.rejection_reason in ["international_content", "not_india_relevant", "no_india_reference"]:
                            self.stats["rejected_international"] += 1
                        elif validation.rejection_reason == "duplicate_content":
                            self.stats["rejected_duplicate"] += 1
                        continue

                    if nlp_result.is_alert_worthy:
                        post_dict["nlp"] = nlp_result.to_dict()
                        post_dict["validation"] = {
                            "confidence": validation.confidence,
                            "india_score": validation.details.get("india_score", 0)
                        }

                        await self.broadcaster.process_and_broadcast(
                            post_dict,
                            nlp_result.to_dict()
                        )
                        alerts_this_cycle += 1
                        self.stats["alerts_generated"] += 1

                print(f"  Generated {alerts_this_cycle} alerts (rejected {rejected_this_cycle} posts)")

                # Wait for next cycle
                await asyncio.sleep(self.scrape_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scrape error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def run(
        self,
        keywords: List[str] = None,
        platforms: List[str] = None
    ):
        """
        Main run loop
        Starts WebSocket server and scraping
        """
        keywords = keywords or DEFAULT_KEYWORDS
        platforms = platforms or ["twitter", "youtube", "news", "instagram"]  # Instagram now uses RapidAPI

        self.running = True
        self.stats["started_at"] = datetime.now().isoformat()
        self._loop = asyncio.get_event_loop()

        print("=" * 60)
        print("  BLUERADAR REAL-TIME ENGINE")
        print("  Ocean Hazard Monitoring System")
        print("=" * 60)
        print(f"\nConfiguration:")
        print(f"  WebSocket: ws://localhost:{self.ws_port}")
        print(f"  Keywords: {len(keywords)}")
        print(f"  Platforms: {platforms}")
        print(f"  Scrape interval: {self.scrape_interval}s")
        print("\n" + "=" * 60)

        # Start WebSocket server
        ws_task = asyncio.create_task(self.ws_server.start())

        # Start scraping loop
        scrape_task = asyncio.create_task(
            self._scrape_loop(keywords, platforms)
        )

        # Handle shutdown
        def shutdown():
            print("\nShutting down...")
            self.running = False
            scrape_task.cancel()
            self.ws_server.stop()

        # Set up signal handlers
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, shutdown)
        except:
            pass  # Signal handlers not available on Windows

        try:
            await asyncio.gather(ws_task, scrape_task)
        except asyncio.CancelledError:
            pass

    def get_stats(self) -> Dict:
        """Get engine statistics"""
        return {
            **self.stats,
            "ws_clients": len(self.ws_server.clients),
            "alerts_in_queue": len(self.ws_server.alert_queue.alerts),
            "validator_stats": self.validator.get_stats()
        }


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="BlueRadar Real-Time Engine")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--interval", type=int, default=300, help="Scrape interval (seconds)")
    parser.add_argument("--platforms", nargs="+", default=["twitter", "youtube", "news", "instagram"],
                       help="Platforms to scrape")
    parser.add_argument("--keywords", nargs="+", help="Keywords to search")

    args = parser.parse_args()

    # Create engine (Instagram sessions no longer needed - using RapidAPI)
    engine = RealTimeEngine(
        ws_port=args.port,
        scrape_interval=args.interval
    )

    # Run
    await engine.run(
        keywords=args.keywords,
        platforms=args.platforms
    )


if __name__ == "__main__":
    asyncio.run(main())
