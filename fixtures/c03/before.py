def lookup(cache, tenant, record_id, load):
    key = record_id
    if key not in cache:
        cache[key] = load(tenant, record_id)
    return cache[key]
