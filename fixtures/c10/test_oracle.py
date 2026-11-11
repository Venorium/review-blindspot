import unittest
import candidate

class Checks(unittest.TestCase):
    def test_offset_crosses_date_boundary(self):
        self.assertEqual(candidate.utc_day('2024-01-01T00:30:00+02:00'), '2023-12-31')
        self.assertEqual(candidate.utc_day('2024-01-01T23:30:00-02:00'), '2024-01-02')
