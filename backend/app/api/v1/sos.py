"""
SOS Emergency Alert Endpoints
API endpoints for fishermen SOS emergency alerts
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    BackgroundTasks
)
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.config import settings
from app.database import get_database
from app.models.user import User
from app.models.rbac import UserRole
from app.models.sos import (
    SOSAlert,
    SOSStatus,
    SOSPriority,
    SOSTriggerRequest,
    SOSAcknowledgeRequest,
    SOSDispatchRequest,
    SOSResolveRequest,
    SOSCancelRequest,
    SOSResponse,
    SOSListResponse
)
from app.middleware.security import get_current_user
from app.services.fast2sms_service import fast2sms_service
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sos", tags=["SOS Emergency Alerts"])


async def generate_sos_id(db: AsyncIOMotorDatabase) -> str:
    """Generate unique SOS ID in format SOS-YYYYMMDD-XXXX"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"SOS-{today}-"

    # Find the highest sequence number for today
    latest = await db.sos_alerts.find_one(
        {"sos_id": {"$regex": f"^{prefix}"}},
        sort=[("sos_id", -1)]
    )

    if latest:
        # Extract sequence number and increment
        try:
            seq = int(latest["sos_id"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


async def find_nearest_coast_guard(
    db: AsyncIOMotorDatabase,
    latitude: float,
    longitude: float
) -> Optional[dict]:
    """Find nearest coast guard station (simplified - uses static data)"""
    # In a real implementation, this would query coast guard stations
    # For now, return a placeholder
    return {
        "name": "Coast Guard Station",
        "distance_km": None,
        "contact": "1554"  # Indian Coast Guard emergency number
    }


async def notify_authorities(
    db: AsyncIOMotorDatabase,
    sos_alert: SOSAlert,
    background_tasks: BackgroundTasks
):
    """Notify relevant authorities about the SOS alert"""
    # Find authority users in the region (simplified)
    authorities = await db.users.find({
        "role": {"$in": ["authority", "authority_admin"]},
        "is_active": True
    }).to_list(length=50)

    # Log notification
    logger.info(f"Notifying {len(authorities)} authorities about SOS {sos_alert.sos_id}")

    # In a real implementation, send push notifications to authorities
    # For now, just log
    for auth in authorities:
        logger.info(f"Would notify authority: {auth.get('name', auth.get('email'))}")


@router.post("/trigger", response_model=SOSResponse)
async def trigger_sos(
    request: SOSTriggerRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Trigger an SOS emergency alert.
    Captures GPS location and notifies emergency contacts and authorities.

    - Requires authenticated user
    - Sends SMS to emergency contacts via Fast2SMS
    - Notifies nearby authorities
    - Returns SOS ID for tracking
    """
    try:
        # Generate SOS ID
        sos_id = await generate_sos_id(db)

        # Get user's emergency contacts from profile
        user_doc = await db.users.find_one({"user_id": current_user.user_id})
        emergency_contacts = user_doc.get("emergency_contacts", []) if user_doc else []

        # Create GeoJSON location
        location = {
            "type": "Point",
            "coordinates": [request.longitude, request.latitude]
        }

        # Find nearest coast guard
        nearest_cg = await find_nearest_coast_guard(db, request.latitude, request.longitude)

        # Create SOS alert
        sos_alert = SOSAlert(
            sos_id=sos_id,
            user_id=current_user.user_id,
            user_name=current_user.name or "Unknown",
            user_phone=current_user.phone or "",
            location=location,
            latitude=request.latitude,
            longitude=request.longitude,
            vessel_id=request.vessel_id,
            vessel_name=request.vessel_name,
            crew_count=request.crew_count or 1,
            message=request.message,
            priority=request.priority,
            status=SOSStatus.ACTIVE,
            nearest_coast_guard=nearest_cg,
            emergency_contacts_notified=emergency_contacts
        )

        # Add initial history entry
        sos_alert.add_history_entry(
            action="created",
            user_id=current_user.user_id,
            user_name=current_user.name or "Unknown",
            notes=request.message
        )

        # Save to database
        result = await db.sos_alerts.insert_one(sos_alert.to_mongo())

        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create SOS alert"
            )

        # Send SMS to emergency contacts (background task)
        if emergency_contacts:
            phone_numbers = [c.get("phone") for c in emergency_contacts if c.get("phone")]
            if phone_numbers:
                background_tasks.add_task(
                    send_sos_sms,
                    db,
                    sos_id,
                    phone_numbers,
                    current_user.name or "Unknown",
                    request.latitude,
                    request.longitude,
                    request.vessel_name,
                    request.crew_count or 1,
                    request.message  # Pass distress message to SMS
                )

        # Notify authorities (background task)
        background_tasks.add_task(notify_authorities, db, sos_alert, background_tasks)

        # Audit log
        await AuditLogger.log(
            user_id=current_user.user_id,
            action="sos_triggered",
            details={
                "sos_id": sos_id,
                "latitude": request.latitude,
                "longitude": request.longitude,
                "priority": request.priority.value
            },
            db=db
        )

        logger.info(f"SOS alert {sos_id} created by user {current_user.user_id}")

        return SOSResponse(
            success=True,
            message="SOS alert triggered successfully. Help is on the way.",
            sos_id=sos_id,
            data={
                "latitude": request.latitude,
                "longitude": request.longitude,
                "emergency_contacts_notified": len(emergency_contacts),
                "nearest_coast_guard": nearest_cg
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering SOS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger SOS: {str(e)}"
        )


async def send_sos_sms(
    db: AsyncIOMotorDatabase,
    sos_id: str,
    phone_numbers: List[str],
    fisherman_name: str,
    latitude: float,
    longitude: float,
    vessel_name: Optional[str],
    crew_count: int,
    distress_message: Optional[str] = None
):
    """Background task to send SOS SMS"""
    try:
        result = await fast2sms_service.send_sos_alert(
            phone_numbers=phone_numbers,
            fisherman_name=fisherman_name,
            latitude=latitude,
            longitude=longitude,
            sos_id=sos_id,
            vessel_name=vessel_name,
            crew_count=crew_count,
            distress_message=distress_message
        )

        # Update SOS alert with SMS status
        await db.sos_alerts.update_one(
            {"sos_id": sos_id},
            {
                "$set": {
                    "sms_sent": result.get("success", False),
                    "sms_sent_at": datetime.now(timezone.utc),
                    "sms_recipients": phone_numbers if result.get("success") else [],
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.get("success"):
            logger.info(f"SOS SMS sent for {sos_id} to {len(phone_numbers)} contacts")
        else:
            logger.error(f"Failed to send SOS SMS for {sos_id}: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error sending SOS SMS: {str(e)}")


@router.get("/active", response_model=SOSListResponse)
async def get_active_sos_alerts(
    status_filter: Optional[SOSStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get active SOS alerts.

    - Authority users see all active alerts
    - Citizens see only their own alerts
    """
    try:
        # Build query based on user role
        query = {}

        if current_user.role in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN, UserRole.ANALYST]:
            # Authorities see all alerts
            if status_filter:
                query["status"] = status_filter.value
            else:
                # Default to active/acknowledged/dispatched
                query["status"] = {"$in": ["active", "acknowledged", "dispatched"]}
        else:
            # Citizens see only their own alerts
            query["user_id"] = current_user.user_id
            if status_filter:
                query["status"] = status_filter.value

        # Get total count
        total = await db.sos_alerts.count_documents(query)

        # Get active count
        active_count = await db.sos_alerts.count_documents({
            **query,
            "status": "active"
        }) if not status_filter else 0

        # Get alerts
        cursor = db.sos_alerts.find(query).sort("created_at", -1).skip(skip).limit(limit)
        alerts = await cursor.to_list(length=limit)

        # Convert to response format
        data = []
        for alert in alerts:
            sos = SOSAlert.from_mongo(alert)
            data.append({
                "sos_id": sos.sos_id,
                "user_name": sos.user_name,
                "user_phone": sos.user_phone,
                "latitude": sos.latitude,
                "longitude": sos.longitude,
                "vessel_name": sos.vessel_name,
                "crew_count": sos.crew_count,
                "message": sos.message,
                "status": sos.status.value,
                "priority": sos.priority.value,
                "created_at": sos.created_at.isoformat(),
                "acknowledged_by_name": sos.acknowledged_by_name,
                "acknowledged_at": sos.acknowledged_at.isoformat() if sos.acknowledged_at else None,
                "sms_sent": sos.sms_sent,
                "nearest_coast_guard": sos.nearest_coast_guard
            })

        return SOSListResponse(
            success=True,
            total=total,
            active_count=active_count if not status_filter else await db.sos_alerts.count_documents({"status": "active"}),
            data=data
        )

    except Exception as e:
        logger.error(f"Error fetching SOS alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch SOS alerts: {str(e)}"
        )


@router.get("/{sos_id}", response_model=SOSResponse)
async def get_sos_detail(
    sos_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get detailed information about a specific SOS alert"""
    try:
        alert = await db.sos_alerts.find_one({"sos_id": sos_id})

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SOS alert not found"
            )

        # Check access - authorities can see all, citizens only their own
        if current_user.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN, UserRole.ANALYST]:
            if alert.get("user_id") != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

        sos = SOSAlert.from_mongo(alert)

        return SOSResponse(
            success=True,
            message="SOS alert retrieved",
            sos_id=sos_id,
            data=sos.model_dump(exclude={"id"})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching SOS detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch SOS detail: {str(e)}"
        )


@router.patch("/{sos_id}/acknowledge", response_model=SOSResponse)
async def acknowledge_sos(
    sos_id: str,
    request: SOSAcknowledgeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Acknowledge an SOS alert (Authority only).
    Notifies the fisherman that help is coming.
    """
    # Check authorization
    if current_user.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authority users can acknowledge SOS alerts"
        )

    try:
        # Get the alert
        alert = await db.sos_alerts.find_one({"sos_id": sos_id})

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SOS alert not found"
            )

        if alert.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge SOS in '{alert.get('status')}' status"
            )

        # Update alert
        now = datetime.now(timezone.utc)
        update_data = {
            "status": SOSStatus.ACKNOWLEDGED.value,
            "acknowledged_by": current_user.user_id,
            "acknowledged_at": now,
            "acknowledged_by_name": current_user.name or current_user.email,
            "updated_at": now
        }

        # Add history entry
        history_entry = {
            "action": "acknowledged",
            "user_id": current_user.user_id,
            "user_name": current_user.name or current_user.email,
            "timestamp": now.isoformat(),
            "notes": request.notes
        }

        await db.sos_alerts.update_one(
            {"sos_id": sos_id},
            {
                "$set": update_data,
                "$push": {"history": history_entry}
            }
        )

        # Send SMS to fisherman (background)
        if alert.get("user_phone"):
            background_tasks.add_task(
                send_acknowledged_sms,
                alert.get("user_phone"),
                sos_id,
                current_user.name or "Authority",
                getattr(current_user, 'authority_organization', None)
            )

        # Audit log
        await AuditLogger.log(
            user_id=current_user.user_id,
            action="sos_acknowledged",
            details={"sos_id": sos_id},
            db=db
        )

        logger.info(f"SOS {sos_id} acknowledged by {current_user.user_id}")

        return SOSResponse(
            success=True,
            message="SOS alert acknowledged. Fisherman has been notified.",
            sos_id=sos_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging SOS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge SOS: {str(e)}"
        )


