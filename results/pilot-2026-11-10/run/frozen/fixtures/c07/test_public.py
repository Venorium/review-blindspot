import unittest
import candidate

class Checks(unittest.TestCase):
    def test_valid_batch(self):
        store = [1]
        candidate.append_batch(store, [2, 3])
        self.assertEqual(store, [1, 2, 3])
    def test_invalid_first_value(self):
        store = [1]
        with self.assertRaises(ValueError):
            candidate.append_batch(store, [-1])
        self.assertEqual(store, [1])
