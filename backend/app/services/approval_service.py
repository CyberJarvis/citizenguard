"""
Approval Service (V2)
Handles hybrid mode approval logic for hazard reports.

This service manages:
1. AI recommendation confirmation by authority/analyst
2. Manual verification workflows
3. Credibility updates on any approval (AI or manual)
4. Tracking approval sources (AI_AUTO, AI_RECOMMENDED, AUTHORITY_MANUAL, ANALYST_VERIFIED)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.hazard import (
    HazardReport, ApprovalSource, TicketCreationStatus
)
from app.models.verification import (
    VerificationResult, VerificationDecision, AIRecommendation,
    VERIFICATION_THRESHOLDS
)
from app.models.user import User, CredibilityMetrics

logger = logging.getLogger(__name__)


class ApprovalService:
    """
    Service for handling hybrid mode approval workflows.

    Responsibilities:
    - Confirm AI recommendations (75-85% score reports)
    - Manual verification for reports needing review
    - Update reporter credibility on any approval/rejection
    - Track approval source for audit trail
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize approval service with database connection."""
        self.db = db

    async def confirm_ai_recommendation(
        self,
        report_id: str,
        confirmed_by_id: str,
        confirmed_by_name: str,
        confirmed_by_role: str,
        confirmation_notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[HazardReport]]:
        """
        Confirm an AI recommendation (for 75-85% score reports).

        This is called when an authority/analyst agrees with the AI's
        recommendation to approve a report.

        Args:
            report_id: The report ID to confirm
            confirmed_by_id: User ID of confirming authority/analyst
            confirmed_by_name: Name of confirming user
            confirmed_by_role: Role of confirming user (authority/analyst)
            confirmation_notes: Optional notes about the confirmation

        Returns:
            Tuple of (success, message, updated_report)
        """
        try:
            # Fetch the report
            report_doc = await self.db.hazard_reports.find_one({"report_id": report_id})
            if not report_doc:
                return False, f"Report {report_id} not found", None

            report = HazardReport.from_mongo(report_doc)

            # Validate the report is in the right state
            if report.verification_status != "needs_manual_review":
                return False, f"Report is not awaiting confirmation (status: {report.verification_status})", None

            # Check if this report has AI recommendation
            verification_doc = await self.db.verification_results.find_one({"report_id": report_id})
            if not verification_doc:
                return False, "No verification result found for this report", None

            ai_recommendation = verification_doc.get("ai_recommendation")
            if ai_recommendation != AIRecommendation.RECOMMEND_APPROVE.value:
                return False, f"Report does not have AI recommendation for approval (recommendation: {ai_recommendation})", None

            # Update the report
            now = datetime.now(timezone.utc)
            approval_source = ApprovalSource.AI_RECOMMENDED.value

            update_data = {
                "verification_status": "verified",
                "approval_source": approval_source,
                "approval_source_details": {
                    "ai_score": verification_doc.get("composite_score"),
                    "ai_recommendation": ai_recommendation,
                    "confirmed_by_id": confirmed_by_id,
                    "confirmed_by_name": confirmed_by_name,
                    "confirmed_by_role": confirmed_by_role,
                    "confirmation_notes": confirmation_notes,
                    "confirmed_at": now
                },
                "verified_by": confirmed_by_id,
                "verified_by_name": confirmed_by_name,
                "verified_at": now,
                "ticket_creation_status": TicketCreationStatus.PENDING.value,
                "requires_authority_confirmation": False,
                "confirmation_received_at": now,
                "confirmed_by": confirmed_by_id,
                "confirmed_by_name": confirmed_by_name,
                "updated_at": now
            }

            await self.db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$set": update_data}
            )

            # Update verification result with authority confirmation
            await self.db.verification_results.update_one(
                {"report_id": report_id},
                {
                    "$set": {
                        "requires_authority_confirmation": False,
                        "authority_confirmation": {
                            "confirmed_by_id": confirmed_by_id,
                            "confirmed_by_name": confirmed_by_name,
                            "confirmed_by_role": confirmed_by_role,
                            "confirmed_at": now,
                            "notes": confirmation_notes
                        }
                    }
                }
            )

            # Update reporter credibility (+5 for verified report)
            await self._update_reporter_credibility(report.user_id, verified=True)

            logger.info(
                f"AI recommendation confirmed for report {report_id} by {confirmed_by_name} ({confirmed_by_role})"
            )

            # Fetch updated report
            updated_doc = await self.db.hazard_reports.find_one({"report_id": report_id})
            updated_report = HazardReport.from_mongo(updated_doc)

            return True, "AI recommendation confirmed. Report verified and ready for ticket creation.", updated_report

        except Exception as e:
            logger.error(f"Error confirming AI recommendation for {report_id}: {e}")
            return False, f"Error: {str(e)}", None

    async def manual_verify_report(
        self,
        report_id: str,
        verified_by_id: str,
        verified_by_name: str,
        verified_by_role: str,
        verification_notes: Optional[str] = None,
        override_ai: bool = False
    ) -> Tuple[bool, str, Optional[HazardReport]]:
        """
        Manually verify a report (without AI recommendation).

        This is for reports in the 40-75% range that need full manual review,
        or for overriding AI decisions.

        Args:
            report_id: The report ID to verify
            verified_by_id: User ID of verifying authority/analyst
            verified_by_name: Name of verifying user
            verified_by_role: Role of verifying user
            verification_notes: Optional notes about the verification
            override_ai: Whether this is overriding an AI rejection

        Returns:
            Tuple of (success, message, updated_report)
        """
        try:
            # Fetch the report
            report_doc = await self.db.hazard_reports.find_one({"report_id": report_id})
            if not report_doc:
                return False, f"Report {report_id} not found", None

            report = HazardReport.from_mongo(report_doc)

            # Validate the report can be verified
            valid_statuses = ["pending", "needs_manual_review"]
            if report.verification_status not in valid_statuses:
                return False, f"Report cannot be verified (status: {report.verification_status})", None

            # Determine approval source
            if verified_by_role in ["authority", "authority_admin"]:
                approval_source = ApprovalSource.AUTHORITY_MANUAL.value
            else:
                approval_source = ApprovalSource.ANALYST_VERIFIED.value

            now = datetime.now(timezone.utc)

            # Build approval details
            approval_details = {
                "verified_by_id": verified_by_id,
                "verified_by_name": verified_by_name,
                "verified_by_role": verified_by_role,
                "verification_notes": verification_notes,
                "verified_at": now,
                "override_ai": override_ai
            }

            # Add AI info if overriding
            if override_ai:
                verification_doc = await self.db.verification_results.find_one({"report_id": report_id})
                if verification_doc:
                    approval_details["ai_score"] = verification_doc.get("composite_score")
                    approval_details["ai_recommendation"] = verification_doc.get("ai_recommendation")

            update_data = {
                "verification_status": "verified",
                "approval_source": approval_source,
                "approval_source_details": approval_details,
                "verified_by": verified_by_id,
                "verified_by_name": verified_by_name,
                "verified_at": now,
                "ticket_creation_status": TicketCreationStatus.PENDING.value,
                "requires_authority_confirmation": False,
                "updated_at": now
            }

            await self.db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$set": update_data}
            )

            # Update reporter credibility (+5 for verified report)
            await self._update_reporter_credibility(report.user_id, verified=True)

            logger.info(
                f"Report {report_id} manually verified by {verified_by_name} ({verified_by_role})"
            )

            # Fetch updated report
            updated_doc = await self.db.hazard_reports.find_one({"report_id": report_id})
            updated_report = HazardReport.from_mongo(updated_doc)

            return True, "Report verified. Ready for ticket creation.", updated_report

        except Exception as e:
            logger.error(f"Error manually verifying report {report_id}: {e}")
            return False, f"Error: {str(e)}", None

    async def reject_report(
        self,
        report_id: str,
        rejected_by_id: str,
        rejected_by_name: str,
        rejected_by_role: str,
        rejection_reason: str
    ) -> Tuple[bool, str, Optional[HazardReport]]:
        """
        Reject a report (manual rejection).

        Args:
            report_id: The report ID to reject
            rejected_by_id: User ID of rejecting authority/analyst
            rejected_by_name: Name of rejecting user
            rejected_by_role: Role of rejecting user
            rejection_reason: Reason for rejection

        Returns:
            Tuple of (success, message, updated_report)
        """
        try:
            # Fetch the report
            report_doc = await self.db.hazard_reports.find_one({"report_id": report_id})
            if not report_doc:
                return False, f"Report {report_id} not found", None

            report = HazardReport.from_mongo(report_doc)

            # Validate the report can be rejected
            if report.verification_status in ["rejected", "auto_rejected"]:
                return False, f"Report already rejected (status: {report.verification_status})", None

            now = datetime.now(timezone.utc)

            update_data = {
                "verification_status": "rejected",
                "rejected_by": rejected_by_id,
                "rejected_by_name": rejected_by_name,
                "rejected_at": now,
                "rejection_reason": rejection_reason,
                "ticket_creation_status": TicketCreationStatus.NOT_ELIGIBLE.value,
                "updated_at": now
            }

            await self.db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$set": update_data}
            )

            # Update reporter credibility (-3 for rejected report)
            await self._update_reporter_credibility(report.user_id, verified=False)

            logger.info(
                f"Report {report_id} rejected by {rejected_by_name} ({rejected_by_role}): {rejection_reason}"
            )

            # Fetch updated report
            updated_doc = await self.db.hazard_reports.find_one({"report_id": report_id})
            updated_report = HazardReport.from_mongo(updated_doc)

            return True, "Report rejected.", updated_report

        except Exception as e:
            logger.error(f"Error rejecting report {report_id}: {e}")
            return False, f"Error: {str(e)}", None

    async def get_pending_recommendations(
        self,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get reports with AI recommendations awaiting confirmation.

        These are reports with scores 75-85% where AI recommends approval
        but authority/analyst confirmation is needed.

        Args:
            limit: Maximum number of results
            skip: Number of results to skip (pagination)

        Returns:
            List of reports awaiting confirmation
        """
        try:
            # Find verification results that need confirmation
            pipeline = [
                {
                    "$match": {
                        "ai_recommendation": AIRecommendation.RECOMMEND_APPROVE.value,
                        "requires_authority_confirmation": True,
                        "$or": [
                            {"authority_confirmation": None},
                            {"authority_confirmation": {"$exists": False}}
                        ]
                    }
                },
                {
                    "$lookup": {
                        "from": "hazard_reports",
                        "localField": "report_id",
                        "foreignField": "report_id",
                        "as": "report"
                    }
                },
                {"$unwind": "$report"},
                {
                    "$match": {
                        "report.verification_status": "needs_manual_review"
                    }
                },
                {"$sort": {"verified_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
                {
                    "$project": {
                        "verification_id": 1,
                        "report_id": 1,
                        "composite_score": 1,
                        "ai_recommendation": 1,
                        "decision_reason": 1,
                        "verified_at": 1,
                        "report.hazard_type": 1,
                        "report.description": 1,
                        "report.location": 1,
                        "report.user_id": 1,
                        "report.created_at": 1
                    }
                }
            ]

            cursor = self.db.verification_results.aggregate(pipeline)
            results = await cursor.to_list(length=limit)

            return results

        except Exception as e:
            logger.error(f"Error getting pending recommendations: {e}")
            return []

    async def get_manual_review_queue(
        self,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get reports in manual review queue (40-75% score range).

        These need full manual review by authority/analyst.

        Args:
            limit: Maximum number of results
            skip: Number of results to skip (pagination)

        Returns:
            List of reports needing manual review
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "ai_recommendation": AIRecommendation.REVIEW.value,
                        "$or": [
                            {"authority_confirmation": None},
                            {"authority_confirmation": {"$exists": False}}
                        ]
                    }
                },
                {
                    "$lookup": {
                        "from": "hazard_reports",
                        "localField": "report_id",
                        "foreignField": "report_id",
                        "as": "report"
                    }
                },
                {"$unwind": "$report"},
                {
                    "$match": {
                        "report.verification_status": "needs_manual_review"
                    }
                },
                {"$sort": {"verified_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
                {
                    "$project": {
                        "verification_id": 1,
                        "report_id": 1,
                        "composite_score": 1,
                        "ai_recommendation": 1,
                        "decision_reason": 1,
                        "layer_results": 1,
                        "verified_at": 1,
                        "report.hazard_type": 1,
                        "report.description": 1,
                        "report.location": 1,
                        "report.user_id": 1,
                        "report.image_url": 1,
                        "report.created_at": 1
                    }
                }
            ]

            cursor = self.db.verification_results.aggregate(pipeline)
            results = await cursor.to_list(length=limit)

            return results

        except Exception as e:
            logger.error(f"Error getting manual review queue: {e}")
            return []

    async def _update_reporter_credibility(
        self,
        user_id: str,
        verified: bool
    ) -> None:
        """
        Update reporter's credibility score based on verification outcome.

        V2 credibility system:
        - +5 for verified reports (capped at 100)
        - -3 for rejected reports (floored at 0)
        - Also updates verified_reports/rejected_reports counters

        Args:
            user_id: The user ID to update
            verified: True if report was verified, False if rejected
        """
        try:
            user_doc = await self.db.users.find_one({"user_id": user_id})
            if not user_doc:
                logger.warning(f"User {user_id} not found for credibility update")
                return

            current_score = user_doc.get("credibility_score", 50)
            verified_reports = user_doc.get("verified_reports", 0)
            rejected_reports = user_doc.get("rejected_reports", 0)
            total_reports = user_doc.get("total_reports", 0)

            if verified:
                # +5 for verified report, capped at 100
                new_score = min(100, current_score + 5)
                verified_reports += 1
            else:
                # -3 for rejected report, floored at 0
                new_score = max(0, current_score - 3)
                rejected_reports += 1

            total_reports += 1

            # Calculate credibility metrics breakdown
            created_at = user_doc.get("created_at", datetime.now(timezone.utc))
            if isinstance(created_at, datetime):
                account_age_days = (datetime.now(timezone.utc) - created_at).days
            else:
                account_age_days = 0

            metrics = CredibilityMetrics.calculate(
                total_reports=total_reports,
                verified_reports=verified_reports,
                rejected_reports=rejected_reports,
                account_age_days=account_age_days
            )

            await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "credibility_score": new_score,
                        "verified_reports": verified_reports,
                        "rejected_reports": rejected_reports,
                        "total_reports": total_reports,
                        "credibility_metrics": metrics.model_dump(),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            logger.info(
                f"Updated credibility for user {user_id}: "
                f"{current_score} -> {new_score} ({'verified' if verified else 'rejected'})"
            )

        except Exception as e:
            logger.error(f"Error updating credibility for user {user_id}: {e}")

    async def get_approval_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get approval statistics for the specified period.

        Args:
            start_date: Start of period (defaults to last 30 days)
            end_date: End of period (defaults to now)

        Returns:
            Statistics dictionary
        """
        try:
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                from datetime import timedelta
                start_date = end_date - timedelta(days=30)

            # Count by approval source
            pipeline = [
                {
                    "$match": {
                        "verification_status": "verified",
                        "verified_at": {"$gte": start_date, "$lte": end_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$approval_source",
                        "count": {"$sum": 1}
                    }
                }
            ]

            cursor = self.db.hazard_reports.aggregate(pipeline)
            results = await cursor.to_list(length=10)

            stats = {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "by_source": {r["_id"]: r["count"] for r in results if r["_id"]},
                "total_verified": sum(r["count"] for r in results),
            }

            # Count rejections
            rejection_count = await self.db.hazard_reports.count_documents({
                "verification_status": {"$in": ["rejected", "auto_rejected"]},
                "updated_at": {"$gte": start_date, "$lte": end_date}
            })
            stats["total_rejected"] = rejection_count

            # Count pending recommendations
            pending_count = await self.db.verification_results.count_documents({
                "ai_recommendation": AIRecommendation.RECOMMEND_APPROVE.value,
                "requires_authority_confirmation": True,
                "$or": [
                    {"authority_confirmation": None},
                    {"authority_confirmation": {"$exists": False}}
                ]
            })
            stats["pending_recommendations"] = pending_count

            return stats

        except Exception as e:
            logger.error(f"Error getting approval stats: {e}")
            return {}


# Singleton instance
_approval_service: Optional[ApprovalService] = None


def get_approval_service(db: AsyncIOMotorDatabase) -> ApprovalService:
    """Get or create approval service instance."""
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService(db)
    return _approval_service
