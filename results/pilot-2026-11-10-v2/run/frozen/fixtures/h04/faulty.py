class Ledger:
    def __init__(self):
        self.entries = []

    def record(self, src, dst, amount, memo=""):
        if len(memo) > 40:
            raise ValueError("memo too long")
        self.entries.append((src, dst, amount, memo))


def transfer(accounts, ledger, src, dst, amount, memo=""):
    if amount <= 0:
        raise ValueError("amount must be positive")
    if src == dst or src not in accounts or dst not in accounts:
        raise ValueError("unknown or identical accounts")
    if accounts[src] < amount:
        raise ValueError("insufficient funds")
    accounts[src] -= amount
    accounts[dst] += amount
    ledger.record(src, dst, amount, memo)
    return accounts[src]
