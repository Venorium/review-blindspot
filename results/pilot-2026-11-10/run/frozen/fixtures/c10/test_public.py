import unittest
import candidate

class Checks(unittest.TestCase):
    def test_utc_and_same_day(self):
        self.assertEqual(candidate.utc_day('2024-01-01T12:00:00+00:00'), '2024-01-01')
        self.assertEqual(candidate.utc_day('2024-01-01T12:00:00+02:00'), '2024-01-01')
