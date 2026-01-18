from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, EmailStr, validator
import re


class EmergencyContact(BaseModel):
    """Emergency contact model"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    relationship: Optional[str] = Field(None, max_length=50)


class ProfileUpdate(BaseModel):
    """Profile update request model"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="User's full name")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[Dict] = Field(None, description="User location (lat, lon, address)")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")
    emergency_contacts: Optional[List[EmergencyContact]] = Field(None, description="Emergency contacts for SOS alerts")

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None and v.strip():
            # Remove spaces and special characters
            cleaned = re.sub(r'[^\d+]', '', v)
            if len(cleaned) < 10:
                raise ValueError('Phone number must be at least 10 digits')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "phone": "+1234567890",
                "bio": "Ocean conservation enthusiast",
                "location": {
                    "lat": 13.0827,
                    "lon": 80.2707,
                    "address": "Chennai, India"
                }
            }
        }


class ProfileResponse(BaseModel):
    """Profile response model"""
    user_id: str
    email: Optional[str]
    phone: Optional[str]
    name: str
    role: str
    profile_picture: Optional[str]
    bio: Optional[str]
    location: Optional[Dict]
    credibility_score: int
    total_reports: int
    verified_reports: int
    email_verified: bool
    phone_verified: bool
    created_at: str
    emergency_contacts: Optional[List[Dict]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR-123",
                "email": "john@example.com",
                "phone": "+1234567890",
                "name": "John Doe",
                "role": "CITIZEN",
                "profile_picture": "/uploads/profiles/user123.jpg",
                "bio": "Ocean conservation enthusiast",
                "location": {
                    "lat": 13.0827,
                    "lon": 80.2707,
                    "address": "Chennai, India"
                },
                "credibility_score": 85,
                "total_reports": 15,
                "verified_reports": 12,
                "email_verified": True,
                "phone_verified": False,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class UserStats(BaseModel):
    """User statistics model"""
    total_reports: int = 0
    verified_reports: int = 0
    pending_reports: int = 0
    rejected_reports: int = 0
    credibility_score: int = 0
    total_likes: int = 0
    reports_by_type: Dict[str, int] = {}
    recent_activity: List[Dict] = []

    class Config:
        json_schema_extra = {
            "example": {
                "total_reports": 15,
                "verified_reports": 12,
                "pending_reports": 2,
                "rejected_reports": 1,
                "credibility_score": 85,
                "total_likes": 45,
                "reports_by_type": {
                    "HIGH_WAVES": 5,
                    "POLLUTION": 10
                },
                "recent_activity": [
                    {
                        "type": "report_submitted",
                        "date": "2025-01-15",
                        "description": "Reported high waves"
                    }
                ]
            }
        }


class PublicProfileResponse(BaseModel):
    """Public profile response (limited info for other users)"""
    user_id: str
    name: str
    role: str
    profile_picture: Optional[str]
    bio: Optional[str]
    credibility_score: int
    total_reports: int
    verified_reports: int
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR-123",
                "name": "John Doe",
                "role": "CITIZEN",
                "profile_picture": "/uploads/profiles/user123.jpg",
                "bio": "Ocean conservation enthusiast",
                "credibility_score": 85,
                "total_reports": 15,
                "verified_reports": 12,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }
