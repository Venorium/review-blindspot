from datetime import timedelta


def add_business_days(start, n):
    if n == 0:
        return start
    day = start
    if day.weekday() >= 5:
        day += timedelta(days=7 - day.weekday())
    weeks, extra = divmod(n, 5)
    day += timedelta(weeks=weeks)
    if day.weekday() + extra >= 5:
        extra += 2
    return day + timedelta(days=extra)
