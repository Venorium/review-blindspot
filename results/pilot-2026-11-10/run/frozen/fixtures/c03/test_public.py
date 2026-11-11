import unittest
import candidate

class Checks(unittest.TestCase):
    def test_same_tenant_hit(self):
        cache, calls = {}, []
        def load(t, r):
            calls.append((t, r))
            return t + ':' + r
        self.assertEqual(candidate.lookup(cache, 'a', '1', load), 'a:1')
        self.assertEqual(candidate.lookup(cache, 'a', '1', load), 'a:1')
        self.assertEqual(len(calls), 1)
