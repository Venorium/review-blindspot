def totals(lines):
    result = {}
    for product, quantity in lines:
        result[product] = result.get(product, 0) + quantity
    return result
