class Catalog:
    def __init__(self, prices):
        self._prices = dict(prices)
        self.reads = 0

    def _read(self, sku):
        self.reads += 1
        return self._prices[sku]

    def price(self, sku):
        return self._read(sku)

    def update_price(self, sku, cents):
        if cents < 0:
            raise ValueError("price must be non-negative")
        self._prices[sku] = cents

    def quote(self, order):
        return sum(self.price(sku) * quantity for sku, quantity in order)
