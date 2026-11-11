def divide(n, d):
    quotient = abs(n) // d
    return -quotient if n < 0 else quotient
