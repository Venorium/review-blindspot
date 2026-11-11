def ordered(events):
    return sorted(events, key=lambda e: str(e['version']))
