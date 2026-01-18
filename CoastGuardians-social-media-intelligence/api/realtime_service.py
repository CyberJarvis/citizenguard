"""
BlueRadar Real-Time Alert Service
WebSocket and Server-Sent Events for live marine disaster monitoring
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse
import uuid

from api.models import ProcessedPost, RealTimeAlert, AlertConfig
from api.analysis_service import BlueRadarAnalysisService


class ConnectionManager:
    """Manages WebSocket connections for real-time alerts"""

    def __init__(self):
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        # Alert subscriptions by connection ID
        self.subscriptions: Dict[str, AlertConfig] = {}
        # Client metadata
        self.client_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """Accept WebSocket connection and assign client ID"""
        if client_id is None:
            client_id = str(uuid.uuid4())

        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_metadata[client_id] = {
            "connected_at": datetime.now(timezone.utc),
            "last_ping": datetime.now(timezone.utc),
            "alert_count": 0
        }

        print(f"🔗 Client {client_id} connected to real-time alerts")
        return client_id

    def disconnect(self, client_id: str):
        """Remove client connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        if client_id in self.client_metadata:
            del self.client_metadata[client_id]
        print(f"❌ Client {client_id} disconnected")

    def subscribe_alerts(self, client_id: str, alert_config: AlertConfig):
        """Subscribe client to specific alert criteria"""
        if client_id in self.active_connections:
            self.subscriptions[client_id] = alert_config
            print(f"📋 Client {client_id} subscribed to alerts: {alert_config.disaster_types}")

    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
                self.client_metadata[client_id]["last_ping"] = datetime.now(timezone.utc)
            except Exception as e:
                print(f"❌ Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast_alert(self, alert: RealTimeAlert):
        """Broadcast alert to all matching subscribers"""
        alert_data = {
            "type": "alert",
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "disaster_type": alert.post.analysis.disaster_type,
            "location": alert.post.analysis.location_mentioned,
            "urgency": alert.post.analysis.urgency,
            "priority": alert.post.priority_level,
            "text_preview": alert.post.original_post.text[:150] + "..." if len(alert.post.original_post.text) > 150 else alert.post.original_post.text,
            "platform": alert.post.original_post.platform,
            "relevance_score": alert.post.analysis.relevance_score,
            "triggered_at": alert.triggered_at.isoformat(),
            "alert_reason": alert.alert_reason
        }

        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                # Check if alert matches client subscription
                if self._matches_subscription(client_id, alert):
                    await websocket.send_text(json.dumps(alert_data))
                    self.client_metadata[client_id]["alert_count"] += 1
                    print(f"📢 Alert sent to client {client_id}: {alert.severity} - {alert.post.analysis.disaster_type}")
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                print(f"❌ Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def _matches_subscription(self, client_id: str, alert: RealTimeAlert) -> bool:
        """Check if alert matches client's subscription criteria"""
        if client_id not in self.subscriptions:
            return True  # Default: send all alerts

        config = self.subscriptions[client_id]

        # Check disaster type filter
        if config.disaster_types and alert.post.analysis.disaster_type not in config.disaster_types:
            return False

        # Check urgency level filter
        if config.urgency_levels and alert.post.analysis.urgency not in config.urgency_levels:
            return False

        # Check minimum relevance score
        if alert.post.analysis.relevance_score < config.min_relevance_score:
            return False

        # Check location filter
        if config.locations:
            alert_location = alert.post.analysis.location_mentioned
            if not alert_location:
                return False
            location_match = any(loc.lower() in alert_location.lower() for loc in config.locations)
            if not location_match:
                return False

        # Check keyword filter
        if config.keywords:
            text_content = alert.post.original_post.text.lower()
            keyword_match = any(keyword.lower() in text_content for keyword in config.keywords)
            if not keyword_match:
                return False

        return True

    async def send_system_status(self, client_id: str):
        """Send system status to specific client"""
        status_data = {
            "type": "system_status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connected_clients": len(self.active_connections),
            "client_alerts_sent": self.client_metadata.get(client_id, {}).get("alert_count", 0),
            "system_health": "operational"
        }
        await self.send_personal_message(status_data, client_id)

    async def send_heartbeat_to_all(self):
        """Send heartbeat to all connected WebSocket clients"""
        heartbeat_data = {
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "connections": len(self.active_connections)
        }

        disconnected_clients = []
        for client_id in self.active_connections:
            try:
                await self.send_personal_message(heartbeat_data, client_id)
            except Exception as e:
                print(f"❌ Error sending heartbeat to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_alerts_sent = sum(
            metadata.get("alert_count", 0)
            for metadata in self.client_metadata.values()
        )

        return {
            "active_connections": len(self.active_connections),
            "total_alerts_sent": total_alerts_sent,
            "subscription_count": len(self.subscriptions),
            "average_alerts_per_client": total_alerts_sent / max(len(self.active_connections), 1)
        }


class BlueRadarRealtimeAlerts:
    """Real-time alert processing and distribution system"""

    def __init__(self, analysis_service: BlueRadarAnalysisService):
        self.analysis_service = analysis_service
        self.connection_manager = ConnectionManager()
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        self.sse_alert_queue: asyncio.Queue = asyncio.Queue()  # Separate queue for SSE
        self.processing_alerts = False
        self.heartbeat_running = False

        # Alert generation settings
        self.alert_thresholds = {
            "P0": {"severity": "CRITICAL", "min_relevance": 8.0},
            "P1": {"severity": "HIGH", "min_relevance": 7.0},
            "P2": {"severity": "MEDIUM", "min_relevance": 0.0},  # Temporarily lowered for testing
            "P3": {"severity": "LOW", "min_relevance": 0.0}     # Temporarily lowered for testing
        }

    async def start_alert_processor(self):
        """Start background task for processing alerts"""
        if not self.processing_alerts:
            self.processing_alerts = True
            asyncio.create_task(self._process_alert_queue())
            print("🚀 Real-time alert processor started")

        if not self.heartbeat_running:
            self.heartbeat_running = True
            asyncio.create_task(self._heartbeat_sender())
            print("💓 Heartbeat sender started")

    async def stop_alert_processor(self):
        """Stop alert processing"""
        self.processing_alerts = False
        self.heartbeat_running = False
        print("⏹️ Real-time alert processor stopped")
        print("⏹️ Heartbeat sender stopped")

    async def process_post_for_alerts(self, processed_post: ProcessedPost):
        """Process analyzed post and generate alerts if needed"""
        try:
            # Check if post meets alert criteria
            if self._should_generate_alert(processed_post):
                alert = self._create_alert(processed_post)
                # Send to both WebSocket queue and SSE queue
                await self.alert_queue.put(alert)
                await self.sse_alert_queue.put(alert)
                print(f"⚠️ Alert queued: {alert.severity} - {processed_post.analysis.disaster_type}")

        except Exception as e:
            print(f"❌ Error processing post for alerts: {e}")

    def _should_generate_alert(self, processed_post: ProcessedPost) -> bool:
        """Determine if processed post should trigger an alert"""
        priority = processed_post.priority_level
        analysis = processed_post.analysis

        # Only generate alerts for P0-P3 priority posts
        if priority not in ["P0", "P1", "P2", "P3"]:
            return False

        # Check minimum relevance threshold for priority level
        threshold_config = self.alert_thresholds.get(priority, {})
        min_relevance = threshold_config.get("min_relevance", 5.0)

        if analysis.relevance_score < min_relevance:
            return False

        # Only alert for actual disaster types (not 'none') - temporarily disabled for testing
        # if analysis.disaster_type == "none":
        #     return False

        # Additional filters for misinformation
        if processed_post.misinformation_analysis:
            # Don't alert for high misinformation risk
            if processed_post.misinformation_analysis.risk_level == "high_misinformation_risk":
                return False

        return True

    def _create_alert(self, processed_post: ProcessedPost) -> RealTimeAlert:
        """Create real-time alert from processed post"""
        priority = processed_post.priority_level
        severity = self.alert_thresholds.get(priority, {}).get("severity", "LOW")

        # Generate alert reason
        reasons = []
        if processed_post.analysis.urgency in ["critical", "high"]:
            reasons.append(f"{processed_post.analysis.urgency} urgency")
        if processed_post.analysis.relevance_score >= 8.0:
            reasons.append("high relevance")
        if processed_post.analysis.location_mentioned:
            reasons.append("location specific")
        if processed_post.original_post.user and processed_post.original_post.user.verified:
            reasons.append("verified source")

        alert_reason = ", ".join(reasons) if reasons else "disaster relevance"

        return RealTimeAlert(
            post=processed_post,
            alert_reason=alert_reason,
            severity=severity,
            triggered_at=datetime.now(timezone.utc),
            notification_sent=False
        )

    async def _process_alert_queue(self):
        """Background task to process queued alerts"""
        print("📡 Alert queue processor started")
        while self.processing_alerts:
            try:
                # Wait for alert with timeout
                alert = await asyncio.wait_for(self.alert_queue.get(), timeout=1.0)

                # Broadcast alert to connected clients
                await self.connection_manager.broadcast_alert(alert)
                alert.notification_sent = True

                # Mark task as done
                self.alert_queue.task_done()

            except asyncio.TimeoutError:
                # Continue loop if no alerts in queue
                continue
            except Exception as e:
                print(f"❌ Error processing alert queue: {e}")
                await asyncio.sleep(1)

        print("⏹️ Alert queue processor stopped")

    async def _heartbeat_sender(self):
        """Background task to send periodic heartbeats to WebSocket clients"""
        print("💓 Heartbeat sender starting...")
        while self.heartbeat_running:
            try:
                if len(self.connection_manager.active_connections) > 0:
                    await self.connection_manager.send_heartbeat_to_all()
                    print(f"💓 Heartbeat sent to {len(self.connection_manager.active_connections)} clients")

                await asyncio.sleep(10)  # Send heartbeat every 10 seconds

            except Exception as e:
                print(f"❌ Error in heartbeat sender: {e}")
                await asyncio.sleep(5)  # Wait before retrying

        print("💓 Heartbeat sender stopped")

    async def get_active_alerts_sse(self):
        """Server-Sent Events stream for active alerts"""
        async def event_stream():
            # Send initial connection message
            yield {
                "event": "connected",
                "data": json.dumps({
                    "message": "SSE connection established",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            }

            last_heartbeat = time.time()

            while True:
                try:
                    # Send heartbeat every 10 seconds (faster for demo)
                    current_time = time.time()
                    if current_time - last_heartbeat > 10:
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "status": "active",
                                "connections": len(self.connection_manager.active_connections)
                            })
                        }
                        last_heartbeat = current_time

                    # Check for alerts (non-blocking)
                    try:
                        alert = self.sse_alert_queue.get_nowait()

                        alert_data = {
                            "alert_id": alert.alert_id,
                            "severity": alert.severity,
                            "disaster_type": alert.post.analysis.disaster_type,
                            "location": alert.post.analysis.location_mentioned,
                            "text_preview": alert.post.original_post.text[:100] + "...",
                            "triggered_at": alert.triggered_at.isoformat(),
                            "priority": alert.post.priority_level
                        }

                        yield {
                            "event": "alert",
                            "data": json.dumps(alert_data)
                        }

                        self.sse_alert_queue.task_done()

                    except asyncio.QueueEmpty:
                        # Continue if no alerts
                        pass

                    await asyncio.sleep(0.5)  # Prevent busy waiting

                except Exception as e:
                    print(f"❌ SSE stream error: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }
                    break

        return EventSourceResponse(event_stream())


# Global instance
realtime_alerts = None

def get_realtime_alerts() -> BlueRadarRealtimeAlerts:
    """Get global realtime alerts instance"""
    global realtime_alerts
    return realtime_alerts

def initialize_realtime_alerts(analysis_service: BlueRadarAnalysisService):
    """Initialize global realtime alerts system"""
    global realtime_alerts
    if realtime_alerts is None:
        realtime_alerts = BlueRadarRealtimeAlerts(analysis_service)
    return realtime_alerts