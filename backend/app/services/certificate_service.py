"""
Certificate Service
Generate and manage volunteer certificates using ReportLab
"""

import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Certificate storage directory
CERTIFICATE_DIR = "uploads/certificates"

# Ensure directory exists
os.makedirs(CERTIFICATE_DIR, exist_ok=True)


class CertificateService:
    """Service for generating and managing volunteer certificates"""

    @staticmethod
    def generate_certificate_id() -> str:
        """Generate unique certificate ID"""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:5].upper()
        return f"CERT-{date_str}-{unique_part}"

    @staticmethod
    def generate_pdf(
        certificate_id: str,
        user_name: str,
        event_title: str,
        event_date: datetime,
        event_location: str,
        organizer_name: str,
        community_name: str,
        points_awarded: int = 50
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate a PDF certificate

        Args:
            certificate_id: Unique certificate ID
            user_name: Name of the volunteer
            event_title: Title of the event
            event_date: Date of the event
            event_location: Location of the event
            organizer_name: Name of the event organizer
            community_name: Name of the community
            points_awarded: Points awarded for participation

        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            # File path
            filename = f"{certificate_id}.pdf"
            filepath = os.path.join(CERTIFICATE_DIR, filename)

            # Create PDF in landscape A4
            c = canvas.Canvas(filepath, pagesize=landscape(A4))
            width, height = landscape(A4)

            # Colors
            primary_blue = HexColor("#1e40af")
            secondary_blue = HexColor("#3b82f6")
            gold = HexColor("#d97706")
            dark_text = HexColor("#1f2937")
            light_text = HexColor("#6b7280")

            # Background gradient effect (simplified)
            c.setFillColor(HexColor("#f0f9ff"))
            c.rect(0, 0, width, height, fill=True, stroke=False)

            # Border
            c.setStrokeColor(primary_blue)
            c.setLineWidth(3)
            c.roundRect(30, 30, width - 60, height - 60, 10, stroke=True, fill=False)

            # Inner decorative border
            c.setStrokeColor(secondary_blue)
            c.setLineWidth(1)
            c.roundRect(45, 45, width - 90, height - 90, 8, stroke=True, fill=False)

            # Header - CoastGuardian Logo/Text
            c.setFillColor(primary_blue)
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(width / 2, height - 80, "CoastGuardian")

            c.setFillColor(secondary_blue)
            c.setFont("Helvetica", 12)
            c.drawCentredString(width / 2, height - 100, "Ocean Safety & Conservation Platform")

            # Certificate Title
            c.setFillColor(gold)
            c.setFont("Helvetica-Bold", 36)
            c.drawCentredString(width / 2, height - 160, "CERTIFICATE OF APPRECIATION")

            # Decorative line
            c.setStrokeColor(gold)
            c.setLineWidth(2)
            c.line(width / 2 - 150, height - 175, width / 2 + 150, height - 175)

            # "This is to certify that"
            c.setFillColor(light_text)
            c.setFont("Helvetica", 14)
            c.drawCentredString(width / 2, height - 210, "This is to certify that")

            # Volunteer Name
            c.setFillColor(primary_blue)
            c.setFont("Helvetica-Bold", 32)
            c.drawCentredString(width / 2, height - 250, user_name)

            # Underline for name
            name_width = c.stringWidth(user_name, "Helvetica-Bold", 32)
            c.setStrokeColor(gold)
            c.setLineWidth(1)
            c.line(width / 2 - name_width / 2 - 20, height - 260,
                   width / 2 + name_width / 2 + 20, height - 260)

            # "has successfully participated in"
            c.setFillColor(light_text)
            c.setFont("Helvetica", 14)
            c.drawCentredString(width / 2, height - 295, "has successfully participated in")

            # Event Title
            c.setFillColor(dark_text)
            c.setFont("Helvetica-Bold", 20)
            # Truncate event title if too long
            display_title = event_title[:50] + "..." if len(event_title) > 50 else event_title
            c.drawCentredString(width / 2, height - 330, display_title)

            # Event details
            c.setFillColor(light_text)
            c.setFont("Helvetica", 12)
            event_date_str = event_date.strftime("%B %d, %Y") if event_date else "N/A"
            c.drawCentredString(width / 2, height - 360, f"held on {event_date_str}")
            c.drawCentredString(width / 2, height - 380, f"at {event_location}")

            # Community name
            c.setFillColor(secondary_blue)
            c.setFont("Helvetica-Oblique", 12)
            c.drawCentredString(width / 2, height - 405, f"organized by {community_name}")

            # Points Badge
            c.setFillColor(gold)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width / 2, height - 440, f"Points Earned: {points_awarded}")

            # Footer section
            footer_y = 100

            # Certificate ID
            c.setFillColor(light_text)
            c.setFont("Helvetica", 10)
            c.drawString(70, footer_y, f"Certificate ID: {certificate_id}")

            # Issue Date
            issue_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
            c.drawString(70, footer_y - 15, f"Issued: {issue_date}")

            # Organizer signature area (right side)
            c.setStrokeColor(dark_text)
            c.setLineWidth(1)
            c.line(width - 250, footer_y + 30, width - 70, footer_y + 30)

            c.setFillColor(dark_text)
            c.setFont("Helvetica", 10)
            c.drawCentredString(width - 160, footer_y + 10, organizer_name)
            c.setFont("Helvetica-Oblique", 9)
            c.drawCentredString(width - 160, footer_y - 5, "Event Organizer")

            # Verification note
            c.setFillColor(light_text)
            c.setFont("Helvetica", 8)
            c.drawCentredString(width / 2, 50, f"Verify this certificate at: coastguardian.in/verify/{certificate_id}")

            # Save PDF
            c.save()

            relative_path = f"/uploads/certificates/{filename}"

            logger.info(f"Certificate generated: {certificate_id}")
            return True, "Certificate generated successfully", relative_path

        except Exception as e:
            logger.error(f"Error generating certificate: {e}")
            return False, f"Failed to generate certificate: {str(e)}", None

    @staticmethod
    async def generate_certificate(
        db: AsyncIOMotorDatabase,
        event_id: str,
        user_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Generate certificate for a user's event attendance

        Args:
            db: Database connection
            event_id: Event ID
            user_id: User ID

        Returns:
            Tuple of (success, message, certificate_data)
        """
        try:
            # Get event details
            event = await db.events.find_one({"event_id": event_id})
            if not event:
                return False, "Event not found", None

            # Get registration
            registration = await db.event_registrations.find_one({
                "event_id": event_id,
                "user_id": user_id
            })

            if not registration:
                return False, "Registration not found", None

            # Check if user attended
            if registration.get("registration_status") != "attended":
                return False, "Certificate is only available for attended events", None

            # Check if certificate already exists
            if registration.get("certificate_generated") and registration.get("certificate_url"):
                return True, "Certificate already generated", {
                    "certificate_id": registration.get("certificate_id"),
                    "certificate_url": registration.get("certificate_url")
                }

            # Get user details
            user = await db.users.find_one({"user_id": user_id})
            if not user:
                return False, "User not found", None

            # Get community details
            community = await db.communities.find_one({"community_id": event.get("community_id")})
            community_name = community.get("name", "CoastGuardian Community") if community else "CoastGuardian Community"

            # Generate certificate
            certificate_id = CertificateService.generate_certificate_id()

            success, message, filepath = CertificateService.generate_pdf(
                certificate_id=certificate_id,
                user_name=user.get("name", registration.get("user_name", "Volunteer")),
                event_title=event.get("title", "Volunteer Event"),
                event_date=event.get("event_date"),
                event_location=event.get("location_address", "Coastal Location"),
                organizer_name=event.get("organizer_name", "Event Organizer"),
                community_name=community_name,
                points_awarded=registration.get("points_awarded", event.get("points_per_attendee", 50))
            )

            if not success:
                return False, message, None

            # Update registration with certificate info
            await db.event_registrations.update_one(
                {"event_id": event_id, "user_id": user_id},
                {
                    "$set": {
                        "certificate_generated": True,
                        "certificate_url": filepath,
                        "certificate_id": certificate_id
                    }
                }
            )

            # Store certificate record
            certificate_record = {
                "certificate_id": certificate_id,
                "event_id": event_id,
                "user_id": user_id,
                "user_name": user.get("name", registration.get("user_name")),
                "user_email": registration.get("user_email"),
                "event_title": event.get("title"),
                "event_date": event.get("event_date"),
                "event_location": event.get("location_address"),
                "organizer_name": event.get("organizer_name"),
                "community_name": community_name,
                "certificate_url": filepath,
                "generated_at": datetime.now(timezone.utc),
                "emailed_at": None
            }

            await db.certificates.insert_one(certificate_record)

            return True, "Certificate generated successfully", {
                "certificate_id": certificate_id,
                "certificate_url": filepath,
                "user_name": user.get("name"),
                "event_title": event.get("title")
            }

        except Exception as e:
            logger.error(f"Error generating certificate: {e}")
            return False, f"Failed to generate certificate: {str(e)}", None

    @staticmethod
    async def get_certificate(
        db: AsyncIOMotorDatabase,
        certificate_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Get certificate by ID

        Args:
            db: Database connection
            certificate_id: Certificate ID

        Returns:
            Tuple of (success, message, certificate_data)
        """
        try:
            certificate = await db.certificates.find_one({"certificate_id": certificate_id})
            if not certificate:
                return False, "Certificate not found", None

            # Convert ObjectId to string
            if "_id" in certificate:
                certificate["_id"] = str(certificate["_id"])

            return True, "Certificate found", certificate

        except Exception as e:
            logger.error(f"Error getting certificate: {e}")
            return False, f"Failed to get certificate: {str(e)}", None

    @staticmethod
    async def get_user_certificates(
        db: AsyncIOMotorDatabase,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[bool, str, list, int]:
        """
        Get all certificates for a user

        Args:
            db: Database connection
            user_id: User ID
            skip: Pagination skip
            limit: Pagination limit

        Returns:
            Tuple of (success, message, certificates, total)
        """
        try:
            query = {"user_id": user_id}

            # Get total count
            total = await db.certificates.count_documents(query)

            # Get certificates
            cursor = db.certificates.find(query).sort("generated_at", -1).skip(skip).limit(limit)
            certificates = []

            async for cert in cursor:
                if "_id" in cert:
                    cert["_id"] = str(cert["_id"])
                certificates.append(cert)

            return True, "Certificates retrieved", certificates, total

        except Exception as e:
            logger.error(f"Error getting user certificates: {e}")
            return False, f"Failed to get certificates: {str(e)}", [], 0

    @staticmethod
    async def verify_certificate(
        db: AsyncIOMotorDatabase,
        certificate_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify a certificate (public endpoint)

        Args:
            db: Database connection
            certificate_id: Certificate ID

        Returns:
            Tuple of (valid, message, verification_data)
        """
        try:
            certificate = await db.certificates.find_one({"certificate_id": certificate_id})

            if not certificate:
                return False, "Certificate not found or invalid", None

            # Return public verification data
            verification_data = {
                "valid": True,
                "certificate_id": certificate_id,
                "user_name": certificate.get("user_name"),
                "event_title": certificate.get("event_title"),
                "event_date": certificate.get("event_date").isoformat() if certificate.get("event_date") else None,
                "event_location": certificate.get("event_location"),
                "organizer_name": certificate.get("organizer_name"),
                "community_name": certificate.get("community_name"),
                "issued_at": certificate.get("generated_at").isoformat() if certificate.get("generated_at") else None
            }

            return True, "Certificate verified", verification_data

        except Exception as e:
            logger.error(f"Error verifying certificate: {e}")
            return False, f"Verification failed: {str(e)}", None

    @staticmethod
    async def mark_certificate_emailed(
        db: AsyncIOMotorDatabase,
        certificate_id: str
    ) -> bool:
        """Mark certificate as emailed"""
        try:
            await db.certificates.update_one(
                {"certificate_id": certificate_id},
                {"$set": {"emailed_at": datetime.now(timezone.utc)}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking certificate emailed: {e}")
            return False
