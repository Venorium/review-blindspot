import unittest
import candidate

class Checks(unittest.TestCase):
    def test_positive_limit(self):
        self.assertEqual(candidate.recent([1, 2, 3], 2), [2, 3])
    def test_large_limit(self):
        self.assertEqual(candidate.recent([1], 5), [1])
