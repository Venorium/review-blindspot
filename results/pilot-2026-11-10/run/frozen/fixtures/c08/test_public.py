import unittest
import candidate

class Checks(unittest.TestCase):
    def test_present_and_missing(self):
        self.assertEqual(candidate.setting({'x': 3}, 'x', 9), 3)
        self.assertEqual(candidate.setting({}, 'x', 9), 9)
