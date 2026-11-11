def unique_by(items, key):
    return list({key(item): item for item in items}.values())
