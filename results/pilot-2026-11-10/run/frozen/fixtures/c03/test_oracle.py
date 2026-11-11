import unittest
import candidate

class Checks(unittest.TestCase):
    def test_tenant_separation(self):
        cache = {}
        load = lambda t, r: t + ':' + r
        candidate.lookup(cache, 'a', '1', load)
        self.assertEqual(candidate.lookup(cache, 'b', '1', load), 'b:1')
