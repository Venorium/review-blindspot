def quota(tier):
    limits = {'basic': 10, 'premium': 100}
    return limits.get(tier, 100)
