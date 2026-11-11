from datetime import date, timedelta
import unittest
import candidate


def reference(start, n):
    day = start
    while day.weekday() >= 5:
        day += timedelta(days=1)
    while n:
        day += timedelta(days=1)
        if day.weekday() < 5:
            n -= 1
    return day


class Checks(unittest.TestCase):
    def test_weekend_start_with_zero(self):
        self.assertEqual(candidate.add_business_days(date(2026, 11, 7), 0), date(2026, 11, 9))

    def test_every_start_day_and_small_n(self):
        for offset in range(14):
            start = date(2026, 11, 2) + timedelta(days=offset)
            for n in range(12):
                self.assertEqual(candidate.add_business_days(start, n), reference(start, n), (start, n))
