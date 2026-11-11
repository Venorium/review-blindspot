import unittest
import candidate


class Checks(unittest.TestCase):
    def test_charges(self):
        self.assertEqual(candidate.percent_of(1000, 15), 150)
        self.assertEqual(candidate.percent_of(999, 10), 100)

    def test_refund_without_tie(self):
        self.assertEqual(candidate.percent_of(-1000, 15), -150)

    def test_zero(self):
        self.assertEqual(candidate.percent_of(0, 50), 0)
