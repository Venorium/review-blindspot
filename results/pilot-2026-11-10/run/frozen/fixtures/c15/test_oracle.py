import unittest
import candidate

class Checks(unittest.TestCase):
    def test_equal_version_no_effect(self):
        state = {'version': 2, 'value': 'a', 'writes': 7}
        self.assertFalse(candidate.advance(state, 2, 'b'))
        self.assertEqual(state, {'version': 2, 'value': 'a', 'writes': 7})
