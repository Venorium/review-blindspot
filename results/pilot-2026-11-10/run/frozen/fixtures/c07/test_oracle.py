import unittest
import candidate

class Checks(unittest.TestCase):
    def test_invalid_later_value_is_atomic(self):
        store = [1]
        with self.assertRaises(ValueError):
            candidate.append_batch(store, [2, -1])
        self.assertEqual(store, [1])
