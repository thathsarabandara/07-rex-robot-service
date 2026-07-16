from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Return timezone-naive datetime representing UTC now."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def format_iso(dt: datetime | None) -> str | None:
    """Format datetime to ISO 8601 string ending with Z."""
    if dt is None:
        return None
    # Force Z formatting
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
