import unittest
import candidate


class Checks(unittest.TestCase):
    def test_identity_key(self):
        self.assertEqual(candidate.unique_by([3, 1, 3, 2, 1], lambda x: x), [3, 1, 2])

    def test_empty_and_unchanged(self):
        items = [1, 1]
        self.assertEqual(candidate.unique_by([], lambda x: x), [])
        candidate.unique_by(items, lambda x: x)
        self.assertEqual(items, [1, 1])
