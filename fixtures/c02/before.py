def recent(items, limit):
    start = len(items) - limit
    return list(items[max(0, start):])
