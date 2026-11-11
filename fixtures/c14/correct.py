def quota(tier):
    limits = {'basic': 10, 'premium': 100}
    if tier not in limits:
        raise ValueError('unknown tier')
    return limits[tier]
