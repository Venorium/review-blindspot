import unittest
import candidate


class Checks(unittest.TestCase):
    def test_update_after_read_is_visible(self):
        catalog = candidate.Catalog({"a": 250, "b": 100})
        self.assertEqual(catalog.quote([("a", 1)]), 250)
        catalog.update_price("a", 400)
        self.assertEqual(catalog.price("a"), 400)
        self.assertEqual(catalog.quote([("a", 2), ("b", 1)]), 900)

    def test_each_sku_read_once_between_updates(self):
        catalog = candidate.Catalog({"a": 250})
        catalog.quote([("a", 1)])
        catalog.quote([("a", 3)])
        self.assertEqual(catalog.reads, 1)
