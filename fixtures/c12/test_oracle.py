import unittest
import candidate

class Checks(unittest.TestCase):
    def test_repeated_product(self):
        self.assertEqual(candidate.totals([('a', 2), ('a', 3)]), {'a': 5})
