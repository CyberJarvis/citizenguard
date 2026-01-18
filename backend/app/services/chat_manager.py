import json
import logging
from typing import Dict, Set
from datetime import datetime, timezone
from fastapi import WebSocket
from app.models.chat import UserPresence

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""

    def __init__(self):
        # Dictionary of room_id -> set of (websocket, user_info) tuples
        self.active_connections: Dict[str, Set[tuple]] = {}
        # Dictionary of user_id -> UserPresence
        self.user_presence: Dict[str, UserPresence] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str, user_role: str, profile_picture: str = None):
        """Accept WebSocket connection and add to room"""
        await websocket.accept()

        # Initialize room if it doesn't exist
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()

        # Check if user is already connected to this room
        existing_connections = []
        for ws, user_info_str in self.active_connections[room_id]:
            user_info = json.loads(user_info_str)
            if user_info.get("user_id") == user_id:
                existing_connections.append((ws, user_info_str))

        # Remove existing connections for the same user (handle reconnection)
        # Don't await the close to avoid race conditions - just remove from tracking
        for existing_conn in existing_connections:
            try:
                existing_ws, existing_info = existing_conn
                self.active_connections[room_id].discard(existing_conn)
                # Close asynchronously without waiting - fire and forget
                try:
                    await existing_ws.close(code=1000, reason="User reconnected from another session")
                except Exception:
                    pass  # Connection may already be closed
                logger.info(f"Closed existing connection for user {user_name} ({user_id})")
            except Exception as e:
                logger.warning(f"Error handling existing connection: {e}")

        # Add new connection with user info
        user_info = {
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "profile_picture": profile_picture
        }
        self.active_connections[room_id].add((websocket, json.dumps(user_info)))

        # Update user presence
        self.user_presence[user_id] = UserPresence(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            room_id=room_id,
            joined_at=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )

        logger.info(f"User {user_name} ({user_id}) connected to room {room_id}")

        # Only broadcast join notification if this user wasn't already in the room
        was_user_present = len(existing_connections) > 0
        
        if not was_user_present:
            # Broadcast join notification only for truly new users to OTHER users (not the joiner)
            await self.broadcast_to_room(
                room_id=room_id,
                message={
                    "type": "join",
                    "data": {
                        "user_id": user_id,
                        "user_name": user_name,
                        "user_role": user_role,
                        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                        "message": f"{user_name} joined the chat"
                    }
                },
                exclude_ws=websocket  # Don't send join message to the user who just joined
            )

        # Send online users list to new user
        await self.send_online_users(websocket, room_id)

    def disconnect(self, websocket: WebSocket, room_id: str, user_id: str = None, user_name: str = None):
        """Remove WebSocket connection from room"""
        if room_id not in self.active_connections:
            return

        # Find and remove the connection
        to_remove = None
        user_role = None

        for conn, user_info_str in self.active_connections[room_id]:
            if conn == websocket:
                to_remove = (conn, user_info_str)
                user_info = json.loads(user_info_str)
                # Always get user info from the stored data for consistency
                if not user_id:
                    user_id = user_info.get("user_id")
                if not user_name:
                    user_name = user_info.get("user_name")
                user_role = user_info.get("user_role")
                break

        if not to_remove:
            return

        try:
            self.active_connections[room_id].remove(to_remove)
        except KeyError:
            pass  # Already removed

        logger.info(f"User {user_name} ({user_id}) disconnected from room {room_id}")

        # Remove from presence if exists
        if user_id and user_id in self.user_presence:
            del self.user_presence[user_id]

        # Check if user still has other connections in this room
        user_still_present = False
        if room_id in self.active_connections:
            for ws, user_info_str in self.active_connections[room_id]:
                user_info = json.loads(user_info_str)
                if user_info.get("user_id") == user_id:
                    user_still_present = True
                    break

        # Only broadcast leave message if user has no more connections
        if not user_still_present and user_name and user_id:
            import asyncio
            try:
                asyncio.create_task(self.broadcast_to_room(
                    room_id=room_id,
                    message={
                        "type": "leave",
                        "data": {
                            "user_id": user_id,
                            "user_name": user_name,
                            "user_role": user_role or "CITIZEN",
                            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                            "message": f"{user_name} left the chat"
                        }
                    }
                ))
            except Exception as e:
                logger.warning(f"Error sending leave notification: {e}")

        # Clean up empty rooms
        if room_id in self.active_connections and not self.active_connections[room_id]:
            del self.active_connections[room_id]
            logger.info(f"Room {room_id} removed (no active connections)")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_room(self, room_id: str, message: dict, exclude_ws: WebSocket = None):
        """Broadcast message to all connections in a room"""
        if room_id not in self.active_connections:
            logger.warning(f"Attempted to broadcast to non-existent room: {room_id}")
            return

        # Create a copy of connections to avoid modification during iteration
        connections = list(self.active_connections[room_id])
        disconnected = []

        for websocket, user_info_str in connections:
            # Skip excluded websocket if specified
            if exclude_ws and websocket == exclude_ws:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.append((websocket, user_info_str))

        # Clean up disconnected websockets
        for ws, user_info_str in disconnected:
            user_info = json.loads(user_info_str)
            self.disconnect(ws, room_id, user_info.get("user_id"), user_info.get("user_name"))

    async def send_online_users(self, websocket: WebSocket, room_id: str):
        """Send list of online users to a specific connection"""
        online_users = self.get_online_users(room_id)
        await self.send_personal_message({
            "type": "online_users",
            "data": {
                "room_id": room_id,
                "count": len(online_users),
                "users": online_users
            }
        }, websocket)

    def get_online_users(self, room_id: str) -> list:
        """Get list of online users in a room"""
        if room_id not in self.active_connections:
            return []

        users = []
        seen_user_ids = set()

        for websocket, user_info_str in self.active_connections[room_id]:
            user_info = json.loads(user_info_str)
            user_id = user_info.get("user_id")

            # Avoid duplicates (same user with multiple connections)
            if user_id not in seen_user_ids:
                seen_user_ids.add(user_id)
                users.append({
                    "user_id": user_info.get("user_id"),
                    "user_name": user_info.get("user_name"),
                    "user_role": user_info.get("user_role"),
                    "profile_picture": user_info.get("profile_picture")
                })

        return users

    def get_connection_count(self, room_id: str) -> int:
        """Get number of active connections in a room"""
        if room_id not in self.active_connections:
            return 0
        return len(self.active_connections[room_id])

    async def broadcast_typing(self, room_id: str, user_id: str, user_name: str, is_typing: bool):
        """Broadcast typing indicator"""
        await self.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "typing",
                "data": {
                    "user_id": user_id,
                    "user_name": user_name,
                    "is_typing": is_typing,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            }
        )


# Global singleton instance
chat_manager = ConnectionManager()
