def cents(mills):
    quotient, remainder = divmod(mills, 10)
    return quotient + (remainder > 5)
