def recent(items, limit):
    return list(items[-limit:]) if limit else []
