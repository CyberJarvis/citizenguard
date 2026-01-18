#!/usr/bin/env python3
"""
BlueRadar Real-Time Runner
Starts both the WebSocket server and HTTP dashboard server
"""

import asyncio
import http.server
import socketserver
import threading
import webbrowser
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from realtime.engine import RealTimeEngine


def start_http_server(port=8080):
    """Start HTTP server for dashboard"""
    dashboard_dir = Path(__file__).parent / "dashboard"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def log_message(self, format, *args):
            pass  # Suppress HTTP logs

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Dashboard: http://localhost:{port}")
        httpd.serve_forever()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="BlueRadar Real-Time System")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--http-port", type=int, default=8080, help="Dashboard HTTP port")
    parser.add_argument("--interval", type=int, default=120, help="Scrape interval (seconds)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--platforms", nargs="+", default=["twitter", "youtube", "news", "instagram"],
                       help="Platforms to scrape (twitter, youtube, news, instagram)")

    args = parser.parse_args()

    print("=" * 60)
    print("  BLUERADAR REAL-TIME SYSTEM")
    print("  Ocean Hazard Monitoring")
    print("=" * 60)

    # Start HTTP server in background thread
    http_thread = threading.Thread(
        target=start_http_server,
        args=(args.http_port,),
        daemon=True
    )
    http_thread.start()

    # Open browser
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.http_port}")

    # Create and run engine (Instagram now uses RapidAPI, no sessions needed)
    engine = RealTimeEngine(
        ws_port=args.ws_port,
        scrape_interval=args.interval
    )

    print(f"\nWebSocket: ws://localhost:{args.ws_port}")
    print(f"Dashboard: http://localhost:{args.http_port}")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)

    try:
        await engine.run(platforms=args.platforms)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
