from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from rbs.cli import main
from rbs.io import ROOT, RBSError, file_hash, read_json
from rbs.packets import MODE_DEMO, check_packet, load_manifest
from rbs.quickstart import quickstart


class QuickstartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_two_default_runs_preserve_first_run_and_packet_integrity(self):
        with patch('rbs.quickstart.tempfile.gettempdir', return_value=str(self.root)):
            first = quickstart()
            before = {p.relative_to(first['workspace']): file_hash(p)
                      for p in Path(first['workspace']).rglob('*') if p.is_file()}
            second = quickstart()
        self.assertNotEqual(first['workspace'], second['workspace'])
        after = {p.relative_to(first['workspace']): file_hash(p)
                 for p in Path(first['workspace']).rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        for result in (first, second):
            self.assertTrue(result['temporary_workspace'])
            self.assertEqual(result['mode'], MODE_DEMO)
            self.assertEqual(result['network_calls_made'], 0)
            self.assertEqual(result['review_jobs'], 16)
            manifest = load_manifest(Path(result['run']))
            for job in manifest['jobs']:
                check_packet(manifest, job)
            metrics = read_json(Path(result['metrics']))
            self.assertIs(metrics['results_are_model_evidence'], False)
            for summary in result['summary']:
                arm = next(a for a in metrics['arms'] if a['arm_id'] == summary['arm_id'])
                self.assertEqual(summary, {key: arm[key] for key in summary})

    def test_json_cli_with_explicit_path_containing_spaces_and_accents(self):
        out = self.root / 'kept demo é ü'
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(['quickstart', '--out', str(out), '--json'])
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertFalse(result['temporary_workspace'])
        self.assertIs(result['results_are_model_evidence'], False)
        for key in ('report', 'metrics', 'outcomes_csv'):
            self.assertTrue(Path(result[key]).is_file())

    def test_guided_output_discloses_simulation_and_report_path(self):
        stdout = StringIO()
        with patch('rbs.quickstart.tempfile.gettempdir', return_value=str(self.root)):
            with redirect_stdout(stdout):
                code = main(['quickstart'])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn('SCRIPTED SIMULATION ONLY', output)
        self.assertIn('No model was called', output)
        self.assertIn('REPORT.md', output)
        self.assertIn('temporary directory', output)
        self.assertIn('Controls rejected:', output)

    def test_existing_destination_refused_without_changing_files(self):
        marker = self.root / 'keep.txt'
        marker.write_text('original', encoding='utf-8')
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main(['quickstart', '--out', str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn('choose a new --out', stderr.getvalue())
        self.assertEqual(list(self.root.iterdir()), [marker])
        self.assertEqual(marker.read_text(encoding='utf-8'), 'original')

    def test_repository_and_parent_destinations_refused_before_writing(self):
        forbidden = ROOT / 'runs' / 'quickstart-must-not-be-created'
        self.assertFalse(forbidden.exists())
        for out in (ROOT, ROOT.parent, forbidden):
            with self.subTest(out=out):
                with self.assertRaisesRegex(RBSError, 'outside the repository'):
                    quickstart(out)
        self.assertFalse(forbidden.exists())

    def test_temporary_directory_inside_repository_refused(self):
        with patch('rbs.quickstart.tempfile.gettempdir', return_value=str(ROOT)):
            with self.assertRaisesRegex(RBSError, 'outside the repository'):
                quickstart()
