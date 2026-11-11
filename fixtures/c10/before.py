from datetime import datetime

def utc_day(timestamp):
    parsed = datetime.fromisoformat(timestamp)
    return str(parsed.date())
