import unittest
import candidate

class Checks(unittest.TestCase):
    def test_zero_limit(self):
        self.assertEqual(candidate.recent([1, 2, 3], 0), [])
