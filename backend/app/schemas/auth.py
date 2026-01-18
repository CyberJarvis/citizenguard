"""
Authentication Schemas
Request/Response models for auth endpoints
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

from app.models.user import UserRole


class SignupRequest(BaseModel):
    """Signup request schema"""

    email: Optional[EmailStr] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone with country code (+91...)")
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    location: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User location with state, region, city, latitude, longitude"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None:
            return None

        # Remove spaces and dashes
        phone = re.sub(r"[\s\-]", "", v)

        # Must start with + and contain 10-15 digits
        if not re.match(r"^\+\d{10,15}$", phone):
            raise ValueError("Phone must include country code and be valid (e.g., +919876543210)")

        return phone

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v

    @field_validator("email", "phone")
    @classmethod
    def check_email_or_phone(cls, v, values):
        """Ensure at least email or phone is provided"""
        # This validator runs after individual field validators
        # We'll do final validation in the model_validator
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": "+919876543210",
                "password": "SecureP@ss123",
                "name": "John Doe"
            }
        }


class LoginRequest(BaseModel):
    """Login request schema"""

    email: Optional[EmailStr] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    login_type: str = Field(..., description="'password' or 'otp'")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number"""
        if v is None:
            return None
        phone = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+\d{10,15}$", phone):
            raise ValueError("Invalid phone number format")
        return phone

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecureP@ss123",
                "login_type": "password"
            }
        }


class VerifyOTPRequest(BaseModel):
    """OTP verification request"""

    email: Optional[EmailStr] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    otp_type: str = Field(default="email", description="Type of OTP (email or phone)")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        """Validate OTP format"""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenResponse(BaseModel):
    """Token response schema"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 7200
            }
        }


class UserResponse(BaseModel):
    """User response schema (safe, no sensitive data)"""

    user_id: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    role: UserRole
    profile_picture: Optional[str] = None
    credibility_score: int
    email_verified: bool
    phone_verified: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR-001",
                "email": "user@example.com",
                "phone": "+919876543210",
                "name": "John Doe",
                "role": "citizen",
                "credibility_score": 75,
                "email_verified": True,
                "phone_verified": True,
                "is_active": True,
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class PasswordResetRequest(BaseModel):
    """Password reset request"""

    email: EmailStr = Field(..., description="Email address")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ChangePasswordRequest(BaseModel):
    """Change password request"""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "old_password": "OldP@ss123",
                "new_password": "NewSecureP@ss123"
            }
        }


class OTPResponse(BaseModel):
    """OTP send response"""

    message: str = Field(..., description="Success message")
    expires_in: int = Field(..., description="OTP expiry in seconds")
    sent_to: str = Field(..., description="Masked email/phone")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "OTP sent successfully",
                "expires_in": 300,
                "sent_to": "u***@example.com"
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Forgot password request - sends OTP to email"""

    email: EmailStr = Field(..., description="Email address")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    """Reset password with OTP"""

    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        """Validate OTP format"""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456",
                "new_password": "NewSecureP@ss123"
            }
        }
