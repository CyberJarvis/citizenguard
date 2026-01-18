"""
Authentication Endpoints
Complete authentication flow with OTP, password, and OAuth
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.config import settings
from app.database import get_database, get_redis
from app.models.user import User, UserRole, AuthProvider, RefreshToken
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    VerifyOTPRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    OTPResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token, create_refresh_token, verify_token
from app.utils.security import generate_user_id, hash_token, mask_email, mask_phone
from app.utils.audit import AuditLogger
from app.services.otp import OTPService
from app.services.email import EmailService
from app.services.sms import SMSService
from app.services.oauth import OAuthService
from app.middleware.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    signup_data: SignupRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register a new user account

    - Validates email/phone uniqueness
    - Creates user with hashed password
    - Returns user profile
    """

    # Validate that either email or phone is provided
    if not signup_data.email and not signup_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone number is required"
        )

    # Check if user already exists
    query = {"$or": []}
    if signup_data.email:
        query["$or"].append({"email": signup_data.email})
    if signup_data.phone:
        query["$or"].append({"phone": signup_data.phone})

    existing_user = await db.users.find_one(query)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or phone already exists"
        )

    # Hash password
    hashed_pwd = hash_password(signup_data.password)

    # Generate user ID
    user_id = generate_user_id()

    # Generate OTP for email verification
    from app.utils.security import generate_otp
    otp = generate_otp(settings.OTP_LENGTH)
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # Create user (inactive until email is verified)
    user = User(
        user_id=user_id,
        email=signup_data.email,
        phone=signup_data.phone,
        hashed_password=hashed_pwd,
        name=signup_data.name,
        location=signup_data.location,  # Save location data for alert notifications
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.CITIZEN,
        email_verified=False if signup_data.email else True,
        phone_verified=False if signup_data.phone else True,
        is_active=False,  # User must verify email first
        pending_otp=otp,
        pending_otp_expires_at=otp_expires_at,
        pending_otp_type="email",
        pending_otp_attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Save to database
    await db.users.insert_one(user.to_mongo())

    # Log signup
    await AuditLogger.log_signup(
        db=db,
        user_id=user_id,
        identifier=signup_data.email or signup_data.phone,
        request=request
    )

    # Send OTP email for verification
    if signup_data.email:
        await EmailService.send_otp_email(signup_data.email, otp)

    logger.info(f"New user signed up: {user_id} - OTP sent for verification")

    # Return success response with message
    return {
        "message": "Account created successfully. Please check your email for the OTP verification code.",
        "email": signup_data.email,
        "user_id": user_id,
        "requires_verification": True
    }


@router.post("/login", response_model=TokenResponse | OTPResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    redis: Optional[Redis] = Depends(get_redis)
):
    """
    Login with email/phone

    - **Password-based**: Returns JWT tokens immediately
    - **OTP-based**: Sends OTP and returns success message
    """

    identifier = login_data.email or login_data.phone

    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone is required"
        )

    # Find user
    query = {}
    if login_data.email:
        query["email"] = login_data.email
    elif login_data.phone:
        query["phone"] = login_data.phone

    user_data = await db.users.find_one(query)

    if not user_data:
        await AuditLogger.log_login_attempt(
            db=db,
            identifier=identifier,
            success=False,
            request=request,
            error="User not found"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    user = User.from_mongo(user_data)

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is banned: {user.ban_reason or 'No reason provided'}"
        )

    # Password-based login
    if login_data.login_type == "password":
        if not login_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )

        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password login not available for this account"
            )

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            await AuditLogger.log_login_attempt(
                db=db,
                identifier=identifier,
                success=False,
                request=request,
                user_id=user.user_id,
                error="Invalid password"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Generate tokens
        access_token = create_access_token(user.user_id, user.role.value)
        refresh_token_str, token_id, expiry = create_refresh_token(user.user_id)

        # Store refresh token
        refresh_token = RefreshToken(
            token_id=token_id,
            user_id=user.user_id,
            token_hash=hash_token(refresh_token_str),
            ip_address=request.client.host if request.client else None,
            device_info={"user_agent": request.headers.get("User-Agent")},
            expires_at=expiry
        )
        await db.refresh_tokens.insert_one(refresh_token.to_mongo())

        # Update last login
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )

        # Log successful login
        await AuditLogger.log_login_attempt(
            db=db,
            identifier=identifier,
            success=True,
            request=request,
            user_id=user.user_id
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    # OTP-based login
    elif login_data.login_type == "otp":
        # Check if Redis is available (required for OTP)
        if not redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OTP login is temporarily unavailable (Redis not connected). Please use password login."
            )

        # Check rate limit
        is_allowed, remaining_time = await OTPService.check_rate_limit(
            redis=redis,
            identifier=identifier,
            otp_type="login"
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many OTP requests. Try again in {remaining_time} seconds."
            )

        # Generate OTP
        otp = await OTPService.generate_and_store(
            redis=redis,
            identifier=identifier,
            otp_type="login"
        )

        # Send OTP
        channel = "email" if login_data.email else "sms"

        if login_data.email:
            await EmailService.send_otp_email(login_data.email, otp)
            masked = mask_email(login_data.email)
        else:
            await SMSService.send_otp_sms(login_data.phone, otp)
            masked = mask_phone(login_data.phone)

        # Log OTP sent
        await AuditLogger.log_otp_sent(
            db=db,
            identifier=identifier,
            channel=channel,
            request=request
        )

        return OTPResponse(
            message="OTP sent successfully",
            expires_in=settings.OTP_EXPIRE_MINUTES * 60,
            sent_to=masked
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login type. Must be 'password' or 'otp'"
        )


