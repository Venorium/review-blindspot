import unittest
import candidate

class Checks(unittest.TestCase):
    def test_new_and_repeated_request(self):
        events = []
        self.assertTrue(candidate.record(events, 'r1', 'p1'))
        self.assertFalse(candidate.record(events, 'r1', 'p1'))
        self.assertEqual(events, [('r1', 'p1')])
