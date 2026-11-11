import unittest
import candidate

class Checks(unittest.TestCase):
    def test_before_expiry(self):
        self.assertTrue(candidate.active(9, 10))
    def test_after_expiry(self):
        self.assertFalse(candidate.active(11, 10))
