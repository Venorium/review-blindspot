import unittest
import candidate

class Checks(unittest.TestCase):
    def test_half_cent(self):
        self.assertEqual(candidate.cents(15), 2)
        self.assertEqual(candidate.cents(25), 3)
