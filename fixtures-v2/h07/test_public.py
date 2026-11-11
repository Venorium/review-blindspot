import unittest
import candidate


def flaky(failures, result="ok"):
    state = {"calls": 0}

    def operation():
        state["calls"] += 1
        if state["calls"] <= failures:
            raise candidate.TransientError("try again")
        return result
    return operation


class Checks(unittest.TestCase):
    def test_first_call_succeeds(self):
        sleeps = []
        self.assertEqual(candidate.call_with_retry(flaky(0), 3, sleeps.append, 1), "ok")
        self.assertEqual(sleeps, [])

    def test_one_retry(self):
        sleeps = []
        self.assertEqual(candidate.call_with_retry(flaky(1), 3, sleeps.append, 1), "ok")
        self.assertEqual(sleeps, [1])

    def test_other_errors_propagate(self):
        def broken():
            raise KeyError("x")
        with self.assertRaises(KeyError):
            candidate.call_with_retry(broken, 3, lambda _: None, 1)
