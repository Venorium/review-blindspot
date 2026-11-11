from datetime import date
import unittest
import candidate


class Checks(unittest.TestCase):
    def test_within_week(self):
        self.assertEqual(candidate.add_business_days(date(2026, 11, 2), 3), date(2026, 11, 5))

    def test_friday_plus_one(self):
        self.assertEqual(candidate.add_business_days(date(2026, 11, 6), 1), date(2026, 11, 9))

    def test_two_weeks(self):
        self.assertEqual(candidate.add_business_days(date(2026, 11, 4), 10), date(2026, 11, 18))

    def test_zero_on_weekday(self):
        self.assertEqual(candidate.add_business_days(date(2026, 11, 4), 0), date(2026, 11, 4))
