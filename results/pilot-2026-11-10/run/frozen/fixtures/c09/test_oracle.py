import unittest
import candidate

class Checks(unittest.TestCase):
    def test_return_is_not_an_alias(self):
        record = {'labels': ['a']}
        result = candidate.labels(record)
        result.append('b')
        self.assertEqual(record['labels'], ['a'])
