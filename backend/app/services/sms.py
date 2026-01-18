"""
SMS Service
Send SMS using Twilio
"""

import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """SMS sending service using Twilio"""

    _client: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Get or create Twilio client"""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials not configured")
            return None

        if not cls._client:
            cls._client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )

        return cls._client

    @staticmethod
    async def send_sms(to_phone: str, message: str) -> bool:
        """
        Send SMS via Twilio

        Args:
            to_phone: Recipient phone number (with country code)
            message: SMS message text

        Returns:
            True if sent successfully, False otherwise
        """
        client = SMSService.get_client()

        if not client:
            logger.error("SMS service not configured")
            return False

        try:
            message_obj = client.messages.create(
                to=to_phone,
                from_=settings.TWILIO_PHONE_NUMBER,
                body=message
            )

            logger.info(f"SMS sent successfully to {to_phone} (SID: {message_obj.sid})")
            return True

        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS to {to_phone}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False

    @staticmethod
    async def send_otp_sms(to_phone: str, otp: str) -> bool:
        """
        Send OTP via SMS

        Args:
            to_phone: Recipient phone number
            otp: OTP code

        Returns:
            True if sent successfully
        """
        message = f"""Your {settings.APP_NAME} verification code is: {otp}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

Do not share this code with anyone."""

        return await SMSService.send_sms(to_phone, message)

    @staticmethod
    async def send_alert_sms(to_phone: str, alert_message: str) -> bool:
        """
        Send alert notification via SMS

        Args:
            to_phone: Recipient phone number
            alert_message: Alert message

        Returns:
            True if sent successfully
        """
        message = f"""{settings.APP_NAME} ALERT:

{alert_message}

Stay safe!"""

        return await SMSService.send_sms(to_phone, message)
