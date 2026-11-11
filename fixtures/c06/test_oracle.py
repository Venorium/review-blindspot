import unittest
import candidate

class Checks(unittest.TestCase):
    def test_same_payload_different_identity(self):
        events = [('r1', 'same')]
        self.assertTrue(candidate.record(events, 'r2', 'same'))
        self.assertEqual(len(events), 2)
    def test_existing_identity_new_payload(self):
        events = [('r1', 'old')]
        self.assertFalse(candidate.record(events, 'r1', 'new'))
        self.assertEqual(events, [('r1', 'old')])
