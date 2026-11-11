import unittest
import candidate

class Checks(unittest.TestCase):
    def test_non_ties(self):
        self.assertEqual(candidate.cents(14), 1)
        self.assertEqual(candidate.cents(16), 2)
        self.assertEqual(candidate.cents(0), 0)
