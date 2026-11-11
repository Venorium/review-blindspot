import unittest
import candidate

class Checks(unittest.TestCase):
    def test_unknown_tier(self):
        with self.assertRaises(ValueError):
            candidate.quota('other')
        with self.assertRaises(ValueError):
            candidate.quota('Premium')
