from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load_module('review_blindspot', ROOT / 'skills/review-blindspot/scripts/review_blindspot.py')
installer = load_module('install_codex_skill', ROOT / 'tools/install_codex_skill.py')


@unittest.skipUnless(shutil.which('git'), 'Git is required for the Codex integration')
class CodexSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rbs-codex-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "project with space é"
        self.repo.mkdir()
        self.env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        self.git('init', '--quiet')
        self.git('config', 'core.autocrlf', 'false')
        (self.repo / 'expiry.py').write_text('def active(now, expiry):\n    return now < expiry\n', encoding='utf-8')
        self.git('add', '--all')
        self.git('commit', '--quiet', '-m', 'Trusted test base')
        (self.repo / 'expiry.py').write_text('def active(now, expiry):\n    return now <= expiry\n', encoding='utf-8')
        self.directory = self.root / 'review'

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=RBS test',
            '-c', 'user.email=rbs@example.invalid', '-c', 'commit.gpgsign=false',
            '-c', 'core.hooksPath=' + str(self.root / 'no-hooks'), *args],
            env=self.env, capture_output=True, check=True)
        return result.stdout

    def capture(self):
        return helper.capture(self.repo, self.directory)

    def ledger(self):
        return helper.read_json(self.directory / 'review.json')

    def save(self, ledger):
        (self.directory / 'review.json').write_text(json.dumps(ledger), encoding='utf-8')

    def document(self, status='supported'):
        ledger = self.ledger()
        ledger['reviewer_context'] = 'same_session'
        for record in ledger['files']:
            record.update(disposition='reviewed', reason='Synthetic test scope.')
        ledger['checks'] = [{'id':'C1','claim':'Synthetic claim, not a model review.',
            'files':[f['path'] for f in ledger['files']], 'status':status,
            'evidence':[{'kind':'inspection','reference':'expiry.py:2','observation':'Constructed observation.', 'sha256':None}]}]
        self.save(ledger)
        return ledger

    def test_initial_capture_exposes_unreviewed_scope_and_is_read_only(self):
        # Working tree and index only: Git may write its own maintenance files under .git.
        def state_of_repo():
            files = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*')
                     if p.is_file() and '.git' not in p.relative_to(self.repo).parts}
            return files, (self.repo / '.git/index').read_bytes()
        before = state_of_repo()
        result = self.capture()
        self.assertEqual(result['changed_files'], 1)
        state = helper.check(self.directory)
        self.assertEqual(state['state'], 'incomplete')
        self.assertIn('expiry.py: unreviewed', state['gaps'])
        self.assertEqual(before, state_of_repo())
        self.assertNotIn('return now', (self.directory / 'snapshot.json').read_text())

    def test_file_marked_reviewed_cannot_hide_missing_claims_or_evidence(self):
        self.capture()
        ledger = self.document()
        ledger['checks'] = []
        self.save(ledger)
        self.assertEqual(helper.check(self.directory)['state'], 'incomplete')
        ledger = self.document()
        ledger['checks'][0]['evidence'] = []
        self.save(ledger)
        self.assertEqual(helper.check(self.directory)['state'], 'incomplete')

    def test_documented_does_not_certify_and_contradiction_remains_visible(self):
        self.capture()
        self.document()
        state = helper.check(self.directory)
        self.assertEqual(state['state'], 'documented')
        self.assertIn('not an approval', helper.render(state))
        self.document('contradicted')
        self.assertEqual(helper.check(self.directory)['state'], 'attention_required')

    def test_changed_code_and_new_untracked_file_invalidate_review(self):
        self.capture()
        self.document()
        original = (self.repo / 'expiry.py').read_bytes()
        (self.repo / 'expiry.py').write_bytes(original + b'# changed\n')
        self.assertEqual(helper.check(self.directory)['state'], 'stale')
        (self.repo / 'expiry.py').write_bytes(original)
        (self.repo / 'new.py').write_text('# additional scope')
        self.assertEqual(helper.check(self.directory)['state'], 'stale')

    def test_staged_deleted_and_untracked_files_are_captured(self):
        (self.repo / 'new file.py').write_text('# staged')
        self.git('add', 'new file.py')
        (self.repo / 'expiry.py').unlink()
        (self.repo / 'other.py').write_text('# untracked')
        result = self.capture()
        self.assertEqual(result['changed_files'], 3)
        records = helper.read_json(self.directory / 'snapshot.json')['files']
        self.assertEqual(next(r for r in records if r['path'] == 'expiry.py')['kind'], 'deleted')

    def test_explicit_base_ref_movement_invalidates_capture(self):
        self.git('branch', 'review-base')
        helper.capture(self.repo, self.directory, 'review-base')
        self.document()
        self.git('add', '--all')
        self.git('commit', '--quiet', '-m', 'Next base')
        self.git('branch', '-f', 'review-base', 'HEAD')
        self.assertEqual(helper.check(self.directory)['state'], 'stale')

    def test_exclusion_and_inconclusive_records_remain_gaps(self):
        self.capture()
        ledger = self.document('inconclusive')
        ledger['files'][0].update(disposition='excluded', reason='Needs unavailable environment')
        self.save(ledger)
        result = helper.check(self.directory)
        self.assertEqual(result['state'], 'incomplete')
        self.assertEqual(len(result['gaps']), 2)

    def test_test_logs_are_bound_and_cannot_escape_review_directory(self):
        self.capture()
        ledger = self.document()
        log = self.directory / 'test.log'
        log.write_bytes(b'Constructed test evidence; not a model result.\n')
        proof = {'kind':'test','reference':'test.log','observation':'Synthetic log for hash validation.',
                 'sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
        ledger['checks'][0]['evidence'] = [proof]
        self.save(ledger)
        self.assertEqual(helper.check(self.directory)['state'], 'documented')
        log.write_bytes(b'changed')
        with self.assertRaisesRegex(helper.ReviewError, 'missing or changed'):
            helper.check(self.directory)
        proof['reference'] = '../outside.log'
        self.save(ledger)
        with self.assertRaisesRegex(helper.ReviewError, 'inside the review'):
            helper.check(self.directory)

    def test_missing_paths_duplicate_keys_and_wrong_binding_are_rejected(self):
        self.capture()
        ledger = self.document()
        ledger['files'] = []
        self.save(ledger)
        with self.assertRaisesRegex(helper.ReviewError, 'exactly once'):
            helper.check(self.directory)
        (self.directory / 'review.json').write_text('{"x":1,"x":2}')
        with self.assertRaisesRegex(helper.ReviewError, 'Duplicate'):
            helper.check(self.directory)
        ledger['snapshot_id'] = 'fabricated'
        self.save(ledger)
        with self.assertRaisesRegex(helper.ReviewError, 'not bound'):
            helper.check(self.directory)

    def test_content_filters_and_external_diff_are_not_executed(self):
        trap = self.root / 'filter-trap.py'
        marker = self.root / 'executed.txt'
        trap.write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\n')
        command = '"' + sys.executable.replace('\\', '/') + '" "' + str(trap).replace('\\', '/') + '"'
        self.git('config', 'filter.trap.clean', command)
        self.git('config', 'filter.trap.process', command)
        self.git('config', 'filter.trap.required', 'true')
        self.git('config', 'diff.external', command)
        (self.repo / '.gitattributes').write_text('*.py filter=trap\n')
        self.capture()
        helper.check(self.directory)
        self.assertFalse(marker.exists())

    def test_capture_refuses_existing_or_in_repo_destination(self):
        self.capture()
        with self.assertRaises(FileExistsError):
            self.capture()
        with self.assertRaisesRegex(helper.ReviewError, 'outside'):
            helper.capture(self.repo, self.repo / 'review')

    def test_unborn_repo_and_conflicted_index_are_errors(self):
        empty = self.root / 'empty'
        empty.mkdir()
        subprocess.run(['git', 'init', '--quiet', str(empty)], check=True, capture_output=True)
        with self.assertRaises(helper.ReviewError):
            helper.capture(empty, self.directory)
        # Three explicit index stages represent an unresolved merge without executing hooks.
        blob = self.git('rev-parse', 'HEAD:expiry.py').decode().strip()
        payload = ('0 ' + '0' * len(blob) + '\texpiry.py\n' +
                   ''.join(f'100644 {blob} {stage}\texpiry.py\n' for stage in (1, 2, 3)))
        subprocess.run(['git','-C',str(self.repo),'update-index','--index-info'],
                       input=payload.encode(), check=True, capture_output=True)
        with self.assertRaisesRegex(helper.ReviewError, 'merge conflicts'):
            self.capture()

    def test_symlink_is_never_followed_and_remains_gap(self):
        outside = self.root / 'secret.txt'
        outside.write_text('do not copy')
        try:
            (self.repo / 'link.txt').symlink_to(outside)
        except OSError:
            self.skipTest('OS does not permit symbolic link creation')
        self.capture()
        self.document()
        result = helper.check(self.directory)
        self.assertEqual(result['state'], 'incomplete')
        self.assertTrue(any('symlink' in gap for gap in result['gaps']))
        self.assertNotIn('do not copy', (self.directory / 'snapshot.json').read_text())

    def test_submodule_is_explicit_gap_without_traversing_it(self):
        commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('update-index', '--add', '--cacheinfo', f'160000,{commit},nested')
        self.capture()
        self.document()
        result = helper.check(self.directory)
        self.assertEqual(result['state'], 'incomplete')
        self.assertIn('nested: unsupported scope (unsupported)', result['gaps'])

    def test_install_is_self_contained_and_never_overwrites(self):
        installed = installer.install(self.repo)
        path = Path(installed['installed'])
        with self.assertRaises(FileExistsError):
            installer.install(self.repo)
        self.git('add', '.agents')
        self.git('commit', '--quiet', '-m', 'Install skill')
        result = subprocess.run([sys.executable, str(path / 'scripts/review_blindspot.py'),
            'capture', '--repo', str(self.repo), '--out', str(self.directory), '--json'],
            cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['changed_files'], 1)
        self.assertEqual(set(installed['files']), set(installer.FILES))

    def test_claude_code_host_uses_its_project_skill_directory(self):
        installed = installer.install(self.repo, 'claude')
        self.assertEqual(Path(installed['installed']), (self.repo / '.claude/skills/review-blindspot').resolve())
        self.assertTrue((Path(installed['installed']) / 'SKILL.md').is_file())
        self.assertFalse((self.repo / '.agents').exists())
        with self.assertRaises(ValueError):
            installer.install(self.repo, 'unknown')

    def test_cli_exit_codes_json_errors_and_report_immutability(self):
        self.capture()
        with redirect_stdout(StringIO()):
            self.assertEqual(helper.main(['check','--review',str(self.directory),'--json']), 1)
        self.document()
        out = self.root / 'report'
        with redirect_stdout(StringIO()):
            self.assertEqual(helper.main(['check','--review',str(self.directory),'--out',str(out)]), 0)
        before = (out / 'REPORT.md').read_bytes()
        error = StringIO()
        with redirect_stderr(error):
            self.assertEqual(helper.main(['check','--review',str(self.directory),'--out',str(out),'--json']), 2)
        self.assertEqual(json.loads(error.getvalue())['state'], 'invalid_artifacts')
        self.assertEqual((out / 'REPORT.md').read_bytes(), before)

    def test_clean_repo_has_no_substantive_review_and_markup_is_escaped(self):
        self.git('add', '--all')
        self.git('commit', '--quiet', '-m', 'Clean')
        self.capture()
        self.assertEqual(helper.check(self.directory)['state'], 'no_changes')
        self.assertEqual(helper.cell('<script>|[link]'), '&lt;script&gt;\\|\\[link\\]')


if __name__ == '__main__':
    unittest.main()
