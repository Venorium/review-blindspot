import unittest
import candidate


class Checks(unittest.TestCase):
    def test_list_input(self):
        self.assertEqual(candidate.allocate([("a", 1), ("b", 3)], 100), {"a": 25, "b": 75})

    def test_rounding_down(self):
        self.assertEqual(candidate.allocate([("a", 1), ("b", 1), ("c", 1)], 10), {"a": 3, "b": 3, "c": 3})
