from datetime import timedelta


def add_business_days(start, n):
    day = start
    while day.weekday() >= 5:
        day += timedelta(days=1)
    remaining = n
    while remaining:
        day += timedelta(days=1)
        if day.weekday() < 5:
            remaining -= 1
    return day
