import unittest
import candidate


class Checks(unittest.TestCase):
    def test_distinct_priorities(self):
        self.assertEqual(candidate.queue_order([("t1", 1), ("t2", 5), ("t3", 3)]), ["t2", "t3", "t1"])

    def test_input_unchanged(self):
        tickets = [("t1", 2), ("t2", 9)]
        candidate.queue_order(tickets)
        self.assertEqual(tickets, [("t1", 2), ("t2", 9)])
