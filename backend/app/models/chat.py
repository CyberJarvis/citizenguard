from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """Message type enumeration"""
    TEXT = "text"
    SYSTEM = "system"
    JOIN = "join"
    LEAVE = "leave"


class ChatMessage(BaseModel):
    """Chat message model for MongoDB"""
    message_id: str = Field(..., description="Unique message ID")
    room_id: str = Field(default="general", description="Chat room ID")
    user_id: str = Field(..., description="User ID who sent the message")
    user_name: str = Field(..., description="User display name")
    user_role: str = Field(default="CITIZEN", description="User role")
    profile_picture: Optional[str] = Field(None, description="User profile picture URL")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Message type")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    edited: bool = Field(default=False, description="Whether message was edited")
    edited_at: Optional[datetime] = Field(None, description="Edit timestamp")
    deleted: bool = Field(default=False, description="Soft delete flag")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123",
                "room_id": "general",
                "user_id": "user_123",
                "user_name": "John Doe",
                "user_role": "CITIZEN",
                "message_type": "text",
                "content": "Hello everyone!",
                "timestamp": "2025-01-15T10:30:00Z",
                "edited": False,
                "deleted": False
            }
        }


class ChatRoom(BaseModel):
    """Chat room model"""
    room_id: str = Field(..., description="Unique room ID")
    name: str = Field(..., description="Room name")
    description: Optional[str] = Field(None, description="Room description")
    created_by: str = Field(..., description="User ID who created the room")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    is_public: bool = Field(default=True, description="Public or private room")
    members: List[str] = Field(default_factory=list, description="List of member user IDs")
    active: bool = Field(default=True, description="Room active status")

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "general",
                "name": "General Discussion",
                "description": "Community-wide general chat",
                "created_by": "admin_123",
                "created_at": "2025-01-01T00:00:00Z",
                "is_public": True,
                "members": [],
                "active": True
            }
        }


class MessageCreate(BaseModel):
    """Request model for creating a message"""
    room_id: str = Field(default="general", description="Room ID")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Message type")


class MessageResponse(BaseModel):
    """Response model for a chat message"""
    message_id: str
    room_id: str
    user_id: str
    user_name: str
    user_role: str
    profile_picture: Optional[str] = None
    message_type: str
    content: str
    timestamp: str
    edited: bool

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123",
                "room_id": "general",
                "user_id": "user_123",
                "user_name": "John Doe",
                "user_role": "CITIZEN",
                "message_type": "text",
                "content": "Hello everyone!",
                "timestamp": "2025-01-15T10:30:00Z",
                "edited": False
            }
        }


class UserPresence(BaseModel):
    """User presence in chat"""
    user_id: str
    user_name: str
    user_role: str
    room_id: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class OnlineUsersResponse(BaseModel):
    """Response model for online users"""
    room_id: str
    count: int
    users: List[dict]

    class Config:
        json_schema_extra = {
            "example": {
                "room_id": "general",
                "count": 3,
                "users": [
                    {"user_id": "user_1", "user_name": "Alice", "user_role": "CITIZEN"},
                    {"user_id": "user_2", "user_name": "Bob", "user_role": "ANALYST"}
                ]
            }
        }


class MessagesResponse(BaseModel):
    """Response model for message list"""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [],
                "total": 150,
                "page": 1,
                "page_size": 50,
                "has_more": True
            }
        }


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(..., description="Message type: message, join, leave, typing, error")
    data: dict = Field(..., description="Message payload")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "message",
                "data": {
                    "message_id": "msg_123",
                    "user_name": "John",
                    "content": "Hello!",
                    "timestamp": "2025-01-15T10:30:00Z"
                }
            }
        }
