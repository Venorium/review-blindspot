import unittest
import candidate

class Checks(unittest.TestCase):
    def test_equal_values(self):
        self.assertEqual(candidate.labels({'labels': ['a', 'b']}), ['a', 'b'])
