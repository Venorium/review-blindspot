def record(events, request_id, payload):
    seen = {p for _, p in events}
    if payload in seen:
        return False
    events.append((request_id, payload))
    return True
