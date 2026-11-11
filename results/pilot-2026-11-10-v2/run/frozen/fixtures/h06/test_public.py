import unittest
import candidate


class Checks(unittest.TestCase):
    def test_exact_match_with_whitespace(self):
        self.assertEqual(candidate.find_user(["alice", "bob"], "  bob "), "bob")

    def test_missing(self):
        self.assertIsNone(candidate.find_user(["alice"], "carol"))
