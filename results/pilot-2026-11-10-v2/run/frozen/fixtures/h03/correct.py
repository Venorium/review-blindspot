def percent_of(amount_cents, percent):
    rounded = (abs(amount_cents) * percent + 50) // 100
    return -rounded if amount_cents < 0 else rounded
