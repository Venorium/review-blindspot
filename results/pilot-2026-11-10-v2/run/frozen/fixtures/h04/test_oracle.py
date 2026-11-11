import unittest
import candidate


class Checks(unittest.TestCase):
    def test_rejected_memo_leaves_everything_unchanged(self):
        accounts, ledger = {"a": 10, "b": 0}, candidate.Ledger()
        with self.assertRaises(ValueError):
            candidate.transfer(accounts, ledger, "a", "b", 4, "x" * 41)
        self.assertEqual(accounts, {"a": 10, "b": 0})
        self.assertEqual(ledger.entries, [])

    def test_forty_characters_allowed(self):
        accounts, ledger = {"a": 10, "b": 0}, candidate.Ledger()
        candidate.transfer(accounts, ledger, "a", "b", 1, "x" * 40)
        self.assertEqual(len(ledger.entries), 1)
