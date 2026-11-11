from pathlib import Path
import tempfile
import unittest

from rbs.demo import run_demo
from rbs.io import ROOT, read_json
from rbs.packets import load_manifest, prepare
from rbs.report import write_report
from rbs.store import import_submission
from test_packets_store import config, submission


class ReportPresentationTests(unittest.TestCase):
    def test_scripted_example_preserves_all_original_metric_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_demo(read_json(ROOT / 'configs/smoke.json'), root / 'run', root / 'packets')
            report = Path(result['report']).read_text(encoding='utf-8')
            self.assertIn('Scripted demonstration', report)
            self.assertLess(report.index('At a glance'), report.index('Validity boundaries'))
            self.assertIn('not confidence intervals', report)
            self.assertIn('## Shared misses between reviewers', report)
            self.assertIn('| panel\\_blind | r1 / r2 |', report)
            # Golden snapshot recorded before any presentation change.
            expected = read_json(ROOT / 'tests/data/scripted_metrics.json')
            self.assertEqual(read_json(root / 'run/report/metrics.json'), expected)

    def test_missing_reviews_keep_full_bounds_and_unknown_cost_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepare(config(), root / 'run', root / 'packets')
            result = write_report(root / 'run', root / 'report')
            report = Path(result['report']).read_text(encoding='utf-8')
            self.assertIn('0/1 observed; 0.0% to 100.0%', report)
            self.assertIn('Reported cost: unknown', report)
            self.assertIn('Unverified external reviews', report)
            self.assertNotIn('None USD', report)

    def test_identity_and_output_cap_alerts_are_visible_and_escaped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepare(config(), root / 'run', root / 'packets')
            jobs = load_manifest(root / 'run')['jobs']
            for i, job in enumerate(jobs[:2]):
                value = submission(job)
                value['execution'].update(model_id=f'model-{i}|<b>label</b>',
                                          output_tokens=job['output_token_cap'] + 1)
                import_submission(root / 'run', value)
            result = write_report(root / 'run', root / 'report')
            report = Path(result['report']).read_text(encoding='utf-8')
            self.assertIn('multiple reported model/harness identities: **1**', report)
            self.assertIn('declared output-token cap: **2**', report)
            self.assertIn(jobs[0]['job_id'], report)
            self.assertIn('\\|&lt;b&gt;label&lt;/b&gt;', report)
            self.assertNotIn('<b>', report)
