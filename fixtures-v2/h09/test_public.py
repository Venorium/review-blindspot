import unittest
import candidate


class Checks(unittest.TestCase):
    def test_nested_name(self):
        self.assertEqual(candidate.resolve_upload("/srv/uploads", "a/b.txt"), "/srv/uploads/a/b.txt")

    def test_dot_segments_inside(self):
        self.assertEqual(candidate.resolve_upload("/srv/uploads", "a/../c.txt"), "/srv/uploads/c.txt")

    def test_absolute_rejected(self):
        with self.assertRaises(ValueError):
            candidate.resolve_upload("/srv/uploads", "/etc/passwd")
