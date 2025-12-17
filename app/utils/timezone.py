# Saudi Arabia Timezone Utility
from datetime import datetime, timedelta

# Saudi Arabia is UTC+3
SAUDI_TIMEZONE_OFFSET = timedelta(hours=3)

def get_saudi_time():
    """Get current time in Saudi Arabia timezone (UTC+3)"""
    from datetime import timezone
    saudi_tz = timezone(SAUDI_TIMEZONE_OFFSET)
    return datetime.now(saudi_tz)

def get_saudi_date():
    """Get current date in Saudi Arabia timezone"""
    return get_saudi_time().date()

def to_saudi_time(dt):
    """Convert a datetime to Saudi Arabia timezone"""
    if dt is None:
        return None
    from datetime import timezone
    saudi_tz = timezone(SAUDI_TIMEZONE_OFFSET)
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        return dt.replace(tzinfo=timezone.utc).astimezone(saudi_tz)
    return dt.astimezone(saudi_tz)
