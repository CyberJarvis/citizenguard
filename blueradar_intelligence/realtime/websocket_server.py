"""
BlueRadar WebSocket Server
Real-time alert streaming to dashboard clients
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Set, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import hashlib

try:
    import websockets
    from websockets.asyncio.server import ServerConnection
    from websockets.exceptions import ConnectionClosed
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    ServerConnection = None
    ConnectionClosed = Exception
    print("Warning: websockets not installed. Run: pip install websockets")


@dataclass
class Alert:
    """Real-time alert structure"""
    id: str
    type: str  # hazard type
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    title: str
    description: str
    location: Optional[str]
    region: Optional[str]
    platform: str
    source_url: str
    image_url: Optional[str]
    relevance_score: float
    timestamp: str
    raw_post: Dict

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AlertQueue:
    """
    In-memory queue for alerts with deduplication
    Can be replaced with Redis for production
    """

    def __init__(self, max_size: int = 1000):
        self.alerts: List[Alert] = []
        self.seen_ids: Set[str] = set()
        self.max_size = max_size
        self.lock = asyncio.Lock()

    async def add(self, alert: Alert) -> bool:
        """Add alert to queue, returns True if new"""
        async with self.lock:
            if alert.id in self.seen_ids:
                return False

            self.alerts.append(alert)
            self.seen_ids.add(alert.id)

            # Trim old alerts if needed
            if len(self.alerts) > self.max_size:
                removed = self.alerts.pop(0)
                self.seen_ids.discard(removed.id)

            return True

    async def get_recent(self, count: int = 50) -> List[Alert]:
        """Get recent alerts"""
        async with self.lock:
            return self.alerts[-count:]

    async def get_by_severity(self, severity: str) -> List[Alert]:
        """Get alerts by severity level"""
        async with self.lock:
            return [a for a in self.alerts if a.severity == severity]

    def clear(self):
        """Clear all alerts"""
        self.alerts.clear()
        self.seen_ids.clear()


class WebSocketServer:
    """
    WebSocket server for real-time alert streaming
    Supports multiple clients and topic-based subscriptions
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set = set()
        self.alert_queue = AlertQueue()
        self.running = False
        self.server = None

        # Topic subscriptions
        self.subscriptions: Dict = {}

    async def register(self, websocket):
        """Register new client"""
        self.clients.add(websocket)
        self.subscriptions[websocket] = {"all"}  # Default subscription
        print(f"[WS] Client connected. Total clients: {len(self.clients)}")

        # Send recent alerts to new client
        recent = await self.alert_queue.get_recent(20)
        if recent:
            await websocket.send(json.dumps({
                "type": "history",
                "alerts": [a.to_dict() for a in recent]
            }))

    async def unregister(self, websocket):
        """Unregister client"""
        self.clients.discard(websocket)
        self.subscriptions.pop(websocket, None)
        print(f"[WS] Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast_alert(self, alert: Alert):
        """Broadcast alert to all subscribed clients"""
        # Always add to queue first (even if no clients connected)
        # This ensures alerts are available when clients connect later
        is_new = await self.alert_queue.add(alert)
        if not is_new:
            return

        # No clients connected - alert is still stored in queue for later
        if not self.clients:
            print(f"[WS] Alert queued (no clients): {alert.title[:50]}...")
            return

        message = json.dumps({
            "type": "alert",
            "alert": alert.to_dict()
        })

        # Send to all clients (filter by subscription later)
        disconnected = set()
        for client in self.clients:
            try:
                subs = self.subscriptions.get(client, {"all"})

                # Check if client subscribed to this alert type
                should_send = (
                    "all" in subs or
                    alert.severity in subs or
                    alert.type in subs or
                    (alert.region and alert.region in subs)
                )

                if should_send:
                    await client.send(message)

            except ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                print(f"[WS] Error sending to client: {e}")
                disconnected.add(client)

        # Clean up disconnected clients
        for client in disconnected:
            await self.unregister(client)

    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register(websocket)

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def handle_message(self, websocket, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "subscribe":
                # Subscribe to topics
                topics = data.get("topics", [])
                if topics:
                    self.subscriptions[websocket] = set(topics)
                    await websocket.send(json.dumps({
                        "type": "subscribed",
                        "topics": list(topics)
                    }))

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif msg_type == "get_history":
                count = data.get("count", 50)
                recent = await self.alert_queue.get_recent(count)
                await websocket.send(json.dumps({
                    "type": "history",
                    "alerts": [a.to_dict() for a in recent]
                }))

            elif msg_type == "get_stats":
                stats = await self.get_stats()
                await websocket.send(json.dumps({
                    "type": "stats",
                    "data": stats
                }))

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[WS] Error handling message: {e}")

    async def get_stats(self) -> Dict:
        """Get server statistics"""
        alerts = await self.alert_queue.get_recent(1000)

        severity_counts = {}
        type_counts = {}
        region_counts = {}

        for alert in alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
            if alert.type:
                type_counts[alert.type] = type_counts.get(alert.type, 0) + 1
            if alert.region:
                region_counts[alert.region] = region_counts.get(alert.region, 0) + 1

        return {
            "connected_clients": len(self.clients),
            "total_alerts": len(alerts),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "by_region": region_counts,
            "timestamp": datetime.now().isoformat()
        }

    async def start(self):
        """Start WebSocket server"""
        if not WEBSOCKETS_AVAILABLE:
            print("Error: websockets library not installed")
            return

        self.running = True
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )

        print(f"[WS] Server started at ws://{self.host}:{self.port}")

        await self.server.wait_closed()

    def stop(self):
        """Stop server"""
        self.running = False
        if self.server:
            self.server.close()


class AlertBroadcaster:
    """
    Bridge between scrapers and WebSocket server
    Converts posts to alerts and broadcasts them
    """

    def __init__(self, ws_server: WebSocketServer):
        self.ws_server = ws_server
        self.processed_count = 0

    def create_alert_from_post(self, post: Dict, nlp_result: Dict) -> Optional[Alert]:
        """Convert a processed post to an alert"""
        if not nlp_result.get("is_alert_worthy", False):
            return None

        # Generate unique ID
        text = post.get("text", "")[:100]
        alert_id = hashlib.md5(f"{post.get('id', '')}{text}".encode()).hexdigest()[:16]

        # Create title
        hazard = nlp_result.get("hazard_type", "hazard")
        severity = nlp_result.get("severity", "MEDIUM")
        locations = nlp_result.get("locations", [])
        location_str = locations[0] if locations else "Unknown location"

        title = f"{severity}: {hazard.title()} detected near {location_str.title()}"

        return Alert(
            id=alert_id,
            type=hazard,
            severity=severity,
            title=title,
            description=text[:300],
            location=location_str if locations else None,
            region=nlp_result.get("primary_region"),
            platform=post.get("platform", "unknown"),
            source_url=post.get("url", ""),
            image_url=post.get("image_urls", [None])[0] if post.get("image_urls") else None,
            relevance_score=nlp_result.get("relevance_score", 0),
            timestamp=datetime.now().isoformat(),
            raw_post=post
        )

    async def process_and_broadcast(self, post: Dict, nlp_result: Dict):
        """Process post and broadcast if alert-worthy"""
        alert = self.create_alert_from_post(post, nlp_result)

        if alert:
            await self.ws_server.broadcast_alert(alert)
            self.processed_count += 1
            print(f"[ALERT] {alert.severity}: {alert.title}")

    async def broadcast_batch(self, posts: List[Dict]):
        """Process and broadcast multiple posts"""
        for post in posts:
            nlp = post.get("nlp", {})
            if nlp:
                await self.process_and_broadcast(post, nlp)


# Demo/Test function
async def demo_server():
    """Demo the WebSocket server"""
    if not WEBSOCKETS_AVAILABLE:
        print("Install websockets: pip install websockets")
        return

    server = WebSocketServer(port=8765)
    broadcaster = AlertBroadcaster(server)

    # Start server in background
    server_task = asyncio.create_task(server.start())

    # Wait a bit for server to start
    await asyncio.sleep(1)

    # Simulate some alerts
    test_posts = [
        {
            "id": "test1",
            "text": "BREAKING: Cyclone Michaung makes landfall near Chennai. Red alert issued!",
            "platform": "twitter",
            "url": "https://twitter.com/test/1",
            "image_urls": ["https://example.com/cyclone.jpg"],
            "nlp": {
                "is_alert_worthy": True,
                "hazard_type": "cyclone",
                "severity": "CRITICAL",
                "locations": ["chennai"],
                "primary_region": "east_coast",
                "relevance_score": 95
            }
        },
        {
            "id": "test2",
            "text": "Severe flooding in Mumbai suburbs. Multiple areas waterlogged.",
            "platform": "instagram",
            "url": "https://instagram.com/p/test2",
            "image_urls": [],
            "nlp": {
                "is_alert_worthy": True,
                "hazard_type": "flood",
                "severity": "HIGH",
                "locations": ["mumbai"],
                "primary_region": "west_coast",
                "relevance_score": 78
            }
        }
    ]

    print("\nBroadcasting test alerts...")
    await broadcaster.broadcast_batch(test_posts)

    print(f"\nServer running at ws://localhost:8765")
    print("Connect with a WebSocket client to receive alerts")
    print("Press Ctrl+C to stop")

    try:
        await server_task
    except asyncio.CancelledError:
        server.stop()


if __name__ == "__main__":
    asyncio.run(demo_server())
