import unittest

from rbs.metrics import total


class ExactTotalTests(unittest.TestCase):
    def test_float_sums_do_not_depend_on_python_version(self):
        # Plain sum() gives 0.9999999999999999 on Python 3.11 and 1.0 from 3.12 onward.
        self.assertEqual(total([0.1] * 10), 1.0)
        self.assertEqual(total([4362.046, 0.001, -0.001]), 4362.046)

    def test_integers_stay_integers(self):
        value = total([108435, 1])
        self.assertEqual(value, 108436)
        self.assertIsInstance(value, int)


if __name__ == "__main__":
    unittest.main()
