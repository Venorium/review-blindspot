import unittest
import candidate

class Checks(unittest.TestCase):
    def test_explicit_falsey_values(self):
        for value in [None, False, 0, '']:
            with self.subTest(value=value):
                self.assertEqual(candidate.setting({'x': value}, 'x', 'fallback'), value)
