import unittest
import candidate


class Checks(unittest.TestCase):
    def test_successful_transfer(self):
        accounts, ledger = {"a": 10, "b": 0}, candidate.Ledger()
        self.assertEqual(candidate.transfer(accounts, ledger, "a", "b", 4, "rent"), 6)
        self.assertEqual(accounts, {"a": 6, "b": 4})
        self.assertEqual(ledger.entries, [("a", "b", 4, "rent")])

    def test_insufficient_funds_changes_nothing(self):
        accounts, ledger = {"a": 1, "b": 0}, candidate.Ledger()
        with self.assertRaises(ValueError):
            candidate.transfer(accounts, ledger, "a", "b", 5)
        self.assertEqual(accounts, {"a": 1, "b": 0})
        self.assertEqual(ledger.entries, [])
