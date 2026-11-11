import unittest
import candidate

class Checks(unittest.TestCase):
    def test_new_and_old_version(self):
        state = {'version': 2, 'value': 'a', 'writes': 0}
        self.assertTrue(candidate.advance(state, 3, 'b'))
        self.assertFalse(candidate.advance(state, 1, 'c'))
        self.assertEqual(state, {'version': 3, 'value': 'b', 'writes': 1})
