import unittest
import candidate

class Checks(unittest.TestCase):
    def test_numeric_order(self):
        events = [{'version': '10'}, {'version': '2'}]
        self.assertEqual([e['version'] for e in candidate.ordered(events)], ['2', '10'])
    def test_numeric_tie_stability(self):
        a, b = {'version': '02', 'id': 'a'}, {'version': '2', 'id': 'b'}
        self.assertEqual(candidate.ordered([b, a]), [b, a])
