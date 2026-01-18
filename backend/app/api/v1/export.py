"""
Unified Export API Router
Provides export functionality for all authorized roles (Analyst, Authority, Admin)
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.middleware.rbac import get_current_user
from app.models.user import User
from app.models.rbac import UserRole
from app.models.analyst import ExportJob, ExportStatus, ExportFormat, ExportType
from app.services.export_service import get_export_service

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# ENUMS AND MODELS
# =============================================================================

class DataType(str, Enum):
    """Extended data types for unified export"""
    REPORTS = "reports"
    TICKETS = "tickets"
    ALERTS = "alerts"
    USERS = "users"
    AUDIT_LOGS = "audit_logs"
    SMI = "smi"
    ANALYTICS = "analytics"
    TRENDS = "trends"
    GEO = "geo"


class UnifiedExportRequest(BaseModel):
    """Request model for unified export"""
    data_type: DataType = Field(..., description="Type of data to export")
    export_format: ExportFormat = Field(..., description="Export format: csv, excel, pdf")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Query filters")
    date_range: Dict[str, Any] = Field(default_factory=dict, description="Date range config")
    columns: Optional[List[str]] = Field(None, description="Columns to include")
    format_settings: Optional[Dict[str, Any]] = Field(None, description="Format-specific settings")


# =============================================================================
# ROLE-BASED ACCESS CONTROL
# =============================================================================

# Define which data types each role can export
ROLE_DATA_ACCESS = {
    UserRole.ANALYST: [
        DataType.REPORTS, DataType.TICKETS, DataType.ALERTS,
        DataType.SMI, DataType.ANALYTICS, DataType.TRENDS, DataType.GEO
    ],
    UserRole.AUTHORITY: [
        DataType.REPORTS, DataType.TICKETS, DataType.ALERTS,
        DataType.ANALYTICS, DataType.TRENDS, DataType.GEO
    ],
    UserRole.AUTHORITY_ADMIN: [
        DataType.REPORTS, DataType.TICKETS, DataType.ALERTS, DataType.USERS,
        DataType.AUDIT_LOGS, DataType.SMI, DataType.ANALYTICS, DataType.TRENDS, DataType.GEO
    ],
}

# Roles that get PII filtered (analysts don't see PII)
PII_FILTERED_ROLES = [UserRole.ANALYST]


def can_export_data_type(user: User, data_type: DataType) -> bool:
    """Check if user's role can export the specified data type"""
    allowed_types = ROLE_DATA_ACCESS.get(user.role, [])
    return data_type in allowed_types