@router.post("/verify-otp")
async def verify_otp(
    request: Request,
    otp_data: VerifyOTPRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    redis: Optional[Redis] = Depends(get_redis)
):
    """
    Verify OTP for email/phone verification

    - Verifies OTP from MongoDB (or Redis if available)
    - Activates user account after successful verification
    - Returns success message (user must login after verification)
    """

    identifier = otp_data.email or otp_data.phone

    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone is required"
        )

    # Find user
    query = {}
    if otp_data.email:
        query["email"] = otp_data.email
    elif otp_data.phone:
        query["phone"] = otp_data.phone

    user_data = await db.users.find_one(query)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user = User.from_mongo(user_data)

    # Try Redis first if available, otherwise use MongoDB OTP
    is_valid = False
    use_redis = False

    if redis:
        try:
            # Verify OTP from Redis
            is_valid = await OTPService.verify(
                redis=redis,
                identifier=identifier,
                otp=otp_data.otp,
                otp_type=otp_data.otp_type
            )
            use_redis = True

            if not is_valid:
                remaining_attempts = await OTPService.get_remaining_attempts(
                    redis=redis,
                    identifier=identifier,
                    otp_type=otp_data.otp_type
                )

                await AuditLogger.log_otp_verified(
                    db=db,
                    user_id=user.user_id,
                    identifier=identifier,
                    request=request,
                    success=False
                )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
                )
        except Exception as redis_error:
            logger.warning(f"Redis error, falling back to MongoDB: {redis_error}")
            use_redis = False

    if not use_redis:
        # Verify OTP from MongoDB (fallback)
        if not user.pending_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending OTP found. Please request a new OTP."
            )

        # Check if OTP expired
        if user.pending_otp_expires_at:
            # Ensure the expiry datetime is timezone-aware for comparison
            expires_at = user.pending_otp_expires_at
            if expires_at.tzinfo is None:
                # If timezone-naive, assume it's UTC (MongoDB stores datetimes as UTC)
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP has expired. Please request a new one."
                )

        # Check max attempts
        if user.pending_otp_attempts >= settings.OTP_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invalid attempts. Please request a new OTP."
            )

        # Verify OTP
        if user.pending_otp != otp_data.otp:
            # Increment attempts
            await db.users.update_one(
                {"user_id": user.user_id},
                {"$inc": {"pending_otp_attempts": 1}}
            )

            remaining = settings.OTP_MAX_ATTEMPTS - (user.pending_otp_attempts + 1)

            await AuditLogger.log_otp_verified(
                db=db,
                user_id=user.user_id,
                identifier=identifier,
                request=request,
                success=False
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid OTP. {remaining} attempts remaining."
            )

        is_valid = True

    # OTP is valid - activate account and mark as verified
    update_fields = {
        "is_active": True,
        "updated_at": datetime.now(timezone.utc),
        "pending_otp": None,
        "pending_otp_expires_at": None,
        "pending_otp_type": None,
        "pending_otp_attempts": 0
    }

    if otp_data.email:
        update_fields["email_verified"] = True
    elif otp_data.phone:
        update_fields["phone_verified"] = True

    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": update_fields}
    )

    # Send welcome email after successful verification
    if otp_data.email:
        await EmailService.send_welcome_email(otp_data.email, user.name or "User")

    # Log successful verification
    await AuditLogger.log_otp_verified(
        db=db,
        user_id=user.user_id,
        identifier=identifier,
        request=request,
        success=True
    )

    logger.info(f"User {user.user_id} verified successfully - account activated")

    return {
        "message": "Email verified successfully! Your account is now active. You can now sign in.",
        "email_verified": True,
        "account_active": True
    }


