import unittest
import candidate


class Checks(unittest.TestCase):
    def test_ascii_case(self):
        self.assertEqual(candidate.find_user(["Alice"], "ALICE"), "Alice")

    def test_full_case_folding(self):
        self.assertEqual(candidate.find_user(["Stra\u00dfe"], "STRASSE"), "Stra\u00dfe")