def should_filter_pii(user: User) -> bool:
    """Check if PII should be filtered for this user"""
    return user.role in PII_FILTERED_ROLES


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def map_data_type_to_export_type(data_type: DataType) -> ExportType:
    """Map unified data type to legacy ExportType for backward compatibility"""
    mapping = {
        DataType.REPORTS: ExportType.REPORTS,
        DataType.ANALYTICS: ExportType.ANALYTICS,
        DataType.TRENDS: ExportType.TRENDS,
        DataType.GEO: ExportType.GEO,
        DataType.TICKETS: ExportType.CUSTOM,
        DataType.ALERTS: ExportType.CUSTOM,
        DataType.USERS: ExportType.CUSTOM,
        DataType.AUDIT_LOGS: ExportType.CUSTOM,
        DataType.SMI: ExportType.CUSTOM,
    }
    return mapping.get(data_type, ExportType.CUSTOM)


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.post("")
async def create_unified_export(
    export_data: UnifiedExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a unified export job for any authorized role.

    - **Analyst**: Can export reports (PII filtered), tickets, alerts, SMI data
    - **Authority**: Can export reports (full), tickets, alerts
    - **Admin**: Can export all data including users and audit logs
    """
    # Check if user role is allowed to export
    if current_user.role not in ROLE_DATA_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role is not authorized to export data"
        )

    # Check if user can export this specific data type
    if not can_export_data_type(current_user, export_data.data_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your role cannot export {export_data.data_type.value} data"
        )

    try:
        now = datetime.now(timezone.utc)
        job_id = f"EXP_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

        # Map to legacy export type
        export_type = map_data_type_to_export_type(export_data.data_type)

        # Add data_type to query_config for extended types
        query_config = export_data.filters.copy()
        query_config["_data_type"] = export_data.data_type.value
        query_config["_include_pii"] = not should_filter_pii(current_user)

        export_job = ExportJob(
            job_id=job_id,
            user_id=current_user.user_id,
            export_type=export_type,
            export_format=export_data.export_format,
            query_config=query_config,
            date_range=export_data.date_range,
            columns=export_data.columns,
            status=ExportStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=24)
        )

        await db.export_jobs.insert_one(export_job.to_mongo())

        # Process the export immediately
        export_service = get_export_service(db)
        success = await process_extended_export(
            export_service,
            job_id,
            export_data.data_type,
            db,
            should_filter_pii(current_user)
        )

        # Get updated job status
        updated_job = await db.export_jobs.find_one({"job_id": job_id})

        logger.info(
            f"User {current_user.user_id} ({current_user.role.value}) "
            f"created export job {job_id} for {export_data.data_type.value}, success={success}"
        )

        if updated_job:
            job_data = ExportJob.from_mongo(updated_job)
            return {
                "success": True,
                "job_id": job_id,
                "status": job_data.status.value,
                "progress": job_data.progress,
                "file_name": job_data.file_name,
                "file_size": job_data.file_size,
                "record_count": job_data.record_count,
                "message": "Export completed successfully" if success else "Export failed"
            }

        return {
            "success": False,
            "job_id": job_id,
            "error": "Export processing failed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating unified export job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export job"
        )


async def process_extended_export(
    export_service,
    job_id: str,
    data_type: DataType,
    db: AsyncIOMotorDatabase,
    filter_pii: bool
) -> bool:
    """
    Process export for extended data types (tickets, alerts, users, audit_logs)
    """
    # For standard types, use the existing service
    if data_type in [DataType.REPORTS, DataType.ANALYTICS, DataType.TRENDS, DataType.GEO]:
        return await export_service.process_export_job(job_id)

    # For extended types, fetch data differently
    try:
        job_doc = await db.export_jobs.find_one({"job_id": job_id})
        if not job_doc:
            return False

        job = ExportJob.from_mongo(job_doc)

        # Update status to processing
        await db.export_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": ExportStatus.PROCESSING.value, "progress": 10}}
        )

        # Fetch data based on type
        data = await fetch_extended_data(db, data_type, job.query_config, job.date_range, filter_pii)

        await db.export_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"progress": 60}}
        )

        # Generate file
        if job.export_format == ExportFormat.CSV:
            content = await export_service.generate_csv(data, job.columns)
            extension = "csv"
        elif job.export_format == ExportFormat.EXCEL:
            content = await export_service.generate_excel(data, ExportType.CUSTOM, job.columns)
            extension = "xlsx"
        else:  # PDF
            title = f"CoastGuardian {data_type.value.replace('_', ' ').title()} Report"
            content = await generate_extended_pdf(data, data_type, title)
            extension = "pdf"

        # Save file
        from pathlib import Path
        EXPORT_DIR = Path("exports")
        EXPORT_DIR.mkdir(exist_ok=True)

        file_name = f"{job_id}_{data_type.value}_{datetime.now().strftime('%Y%m%d')}.{extension}"
        file_path = EXPORT_DIR / file_name

        with open(file_path, 'wb') as f:
            f.write(content)

        # Update job as completed
        await db.export_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": ExportStatus.COMPLETED.value,
                    "progress": 100,
                    "completed_at": datetime.now(timezone.utc),
                    "file_path": str(file_path),
                    "file_name": file_name,
                    "file_size": len(content),
                    "record_count": len(data) if isinstance(data, list) else 1
                }
            }
        )

        return True

    except Exception as e:
        logger.error(f"Error processing extended export {job_id}: {e}")
        await db.export_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": ExportStatus.FAILED.value,
                    "error_message": str(e),
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )
        return False


def clean_query_filters(query_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean query config by removing:
    - Internal keys (starting with _)
    - UI placeholder values ('all', 'All', '', None)
    - Pagination/sort keys
    """
    if not query_config:
        return {}

    exclude_values = {'all', 'All', '', None}
    exclude_keys = {'page', 'limit', 'skip', 'sort', 'sort_by', 'sort_order'}

    cleaned = {}
    for key, value in query_config.items():
        # Skip internal keys
        if key.startswith('_'):
            continue
        # Skip pagination/sort keys
        if key in exclude_keys:
            continue
        # Skip placeholder values
        if value in exclude_values:
            continue
        # Skip empty lists
        if isinstance(value, list) and len(value) == 0:
            continue
        # Include valid values
        cleaned[key] = value

    return cleaned


async def fetch_extended_data(
    db: AsyncIOMotorDatabase,
    data_type: DataType,
    query_config: Dict[str, Any],
    date_range: Dict[str, Any],
    filter_pii: bool
) -> List[Dict[str, Any]]:
    """Fetch data for extended data types"""

    # Clean query config - remove internal keys and placeholder values
    clean_config = clean_query_filters(query_config)

    logger.info(f"Fetching data for type: {data_type.value}, date_range: {date_range}, filters: {clean_config}")

    if data_type == DataType.TICKETS:
        collection = db.tickets
        # Build date filter for tickets (uses created_at)
        date_filter = build_date_filter(date_range, "created_at")
        query = {**date_filter, **clean_config}
        logger.info(f"Tickets query: {query}")
        cursor = collection.find(query).sort("created_at", -1).limit(10000)
        data = await cursor.to_list(10000)
        logger.info(f"Found {len(data)} tickets")

    elif data_type == DataType.ALERTS:
        collection = db.alerts
        # Alerts use created_at for filtering
        date_filter = build_date_filter(date_range, "created_at")
        query = {**date_filter, **clean_config}
        logger.info(f"Alerts query: {query}")
        cursor = collection.find(query).sort("created_at", -1).limit(10000)
        data = await cursor.to_list(10000)
        logger.info(f"Found {len(data)} alerts")

    elif data_type == DataType.USERS:
        collection = db.users
        # Users - fetch all, date filter is optional
        date_filter = build_date_filter(date_range, "created_at") if date_range else {}
        query = {**date_filter, **clean_config}
        logger.info(f"Users query: {query}")
        cursor = collection.find(query).sort("created_at", -1).limit(10000)
        data = await cursor.to_list(10000)
        logger.info(f"Found {len(data)} users")

    elif data_type == DataType.AUDIT_LOGS:
        collection = db.audit_logs
        # Audit logs use timestamp field, not created_at
        date_filter = build_date_filter(date_range, "timestamp")
        query = {**date_filter, **clean_config}
        logger.info(f"Audit logs query: {query}")
        cursor = collection.find(query).sort("timestamp", -1).limit(10000)
        data = await cursor.to_list(10000)
        logger.info(f"Found {len(data)} audit logs")

    elif data_type == DataType.SMI:
        # Try smi_posts collection first, then fall back to hazard_reports with source
        try:
            collection = db.smi_posts
            date_filter = build_date_filter(date_range, "created_at")
            query = {**date_filter, **clean_config}
            cursor = collection.find(query).sort("created_at", -1).limit(10000)
            data = await cursor.to_list(10000)
            logger.info(f"Found {len(data)} SMI posts")
        except Exception:
            # Fallback to hazard_reports with social media source
            collection = db.hazard_reports
            date_filter = build_date_filter(date_range, "created_at")
            query = {**date_filter, **clean_config, "source": {"$exists": True}}
            cursor = collection.find(query).sort("created_at", -1).limit(10000)
            data = await cursor.to_list(10000)
            logger.info(f"Found {len(data)} SMI records from hazard_reports")

    else:
        data = []
        logger.warning(f"Unknown data type: {data_type}")

    # Process data - convert ObjectId and datetime to strings, filter PII
    processed_data = []
    for record in data:
        processed = process_record(record, filter_pii)
        processed_data.append(processed)

    logger.info(f"Returning {len(processed_data)} processed records for {data_type.value}")
    return processed_data


def build_date_filter(date_range: Dict[str, Any], date_field: str = "created_at") -> Dict[str, Any]:
    """Build MongoDB date filter from date range config

    Args:
        date_range: Date range configuration with 'start', 'end', or 'relative' keys
        date_field: The field name to filter on (e.g., 'created_at', 'timestamp', 'issued_at')

    Returns:
        MongoDB query filter dict
    """
    if not date_range:
        return {}

    date_filter = {}

    if date_range.get("start"):
        try:
            start_date = datetime.fromisoformat(date_range["start"].replace('Z', '+00:00'))
            date_filter[date_field] = {"$gte": start_date}
        except (ValueError, AttributeError):
            pass

    if date_range.get("end"):
        try:
            end_date = datetime.fromisoformat(date_range["end"].replace('Z', '+00:00'))
            if date_field in date_filter:
                date_filter[date_field]["$lte"] = end_date
            else:
                date_filter[date_field] = {"$lte": end_date}
        except (ValueError, AttributeError):
            pass

    # Handle relative date ranges
    if date_range.get("relative"):
        now = datetime.now(timezone.utc)
        relative = date_range["relative"]
        if relative == "7days":
            start = now - timedelta(days=7)
        elif relative == "30days":
            start = now - timedelta(days=30)
        elif relative == "90days":
            start = now - timedelta(days=90)
        elif relative == "year":
            start = now - timedelta(days=365)
        elif relative == "all":
            # No date filter for "all time"
            return {}
        else:
            start = now - timedelta(days=30)
        date_filter[date_field] = {"$gte": start, "$lte": now}

    return date_filter


def process_record(record: Dict[str, Any], filter_pii: bool) -> Dict[str, Any]:
    """Process a record, optionally filtering PII"""
    # Convert ObjectId to string
    if "_id" in record:
        record["_id"] = str(record["_id"])

    # Convert datetime to ISO format
    for key, value in list(record.items()):
        if isinstance(value, datetime):
            record[key] = value.isoformat()

    # Filter PII if needed
    if filter_pii:
        pii_fields = ['name', 'email', 'phone', 'address', 'full_name', 'user_name',
                     'contact', 'personal_info', 'profile_picture', 'reporter_name',
                     'user_email', 'user_phone']
        for field in pii_fields:
            if field in record:
                record[field] = "[REDACTED]"

    return record


async def generate_extended_pdf(
    data: List[Dict[str, Any]],
    data_type: DataType,
    title: str
) -> bytes:
    """Generate PDF for extended data types"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=30)
    story.append(Paragraph(title, title_style))

    # Generation info
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", info_style))
    story.append(Spacer(1, 20))

    if not data:
        story.append(Paragraph("No data available for the selected criteria.", styles['Normal']))
    else:
        story.append(Paragraph(f"Total Records: {len(data)}", styles['Heading2']))
        story.append(Spacer(1, 10))

        # Get columns based on data type
        if data_type == DataType.TICKETS:
            columns = ['ticket_id', 'status', 'priority', 'created_at']
            headers = ['Ticket ID', 'Status', 'Priority', 'Created']
        elif data_type == DataType.ALERTS:
            columns = ['alert_id', 'title', 'severity', 'status', 'issued_at']
            headers = ['Alert ID', 'Title', 'Severity', 'Status', 'Issued']
        elif data_type == DataType.USERS:
            columns = ['user_id', 'name', 'role', 'is_active', 'created_at']
            headers = ['User ID', 'Name', 'Role', 'Active', 'Joined']
        elif data_type == DataType.AUDIT_LOGS:
            columns = ['timestamp', 'user_name', 'action_type', 'resource']
            headers = ['Timestamp', 'User', 'Action', 'Resource']
        else:
            columns = list(data[0].keys())[:5] if data else []
            headers = [c.replace('_', ' ').title() for c in columns]

        table_data = [headers]
        for record in data[:50]:  # Limit to 50 for PDF
            row = []
            for col in columns:
                value = record.get(col, '')
                if isinstance(value, str) and len(value) > 30:
                    value = value[:27] + '...'
                row.append(str(value) if value else '')
            table_data.append(row)

        if len(data) > 50:
            table_data.append(['...', f'{len(data) - 50} more records', '', '', ''][:len(columns)])

        col_width = 6.5 * inch / len(columns)
        t = Table(table_data, colWidths=[col_width] * len(columns))
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E8E8E8')]),
        ]))
        story.append(t)

    # Footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    story.append(Paragraph("CoastGuardian - Ocean Hazard Reporting Platform for INCOIS", footer_style))

    doc.build(story)
    return output.getvalue()


@router.get("/{job_id}")
async def get_export_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get status of an export job"""
    job_doc = await db.export_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user.user_id
    })

    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    job = ExportJob.from_mongo(job_doc)

    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": job.progress,
        "file_name": job.file_name,
        "file_size": job.file_size,
        "record_count": job.record_count,
        "error_message": job.error_message
    }


@router.get("/{job_id}/download")
async def download_export_file(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Download a completed export file"""
    job_doc = await db.export_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user.user_id
    })

    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    job = ExportJob.from_mongo(job_doc)

    if job.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is not ready. Current status: {job.status.value}"
        )

    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found"
        )

    # Determine content type
    content_type_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"
    }

    file_ext = job.file_name.split('.')[-1] if job.file_name else "csv"
    content_type = content_type_map.get(file_ext, "application/octet-stream")

    return FileResponse(
        path=job.file_path,
        filename=job.file_name,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={job.file_name}"}
    )


@router.delete("/{job_id}")
async def delete_export(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete an export job and its file"""
    job_doc = await db.export_jobs.find_one({
        "job_id": job_id,
        "user_id": current_user.user_id
    })

    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )

    job = ExportJob.from_mongo(job_doc)

    # Delete file if exists
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete export file {job.file_path}: {e}")

    # Delete job record
    await db.export_jobs.delete_one({"job_id": job_id})

    return {"success": True, "message": "Export job deleted successfully"}
