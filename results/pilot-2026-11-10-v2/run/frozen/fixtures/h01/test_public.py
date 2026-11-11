import unittest
import candidate


class Checks(unittest.TestCase):
    def test_quote_sums_lines(self):
        catalog = candidate.Catalog({"a": 250, "b": 100})
        self.assertEqual(catalog.quote([("a", 2), ("b", 3)]), 800)

    def test_update_before_first_read(self):
        catalog = candidate.Catalog({"a": 250})
        catalog.update_price("a", 300)
        self.assertEqual(catalog.price("a"), 300)

    def test_unknown_sku_and_negative_price(self):
        catalog = candidate.Catalog({"a": 1})
        with self.assertRaises(KeyError):
            catalog.price("missing")
        with self.assertRaises(ValueError):
            catalog.update_price("a", -1)
