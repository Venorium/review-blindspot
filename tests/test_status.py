from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rbs.cli import main
from rbs.demo import run_demo
from rbs.io import ROOT, RBSError, file_hash, read_json
from rbs.packets import load_manifest, prepare
from rbs.status import command_text, format_status, run_status
from rbs.store import import_adjudication, import_submission
from test_packets_store import config, submission


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run, self.packets = self.root / 'run é ü', self.root / 'packets'
        prepare(config(), self.run, self.packets)
        self.manifest = load_manifest(self.run)

    def test_empty_run_is_read_only_and_unknown_cost_is_not_zero(self):
        before = {p.relative_to(self.root): file_hash(p) for p in self.root.rglob('*') if p.is_file()}
        result = run_status(self.run)
        self.assertEqual(result['state'], 'awaiting_reviews')
        self.assertEqual(result['reviews']['missing'], 8)
        self.assertEqual(result['adjudications']['required'], 0)
        self.assertIsNone(result['cost_usd']['known_sum'])
        self.assertEqual(result['cost_usd']['unknown_jobs'], 8)
        after = {p.relative_to(self.root): file_hash(p) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result, run_status(self.run))

    def test_failed_attempt_cost_is_counted_and_abstention_needs_attention(self):
        jobs = self.manifest['jobs']
        failed = submission(jobs[0])
        failed['execution'].update(status='timeout', cost_usd=0.2)
        failed['review'] = None
        import_submission(self.run, failed)
        abstain = submission(jobs[1])
        abstain['review']['verdict'] = 'abstain'
        import_submission(self.run, abstain)
        result = run_status(self.run)
        self.assertEqual(result['state'], 'needs_attention')
        self.assertEqual(result['reviews']['received'], 2)
        self.assertEqual(result['reviews']['missing'], 6)
        self.assertEqual(result['reviews']['failed'], 1)
        self.assertEqual(result['reviews']['abstained'], 1)
        self.assertEqual(result['cost_usd'], {'known_sum': 0.2, 'known_jobs': 1, 'unknown_jobs': 7})
        self.assertEqual(result['execution_errors'], [{'job_id': jobs[0]['job_id'], 'status': 'timeout'}])

    def test_adjudication_pending_then_unresolved_is_not_complete(self):
        target = next(j for j in self.manifest['jobs'] if j['variant'] == 'faulty')
        for job in self.manifest['jobs']:
            value = submission(job)
            if job == target:
                value['review']['verdict'] = 'request_changes'
                value['review']['findings'] = [{'finding_id': 'f1', 'file': 'candidate.py',
                    'line_start': 1, 'line_end': 1, 'severity': 'medium',
                    'description': 'Constructed finding.', 'evidence': 'Constructed evidence.'}]
            import_submission(self.run, value)
        result = run_status(self.run)
        self.assertEqual(result['state'], 'awaiting_adjudication')
        self.assertEqual(result['adjudications']['missing'], 1)
        self.assertTrue(any('grading-packets' in (a['argv'] or []) for a in result['next_actions']))
        path = self.run / 'responses' / (target['job_id'] + '.json')
        import_adjudication(self.run, {'schema_version': 1, 'job_id': target['job_id'],
            'submission_sha256': file_hash(path), 'target_detection': 'unresolved',
            'finding_ids': [], 'rationale': 'Test ambiguity.', 'grader_id': 'test-grader',
            'method': 'manual', 'evidence_reference': 'test_status.py; constructed annotation'})
        result = run_status(self.run)
        self.assertEqual(result['state'], 'needs_attention')
        self.assertEqual(result['adjudications']['unresolved'], 1)

    def test_complete_scripted_run_discloses_simulation_and_new_report_path(self):
        run = self.root / 'demo'
        run_demo(config(), run, self.root / 'demo-packets')
        (run / 'report-001').mkdir()
        result = run_status(run)
        self.assertEqual(result['state'], 'records_complete')
        self.assertEqual(result['cost_usd']['known_sum'], 0)
        self.assertIn('SCRIPTED SIMULATION ONLY', format_status(result))
        self.assertIn('do not certify', format_status(result))
        self.assertEqual(Path(result['next_actions'][-1]['argv'][-1]), (run / 'report-002').resolve())

    def test_complete_external_approvals_are_not_certified(self):
        for job in self.manifest['jobs']:
            import_submission(self.run, submission(job))
        result = run_status(self.run)
        self.assertEqual(result['state'], 'records_complete')
        self.assertIn('unverified', format_status(result))
        self.assertEqual(result['cost_usd']['unknown_jobs'], 8)

    def test_packet_tamper_is_not_reported_as_healthy(self):
        job = self.manifest['jobs'][0]
        (self.packets / job['job_id'] / 'candidate.py').write_text('# changed')
        with self.assertRaises(RBSError):
            run_status(self.run)

    def test_changed_response_is_json_error_with_nonzero_exit(self):
        path = import_submission(self.run, submission(self.manifest['jobs'][0]))
        path.write_text('{}')
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(['status', '--run', str(self.run), '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(json.loads(err.getvalue())['state'], 'invalid_artifacts')
        self.assertNotIn('Traceback', err.getvalue())

    def test_deleted_required_directory_is_error(self):
        (self.run / 'responses').rmdir()
        with self.assertRaisesRegex(RBSError, 'run directory'):
            run_status(self.run)

    def test_cli_json_success_and_human_failure(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(['status', '--run', str(self.run), '--json']), 0)
        self.assertEqual(json.loads(out.getvalue())['reviews']['expected'], 8)
        err = StringIO()
        with redirect_stderr(err):
            self.assertEqual(main(['status', '--run', str(self.root / 'absent')]), 2)
        self.assertIn('ERROR:', err.getvalue())

    def test_suggested_commands_quote_shell_metacharacters(self):
        args = ['python', '-m', 'rbs', 'report', '--run', "C:/run $(nope)/it's here"]
        with patch('rbs.status.os.name', 'nt'):
            text = command_text(args)
            self.assertIn("'C:/run $(nope)/it''s here'", text)
            self.assertTrue(text.startswith("& 'python'"))
        with patch('rbs.status.os.name', 'posix'):
            import shlex
            self.assertEqual(shlex.split(command_text(args)), args)
