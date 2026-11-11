def record(events, request_id, payload):
    if any(p == payload for _, p in events):
        return False
    events.append((request_id, payload))
    return True
