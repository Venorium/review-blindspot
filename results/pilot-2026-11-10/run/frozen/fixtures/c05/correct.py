def ordered(events):
    return sorted(events, key=lambda e: int(e['version']))
