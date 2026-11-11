import unittest
import candidate


def always_failing():
    raise candidate.TransientError("down")


class Checks(unittest.TestCase):
    def test_no_sleep_after_final_failure(self):
        sleeps = []
        with self.assertRaises(candidate.TransientError):
            candidate.call_with_retry(always_failing, 3, sleeps.append, 1)
        self.assertEqual(sleeps, [1, 2])

    def test_single_attempt_never_sleeps(self):
        sleeps = []
        with self.assertRaises(candidate.TransientError):
            candidate.call_with_retry(always_failing, 1, sleeps.append, 5)
        self.assertEqual(sleeps, [])
