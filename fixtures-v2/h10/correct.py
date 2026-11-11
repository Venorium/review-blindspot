def unique_by(items, key):
    first = {}
    for item in items:
        first.setdefault(key(item), item)
    return list(first.values())
