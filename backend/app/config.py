"""
Application Configuration
Loads and validates environment variables using Pydantic Settings
"""

import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "CoastGuardian"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Server - Use PORT from environment (Railway provides this)
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8000)

    @field_validator("PORT", mode="before")
    @classmethod
    def get_port(cls, v):
        """Get PORT from environment variable (Railway sets this dynamically)"""
        return int(os.environ.get("PORT", v or 8000))

    # Security - Use environment variables or generate defaults
    # WARNING: In production, always set these via environment variables!
    SECRET_KEY: str = Field(default="coastguardian-dev-secret-key-change-in-production-minimum-32-chars")
    JWT_SECRET_KEY: str = Field(default="coastguardian-jwt-secret-key-change-in-production-minimum-32-chars")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - Include all production URLs
    # Default includes localhost for development + common Vercel/Railway patterns
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://localhost:3000,https://coastguardians-production.up.railway.app,https://coastguardians-production-f8f7.up.railway.app"

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def parse_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins and add wildcard patterns"""
        origins = [origin.strip() for origin in v.split(",")]
        # Also allow any Vercel preview deployments
        return origins

    # MongoDB - Reads from .env locally or Railway environment variables
    MONGODB_URL: str = ""  # Set via environment variable
    MONGODB_DB_NAME: str = "CoastGuardian"
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_MAX_POOL_SIZE: int = 50

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_SSL: bool = False

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@CoastGuardian.in"
    SMTP_FROM_NAME: str = "CoastGuardian"
    SMTP_TLS: bool = True

    # SMS (Twilio) - Legacy
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # SMS (Fast2SMS) - Primary for India
    FAST2SMS_API_KEY: str = ""
    FAST2SMS_SENDER_ID: str = "CSTGRD"
    FAST2SMS_ROUTE: str = "dlt"  # DLT route for transactional SMS in India
    FAST2SMS_ENABLED: bool = False  # Set to True when configured

    # Web Push (VAPID) - For browser push notifications
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CONTACT_EMAIL: str = "admin@coastguardian.in"
    PUSH_NOTIFICATIONS_ENABLED: bool = False  # Set to True when VAPID keys are configured

    # Predictive Alerts
    PREDICTIVE_ALERT_CHECK_INTERVAL: int = 300  # 5 minutes
    PREDICTIVE_ALERTS_ENABLED: bool = True

    # OTP
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 3

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 3600
    RATE_LIMIT_MAX_REQUESTS_PER_WINDOW: int = 100
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Session
    SESSION_COOKIE_NAME: str = "CoastGuardian_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_MAX_AGE: int = 86400

    # Password Policy
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

    # Social Media Intelligence (SMI) Module - BlueRadar Integration
    SMI_ENABLED: bool = True
    SMI_BASE_URL: str = "ws://localhost:8765"  # BlueRadar WebSocket server
    SMI_TIMEOUT_SECONDS: int = 30
    SMI_ALERT_SYNC_INTERVAL_SECONDS: int = 30
    SMI_CRITICAL_ALERT_THRESHOLD: float = 7.0  # Relevance score threshold (0-10)
    SMI_AUTO_START_FEED: bool = True
    SMI_DEFAULT_POST_INTERVAL: int = 300  # 5 minutes between scrape cycles
    SMI_DEFAULT_DISASTER_PROBABILITY: float = 0.3  # Not used by BlueRadar

    # BlueRadar Intelligence Settings
    BLUERADAR_SCRAPE_INTERVAL: int = 300  # 5 minutes
    BLUERADAR_PLATFORMS: str = "twitter,youtube,news,instagram"
    BLUERADAR_MAX_POSTS_PER_PLATFORM: int = 10

    # VectorDB Module (FAISS-based hazard classification)
    VECTORDB_ENABLED: bool = True
    VECTORDB_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    VECTORDB_EMBED_DIM: int = 384
    VECTORDB_INDEX_PATH: str = "data/models/vectordb_index"
    VECTORDB_CLASSIFICATION_THRESHOLD: float = 0.6

    # MultiHazard Detection Module
    MULTIHAZARD_ENABLED: bool = True
    WEATHERAPI_KEY: str = ""  # Set via WEATHERAPI_KEY env variable
    
    MULTIHAZARD_MONITORING_INTERVAL_SECONDS: int = 300
    MULTIHAZARD_AUTO_START: bool = True
    TSUNAMI_MODEL_PATH: str = "data/models/tsunami_classifier.pkl"
    TSUNAMI_ML_THRESHOLD: float = 0.7

    # AWS S3 Storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "coastguardian-bucket"
    S3_ENABLED: bool = False  # Set to True when S3 is configured
    S3_PRESIGNED_URL_EXPIRY: int = 3600  # 1 hour for upload URLs

    @property
    def s3_base_url(self) -> str:
        """Construct S3 base URL for public access"""
        return f"https://{self.S3_BUCKET_NAME}.s3.{self.AWS_REGION}.amazonaws.com"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        protocol = "rediss" if self.REDIS_SSL else "redis"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# Global settings instance
settings = Settings()
