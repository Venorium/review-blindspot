def record(events, request_id, payload):
    if any(r == request_id for r, _ in events):
        return False
    events.append((request_id, payload))
    return True
