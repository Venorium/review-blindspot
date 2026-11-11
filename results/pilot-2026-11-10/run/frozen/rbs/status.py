"""Read-only progress and integrity diagnostics; never experimental certification."""
from collections import Counter
import os
from pathlib import Path
import shlex

from .io import RBSError
from .packets import MODE_DEMO, check_packet
from .store import observations


def _new_path(parent: Path, name: str) -> Path:
    number = 1
    while (parent / f'{name}-{number:03d}').exists():
        number += 1
    return parent / f'{name}-{number:03d}'


def run_status(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    for name in ('responses', 'adjudications', 'integrity', 'frozen'):
        folder = run_dir / name
        if not folder.is_dir() or folder.is_symlink():
            raise RBSError(f'Missing or symlinked run directory: {folder}')
    manifest, rows = observations(run_dir)
    for job in manifest['jobs']:
        check_packet(manifest, job)
    received = [row for row in rows if row['submission'] is not None]
    statuses = Counter(row['submission']['execution']['status'] for row in received)
    successful = [row for row in received if row['submission']['execution']['status'] == 'ok']
    blocking = [row for row in successful if row['submission']['review']['verdict'] == 'request_changes']
    abstained = sum(row['submission']['review']['verdict'] == 'abstain' for row in successful)
    errors = [{'job_id': row['job_id'], 'status': row['submission']['execution']['status']}
              for row in received if row['submission']['execution']['status'] != 'ok']
    required = len(blocking)
    recorded = sum(row['annotation'] is not None for row in blocking)
    ambiguous = sum(row['annotation'] is not None and
                    row['annotation']['target_detection'] == 'unresolved' for row in blocking)
    missing = len(rows) - len(received)
    costs = [row['submission']['execution']['cost_usd'] for row in received
             if row['submission']['execution']['cost_usd'] is not None]
    if errors or abstained or ambiguous:
        state = 'needs_attention'
    elif missing:
        state = 'awaiting_reviews'
    elif required > recorded:
        state = 'awaiting_adjudication'
    else:
        state = 'records_complete'

    actions = []
    if errors or abstained or ambiguous:
        actions.append({'message': 'Inspect the recorded incidents or unresolved decisions. '
                        'Preserve this run; any new attempt needs a new run under a declared policy.',
                        'argv': None})
    if missing:
        actions.append({'message': 'Import an actual transport submission for a missing job '
                        '(replace SUBMISSION.json with its file).',
                        'argv': ['python', '-m', 'rbs', 'import-review', '--run', str(run_dir),
                                 '--file', 'SUBMISSION.json']})
    if required > recorded:
        grading = _new_path(Path(manifest['packet_root']).parent, run_dir.name + '-grading')
        actions.append({'message': 'Export assessor-only packets for separate target adjudication. '
                        'Already annotated blocking reviews are also included.',
                        'argv': ['python', '-m', 'rbs', 'grading-packets', '--run', str(run_dir),
                                 '--out', str(grading)]})
        actions.append({'message': 'Import a completed annotation (replace ANNOTATION.json).',
                        'argv': ['python', '-m', 'rbs', 'adjudicate', '--run', str(run_dir),
                                 '--file', 'ANNOTATION.json']})
    report = _new_path(run_dir, 'report')
    actions.append({'message': 'Create a new report snapshot; missing and unresolved outcomes remain visible.',
                    'argv': ['python', '-m', 'rbs', 'report', '--run', str(run_dir), '--out', str(report)]})
    return {
        'schema_version': 1, 'run': str(run_dir), 'mode': manifest['mode'],
        'state': state, 'protocol_id': manifest['config']['protocol_id'],
        'integrity': 'manifest, frozen files, recorded results and reviewer packets checked',
        'reviews': {'expected': len(rows), 'received': len(received), 'missing': missing,
                    'successful': len(successful), 'failed': len(errors), 'abstained': abstained,
                    'status_counts': dict(sorted(statuses.items()))},
        'adjudications': {'required': required, 'recorded': recorded,
                         'missing': required - recorded, 'unresolved': ambiguous},
        'cost_usd': {'known_sum': sum(costs) if costs else None, 'known_jobs': len(costs),
                     'unknown_jobs': len(rows) - len(costs)},
        'execution_errors': errors, 'next_actions': actions,
        'warnings': ['Records complete means data collection is complete, not scientific validation.',
                     'Checksums detect accidental changes; they do not establish isolation or authenticity.'],
        'network_calls_made': 0,
    }


def command_text(argv: list[str]) -> str:
    # Paths can contain spaces, apostrophes or shell metacharacters. These are
    # suggestions only, never executed here. Windows suggestions target PowerShell.
    if os.name == 'nt':
        return '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in argv)
    return shlex.join(argv)


def format_status(result: dict) -> str:
    reviews, grading, cost = result['reviews'], result['adjudications'], result['cost_usd']
    lines = ['Review Blind Spot | run status', '', f"State: {result['state'].upper()}",
             f"Mode:  {result['mode']}", f"Run:   {result['run']}", '']
    if result['mode'] == MODE_DEMO:
        lines += ['SCRIPTED SIMULATION ONLY. No model performance is measured.', '']
    else:
        lines += ['External results remain unverified experimental evidence.', '']
    lines += [f"Reviews        {reviews['received']}/{reviews['expected']} received | {reviews['missing']} missing",
              f"Executions     {reviews['successful']} successful | {reviews['failed']} failed | {reviews['abstained']} abstained",
              f"Adjudications  {grading['recorded']}/{grading['required']} required records | {grading['missing']} missing | {grading['unresolved']} unresolved"]
    known = 'unknown' if cost['known_sum'] is None else f"{cost['known_sum']:.6g} USD"
    lines += [f"Reported cost  {known} known subtotal | {cost['known_jobs']} known jobs | {cost['unknown_jobs']} unknown",
              '', 'Integrity: ' + result['integrity'] + '.',
              'Complete records do not certify model quality, isolation or scientific validity.',
              '', 'Next actions (nothing is executed by status):']
    for action in result['next_actions']:
        lines.append('- ' + action['message'])
        if action['argv']:
            lines.append('  ' + command_text(action['argv']))
    return '\n'.join(lines)
