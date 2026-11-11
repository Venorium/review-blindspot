"""Show incomplete -> attention_required -> stale without calling a model."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

from install_codex_skill import install


def main():
    workspace = Path(tempfile.mkdtemp(prefix='rbs-codex-demo-'))
    project = workspace / 'project'
    project.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}

    def git(*args):
        subprocess.run(['git', '-C', str(project), '-c', 'core.hooksPath=' + str(workspace / 'no-hooks'),
            '-c', 'user.name=RBS demonstration', '-c', 'user.email=demo@example.invalid',
            '-c', 'commit.gpgsign=false', *args], env=env, check=True, capture_output=True, timeout=30)

    git('init', '--quiet')
    git('config', 'core.autocrlf', 'false')
    (project / 'expiry.py').write_text('def active(now, expires_at):\n    return now < expires_at\n', encoding='utf-8')
    (project / 'SPEC.md').write_text('A token is active exactly when now < expires_at.\n', encoding='utf-8')
    installed = install(project)
    git('add', '--all')
    git('commit', '--quiet', '-m', 'Trusted demonstration with skill installed')
    (project / 'expiry.py').write_text('def active(now, expires_at):\n    return now <= expires_at\n', encoding='utf-8')
    script = Path(installed['installed']) / 'scripts/review_blindspot.py'
    review = workspace / 'review'

    def run(*args):
        result = subprocess.run([sys.executable, str(script), *args, '--json'],
                                capture_output=True, text=True, timeout=45)
        if result.returncode not in (0, 1):
            raise ValueError(result.stderr)
        return json.loads(result.stdout)

    run('capture', '--repo', str(project), '--out', str(review))
    states = [run('check', '--review', str(review), '--out', str(review / 'report-001'))['state']]
    ledger = json.loads((review / 'review.json').read_text(encoding='utf-8'))
    ledger['reviewer_context'] = 'same_session'
    ledger['files'][0].update(disposition='reviewed', reason='Scripted source inspection example.')
    ledger['checks'] = [{'id': 'C1', 'claim': 'A token is inactive at its exact expiration time.',
        'files': ['expiry.py'], 'status': 'contradicted', 'evidence': [{
            'kind': 'inspection', 'reference': 'expiry.py:2 and SPEC.md:1',
            'observation': 'At now == expires_at, <= returns True; the contract requires strict <. '
                           'Scripted example; no project code executed and no model evaluated.',
            'sha256': None}]}]
    (review / 'review.json').write_text(json.dumps(ledger, indent=2), encoding='utf-8')
    states.append(run('check', '--review', str(review), '--out', str(review / 'report-002'))['state'])
    (project / 'expiry.py').write_text('def active(now, expires_at):\n    return now < expires_at\n', encoding='utf-8')
    states.append(run('check', '--review', str(review), '--out', str(review / 'report-003'))['state'])
    if states != ['incomplete', 'attention_required', 'stale']:
        raise ValueError('Unexpected demo states: ' + repr(states))
    result = {'mode': 'SCRIPTED_INTEGRATION_DEMO_NOT_MODEL_RESULTS', 'workspace': str(workspace),
              'states': states, 'example_report': str(review / 'report-002/REPORT.md'),
              'stale_report': str(review / 'report-003/REPORT.md'), 'model_calls': 0,
              'note': 'Temporary workspace; three reports retained. No project source executed.'}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
