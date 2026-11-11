import unittest
import candidate

class Checks(unittest.TestCase):
    def test_single_digit_versions(self):
        events = [{'version': '2'}, {'version': '1'}]
        self.assertEqual(candidate.ordered(events), list(reversed(events)))
