import unittest
import candidate


class Checks(unittest.TestCase):
    def test_first_item_is_kept(self):
        rows = [("a", 1), ("b", 2), ("a", 3)]
        self.assertEqual(candidate.unique_by(rows, lambda row: row[0]), [("a", 1), ("b", 2)])
