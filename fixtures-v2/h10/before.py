def unique_by(items, key):
    result = []
    seen = []
    for item in items:
        marker = key(item)
        if marker not in seen:
            seen.append(marker)
            result.append(item)
    return result
