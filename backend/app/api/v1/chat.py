import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.chat import (
    ChatMessage,
    MessageResponse,
    MessagesResponse,
    OnlineUsersResponse,
    MessageType,
    WebSocketMessage
)
from app.models.user import User
from app.middleware.security import get_current_user, verify_token
from app.services.chat_manager import chat_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/messages", response_model=MessagesResponse)
async def get_messages(
    room_id: str = Query(default="general", description="Chat room ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Messages per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get paginated chat messages from a room

    - **room_id**: Chat room ID (default: "general")
    - **page**: Page number (starts at 1)
    - **page_size**: Number of messages per page (max 100)
    """
    try:
        # Calculate skip for pagination
        skip = (page - 1) * page_size

        # Get total count
        total = await db.chat_messages.count_documents({
            "room_id": room_id,
            "deleted": False
        })

        # Get messages sorted by timestamp (newest first)
        cursor = db.chat_messages.find(
            {"room_id": room_id, "deleted": False}
        ).sort("timestamp", -1).skip(skip).limit(page_size)

        messages = await cursor.to_list(length=page_size)

        # Reverse to show oldest first in response
        messages.reverse()

        # Convert to response format
        message_responses = []
        for msg in messages:
            # Ensure timestamp is timezone-aware UTC
            timestamp = msg["timestamp"]
            if timestamp.tzinfo is None:
                # If no timezone info, assume UTC
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            elif timestamp.tzinfo != timezone.utc:
                # Convert to UTC if different timezone
                timestamp = timestamp.astimezone(timezone.utc)
            
            message_responses.append(MessageResponse(
                message_id=msg["message_id"],
                room_id=msg["room_id"],
                user_id=msg["user_id"],
                user_name=msg["user_name"],
                user_role=msg["user_role"],
                profile_picture=msg.get("profile_picture"),
                message_type=msg["message_type"],
                content=msg["content"],
                timestamp=timestamp.isoformat().replace('+00:00', 'Z'),  # Ensure Z suffix for UTC
                edited=msg.get("edited", False)
            ))

        has_more = (skip + page_size) < total

        return MessagesResponse(
            messages=message_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.get("/online-users", response_model=OnlineUsersResponse)
async def get_online_users(
    room_id: str = Query(default="general", description="Chat room ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of currently online users in a chat room

    - **room_id**: Chat room ID (default: "general")
    """
    try:
        users = chat_manager.get_online_users(room_id)

        return OnlineUsersResponse(
            room_id=room_id,
            count=len(users),
            users=users
        )

    except Exception as e:
        logger.error(f"Error fetching online users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch online users")


@router.get("/rooms")
async def get_chat_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get available chat rooms

    Returns list of public chat rooms and private rooms the user is a member of
    """
    try:
        # For now, return only the general room
        # This can be extended to support multiple rooms
        rooms = [
            {
                "room_id": "general",
                "name": "General Discussion",
                "description": "Community-wide general chat for ocean safety discussions",
                "is_public": True,
                "online_count": chat_manager.get_connection_count("general")
            }
        ]

        return {"rooms": rooms}

    except Exception as e:
        logger.error(f"Error fetching chat rooms: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat rooms")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    room_id: str = Query(default="general", description="Chat room ID"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    WebSocket endpoint for real-time chat

    - **token**: JWT access token for authentication
    - **room_id**: Chat room to join (default: "general")

    Message format:
    ```json
    {
        "type": "message" | "typing",
        "content": "message content" (for type=message),
        "is_typing": true/false (for type=typing)
    }
    ```
    """
    # Track user info for cleanup
    user_id = None
    user_name = None
    user_role = None
    profile_picture = None
    is_connected = False

    try:
        # Verify JWT token
        try:
            payload = verify_token(token)
        except HTTPException as e:
            logger.error(f"Token verification failed: {e.detail}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            await websocket.close(code=1008, reason="Invalid token")
            return

        user_id = payload.get("sub")  # JWT standard field for user ID

        if not user_id:
            logger.error("No user_id in token payload")
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Get user from database
        user_doc = await db.users.find_one({"user_id": user_id})
        if not user_doc:
            logger.error(f"User not found in database: {user_id}")
            await websocket.close(code=1008, reason="User not found")
            return

        user_name = user_doc.get("name", "Unknown User")
        user_role = user_doc.get("role", "CITIZEN").upper()  # Ensure uppercase
        profile_picture = user_doc.get("profile_picture")  # Can be None

        logger.info(f"WebSocket authentication successful for user: {user_name} ({user_id})")

        # Connect to chat
        await chat_manager.connect(websocket, room_id, user_id, user_name, user_role, profile_picture)
        is_connected = True  # Mark as connected for proper cleanup

        # Listen for messages
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type", "message")

            if message_type == "message":
                # Handle chat message
                content = data.get("content", "").strip()

                if not content:
                    continue

                # Validate message length
                if len(content) > 2000:
                    await chat_manager.send_personal_message({
                        "type": "error",
                        "data": {"message": "Message too long (max 2000 characters)"}
                    }, websocket)
                    continue

                # Create message document
                message_id = f"msg_{secrets.token_urlsafe(16)}"
                timestamp = datetime.now(timezone.utc)

                message_doc = ChatMessage(
                    message_id=message_id,
                    room_id=room_id,
                    user_id=user_id,
                    user_name=user_name,
                    user_role=user_role,
                    profile_picture=profile_picture,
                    message_type=MessageType.TEXT,
                    content=content,
                    timestamp=timestamp,
                    edited=False,
                    deleted=False
                )

                # Save to database
                await db.chat_messages.insert_one(message_doc.model_dump())

                # Broadcast to all users in room
                await chat_manager.broadcast_to_room(
                    room_id=room_id,
                    message={
                        "type": "message",
                        "data": {
                            "message_id": message_id,
                            "room_id": room_id,
                            "user_id": user_id,
                            "user_name": user_name,
                            "user_role": user_role,
                            "profile_picture": profile_picture,
                            "content": content,
                            "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),  # Ensure Z suffix for UTC
                            "edited": False
                        }
                    }
                )

                logger.info(f"Message from {user_name} in {room_id}: {content[:50]}...")

            elif message_type == "typing":
                # Handle typing indicator
                is_typing = data.get("is_typing", False)
                await chat_manager.broadcast_typing(room_id, user_id, user_name, is_typing)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_name} ({user_id})")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_name} ({user_id}): {e}")
    finally:
        # Disconnect and broadcast leave notification only if we were connected
        if is_connected and user_id:
            try:
                chat_manager.disconnect(websocket, room_id, user_id, user_name)
                logger.info(f"Cleaned up connection for user {user_name} ({user_id})")
            except Exception as cleanup_error:
                logger.error(f"Error during disconnect cleanup: {cleanup_error}")


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a chat message (soft delete)

    Users can only delete their own messages unless they are ADMIN
    """
    try:
        # Find the message
        message = await db.chat_messages.find_one({"message_id": message_id})

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Check permissions
        if message["user_id"] != current_user.user_id and current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Not authorized to delete this message")

        # Soft delete
        await db.chat_messages.update_one(
            {"message_id": message_id},
            {"$set": {"deleted": True}}
        )

        # Broadcast deletion to room
        await chat_manager.broadcast_to_room(
            room_id=message["room_id"],
            message={
                "type": "message_deleted",
                "data": {
                    "message_id": message_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
        )

        return {"success": True, "message": "Message deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete message")
