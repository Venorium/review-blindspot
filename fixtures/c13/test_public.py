import unittest
import candidate

class Checks(unittest.TestCase):
    def test_positive_and_exact(self):
        self.assertEqual(candidate.divide(7, 3), 2)
        self.assertEqual(candidate.divide(-6, 3), -2)
