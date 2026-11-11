import unittest
from rbs.fixtures import catalog,verify_all
from rbs.io import RBSError, ROOT, read_json
from rbs.packets import corpus_root, plan
class CorpusTests(unittest.TestCase):
    def test_fifteen_pairs(self):self.assertEqual(len(catalog()),15)
    def test_every_pair_has_executable_oracle(self):
        r=verify_all()
        for row in r['rows']:
            with self.subTest(case=row['case_id']):
                self.assertTrue(row['ok'],row['checks']);self.assertGreater(row['checks']['faulty_oracle']['failures'],0);self.assertEqual(row['checks']['faulty_oracle']['errors'],0)


class CorpusV2Tests(unittest.TestCase):
    def test_ten_pairs_with_executable_witnesses(self):
        result = verify_all(ROOT / 'fixtures-v2')
        self.assertEqual(result['pairs'], 10)
        for row in result['rows']:
            with self.subTest(case=row['case_id']):
                self.assertTrue(row['ok'], row['checks'])
                self.assertEqual(row['checks']['faulty_oracle']['errors'], 0)

    def test_config_selects_corpus_and_rejects_other_paths(self):
        config = read_json(ROOT / 'configs/pilot-local-v2.json')
        self.assertEqual(plan(config)['review_jobs'], 200)
        self.assertEqual(set(catalog(corpus_root(config))), {f'h{i:02d}' for i in range(1, 11)})
        for bad in ('../fixtures', 'tests', 'fixtures/c01', 7):
            with self.assertRaises(RBSError):
                corpus_root({'corpus': bad})
