import unittest
import candidate

class Checks(unittest.TestCase):
    def test_known_tiers(self):
        self.assertEqual(candidate.quota('basic'), 10)
        self.assertEqual(candidate.quota('premium'), 100)
