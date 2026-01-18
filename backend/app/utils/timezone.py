"""
Timezone Utilities for IST (Indian Standard Time)
All timestamps in CoastGuardians are displayed in IST (UTC+5:30)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union

# IST timezone offset (UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)
IST = timezone(IST_OFFSET, name="IST")


def now_ist() -> datetime:
    """
    Get current datetime in IST timezone.

    Returns:
        datetime: Current time in IST
    """
    return datetime.now(IST)


def now_utc() -> datetime:
    """
    Get current datetime in UTC timezone.
    Use this for storing in database.

    Returns:
        datetime: Current time in UTC
    """
    return datetime.now(timezone.utc)


def utc_to_ist(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert UTC datetime to IST.

    Args:
        dt: datetime in UTC (can be timezone-aware or naive)

    Returns:
        datetime in IST timezone, or None if input is None
    """
    if dt is None:
        return None

    # If naive datetime, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(IST)


def ist_to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert IST datetime to UTC.

    Args:
        dt: datetime in IST

    Returns:
        datetime in UTC timezone, or None if input is None
    """
    if dt is None:
        return None

    # If naive datetime, assume it's IST
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)

    return dt.astimezone(timezone.utc)


def format_ist(dt: Optional[datetime], format_str: str = "%d %b %Y, %I:%M %p IST") -> str:
    """
    Format datetime to IST string for display.

    Args:
        dt: datetime object (UTC or any timezone)
        format_str: strftime format string (default: "01 Jan 2025, 10:30 AM IST")

    Returns:
        Formatted string in IST, or empty string if dt is None
    """
    if dt is None:
        return ""

    ist_dt = utc_to_ist(dt)
    return ist_dt.strftime(format_str)


def format_ist_date(dt: Optional[datetime]) -> str:
    """
    Format datetime to IST date string (without time).

    Args:
        dt: datetime object

    Returns:
        Formatted date string like "01 Jan 2025"
    """
    return format_ist(dt, "%d %b %Y")


def format_ist_time(dt: Optional[datetime]) -> str:
    """
    Format datetime to IST time string (without date).

    Args:
        dt: datetime object

    Returns:
        Formatted time string like "10:30 AM"
    """
    return format_ist(dt, "%I:%M %p")


def format_ist_datetime(dt: Optional[datetime]) -> str:
    """
    Format datetime to full IST datetime string.

    Args:
        dt: datetime object

    Returns:
        Formatted datetime string like "01 Jan 2025, 10:30 AM IST"
    """
    return format_ist(dt, "%d %b %Y, %I:%M %p IST")


def format_ist_short(dt: Optional[datetime]) -> str:
    """
    Format datetime to short IST string.

    Args:
        dt: datetime object

    Returns:
        Formatted string like "01/01/2025 10:30"
    """
    return format_ist(dt, "%d/%m/%Y %H:%M")


def to_ist_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO format string in IST timezone.
    Use this for API responses.

    Args:
        dt: datetime object

    Returns:
        ISO format string with IST offset, or None if dt is None
    """
    if dt is None:
        return None

    ist_dt = utc_to_ist(dt)
    return ist_dt.isoformat()


def parse_ist_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime string as IST.

    Args:
        dt_str: datetime string
        format_str: strftime format string

    Returns:
        datetime object with IST timezone
    """
    dt = datetime.strptime(dt_str, format_str)
    return dt.replace(tzinfo=IST)


def get_ist_date_range(days_back: int = 7) -> tuple:
    """
    Get date range from N days ago to now in IST.

    Args:
        days_back: Number of days to go back

    Returns:
        Tuple of (start_datetime, end_datetime) in UTC for database queries
    """
    now = now_ist()
    start = now - timedelta(days=days_back)
    # Convert both to UTC for database queries
    return ist_to_utc(start), ist_to_utc(now)


def get_ist_today_range() -> tuple:
    """
    Get start and end of today in IST (as UTC for database queries).

    Returns:
        Tuple of (start_of_day, end_of_day) in UTC
    """
    now = now_ist()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return ist_to_utc(start_of_day), ist_to_utc(end_of_day)


def relative_time_ist(dt: Optional[datetime]) -> str:
    """
    Get relative time string (e.g., "2 hours ago", "just now") in IST context.

    Args:
        dt: datetime object

    Returns:
        Relative time string
    """
    if dt is None:
        return ""

    now = now_ist()
    ist_dt = utc_to_ist(dt)
    diff = now - ist_dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years > 1 else ''} ago"


# Custom JSON encoder for IST datetime
def ist_datetime_encoder(dt: datetime) -> str:
    """
    JSON encoder for datetime that converts to IST ISO format.
    Use this in Pydantic model Config.json_encoders

    Args:
        dt: datetime object

    Returns:
        ISO format string in IST
    """
    return to_ist_isoformat(dt)


# ID generation with IST timestamp
def generate_ist_timestamp_id(prefix: str = "") -> str:
    """
    Generate an ID with IST timestamp component.

    Args:
        prefix: Optional prefix for the ID (e.g., "RPT", "TKT")

    Returns:
        ID string like "RPT-20250103-XXXXX"
    """
    import uuid
    ist_now = now_ist()
    date_part = ist_now.strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:5].upper()

    if prefix:
        return f"{prefix}-{date_part}-{random_part}"
    return f"{date_part}-{random_part}"
