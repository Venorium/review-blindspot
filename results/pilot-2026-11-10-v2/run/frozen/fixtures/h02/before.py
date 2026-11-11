def allocate(records, budget):
    records = list(records)
    total = sum(weight for _, weight in records)
    shares = {}
    for name, weight in records:
        shares[name] = budget * weight // total if total else 0
    return shares
