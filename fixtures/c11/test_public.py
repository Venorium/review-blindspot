import unittest
import candidate

class Checks(unittest.TestCase):
    def test_overlap_and_gap(self):
        self.assertTrue(candidate.overlaps((1, 4), (3, 6)))
        self.assertFalse(candidate.overlaps((1, 2), (3, 4)))
