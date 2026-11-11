def allocate(records, budget):
    records = list(records)
    total = sum(weight for _, weight in records)
    return {name: budget * weight // total if total else 0 for name, weight in records}
