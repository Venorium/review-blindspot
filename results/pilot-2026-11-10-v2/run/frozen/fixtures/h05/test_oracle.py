import unittest
import candidate


class Checks(unittest.TestCase):
    def test_equal_priorities_keep_submission_order(self):
        tickets = [("t1", 2), ("t2", 5), ("t3", 2), ("t4", 5)]
        self.assertEqual(candidate.queue_order(tickets), ["t2", "t4", "t1", "t3"])
