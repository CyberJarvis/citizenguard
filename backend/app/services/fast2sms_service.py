"""
Fast2SMS Service
SMS notification service for India using Fast2SMS API
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)


class Fast2SMSService:
    """
    Fast2SMS integration for sending SMS alerts in India.
    Used primarily for SOS emergency alerts to fishermen and authorities.
    """

    BASE_URL = "https://www.fast2sms.com/dev/bulkV2"

    def __init__(self):
        self.api_key = settings.FAST2SMS_API_KEY
        self.sender_id = settings.FAST2SMS_SENDER_ID
        self.route = settings.FAST2SMS_ROUTE
        self.enabled = settings.FAST2SMS_ENABLED

    async def send_sms(
        self,
        phone_numbers: List[str],
        message: str,
        flash: bool = False
    ) -> Dict[str, Any]:
        """
        Send SMS to one or multiple phone numbers.

        Args:
            phone_numbers: List of phone numbers (10-digit Indian numbers)
            message: SMS message content (max 160 chars for single SMS)
            flash: If True, send as flash SMS

        Returns:
            Response dict with success status and details
        """
        if not self.enabled:
            logger.warning("Fast2SMS is disabled. SMS not sent.")
            return {
                "success": False,
                "error": "SMS service is disabled",
                "simulated": True
            }

        if not self.api_key:
            logger.error("Fast2SMS API key not configured")
            return {
                "success": False,
                "error": "SMS service not configured"
            }

        # Clean phone numbers (remove +91 prefix if present)
        cleaned_numbers = []
        for phone in phone_numbers:
            clean = phone.replace("+91", "").replace(" ", "").replace("-", "")
            if len(clean) == 10 and clean.isdigit():
                cleaned_numbers.append(clean)
            else:
                logger.warning(f"Invalid phone number skipped: {phone}")

        if not cleaned_numbers:
            return {
                "success": False,
                "error": "No valid phone numbers provided"
            }

        try:
            headers = {
                "authorization": self.api_key,
                "Content-Type": "application/json"
            }

            # Use bulkV2 endpoint with route=q (Quick SMS)
            # Quick SMS works without DLT registration
            payload = {
                "message": message,
                "language": "english",
                "route": "q",  # Quick transactional route
                "numbers": ",".join(cleaned_numbers)
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload
                )

                result = response.json()

                if response.status_code == 200 and result.get("return"):
                    logger.info(f"SMS sent successfully to {len(cleaned_numbers)} numbers")
                    # Parse credits - message can be string or array
                    credits = None
                    msg = result.get("message")
                    if isinstance(msg, list) and len(msg) > 0:
                        credits = msg[0].get("credits") if isinstance(msg[0], dict) else None
                    return {
                        "success": True,
                        "message_id": result.get("request_id"),
                        "recipients": cleaned_numbers,
                        "credits_used": credits
                    }
                else:
                    error_msg = result.get("message") if isinstance(result.get("message"), str) else "Unknown error"
                    logger.error(f"Fast2SMS error: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            logger.error("Fast2SMS request timed out")
            return {
                "success": False,
                "error": "SMS service timeout"
            }
        except Exception as e:
            logger.error(f"Fast2SMS error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_sos_alert(
        self,
        phone_numbers: List[str],
        fisherman_name: str,
        latitude: float,
        longitude: float,
        sos_id: str,
        vessel_name: Optional[str] = None,
        crew_count: int = 1,
        distress_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SOS emergency alert SMS.

        Args:
            phone_numbers: Emergency contact phone numbers
            fisherman_name: Name of person in distress
            latitude: GPS latitude
            longitude: GPS longitude
            sos_id: Unique SOS alert ID
            vessel_name: Optional vessel name
            crew_count: Number of people on board
            distress_message: Optional custom distress message from user

        Returns:
            Response dict with success status
        """
        # Create short Google Maps link
        map_link = f"maps.google.com/?q={latitude},{longitude}"

        # Build informative message with all key details
        # SMS can be up to 160 chars for single SMS, but we'll allow longer for emergency
        crew_info = f", {crew_count} onboard" if crew_count > 1 else ""
        vessel_info = f" ({vessel_name})" if vessel_name else ""
        distress_info = f" MSG: {distress_message}" if distress_message else ""

        # Priority format: Name, Location link, distress message, then ID
        message = (
            f"EMERGENCY SOS! {fisherman_name}{vessel_info} needs URGENT help{crew_info}. "
            f"LOCATION: {map_link}{distress_info} "
            f"[{sos_id}]"
        )

        logger.info(f"Sending SOS alert SMS for {sos_id} to {len(phone_numbers)} contacts")
        logger.info(f"SMS content ({len(message)} chars): {message}")

        return await self.send_sms(phone_numbers, message, flash=True)

    async def send_sos_acknowledged(
        self,
        phone_number: str,
        sos_id: str,
        authority_name: str,
        authority_org: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS to fisherman when their SOS is acknowledged.

        Args:
            phone_number: Fisherman's phone number
            sos_id: SOS alert ID
            authority_name: Name of acknowledging authority
            authority_org: Organization name

        Returns:
            Response dict
        """
        org_info = f" ({authority_org})" if authority_org else ""
        message = (
            f"Your SOS {sos_id} has been acknowledged by {authority_name}{org_info}. "
            f"Help is on the way. Stay calm."
        )

        return await self.send_sms([phone_number], message)

    async def send_sos_dispatched(
        self,
        phone_number: str,
        sos_id: str,
        eta_minutes: Optional[int] = None,
        rescue_unit: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS when rescue is dispatched.

        Args:
            phone_number: Fisherman's phone number
            sos_id: SOS alert ID
            eta_minutes: Estimated time of arrival
            rescue_unit: Name/ID of rescue unit

        Returns:
            Response dict
        """
        eta_info = f" ETA: {eta_minutes} mins." if eta_minutes else ""
        unit_info = f" Unit: {rescue_unit}." if rescue_unit else ""

        message = (
            f"Rescue dispatched for SOS {sos_id}.{unit_info}{eta_info} "
            f"Stay visible and await rescue."
        )

        return await self.send_sms([phone_number], message)

    async def send_sos_resolved(
        self,
        phone_numbers: List[str],
        sos_id: str,
        fisherman_name: str
    ) -> Dict[str, Any]:
        """
        Send SMS when SOS is resolved (to emergency contacts).

        Args:
            phone_numbers: Emergency contact numbers
            sos_id: SOS alert ID
            fisherman_name: Name of the fisherman

        Returns:
            Response dict
        """
        message = (
            f"SOS {sos_id} for {fisherman_name} has been resolved. "
            f"The person is now safe. - CoastGuardian"
        )

        return await self.send_sms(phone_numbers, message)

    async def check_balance(self) -> Dict[str, Any]:
        """
        Check SMS credit balance.

        Returns:
            Response dict with balance info
        """
        if not self.enabled or not self.api_key:
            return {
                "success": False,
                "error": "SMS service not configured"
            }

        try:
            headers = {
                "authorization": self.api_key
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.fast2sms.com/dev/wallet",
                    headers=headers
                )

                result = response.json()

                if response.status_code == 200 and result.get("return"):
                    return {
                        "success": True,
                        "balance": result.get("wallet")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("message", "Unknown error")
                    }

        except Exception as e:
            logger.error(f"Error checking Fast2SMS balance: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
fast2sms_service = Fast2SMSService()