async def send_acknowledged_sms(
    phone: str,
    sos_id: str,
    authority_name: str,
    authority_org: Optional[str]
):
    """Background task to send acknowledgement SMS"""
    try:
        await fast2sms_service.send_sos_acknowledged(
            phone_number=phone,
            sos_id=sos_id,
            authority_name=authority_name,
            authority_org=authority_org
        )
    except Exception as e:
        logger.error(f"Error sending acknowledgement SMS: {str(e)}")


@router.patch("/{sos_id}/dispatch", response_model=SOSResponse)
async def dispatch_rescue(
    sos_id: str,
    request: SOSDispatchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Mark rescue as dispatched (Authority only).
    """
    if current_user.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authority users can dispatch rescue"
        )

    try:
        alert = await db.sos_alerts.find_one({"sos_id": sos_id})

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SOS alert not found"
            )

        if alert.get("status") not in ["active", "acknowledged"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot dispatch for SOS in '{alert.get('status')}' status"
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "status": SOSStatus.DISPATCHED.value,
            "dispatched_by": current_user.user_id,
            "dispatched_at": now,
            "dispatch_notes": request.dispatch_notes,
            "updated_at": now
        }

        history_entry = {
            "action": "dispatched",
            "user_id": current_user.user_id,
            "user_name": current_user.name or current_user.email,
            "timestamp": now.isoformat(),
            "notes": request.dispatch_notes
        }

        await db.sos_alerts.update_one(
            {"sos_id": sos_id},
            {
                "$set": update_data,
                "$push": {"history": history_entry}
            }
        )

        # Send SMS to fisherman
        if alert.get("user_phone"):
            background_tasks.add_task(
                send_dispatched_sms,
                alert.get("user_phone"),
                sos_id,
                request.eta_minutes,
                request.rescue_unit
            )

        await AuditLogger.log(
            user_id=current_user.user_id,
            action="sos_dispatched",
            details={"sos_id": sos_id, "notes": request.dispatch_notes},
            db=db
        )

        logger.info(f"Rescue dispatched for SOS {sos_id}")

        return SOSResponse(
            success=True,
            message="Rescue dispatched. Fisherman has been notified.",
            sos_id=sos_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dispatching rescue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch rescue: {str(e)}"
        )


async def send_dispatched_sms(
    phone: str,
    sos_id: str,
    eta_minutes: Optional[int],
    rescue_unit: Optional[str]
):
    """Background task to send dispatch SMS"""
    try:
        await fast2sms_service.send_sos_dispatched(
            phone_number=phone,
            sos_id=sos_id,
            eta_minutes=eta_minutes,
            rescue_unit=rescue_unit
        )
    except Exception as e:
        logger.error(f"Error sending dispatch SMS: {str(e)}")


@router.patch("/{sos_id}/resolve", response_model=SOSResponse)
async def resolve_sos(
    sos_id: str,
    request: SOSResolveRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Resolve an SOS alert (Authority only).
    Notifies emergency contacts that the person is safe.
    """
    if current_user.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authority users can resolve SOS alerts"
        )

    try:
        alert = await db.sos_alerts.find_one({"sos_id": sos_id})

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SOS alert not found"
            )

        if alert.get("status") == "resolved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SOS alert is already resolved"
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "status": SOSStatus.RESOLVED.value,
            "resolved_by": current_user.user_id,
            "resolved_at": now,
            "resolution_notes": request.resolution_notes,
            "updated_at": now
        }

        history_entry = {
            "action": "resolved",
            "user_id": current_user.user_id,
            "user_name": current_user.name or current_user.email,
            "timestamp": now.isoformat(),
            "notes": f"{request.outcome}: {request.resolution_notes}"
        }

        await db.sos_alerts.update_one(
            {"sos_id": sos_id},
            {
                "$set": update_data,
                "$push": {"history": history_entry}
            }
        )

        # Notify emergency contacts
        emergency_contacts = alert.get("emergency_contacts_notified", [])
        if emergency_contacts:
            phone_numbers = [c.get("phone") for c in emergency_contacts if c.get("phone")]
            if phone_numbers:
                background_tasks.add_task(
                    send_resolved_sms,
                    phone_numbers,
                    sos_id,
                    alert.get("user_name", "Unknown")
                )

        await AuditLogger.log(
            user_id=current_user.user_id,
            action="sos_resolved",
            details={"sos_id": sos_id, "outcome": request.outcome},
            db=db
        )

        logger.info(f"SOS {sos_id} resolved by {current_user.user_id}")

        return SOSResponse(
            success=True,
            message="SOS alert resolved. Emergency contacts have been notified.",
            sos_id=sos_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving SOS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve SOS: {str(e)}"
        )


