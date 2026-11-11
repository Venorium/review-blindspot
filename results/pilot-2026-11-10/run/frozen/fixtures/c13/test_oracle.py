import unittest
import candidate

class Checks(unittest.TestCase):
    def test_negative_fraction(self):
        self.assertEqual(candidate.divide(-7, 3), -2)
    def test_large_negative(self):
        n = -(10 ** 80 + 1)
        self.assertEqual(candidate.divide(n, 3), -(abs(n) // 3))
