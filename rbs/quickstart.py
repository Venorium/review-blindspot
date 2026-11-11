"""A first offline demo using the existing, explicitly scripted pipeline."""
from pathlib import Path
import tempfile
import uuid

from .demo import run_demo
from .io import ROOT, RBSError, nested, read_json


def quickstart(workspace: Path | None = None) -> dict:
    temporary = workspace is None
    if workspace is None:
        workspace = Path(tempfile.gettempdir()) / ('rbs-demo-' + uuid.uuid4().hex)
    if workspace.is_symlink():
        raise RBSError('Demo destination must be a new directory, not a symbolic link')
    workspace = workspace.resolve()
    if nested(workspace, ROOT):
        raise RBSError('Choose --out outside the repository and not one of its parents; '
                       'reviewer packets must stay separate from the answer keys')
    if workspace.exists():
        raise RBSError('Demo destination already exists; choose a new --out or omit it '
                       'to create a fresh temporary workspace')
    config = read_json(ROOT / 'configs/smoke.json')
    workspace.mkdir(parents=True)
    result = run_demo(config, workspace / 'run', workspace / 'packets')
    report_dir = Path(result['out'])
    metrics = read_json(report_dir / 'metrics.json')
    fields = ('arm_id', 'faulty_groups', 'faulty_approved_groups',
              'target_detected_groups', 'target_unresolved_groups',
              'control_groups', 'control_rejected_groups')
    return {
        **result,
        'workspace': str(workspace),
        'temporary_workspace': temporary,
        'metrics': str(report_dir / 'metrics.json'),
        'outcomes_csv': str(report_dir / 'group_outcomes.csv'),
        'results_are_model_evidence': False,
        'summary': [{key: arm[key] for key in fields} for arm in metrics['arms']],
    }


def format_quickstart(result: dict) -> str:
    lines = [
        'Review Blind Spot | offline demo complete', '',
        'SCRIPTED SIMULATION ONLY: answers were generated from known defects.',
        'No model was called. These numbers do not measure model performance.',
        f"Completed {result['review_jobs']} scripted reviews on {result['pairs']} paired cases.",
        '',
    ]
    for arm in result['summary']:
        lines.extend([
            arm['arm_id'],
            f"  Faulty candidates approved: {arm['faulty_approved_groups']}/{arm['faulty_groups']}",
            f"  Target defects detected: {arm['target_detected_groups']}/{arm['faulty_groups']}"
            f"; unresolved: {arm['target_unresolved_groups']}",
            f"  Controls rejected: {arm['control_rejected_groups']}/{arm['control_groups']}",
        ])
    lines.extend([
        '',
        'Approval, defect detection and control rejection are separate outcomes.',
        'This smoke demo checks the pipeline; it does not compare equal actual costs.',
        '',
        f"Start here (report): {result['report']}",
        f"Machine-readable metrics: {result['metrics']}",
        f"Per-candidate outcomes: {result['outcomes_csv']}",
        f"Workspace (run + reviewer packets): {result['workspace']}",
    ])
    if result['temporary_workspace']:
        lines.append('This workspace is in the system temporary directory. To keep another demo,')
        lines.append('use: python -m rbs quickstart --out ../my-rbs-demo-001 (a new directory).')
    lines.extend([
        '',
        'Next: read README.md and adapters/README.md before a real review.',
        'Real reviews need separately verified access, isolation and an explicit budget.',
    ])
    return '\n'.join(lines)
