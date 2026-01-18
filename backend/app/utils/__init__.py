"""
Utility Functions
"""

from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token, create_refresh_token, verify_token, decode_token
from app.utils.security import generate_user_id, generate_token_id, mask_email, mask_phone
from app.utils.timezone import (
    IST,
    now_ist,
    now_utc,
    utc_to_ist,
    ist_to_utc,
    format_ist,
    format_ist_date,
    format_ist_time,
    format_ist_datetime,
    format_ist_short,
    to_ist_isoformat,
    relative_time_ist,
    ist_datetime_encoder,
    generate_ist_timestamp_id
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "generate_user_id",
    "generate_token_id",
    "mask_email",
    "mask_phone",
    # IST timezone utilities
    "IST",
    "now_ist",
    "now_utc",
    "utc_to_ist",
    "ist_to_utc",
    "format_ist",
    "format_ist_date",
    "format_ist_time",
    "format_ist_datetime",
    "format_ist_short",
    "to_ist_isoformat",
    "relative_time_ist",
    "ist_datetime_encoder",
    "generate_ist_timestamp_id"
]
