import unittest
import candidate


class Checks(unittest.TestCase):
    def test_generator_is_consumed_once(self):
        records = ((name, weight) for name, weight in [("a", 1), ("b", 3)])
        self.assertEqual(candidate.allocate(records, 100), {"a": 25, "b": 75})

    def test_zero_total(self):
        self.assertEqual(candidate.allocate([("a", 0), ("b", 0)], 50), {"a": 0, "b": 0})
