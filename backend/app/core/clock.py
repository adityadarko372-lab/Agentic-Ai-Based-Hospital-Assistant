"""Time helpers.

The demo hospital is in India, so "today" for appointment rules means the
date in India Standard Time (UTC+05:30). India has no daylight saving, so a
fixed offset is exact and avoids needing the tzdata package on Windows.
"""

from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def utc_now() -> datetime:
    """Current time in UTC, timezone-aware (SQLModel requires aware values)."""
    return datetime.now(timezone.utc)


def today_in_india() -> date:
    return datetime.now(IST).date()


def as_utc(value: datetime) -> datetime:
    """Make sure a datetime read back from SQLite carries the UTC offset, so
    JSON responses are unambiguous and browsers show the right local time."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
