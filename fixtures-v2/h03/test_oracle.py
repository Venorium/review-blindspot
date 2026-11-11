import unittest
import candidate


class Checks(unittest.TestCase):
    def test_positive_tie_rounds_up(self):
        self.assertEqual(candidate.percent_of(50, 1), 1)

    def test_refund_mirrors_charge(self):
        for amount in (50, 150, 250, 999, 1234):
            for percent in (1, 3, 7, 50):
                self.assertEqual(candidate.percent_of(-amount, percent), -candidate.percent_of(amount, percent))
