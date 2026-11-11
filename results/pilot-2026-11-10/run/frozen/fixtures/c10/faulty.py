from datetime import datetime

def utc_day(timestamp):
    return datetime.fromisoformat(timestamp).date().isoformat()
