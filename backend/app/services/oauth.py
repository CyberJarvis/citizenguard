"""
OAuth Service
Google OAuth2 authentication
"""

import logging
from typing import Dict, Any, Optional
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth authentication service"""

    _oauth_client: Optional[OAuth] = None

    @classmethod
    def get_oauth_client(cls) -> OAuth:
        """Get or create OAuth client"""
        if not cls._oauth_client:
            cls._oauth_client = OAuth()

            # Register Google OAuth
            if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
                cls._oauth_client.register(
                    name="google",
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET,
                    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                    client_kwargs={"scope": "openid email profile"}
                )

        return cls._oauth_client

    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, Any]:
        """
        Get user info from Google using access token

        Args:
            access_token: Google access token

        Returns:
            User info dictionary

        Raises:
            HTTPException: If request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to fetch user info from Google"
                    )

                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Google user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user info from Google"
            )

    @staticmethod
    async def verify_google_token(id_token: str) -> Dict[str, Any]:
        """
        Verify Google ID token

        Args:
            id_token: Google ID token

        Returns:
            Token payload

        Raises:
            HTTPException: If token is invalid
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
                )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Google token"
                    )

                token_data = response.json()

                # Verify audience (client ID)
                if token_data.get("aud") != settings.GOOGLE_CLIENT_ID:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token audience"
                    )

                return token_data

        except httpx.HTTPError as e:
            logger.error(f"Failed to verify Google token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify Google token"
            )

    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Token response dictionary

        Raises:
            HTTPException: If exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code"
                    },
                    timeout=30.0
                )

                if response.status_code != 200:
                    # Try to parse error response from Google
                    try:
                        error_data = response.json() if 'application/json' in response.headers.get('content-type', '') else {}
                    except (ValueError, KeyError, Exception):
                        error_data = {}

                    error_type = error_data.get('error', 'unknown_error')
                    error_description = error_data.get('error_description', error_data.get('message', response.text))

                    logger.error(f"Token exchange failed with status {response.status_code}")
                    logger.error(f"Error type: {error_type}")
                    logger.error(f"Error description: {error_description}")
                    logger.error(f"Redirect URI used: {redirect_uri}")
                    logger.error(f"Full response: {response.text}")

                    # Provide specific error messages based on Google's error type
                    if error_type == 'redirect_uri_mismatch' or 'redirect_uri_mismatch' in str(error_description).lower():
                        detail = (
                            f"⚠️ Google OAuth Redirect URI Mismatch\n\n"
                            f"The redirect URI '{redirect_uri}' is not authorized in Google Cloud Console.\n\n"
                            f"TO FIX:\n"
                            f"1. Go to: https://console.cloud.google.com/apis/credentials\n"
                            f"2. Find your OAuth 2.0 Client ID\n"
                            f"3. Add '{redirect_uri}' to 'Authorized redirect URIs'\n"
                            f"4. Click 'Save' and wait 5-10 minutes\n\n"
                            f"Google error: {error_description}"
                        )
                    elif error_type == 'invalid_grant':
                        detail = (
                            "Google OAuth authorization code is invalid or expired.\n\n"
                            "This usually happens if:\n"
                            "- The code was already used (codes can only be used once)\n"
                            "- The code expired (codes expire after 10 minutes)\n"
                            "- You refreshed the callback page\n\n"
                            "Please start a fresh login attempt."
                        )
                    elif error_type == 'invalid_client':
                        detail = (
                            "Invalid OAuth client credentials.\n\n"
                            "Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
                            "in your .env file match your Google Cloud Console credentials."
                        )
                    else:
                        detail = (
                            f"Google OAuth Error: {error_type}\n\n"
                            f"Details: {error_description}\n\n"
                            f"If this persists, check:\n"
                            f"1. Google Cloud Console redirect URI is correct\n"
                            f"2. OAuth credentials are valid\n"
                            f"3. Google APIs are enabled in your project"
                        )

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=detail
                    )

                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to Google OAuth: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during authentication"
            )
