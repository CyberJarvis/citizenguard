"""
Email Service
Send emails using SMTP (async)
"""

import logging
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from jinja2 import Template

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email sending service"""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email
            # Port 587 uses STARTTLS, port 465 uses direct TLS
            if settings.SMTP_PORT == 587:
                await aiosmtplib.send(
                    message,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    username=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    start_tls=True,  # Use STARTTLS for port 587
                )
            else:
                # Port 465 or other: use direct TLS
                await aiosmtplib.send(
                    message,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    username=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    use_tls=settings.SMTP_TLS,
                )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    async def send_otp_email(to_email: str, otp: str) -> bool:
        """
        Send OTP email

        Args:
            to_email: Recipient email
            otp: OTP code

        Returns:
            True if sent successfully
        """
        subject = f"Your {settings.APP_NAME} OTP Code"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #0066cc; color: white; padding: 20px; text-align: center; }
                .content { background: #f9f9f9; padding: 30px; border-radius: 5px; margin-top: 20px; }
                .otp-code { font-size: 32px; font-weight: bold; color: #0066cc; text-align: center;
                           padding: 20px; background: white; border-radius: 5px; letter-spacing: 5px; }
                .footer { margin-top: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ app_name }}</h1>
                </div>
                <div class="content">
                    <h2>Your One-Time Password (OTP)</h2>
                    <p>Use the following OTP to complete your authentication:</p>
                    <div class="otp-code">{{ otp }}</div>
                    <p><strong>This OTP will expire in {{ expire_minutes }} minutes.</strong></p>
                    <p>If you didn't request this OTP, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This is an automated email. Please do not reply.</p>
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(
            app_name=settings.APP_NAME,
            otp=otp,
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )

        text_content = f"""
        Your {settings.APP_NAME} OTP Code

        OTP: {otp}

        This OTP will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

        If you didn't request this OTP, please ignore this email.
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    async def send_welcome_email(to_email: str, name: str) -> bool:
        """
        Send welcome email after successful registration

        Args:
            to_email: User email
            name: User name

        Returns:
            True if sent successfully
        """
        subject = f"Welcome to {settings.APP_NAME}!"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #0066cc; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px; }
                .button { display: inline-block; padding: 12px 30px; background: #0066cc;
                         color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {{ app_name }}!</h1>
                </div>
                <div class="content">
                    <h2>Hello {{ name }},</h2>
                    <p>Thank you for joining {{ app_name }}! Your account has been created successfully.</p>
                    <p>You can now report ocean hazards and help keep our coastline safe.</p>
                    <a href="{{ frontend_url }}" class="button">Get Started</a>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(
            app_name=settings.APP_NAME,
            name=name or "User",
            frontend_url=settings.FRONTEND_URL
        )

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content
        )

    @staticmethod
    async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
        """
        Send password reset email with link (legacy method)

        Args:
            to_email: User email
            reset_token: Password reset token

        Returns:
            True if sent successfully
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        subject = f"Reset Your {settings.APP_NAME} Password"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .content { padding: 30px; background: #f9f9f9; border-radius: 5px; }
                .button { display: inline-block; padding: 12px 30px; background: #0066cc;
                         color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>We received a request to reset your password. Click the button below to reset it:</p>
                    <a href="{{ reset_url }}" class="button">Reset Password</a>
                    <p>This link will expire in 15 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(reset_url=reset_url)

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content
        )

    @staticmethod
    async def send_password_reset_otp_email(to_email: str, otp: str) -> bool:
        """
        Send password reset OTP email

        Args:
            to_email: User email
            otp: OTP code

        Returns:
            True if sent successfully
        """
        subject = f"Reset Your {settings.APP_NAME} Password"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
                .content { background: #f9f9f9; padding: 30px; border-radius: 5px; margin-top: 20px; }
                .otp-code { font-size: 32px; font-weight: bold; color: #dc3545; text-align: center;
                           padding: 20px; background: white; border-radius: 5px; letter-spacing: 5px; }
                .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-top: 20px; }
                .footer { margin-top: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset</h1>
                </div>
                <div class="content">
                    <h2>Reset Your Password</h2>
                    <p>We received a request to reset your password. Use the following OTP to complete the password reset:</p>
                    <div class="otp-code">{{ otp }}</div>
                    <p><strong>This OTP will expire in {{ expire_minutes }} minutes.</strong></p>
                    <div class="warning">
                        <strong>Security Notice:</strong> If you didn't request this password reset, please ignore this email and ensure your account is secure.
                    </div>
                </div>
                <div class="footer">
                    <p>This is an automated email. Please do not reply.</p>
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(
            app_name=settings.APP_NAME,
            otp=otp,
            expire_minutes=settings.OTP_EXPIRE_MINUTES
        )

        text_content = f"""
        Reset Your {settings.APP_NAME} Password

        We received a request to reset your password.

        OTP: {otp}

        This OTP will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

        If you didn't request this password reset, please ignore this email.
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    async def send_certificate_email(
        to_email: str,
        user_name: str,
        event_title: str,
        certificate_url: str,
        certificate_id: str
    ) -> bool:
        """
        Send certificate email with download link

        Args:
            to_email: User email
            user_name: User name
            event_title: Event title
            certificate_url: URL to download certificate
            certificate_id: Certificate ID

        Returns:
            True if sent successfully
        """
        subject = f"Your Volunteer Certificate - {event_title}"

        # Construct full URL for certificate download
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        backend_url = frontend_url.replace(':3000', ':8000').replace('localhost', 'localhost')
        download_url = f"{backend_url}{certificate_url}"
        verify_url = f"{frontend_url}/certificates/verify/{certificate_id}"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                .header h1 { margin: 0; font-size: 28px; }
                .content { background: white; padding: 30px; border-radius: 0 0 10px 10px; }
                .certificate-card { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 2px solid #d97706; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }
                .certificate-card h2 { color: #92400e; margin: 0 0 10px 0; }
                .certificate-id { font-family: monospace; background: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; color: #6b7280; }
                .button { display: inline-block; padding: 15px 30px; background: #1e40af; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 10px 5px; }
                .button-secondary { background: #6b7280; }
                .footer { margin-top: 30px; text-align: center; color: #6b7280; font-size: 12px; }
                .highlight { background: #dbeafe; padding: 15px; border-radius: 8px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Congratulations!</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Your volunteer certificate is ready</p>
                </div>
                <div class="content">
                    <p>Dear <strong>{{ user_name }}</strong>,</p>

                    <p>Thank you for your dedication to ocean conservation! Your participation in <strong>{{ event_title }}</strong> has made a real difference.</p>

                    <div class="certificate-card">
                        <h2>Certificate of Appreciation</h2>
                        <p style="margin: 10px 0; color: #78350f;">Your volunteer certificate is ready for download!</p>
                        <p class="certificate-id">Certificate ID: {{ certificate_id }}</p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{{ download_url }}" class="button">Download Certificate</a>
                    </div>

                    <div class="highlight">
                        <strong>Keep Making Waves!</strong><br>
                        Your contribution helps protect our coastlines and marine ecosystems. Join more events to earn additional badges and climb the leaderboard!
                    </div>

                    <p>Thank you for being a CoastGuardian!</p>
                    <p><strong>The CoastGuardian Team</strong></p>
                </div>
                <div class="footer">
                    <p>This is an automated email from {{ app_name }}.</p>
                    <p>2025 CoastGuardian. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(
            user_name=user_name or "Volunteer",
            event_title=event_title,
            certificate_id=certificate_id,
            download_url=download_url,
            verify_url=verify_url,
            app_name=settings.APP_NAME
        )

        text_content = f"""
Congratulations {user_name}!

Your Volunteer Certificate is Ready

Thank you for participating in: {event_title}

Your certificate is ready for download.
Certificate ID: {certificate_id}

Download your certificate at: {download_url}

Thank you for being a CoastGuardian!

The CoastGuardian Team
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    async def send_organizer_approval_email(
        to_email: str,
        user_name: str,
        application_id: str
    ) -> bool:
        """
        Send email notification when organizer application is approved

        Args:
            to_email: User email
            user_name: User name
            application_id: Application ID

        Returns:
            True if sent successfully
        """
        subject = f"Congratulations! Your Organizer Application is Approved - {settings.APP_NAME}"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                .header h1 { margin: 0; font-size: 28px; }
                .content { background: white; padding: 30px; border-radius: 0 0 10px 10px; }
                .success-badge { background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border: 2px solid #059669; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }
                .success-badge h2 { color: #047857; margin: 0; }
                .button { display: inline-block; padding: 15px 30px; background: #059669; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 10px 5px; }
                .features { background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .features ul { margin: 10px 0; padding-left: 20px; }
                .features li { margin: 8px 0; }
                .footer { margin-top: 30px; text-align: center; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application Approved!</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">You are now a Verified Organizer</p>
                </div>
                <div class="content">
                    <p>Dear <strong>{{ user_name }}</strong>,</p>

                    <div class="success-badge">
                        <h2>Congratulations!</h2>
                        <p style="margin: 10px 0 0 0; color: #065f46;">Your organizer application has been approved.</p>
                    </div>

                    <p>We are pleased to inform you that your application to become a Verified Organizer on {{ app_name }} has been reviewed and <strong>approved</strong>!</p>

                    <div class="features">
                        <strong>As a Verified Organizer, you can now:</strong>
                        <ul>
                            <li>Create and manage cleanup communities</li>
                            <li>Organize beach and coastal cleanup events</li>
                            <li>Invite and manage volunteers</li>
                            <li>Issue volunteer certificates</li>
                            <li>Access organizer analytics dashboard</li>
                        </ul>
                    </div>

                    <div style="text-align: center;">
                        <a href="{{ frontend_url }}/community/create" class="button">Create Your First Community</a>
                    </div>

                    <p style="margin-top: 20px;">Thank you for your commitment to protecting our coastlines. We look forward to seeing the positive impact you'll make!</p>

                    <p><strong>The {{ app_name }} Team</strong></p>
                </div>
                <div class="footer">
                    <p>Application ID: {{ application_id }}</p>
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(
            user_name=user_name or "User",
            application_id=application_id,
            app_name=settings.APP_NAME,
            frontend_url=settings.FRONTEND_URL
        )

        text_content = f"""
Congratulations {user_name}!

Your Organizer Application is Approved!

We are pleased to inform you that your application to become a Verified Organizer on {settings.APP_NAME} has been reviewed and approved!

As a Verified Organizer, you can now:
- Create and manage cleanup communities
- Organize beach and coastal cleanup events
- Invite and manage volunteers
- Issue volunteer certificates
- Access organizer analytics dashboard

Visit {settings.FRONTEND_URL}/community/create to create your first community.

Application ID: {application_id}

Thank you for your commitment to protecting our coastlines!

The {settings.APP_NAME} Team
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    async def send_organizer_rejection_email(
        to_email: str,
        user_name: str,
        application_id: str,
        rejection_reason: str
    ) -> bool:
        """
        Send email notification when organizer application is rejected

        Args:
            to_email: User email
            user_name: User name
            application_id: Application ID
            rejection_reason: Reason for rejection

        Returns:
            True if sent successfully
        """
        subject = f"Update on Your Organizer Application - {settings.APP_NAME}"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #6b7280 0%, #9ca3af 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                .header h1 { margin: 0; font-size: 28px; }
                .content { background: white; padding: 30px; border-radius: 0 0 10px 10px; }
                .reason-box { background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }
                .reason-box h3 { color: #991b1b; margin: 0 0 10px 0; }
                .next-steps { background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .button { display: inline-block; padding: 15px 30px; background: #3b82f6; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 10px 5px; }
                .footer { margin-top: 30px; text-align: center; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application Update</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Organizer Application Status</p>
                </div>
                <div class="content">
                    <p>Dear <strong>{{ user_name }}</strong>,</p>

                    <p>Thank you for your interest in becoming a Verified Organizer on {{ app_name }}. After careful review, we regret to inform you that your application has not been approved at this time.</p>

                    <div class="reason-box">
                        <h3>Reason for Decision</h3>
                        <p style="margin: 0;">{{ rejection_reason }}</p>
                    </div>

                    <div class="next-steps">
                        <strong>What's Next?</strong>
                        <p style="margin: 10px 0 0 0;">Don't be discouraged! You can:</p>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>Review the feedback above and address any concerns</li>
                            <li>Gather additional documentation or experience</li>
                            <li>Submit a new application after 30 days</li>
                            <li>Continue participating in community events as a volunteer</li>
                        </ul>
                    </div>

                    <div style="text-align: center;">
                        <a href="{{ frontend_url }}/community/apply" class="button">Apply Again</a>
                    </div>

                    <p style="margin-top: 20px;">We appreciate your dedication to coastal conservation and hope to see you continue as an active member of our community.</p>

                    <p><strong>The {{ app_name }} Team</strong></p>
                </div>
                <div class="footer">
                    <p>Application ID: {{ application_id }}</p>
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(
            user_name=user_name or "User",
            application_id=application_id,
            rejection_reason=rejection_reason,
            app_name=settings.APP_NAME,
            frontend_url=settings.FRONTEND_URL
        )

        text_content = f"""
Dear {user_name},

Thank you for your interest in becoming a Verified Organizer on {settings.APP_NAME}.

After careful review, we regret to inform you that your application has not been approved at this time.

Reason for Decision:
{rejection_reason}

What's Next?
- Review the feedback above and address any concerns
- Gather additional documentation or experience
- Submit a new application after 30 days
- Continue participating in community events as a volunteer

Application ID: {application_id}

We appreciate your dedication to coastal conservation and hope to see you continue as an active member of our community.

The {settings.APP_NAME} Team
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
