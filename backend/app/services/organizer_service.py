"""
Organizer Service
Handles organizer application, verification, and management.
"""

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import UploadFile

from app.models.community import (
    OrganizerApplication,
    ApplicationStatus,
    OrganizerApplicationCreate,
    OrganizerApplicationReview,
    INDIAN_COASTAL_ZONES,
    INDIAN_COASTAL_STATES,
)
from app.models.user import User
from app.models.rbac import UserRole
from app.services.email import EmailService

logger = logging.getLogger(__name__)

# Constants
MINIMUM_CREDIBILITY_SCORE = 80
REAPPLICATION_COOLDOWN_DAYS = 30
MAX_FILE_SIZE_MB = 5
ALLOWED_FILE_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
UPLOAD_DIR = "uploads/organizer_documents"

# Global service instance
_organizer_service: Optional["OrganizerService"] = None


def get_organizer_service(db: AsyncIOMotorDatabase = None) -> "OrganizerService":
    """Get or create organizer service singleton"""
    global _organizer_service
    if _organizer_service is None:
        _organizer_service = OrganizerService(db)
    elif db is not None:
        _organizer_service.db = db
    return _organizer_service


class OrganizerService:
    """Service for managing organizer applications and verification"""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
        self._initialized = False

    async def initialize(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service with database connection"""
        if db is not None:
            self.db = db

        if self.db is None:
            logger.warning("No database connection provided to OrganizerService")
            return

        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        self._initialized = True
        logger.info("OrganizerService initialized successfully")

    def _generate_application_id(self) -> str:
        """Generate unique application ID (ORG-YYYYMMDD-XXXXX)"""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:5].upper()
        return f"ORG-{date_part}-{random_part}"

    async def check_eligibility(self, user: User) -> Dict[str, Any]:
        """
        Check if a user is eligible to apply as an organizer.

        Requirements:
        - Credibility score >= 80
        - No pending application
        - Not already a verified organizer
        - Not rejected within cooldown period
        """
        result = {
            "eligible": False,
            "reason": None,
            "credibility_score": user.credibility_score,
            "required_score": MINIMUM_CREDIBILITY_SCORE,
            "existing_application": None
        }

        # Check if already a verified organizer or higher
        if user.role in [UserRole.VERIFIED_ORGANIZER, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            result["reason"] = "already_organizer"
            result["message"] = "You are already a verified organizer or have a higher role."
            return result

        # Check credibility score
        if user.credibility_score < MINIMUM_CREDIBILITY_SCORE:
            result["reason"] = "insufficient_credibility"
            result["message"] = f"Your credibility score ({user.credibility_score}) is below the required minimum ({MINIMUM_CREDIBILITY_SCORE}). Keep contributing quality reports to improve your score."
            return result

        # Check for existing application
        existing = await self.db.organizer_applications.find_one({"user_id": user.user_id})

        if existing:
            app = OrganizerApplication.from_mongo(existing)
            result["existing_application"] = {
                "application_id": app.application_id,
                "status": app.status.value,
                "applied_at": app.applied_at.isoformat()
            }

            if app.status == ApplicationStatus.PENDING:
                result["reason"] = "pending_application"
                result["message"] = "You already have a pending application. Please wait for review."
                return result

            if app.status == ApplicationStatus.APPROVED:
                result["reason"] = "already_approved"
                result["message"] = "Your application was already approved. You should be a verified organizer."
                return result

            if app.status == ApplicationStatus.REJECTED:
                # Check cooldown period
                if app.reviewed_at:
                    cooldown_end = app.reviewed_at + timedelta(days=REAPPLICATION_COOLDOWN_DAYS)
                    if datetime.now(timezone.utc) < cooldown_end:
                        days_remaining = (cooldown_end - datetime.now(timezone.utc)).days
                        result["reason"] = "cooldown_active"
                        result["message"] = f"You can reapply in {days_remaining} days after your previous rejection."
                        result["cooldown_ends"] = cooldown_end.isoformat()
                        return result
                    else:
                        # Can reapply - delete old application
                        result["can_reapply"] = True

        # All checks passed
        result["eligible"] = True
        result["message"] = "You are eligible to apply as a verified organizer!"
        return result

    async def save_aadhaar_document(self, file: UploadFile, user_id: str) -> str:
        """
        Save uploaded Aadhaar document securely.

        Args:
            file: Uploaded file
            user_id: User ID for organizing files

        Returns:
            File path relative to uploads directory

        Raises:
            ValueError: If file is invalid
        """
        # Validate file type
        if file.content_type not in ALLOWED_FILE_TYPES:
            raise ValueError(f"Invalid file type. Allowed: PDF, JPEG, PNG")

        # Read file content
        content = await file.read()

        # Validate file size
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB")

        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved Aadhaar document for user {user_id}: {file_path}")
        return file_path

    async def submit_application(
        self,
        user: User,
        application_data: OrganizerApplicationCreate,
        aadhaar_file: UploadFile
    ) -> Tuple[bool, str, Optional[OrganizerApplication]]:
        """
        Submit a new organizer application.

        Args:
            user: Current user
            application_data: Application form data
            aadhaar_file: Uploaded Aadhaar document

        Returns:
            Tuple of (success, message, application)
        """
        # Check eligibility first
        eligibility = await self.check_eligibility(user)
        if not eligibility["eligible"]:
            return False, eligibility["message"], None

        # Validate coastal zone and state
        if application_data.coastal_zone not in INDIAN_COASTAL_ZONES:
            return False, f"Invalid coastal zone. Must be one of: {', '.join(INDIAN_COASTAL_ZONES)}", None

        if application_data.state not in INDIAN_COASTAL_STATES:
            return False, f"Invalid state. Must be one of: {', '.join(INDIAN_COASTAL_STATES)}", None

        try:
            # Delete any previous rejected application if reapplying
            if eligibility.get("can_reapply"):
                await self.db.organizer_applications.delete_one({"user_id": user.user_id})

            # Save Aadhaar document
            aadhaar_path = await self.save_aadhaar_document(aadhaar_file, user.user_id)

            # Create application
            application = OrganizerApplication(
                application_id=self._generate_application_id(),
                user_id=user.user_id,
                name=application_data.name,
                email=application_data.email,
                phone=application_data.phone,
                coastal_zone=application_data.coastal_zone,
                state=application_data.state,
                aadhaar_document_url=aadhaar_path,
                credibility_at_application=user.credibility_score,
                status=ApplicationStatus.PENDING,
                applied_at=datetime.now(timezone.utc)
            )

            # Insert into database
            await self.db.organizer_applications.insert_one(application.to_mongo())

            logger.info(f"New organizer application submitted: {application.application_id} by user {user.user_id}")

            return True, "Application submitted successfully! We will review it shortly.", application

        except ValueError as ve:
            return False, str(ve), None
        except Exception as e:
            logger.error(f"Failed to submit organizer application: {e}")
            return False, "Failed to submit application. Please try again.", None

    async def get_application_status(self, user_id: str) -> Optional[OrganizerApplication]:
        """Get the current application status for a user."""
        doc = await self.db.organizer_applications.find_one({"user_id": user_id})
        if doc:
            return OrganizerApplication.from_mongo(doc)
        return None

    async def get_pending_applications(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "applied_at",
        sort_order: int = -1
    ) -> Tuple[List[OrganizerApplication], int]:
        """
        Get all pending applications for admin review.

        Returns:
            Tuple of (applications list, total count)
        """
        query = {"status": ApplicationStatus.PENDING.value}

        # Get total count
        total = await self.db.organizer_applications.count_documents(query)

        # Get applications
        cursor = self.db.organizer_applications.find(query)
        cursor = cursor.sort(sort_by, sort_order).skip(skip).limit(limit)

        applications = []
        async for doc in cursor:
            applications.append(OrganizerApplication.from_mongo(doc))

        return applications, total

    async def get_all_applications(
        self,
        status: Optional[ApplicationStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[OrganizerApplication], int]:
        """Get all applications with optional status filter."""
        query = {}
        if status:
            query["status"] = status.value

        total = await self.db.organizer_applications.count_documents(query)

        cursor = self.db.organizer_applications.find(query)
        cursor = cursor.sort("applied_at", -1).skip(skip).limit(limit)

        applications = []
        async for doc in cursor:
            applications.append(OrganizerApplication.from_mongo(doc))

        return applications, total

    async def approve_application(
        self,
        application_id: str,
        admin_user: User
    ) -> Tuple[bool, str, Optional[OrganizerApplication]]:
        """
        Approve an organizer application.

        Args:
            application_id: Application ID to approve
            admin_user: Admin user performing the action

        Returns:
            Tuple of (success, message, updated application)
        """
        # Get application
        doc = await self.db.organizer_applications.find_one({"application_id": application_id})
        if not doc:
            return False, "Application not found", None

        application = OrganizerApplication.from_mongo(doc)

        if application.status != ApplicationStatus.PENDING:
            return False, f"Application is not pending (current status: {application.status.value})", None

        try:
            now = datetime.now(timezone.utc)

            # Update application status
            await self.db.organizer_applications.update_one(
                {"application_id": application_id},
                {
                    "$set": {
                        "status": ApplicationStatus.APPROVED.value,
                        "reviewed_by_id": admin_user.user_id,
                        "reviewed_by_name": admin_user.name or admin_user.email,
                        "reviewed_at": now
                    }
                }
            )

            # Update user role to VERIFIED_ORGANIZER
            await self.db.users.update_one(
                {"user_id": application.user_id},
                {
                    "$set": {
                        "role": UserRole.VERIFIED_ORGANIZER.value,
                        "role_assigned_by": admin_user.user_id,
                        "role_assigned_at": now,
                        "previous_role": UserRole.CITIZEN.value
                    }
                }
            )

            # Get updated application
            updated_doc = await self.db.organizer_applications.find_one({"application_id": application_id})
            updated_app = OrganizerApplication.from_mongo(updated_doc)

            logger.info(f"Organizer application {application_id} approved by {admin_user.user_id}")

            # Send approval email notification
            try:
                await EmailService.send_organizer_approval_email(
                    to_email=application.email,
                    user_name=application.full_name,
                    application_id=application_id
                )
                logger.info(f"Approval email sent to {application.email}")
            except Exception as email_error:
                logger.warning(f"Failed to send approval email: {email_error}")

            return True, "Application approved successfully. User is now a verified organizer.", updated_app

        except Exception as e:
            logger.error(f"Failed to approve application {application_id}: {e}")
            return False, "Failed to approve application. Please try again.", None

    async def reject_application(
        self,
        application_id: str,
        admin_user: User,
        rejection_reason: str
    ) -> Tuple[bool, str, Optional[OrganizerApplication]]:
        """
        Reject an organizer application.

        Args:
            application_id: Application ID to reject
            admin_user: Admin user performing the action
            rejection_reason: Reason for rejection

        Returns:
            Tuple of (success, message, updated application)
        """
        if not rejection_reason or len(rejection_reason.strip()) < 10:
            return False, "Please provide a detailed rejection reason (at least 10 characters)", None

        # Get application
        doc = await self.db.organizer_applications.find_one({"application_id": application_id})
        if not doc:
            return False, "Application not found", None

        application = OrganizerApplication.from_mongo(doc)

        if application.status != ApplicationStatus.PENDING:
            return False, f"Application is not pending (current status: {application.status.value})", None

        try:
            now = datetime.now(timezone.utc)

            # Update application status
            await self.db.organizer_applications.update_one(
                {"application_id": application_id},
                {
                    "$set": {
                        "status": ApplicationStatus.REJECTED.value,
                        "reviewed_by_id": admin_user.user_id,
                        "reviewed_by_name": admin_user.name or admin_user.email,
                        "reviewed_at": now,
                        "rejection_reason": rejection_reason.strip()
                    }
                }
            )

            # Get updated application
            updated_doc = await self.db.organizer_applications.find_one({"application_id": application_id})
            updated_app = OrganizerApplication.from_mongo(updated_doc)

            logger.info(f"Organizer application {application_id} rejected by {admin_user.user_id}")

            # Send rejection email notification
            try:
                await EmailService.send_organizer_rejection_email(
                    to_email=application.email,
                    user_name=application.name,
                    application_id=application_id,
                    rejection_reason=rejection_reason
                )
                logger.info(f"Rejection email sent to {application.email}")
            except Exception as email_error:
                logger.warning(f"Failed to send rejection email: {email_error}")

            return True, "Application rejected.", updated_app

        except Exception as e:
            logger.error(f"Failed to reject application {application_id}: {e}")
            return False, "Failed to reject application. Please try again.", None

    async def get_application_by_id(self, application_id: str) -> Optional[OrganizerApplication]:
        """Get a specific application by ID."""
        doc = await self.db.organizer_applications.find_one({"application_id": application_id})
        if doc:
            return OrganizerApplication.from_mongo(doc)
        return None

    async def get_aadhaar_document_path(self, application_id: str) -> Optional[str]:
        """Get the Aadhaar document file path for an application (admin only)."""
        doc = await self.db.organizer_applications.find_one(
            {"application_id": application_id},
            {"aadhaar_document_url": 1}
        )
        if doc:
            return doc.get("aadhaar_document_url")
        return None

    async def get_statistics(self) -> Dict[str, Any]:
        """Get organizer application statistics for admin dashboard."""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]

        result = await self.db.organizer_applications.aggregate(pipeline).to_list(length=None)

        stats = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "total": 0
        }

        for item in result:
            status = item["_id"]
            count = item["count"]
            if status in stats:
                stats[status] = count
            stats["total"] += count

        # Get count of verified organizers
        organizer_count = await self.db.users.count_documents({"role": UserRole.VERIFIED_ORGANIZER.value})
        stats["active_organizers"] = organizer_count

        return stats