@router.post("/request-otp")
async def request_otp(
    request: Request,
    otp_request: dict,
    db: AsyncIOMotorDatabase = Depends(get_database),
    redis: Optional[Redis] = Depends(get_redis)
):
    """
    Request/Resend OTP for email or phone verification

    - Generates new OTP
    - Sends via email or SMS
    - Rate-limited to prevent abuse
    """

    email = otp_request.get("email")
    phone = otp_request.get("phone")
    otp_type = otp_request.get("otp_type", "email")

    identifier = email or phone

    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone is required"
        )

    # Find user
    query = {}
    if email:
        query["email"] = email
    elif phone:
        query["phone"] = phone

    user_data = await db.users.find_one(query)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user = User.from_mongo(user_data)

    # Check if user is already verified
    if email and user.email_verified and user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )

    # Generate new OTP
    from app.utils.security import generate_otp
    otp = generate_otp(settings.OTP_LENGTH)
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # Store OTP (Redis if available, otherwise MongoDB)
    if redis:
        await OTPService.generate_and_store(
            redis=redis,
            identifier=identifier,
            otp_type=otp_type
        )
    else:
        # Store in MongoDB
        await db.users.update_one(
            {"user_id": user.user_id},
            {
                "$set": {
                    "pending_otp": otp,
                    "pending_otp_expires_at": otp_expires_at,
                    "pending_otp_type": otp_type,
                    "pending_otp_attempts": 0
                }
            }
        )

    # Send OTP via email or SMS
    if email:
        await EmailService.send_otp_email(email, otp)
        logger.info(f"OTP sent to email: {mask_email(email)}")
    elif phone:
        await SMSService.send_otp_sms(phone, otp)
        logger.info(f"OTP sent to phone: {mask_phone(phone)}")

    return {
        "message": f"OTP sent successfully to your {otp_type}",
        "expires_in_minutes": settings.OTP_EXPIRE_MINUTES
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Refresh access token using refresh token

    - Validates refresh token
    - Checks if token is revoked
    - Returns new access token
    """

    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, expected_type="refresh")

        user_id = payload.get("sub")
        token_id = payload.get("jti")

        if not user_id or not token_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Check if token exists and is not revoked
        token_hash = hash_token(token_data.refresh_token)
        stored_token = await db.refresh_tokens.find_one({
            "token_id": token_id,
            "token_hash": token_hash
        })

        if not stored_token:
            await AuditLogger.log_token_refresh(
                db=db,
                user_id=user_id,
                request=request,
                success=False,
                error="Token not found"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        stored_token_obj = RefreshToken.from_mongo(stored_token) if stored_token else None

        if stored_token_obj and stored_token_obj.is_revoked:
            await AuditLogger.log_token_refresh(
                db=db,
                user_id=user_id,
                request=request,
                success=False,
                error="Token revoked"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        # Get user
        user_data = await db.users.find_one({"user_id": user_id})
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = User.from_mongo(user_data)

        # Generate new access token
        access_token = create_access_token(user.user_id, user.role.value)

        # Log successful refresh
        await AuditLogger.log_token_refresh(
            db=db,
            user_id=user_id,
            request=request,
            success=True
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=token_data.refresh_token,  # Return same refresh token
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    request: Request,
    token_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Logout and revoke refresh token

    - Marks refresh token as revoked
    - Prevents token reuse
    """

    try:
        # Decode refresh token
        payload = verify_token(token_data.refresh_token, expected_type="refresh")
        token_id = payload.get("jti")

        if token_id:
            # Revoke token
            await db.refresh_tokens.update_one(
                {"token_id": token_id, "user_id": current_user.user_id},
                {"$set": {"is_revoked": True}}
            )

        # Log logout
        await AuditLogger.log_logout(
            db=db,
            user_id=current_user.user_id,
            request=request
        )

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return {"message": "Logged out successfully"}  # Always return success


@router.get("/google/login")
async def google_oauth_login(request: Request):
    """
    Initiate Google OAuth2 login

    - Returns Google authorization URL for frontend to redirect
    """

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )

    # Generate state for CSRF protection (frontend should store and validate)
    import secrets
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={state}"
    )

    return {"authorization_url": auth_url, "state": state}


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Google OAuth2 callback

    - Exchanges code for tokens
    - Creates or updates user
    - Returns JWT tokens as JSON
    """

    try:
        # Exchange code for tokens
        token_response = await OAuthService.exchange_code_for_token(
            code=code,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        access_token = token_response.get("access_token")
        id_token = token_response.get("id_token")

        # Get user info
        user_info = await OAuthService.get_google_user_info(access_token)

        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")
        google_id = user_info.get("id")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )

        # Find or create user
        user_data = await db.users.find_one({"email": email})

        is_new_user = False

        if not user_data:
            # Create new user
            is_new_user = True
            user_id = generate_user_id()

            user = User(
                user_id=user_id,
                email=email,
                name=name,
                profile_picture=picture,
                auth_provider=AuthProvider.GOOGLE,
                provider_id=google_id,
                email_verified=True,  # Google emails are verified
                role=UserRole.CITIZEN,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc)
            )

            await db.users.insert_one(user.to_mongo())
        else:
            # Handle existing user - check if user_id exists
            if "user_id" not in user_data or not user_data.get("user_id"):
                # Old user without user_id - add it
                user_id = generate_user_id()
                user_data["user_id"] = user_id
                await db.users.update_one(
                    {"_id": user_data["_id"]},
                    {"$set": {"user_id": user_id}}
                )
                logger.info(f"Added user_id to existing user: {email}")

            # Load user from database
            user = User.from_mongo(user_data)

            # Update user info
            await db.users.update_one(
                {"user_id": user.user_id},
                {"$set": {
                    "last_login": datetime.now(timezone.utc),
                    "profile_picture": picture
                }}
            )

        # Generate JWT tokens
        access_token_jwt = create_access_token(user.user_id, user.role.value)
        refresh_token_str, token_id, expiry = create_refresh_token(user.user_id)

        # Store refresh token
        refresh_token = RefreshToken(
            token_id=token_id,
            user_id=user.user_id,
            token_hash=hash_token(refresh_token_str),
            ip_address=request.client.host if request.client else None,
            device_info={"user_agent": request.headers.get("User-Agent")},
            expires_at=expiry
        )
        await db.refresh_tokens.insert_one(refresh_token.to_mongo())

        # Log OAuth login
        await AuditLogger.log_oauth_login(
            db=db,
            user_id=user.user_id,
            provider="google",
            request=request,
            is_new_user=is_new_user
        )

        # Return tokens as JSON (for frontend-driven OAuth flow)
        return {
            "access_token": access_token_jwt,
            "refresh_token": refresh_token_str,
            "user": user.dict(),  # User.dict() already excludes sensitive fields
            "is_new_user": is_new_user
        }

    except Exception as e:
        logger.error(f"Google OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user profile

    - Requires authentication
    - Returns user details
    """
    return UserResponse(**current_user.dict())


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Change user password

    - Verifies old password
    - Updates to new password
    """

    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change not available for OAuth users"
        )

    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        await AuditLogger.log_password_change(
            db=db,
            user_id=current_user.user_id,
            request=request,
            success=False,
            error="Invalid old password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid old password"
        )

    # Hash new password
    new_hashed = hash_password(password_data.new_password)

    # Update password
    await db.users.update_one(
        {"user_id": current_user.user_id},
        {"$set": {
            "hashed_password": new_hashed,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    # Revoke all refresh tokens (force re-login)
    await db.refresh_tokens.update_many(
        {"user_id": current_user.user_id},
        {"$set": {"is_revoked": True}}
    )

    # Log password change
    await AuditLogger.log_password_change(
        db=db,
        user_id=current_user.user_id,
        request=request,
        success=True
    )

    return {"message": "Password changed successfully. Please login again."}


@router.post("/forgot-password", response_model=OTPResponse)
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Request password reset - sends OTP to email

    - Finds user by email
    - Generates and stores OTP
    - Sends OTP via email
    - Works even if user doesn't exist (security: don't reveal user existence)
    """

    email = forgot_data.email

    # Find user by email
    user_data = await db.users.find_one({"email": email})

    # Security: Always return success message even if user doesn't exist
    # This prevents user enumeration attacks
    if not user_data:
        # Return success but don't actually send email
        logger.warning(f"Password reset requested for non-existent email: {mask_email(email)}")
        return OTPResponse(
            message="If an account exists with this email, you will receive a password reset OTP.",
            expires_in=settings.OTP_EXPIRE_MINUTES * 60,
            sent_to=mask_email(email)
        )

    user = User.from_mongo(user_data)

    # Check if user is active
    if not user.is_active:
        # Return success but don't send email to inactive accounts
        logger.warning(f"Password reset requested for inactive account: {user.user_id}")
        return OTPResponse(
            message="If an account exists with this email, you will receive a password reset OTP.",
            expires_in=settings.OTP_EXPIRE_MINUTES * 60,
            sent_to=mask_email(email)
        )

    # Generate OTP
    from app.utils.security import generate_otp
    otp = generate_otp(settings.OTP_LENGTH)
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # Store OTP in user document
    await db.users.update_one(
        {"user_id": user.user_id},
        {
            "$set": {
                "pending_otp": otp,
                "pending_otp_expires_at": otp_expires_at,
                "pending_otp_type": "password_reset",
                "pending_otp_attempts": 0,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    # Send password reset OTP email
    await EmailService.send_password_reset_otp_email(email, otp)

    # Log password reset request
    await AuditLogger.log(
        db=db,
        action="password_reset_requested",
        user_id=user.user_id,
        details={"email": mask_email(email)},
        request=request,
        success=True
    )

    logger.info(f"Password reset OTP sent to: {mask_email(email)}")

    return OTPResponse(
        message="If an account exists with this email, you will receive a password reset OTP.",
        expires_in=settings.OTP_EXPIRE_MINUTES * 60,
        sent_to=mask_email(email)
    )


@router.post("/reset-password")
async def reset_password(
    request: Request,
    reset_data: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reset password using OTP

    - Verifies OTP
    - Updates password
    - Revokes all refresh tokens (force re-login)
    - Clears pending OTP
    """

    email = reset_data.email
    otp = reset_data.otp
    new_password = reset_data.new_password

    # Find user
    user_data = await db.users.find_one({"email": email})

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user = User.from_mongo(user_data)

    # Check if user has pending OTP
    if not user.pending_otp or user.pending_otp_type != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password reset OTP found. Please request a new one."
        )

    # Check if OTP expired
    if user.pending_otp_expires_at:
        # Ensure the expiry datetime is timezone-aware for comparison
        expires_at = user.pending_otp_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )

    # Check max attempts
    if user.pending_otp_attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many invalid attempts. Please request a new OTP."
        )

    # Verify OTP
    if user.pending_otp != otp:
        # Increment attempts
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$inc": {"pending_otp_attempts": 1}}
        )

        remaining = settings.OTP_MAX_ATTEMPTS - (user.pending_otp_attempts + 1)

        await AuditLogger.log(
            db=db,
            action="password_reset_failed",
            user_id=user.user_id,
            details={"reason": "invalid_otp"},
            request=request,
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OTP. {remaining} attempts remaining."
        )

    # OTP is valid - hash new password
    hashed_password = hash_password(new_password)

    # Log before update for debugging
    logger.info(f"Updating password for user: {user.user_id}")

    # Update password and clear OTP
    update_result = await db.users.update_one(
        {"user_id": user.user_id},
        {
            "$set": {
                "hashed_password": hashed_password,
                "pending_otp": None,
                "pending_otp_expires_at": None,
                "pending_otp_type": None,
                "pending_otp_attempts": 0,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    # Verify the update was successful
    if update_result.modified_count == 0:
        logger.error(f"Failed to update password for user: {user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password. Please try again."
        )

    # Verify the password was actually updated by fetching the user again
    updated_user_data = await db.users.find_one({"user_id": user.user_id})
    if updated_user_data:
        updated_user = User.from_mongo(updated_user_data)
        # Verify new password works
        if not verify_password(new_password, updated_user.hashed_password):
            logger.error(f"Password verification failed after update for user: {user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password update verification failed. Please try again."
            )
        logger.info(f"Password updated and verified for user: {user.user_id}")
    else:
        logger.error(f"User not found after update: {user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User verification failed. Please try again."
        )

    # Revoke all refresh tokens (force re-login)
    await db.refresh_tokens.update_many(
        {"user_id": user.user_id},
        {"$set": {"is_revoked": True}}
    )

    # Log successful password reset
    await AuditLogger.log(
        db=db,
        action="password_reset_success",
        user_id=user.user_id,
        details={"email": mask_email(email)},
        request=request,
        success=True
    )

    logger.info(f"Password reset successful for user: {user.user_id}")

    return {
        "message": "Password reset successfully! You can now login with your new password.",
        "success": True
    }
