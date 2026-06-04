"""Time utilities."""

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string.

    Returns:
        e.g. "2025-07-18T14:30:00.123456+00:00"
    """
    return datetime.now(UTC).isoformat()
