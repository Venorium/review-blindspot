import unittest
import candidate

class Checks(unittest.TestCase):
    def test_distinct_products(self):
        self.assertEqual(candidate.totals([('a', 2), ('b', 3)]), {'a': 2, 'b': 3})
        self.assertEqual(candidate.totals([]), {})