async def send_resolved_sms(
    phone_numbers: List[str],
    sos_id: str,
    fisherman_name: str
):
    """Background task to send resolution SMS"""
    try:
        await fast2sms_service.send_sos_resolved(
            phone_numbers=phone_numbers,
            sos_id=sos_id,
            fisherman_name=fisherman_name
        )
    except Exception as e:
        logger.error(f"Error sending resolution SMS: {str(e)}")


@router.patch("/{sos_id}/cancel", response_model=SOSResponse)
async def cancel_sos(
    sos_id: str,
    request: SOSCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cancel an SOS alert (by the user who triggered it).
    Only active alerts can be cancelled.
    """
    try:
        alert = await db.sos_alerts.find_one({"sos_id": sos_id})

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SOS alert not found"
            )

        # Check ownership
        if alert.get("user_id") != current_user.user_id:
            # Authorities can also cancel
            if current_user.role not in [UserRole.AUTHORITY, UserRole.AUTHORITY_ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only cancel your own SOS alerts"
                )

        if alert.get("status") not in ["active", "acknowledged"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel SOS in '{alert.get('status')}' status"
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "status": SOSStatus.CANCELLED.value,
            "resolution_notes": f"Cancelled by user: {request.reason}",
            "resolved_at": now,
            "resolved_by": current_user.user_id,
            "updated_at": now
        }

        history_entry = {
            "action": "cancelled",
            "user_id": current_user.user_id,
            "user_name": current_user.name or current_user.email,
            "timestamp": now.isoformat(),
            "notes": request.reason
        }

        await db.sos_alerts.update_one(
            {"sos_id": sos_id},
            {
                "$set": update_data,
                "$push": {"history": history_entry}
            }
        )

        await AuditLogger.log(
            user_id=current_user.user_id,
            action="sos_cancelled",
            details={"sos_id": sos_id, "reason": request.reason},
            db=db
        )

        logger.info(f"SOS {sos_id} cancelled by {current_user.user_id}")

        return SOSResponse(
            success=True,
            message="SOS alert cancelled.",
            sos_id=sos_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling SOS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel SOS: {str(e)}"
        )


@router.get("/my/history", response_model=SOSListResponse)
async def get_my_sos_history(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user's SOS alert history"""
    try:
        query = {"user_id": current_user.user_id}

        total = await db.sos_alerts.count_documents(query)
        active_count = await db.sos_alerts.count_documents({
            **query,
            "status": "active"
        })

        cursor = db.sos_alerts.find(query).sort("created_at", -1).skip(skip).limit(limit)
        alerts = await cursor.to_list(length=limit)

        data = []
        for alert in alerts:
            sos = SOSAlert.from_mongo(alert)
            data.append({
                "sos_id": sos.sos_id,
                "latitude": sos.latitude,
                "longitude": sos.longitude,
                "vessel_name": sos.vessel_name,
                "status": sos.status.value,
                "priority": sos.priority.value,
                "created_at": sos.created_at.isoformat(),
                "resolved_at": sos.resolved_at.isoformat() if sos.resolved_at else None
            })

        return SOSListResponse(
            success=True,
            total=total,
            active_count=active_count,
            data=data
        )

    except Exception as e:
        logger.error(f"Error fetching SOS history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch SOS history: {str(e)}"
        )
