def lookup(cache, tenant, record_id, load):
    if record_id not in cache:
        cache[record_id] = load(tenant, record_id)
    return cache[record_id]
