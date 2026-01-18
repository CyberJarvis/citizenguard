"""
Event Service
Handles event CRUD, registration, and attendance management.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.community import (
    Event,
    EventRegistration,
    EventCreate,
    EventUpdate,
    EventStatus,
    EventType,
    RegistrationStatus,
    AttendanceMarkRequest,
    INDIAN_COASTAL_ZONES,
)
from app.models.user import User
from app.models.rbac import UserRole

logger = logging.getLogger(__name__)

# Global service instance
_event_service: Optional["EventService"] = None


def get_event_service(db: AsyncIOMotorDatabase = None) -> "EventService":
    """Get or create event service singleton"""
    global _event_service
    if _event_service is None:
        _event_service = EventService(db)
    elif db is not None:
        _event_service.db = db
    return _event_service


class EventService:
    """Service for managing events and registrations"""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db
        self._initialized = False

    async def initialize(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service with database connection"""
        if db is not None:
            self.db = db

        if self.db is None:
            logger.warning("No database connection provided to EventService")
            return

        self._initialized = True
        logger.info("EventService initialized successfully")

    def _generate_event_id(self) -> str:
        """Generate unique event ID (EVT-YYYYMMDD-XXXXX)"""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:5].upper()
        return f"EVT-{date_part}-{random_part}"

    def _generate_registration_id(self) -> str:
        """Generate unique registration ID (REG-YYYYMMDD-XXXXX)"""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:5].upper()
        return f"REG-{date_part}-{random_part}"

    # =========================================================================
    # Event CRUD
    # =========================================================================

    async def create_event(
        self,
        user: User,
        event_data: EventCreate
    ) -> Tuple[bool, str, Optional[Event]]:
        """
        Create a new event.

        Args:
            user: Current user (must be organizer of the community)
            event_data: Event creation data

        Returns:
            Tuple of (success, message, event)
        """
        # Check user is organizer
        if user.role not in [UserRole.VERIFIED_ORGANIZER, UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
            return False, "Only verified organizers can create events", None

        # Verify community exists and user is organizer
        community = await self.db.communities.find_one({"community_id": event_data.community_id})
        if not community:
            return False, "Community not found", None

        if community["organizer_id"] != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "You can only create events for communities you organize", None

        # Validate event date is in the future
        if event_data.event_date <= datetime.now(timezone.utc):
            return False, "Event date must be in the future", None

        try:
            now = datetime.now(timezone.utc)

            # Get coastal zone from community
            coastal_zone = community.get("coastal_zone", "Mumbai")

            event = Event(
                event_id=self._generate_event_id(),
                community_id=event_data.community_id,
                organizer_id=user.user_id,
                organizer_name=user.name or user.email,
                title=event_data.title,
                description=event_data.description,
                event_type=event_data.event_type,
                location_address=event_data.location_address,
                location_latitude=event_data.location_latitude,
                location_longitude=event_data.location_longitude,
                coastal_zone=coastal_zone,
                event_date=event_data.event_date,
                event_end_date=event_data.event_end_date,
                registration_deadline=event_data.registration_deadline,
                max_volunteers=event_data.max_volunteers,
                is_emergency=event_data.is_emergency,
                related_hazard_id=event_data.related_hazard_id,
                related_alert_id=event_data.related_alert_id,
                status=EventStatus.PUBLISHED,  # Auto-publish
                points_per_attendee=100 if event_data.is_emergency else 50,
                created_at=now,
                updated_at=now
            )

            # Insert into database
            await self.db.events.insert_one(event.to_mongo())

            # Update community total_events
            await self.db.communities.update_one(
                {"community_id": event_data.community_id},
                {"$inc": {"total_events": 1}}
            )

            logger.info(f"Event created: {event.event_id} by {user.user_id}")

            return True, "Event created successfully!", event

        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return False, "Failed to create event. Please try again.", None

    async def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Get an event by ID."""
        doc = await self.db.events.find_one({"event_id": event_id})
        if doc:
            return Event.from_mongo(doc)
        return None

    async def update_event(
        self,
        event_id: str,
        user: User,
        update_data: EventUpdate
    ) -> Tuple[bool, str, Optional[Event]]:
        """Update an event."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return False, "Event not found", None

        # Check ownership
        if event.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "You don't have permission to update this event", None

        # Can't update completed/cancelled events
        if event.status in [EventStatus.COMPLETED, EventStatus.CANCELLED]:
            return False, f"Cannot update {event.status.value} events", None

        try:
            update_dict = {"updated_at": datetime.now(timezone.utc)}

            if update_data.title is not None:
                update_dict["title"] = update_data.title
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.location_address is not None:
                update_dict["location_address"] = update_data.location_address
            if update_data.location_latitude is not None:
                update_dict["location_latitude"] = update_data.location_latitude
            if update_data.location_longitude is not None:
                update_dict["location_longitude"] = update_data.location_longitude
            if update_data.event_date is not None:
                update_dict["event_date"] = update_data.event_date
            if update_data.event_end_date is not None:
                update_dict["event_end_date"] = update_data.event_end_date
            if update_data.registration_deadline is not None:
                update_dict["registration_deadline"] = update_data.registration_deadline
            if update_data.max_volunteers is not None:
                update_dict["max_volunteers"] = update_data.max_volunteers
            if update_data.status is not None:
                update_dict["status"] = update_data.status.value

            await self.db.events.update_one(
                {"event_id": event_id},
                {"$set": update_dict}
            )

            updated = await self.get_event_by_id(event_id)
            return True, "Event updated successfully", updated

        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return False, "Failed to update event", None

    async def cancel_event(
        self,
        event_id: str,
        user: User
    ) -> Tuple[bool, str]:
        """Cancel an event."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return False, "Event not found"

        if event.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "You don't have permission to cancel this event"

        if event.status == EventStatus.COMPLETED:
            return False, "Cannot cancel a completed event"

        try:
            await self.db.events.update_one(
                {"event_id": event_id},
                {"$set": {
                    "status": EventStatus.CANCELLED.value,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )

            # Update all registrations to cancelled
            await self.db.event_registrations.update_many(
                {"event_id": event_id},
                {"$set": {"registration_status": RegistrationStatus.CANCELLED.value}}
            )

            logger.info(f"Event {event_id} cancelled by {user.user_id}")
            return True, "Event cancelled successfully"

        except Exception as e:
            logger.error(f"Failed to cancel event: {e}")
            return False, "Failed to cancel event"

    async def list_events(
        self,
        community_id: Optional[str] = None,
        coastal_zone: Optional[str] = None,
        event_type: Optional[EventType] = None,
        status: Optional[EventStatus] = None,
        is_emergency: Optional[bool] = None,
        upcoming_only: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Event], int]:
        """List events with filters."""
        query = {}

        if community_id:
            query["community_id"] = community_id
        if coastal_zone:
            query["coastal_zone"] = coastal_zone
        if event_type:
            query["event_type"] = event_type.value
        if status:
            query["status"] = status.value
        else:
            # By default, show published and ongoing events
            query["status"] = {"$in": [EventStatus.PUBLISHED.value, EventStatus.ONGOING.value]}
        if is_emergency is not None:
            query["is_emergency"] = is_emergency
        if upcoming_only:
            query["event_date"] = {"$gte": datetime.now(timezone.utc)}

        total = await self.db.events.count_documents(query)

        cursor = self.db.events.find(query)
        cursor = cursor.sort([("event_date", 1)]).skip(skip).limit(limit)

        events = []
        async for doc in cursor:
            events.append(Event.from_mongo(doc))

        return events, total

    async def get_user_events(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get events the user is registered for."""
        # Get user's registrations
        query = {"user_id": user_id}
        total = await self.db.event_registrations.count_documents(query)

        cursor = self.db.event_registrations.find(query)
        cursor = cursor.sort("registered_at", -1).skip(skip).limit(limit)

        results = []
        async for reg_doc in cursor:
            event_doc = await self.db.events.find_one({"event_id": reg_doc["event_id"]})
            if event_doc:
                event = Event.from_mongo(event_doc)
                results.append({
                    "event": event_to_dict(event),
                    "registration": {
                        "registration_id": reg_doc.get("registration_id"),
                        "status": reg_doc.get("registration_status"),
                        "registered_at": reg_doc.get("registered_at").isoformat() if reg_doc.get("registered_at") else None,
                        "points_awarded": reg_doc.get("points_awarded", 0),
                        "certificate_url": reg_doc.get("certificate_url")
                    }
                })

        return results, total

    async def get_organizer_events(
        self,
        organizer_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Event], int]:
        """Get events organized by a user."""
        query = {"organizer_id": organizer_id}
        total = await self.db.events.count_documents(query)

        cursor = self.db.events.find(query)
        cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)

        events = []
        async for doc in cursor:
            events.append(Event.from_mongo(doc))

        return events, total

    # =========================================================================
    # Registration
    # =========================================================================

    async def register_for_event(
        self,
        event_id: str,
        user: User
    ) -> Tuple[bool, str, Optional[EventRegistration]]:
        """Register a user for an event."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return False, "Event not found", None

        if event.status != EventStatus.PUBLISHED:
            return False, f"Cannot register for {event.status.value} events", None

        # Check if registration deadline passed
        if event.registration_deadline and datetime.now(timezone.utc) > event.registration_deadline:
            return False, "Registration deadline has passed", None

        # Check if event is full
        if event.registered_count >= event.max_volunteers:
            return False, "Event is at full capacity", None

        # Check if already registered
        existing = await self.db.event_registrations.find_one({
            "event_id": event_id,
            "user_id": user.user_id
        })
        if existing:
            return False, "You are already registered for this event", None

        try:
            now = datetime.now(timezone.utc)

            registration = EventRegistration(
                registration_id=self._generate_registration_id(),
                event_id=event_id,
                user_id=user.user_id,
                user_name=user.name or user.email,
                user_email=user.email,
                registration_status=RegistrationStatus.REGISTERED,
                registered_at=now
            )

            await self.db.event_registrations.insert_one(registration.to_mongo())

            # Update event registered_count
            await self.db.events.update_one(
                {"event_id": event_id},
                {"$inc": {"registered_count": 1}}
            )

            logger.info(f"User {user.user_id} registered for event {event_id}")
            return True, "Successfully registered for the event!", registration

        except Exception as e:
            logger.error(f"Failed to register for event: {e}")
            return False, "Failed to register. Please try again.", None

    async def unregister_from_event(
        self,
        event_id: str,
        user: User
    ) -> Tuple[bool, str]:
        """Unregister a user from an event."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return False, "Event not found"

        if event.status not in [EventStatus.DRAFT, EventStatus.PUBLISHED]:
            return False, "Cannot unregister from ongoing or completed events"

        registration = await self.db.event_registrations.find_one({
            "event_id": event_id,
            "user_id": user.user_id
        })
        if not registration:
            return False, "You are not registered for this event"

        try:
            await self.db.event_registrations.delete_one({
                "event_id": event_id,
                "user_id": user.user_id
            })

            await self.db.events.update_one(
                {"event_id": event_id},
                {"$inc": {"registered_count": -1}}
            )

            logger.info(f"User {user.user_id} unregistered from event {event_id}")
            return True, "Successfully unregistered from the event"

        except Exception as e:
            logger.error(f"Failed to unregister from event: {e}")
            return False, "Failed to unregister"

    async def get_event_registrations(
        self,
        event_id: str,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all registrations for an event (organizer only)."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return [], 0

        # Check permission
        if event.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return [], 0

        query = {"event_id": event_id}
        total = await self.db.event_registrations.count_documents(query)

        cursor = self.db.event_registrations.find(query)
        cursor = cursor.sort("registered_at", 1).skip(skip).limit(limit)

        registrations = []
        async for doc in cursor:
            reg = EventRegistration.from_mongo(doc)
            registrations.append({
                "registration_id": reg.registration_id,
                "user_id": reg.user_id,
                "user_name": reg.user_name,
                "user_email": reg.user_email,
                "status": reg.registration_status.value,
                "registered_at": reg.registered_at.isoformat(),
                "attendance_marked_at": reg.attendance_marked_at.isoformat() if reg.attendance_marked_at else None,
                "points_awarded": reg.points_awarded
            })

        return registrations, total

    async def check_user_registration(
        self,
        event_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Check if a user is registered for an event."""
        doc = await self.db.event_registrations.find_one({
            "event_id": event_id,
            "user_id": user_id
        })
        if doc:
            reg = EventRegistration.from_mongo(doc)
            return {
                "is_registered": True,
                "registration_id": reg.registration_id,
                "status": reg.registration_status.value,
                "registered_at": reg.registered_at.isoformat()
            }
        return {"is_registered": False}

    # =========================================================================
    # Attendance
    # =========================================================================

    async def mark_attendance(
        self,
        event_id: str,
        user: User,
        attendance_data: AttendanceMarkRequest
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Mark attendance for users at an event."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return False, "Event not found", {}

        # Check permission
        if event.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "Only the event organizer can mark attendance", {}

        # Event should be ongoing or just ended (within reasonable time)
        if event.status not in [EventStatus.PUBLISHED, EventStatus.ONGOING]:
            return False, "Can only mark attendance for published or ongoing events", {}

        try:
            now = datetime.now(timezone.utc)
            marked_count = 0
            points_awarded_total = 0

            for user_id in attendance_data.user_ids:
                # Find registration
                reg_doc = await self.db.event_registrations.find_one({
                    "event_id": event_id,
                    "user_id": user_id
                })

                if reg_doc and reg_doc.get("registration_status") != RegistrationStatus.ATTENDED.value:
                    # Mark as attended
                    points = event.points_per_attendee

                    await self.db.event_registrations.update_one(
                        {"event_id": event_id, "user_id": user_id},
                        {"$set": {
                            "registration_status": RegistrationStatus.ATTENDED.value,
                            "attendance_marked_at": now,
                            "attendance_marked_by": user.user_id,
                            "points_awarded": points
                        }}
                    )

                    # Update user points
                    await self._update_user_points(user_id, points, event.is_emergency)

                    marked_count += 1
                    points_awarded_total += points

            # Update event attended_count
            await self.db.events.update_one(
                {"event_id": event_id},
                {"$inc": {"attended_count": marked_count}}
            )

            # Award organizer bonus points
            organizer_bonus = marked_count * event.organizer_points_per_attendee
            if organizer_bonus > 0:
                await self._update_user_points(event.organizer_id, organizer_bonus, False, is_organizer=True)

            logger.info(f"Attendance marked for {marked_count} users at event {event_id}")

            return True, f"Attendance marked for {marked_count} participants", {
                "marked_count": marked_count,
                "points_awarded": points_awarded_total,
                "organizer_bonus": organizer_bonus
            }

        except Exception as e:
            logger.error(f"Failed to mark attendance: {e}")
            return False, "Failed to mark attendance", {}

    async def _update_user_points(
        self,
        user_id: str,
        points: int,
        is_emergency: bool,
        is_organizer: bool = False
    ):
        """Update user points and check for badges."""
        from app.services.points_service import get_points_service
        points_service = get_points_service(self.db)
        await points_service.add_points(user_id, points, is_emergency, is_organizer)

    async def complete_event(
        self,
        event_id: str,
        user: User
    ) -> Tuple[bool, str]:
        """Mark an event as completed."""
        event = await self.get_event_by_id(event_id)
        if not event:
            return False, "Event not found"

        if event.organizer_id != user.user_id and user.role != UserRole.AUTHORITY_ADMIN:
            return False, "Only the event organizer can complete this event"

        if event.status == EventStatus.COMPLETED:
            return False, "Event is already completed"

        if event.status == EventStatus.CANCELLED:
            return False, "Cannot complete a cancelled event"

        try:
            now = datetime.now(timezone.utc)

            await self.db.events.update_one(
                {"event_id": event_id},
                {"$set": {
                    "status": EventStatus.COMPLETED.value,
                    "completed_at": now,
                    "updated_at": now
                }}
            )

            # Mark non-attended registrations as no_show
            await self.db.event_registrations.update_many(
                {
                    "event_id": event_id,
                    "registration_status": {"$in": [
                        RegistrationStatus.REGISTERED.value,
                        RegistrationStatus.CONFIRMED.value
                    ]}
                },
                {"$set": {"registration_status": RegistrationStatus.NO_SHOW.value}}
            )

            # Update community total_volunteers
            attended = await self.db.event_registrations.count_documents({
                "event_id": event_id,
                "registration_status": RegistrationStatus.ATTENDED.value
            })

            await self.db.communities.update_one(
                {"community_id": event.community_id},
                {"$inc": {"total_volunteers": attended}}
            )

            logger.info(f"Event {event_id} completed by {user.user_id}")
            return True, "Event completed successfully"

        except Exception as e:
            logger.error(f"Failed to complete event: {e}")
            return False, "Failed to complete event"


def event_to_dict(event: Event, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Convert Event object to response dictionary"""
    return {
        "event_id": event.event_id,
        "community_id": event.community_id,
        "organizer_id": event.organizer_id,
        "organizer_name": event.organizer_name,
        "title": event.title,
        "description": event.description,
        "event_type": event.event_type.value if hasattr(event.event_type, 'value') else event.event_type,
        "location_address": event.location_address,
        "location_latitude": event.location_latitude,
        "location_longitude": event.location_longitude,
        "coastal_zone": event.coastal_zone,
        "event_date": event.event_date.isoformat(),
        "event_end_date": event.event_end_date.isoformat() if event.event_end_date else None,
        "registration_deadline": event.registration_deadline.isoformat() if event.registration_deadline else None,
        "max_volunteers": event.max_volunteers,
        "registered_count": event.registered_count,
        "attended_count": event.attended_count,
        "status": event.status.value if hasattr(event.status, 'value') else event.status,
        "is_emergency": event.is_emergency,
        "points_per_attendee": event.points_per_attendee,
        "cover_image_url": event.cover_image_url,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
        "is_organizer": event.organizer_id == user_id if user_id else False,
        "spots_left": max(0, event.max_volunteers - event.registered_count)
    }
