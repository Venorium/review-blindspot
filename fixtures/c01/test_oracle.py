import unittest
import candidate

class Checks(unittest.TestCase):
    def test_exact_expiry(self):
        self.assertFalse(candidate.active(10, 10))
