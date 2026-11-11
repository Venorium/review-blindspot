from datetime import datetime, timezone

def utc_day(timestamp):
    return datetime.fromisoformat(timestamp).astimezone(timezone.utc).date().isoformat()
