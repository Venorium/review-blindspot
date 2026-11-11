import unittest
import candidate


class Checks(unittest.TestCase):
    def test_parent_escape_rejected(self):
        with self.assertRaises(ValueError):
            candidate.resolve_upload("/srv/uploads", "../etc/passwd")

    def test_sibling_prefix_rejected(self):
        with self.assertRaises(ValueError):
            candidate.resolve_upload("/srv/uploads", "../uploads-old/a.txt")

    def test_base_itself_allowed(self):
        self.assertEqual(candidate.resolve_upload("/srv/uploads", "."), "/srv/uploads")
