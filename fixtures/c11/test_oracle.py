import unittest
import candidate

class Checks(unittest.TestCase):
    def test_touching_endpoints(self):
        self.assertFalse(candidate.overlaps((1, 3), (3, 5)))
