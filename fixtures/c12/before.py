def totals(lines):
    result = {}
    for product, quantity in lines:
        result[product] = quantity
    return result
