from __future__ import annotations
import csv
import html
from pathlib import Path
import platform
from . import __version__
from .io import RBSError, digest, file_hash, write_json, write_text
from .metrics import summarize
from .packets import MODE_DEMO
from .store import observations


def _code(folder: Path) -> dict:
    return {p.name: file_hash(p) for p in sorted(folder.glob('*.py')) if p.is_file()}


def _current_code() -> dict:
    return _code(Path(__file__).resolve().parent)


def provenance(run_dir: Path) -> dict:
    """Which code computed a report, relative to the code frozen when the run was prepared."""
    current, frozen = _current_code(), _code(run_dir / 'frozen' / 'rbs')
    inputs = {f'{kind}/{p.name}': file_hash(p) for kind in ('responses', 'adjudications')
              for p in sorted((run_dir / kind).glob('*.json'))}
    changed = sorted(name for name in current.keys() | frozen.keys() if current.get(name) != frozen.get(name))
    return {'schema_version': 1, 'rbs_version': __version__, 'python': platform.python_version(),
            'computing_code_sha256': digest(current), 'frozen_run_code_sha256': digest(frozen),
            'computed_with_frozen_code': not changed, 'modules_differing_from_frozen_code': changed,
            'manifest_sha256': file_hash(run_dir / 'manifest.json'), 'inputs_sha256': digest(inputs),
            'responses': sum(k.startswith('responses/') for k in inputs),
            'adjudications': sum(k.startswith('adjudications/') for k in inputs),
            'note': 'Reports are computed by the installed code, not by the frozen copy. Listed module '
                    'differences may or may not affect metrics; recompute with the frozen code to compare.'}

def _pct(value):
    return 'unknown' if value is None else f'{100 * value:.1f}%'

def _range(bounds):
    lower, upper = bounds
    return _pct(lower) if lower == upper else f'{_pct(lower)} to {_pct(upper)}'

def _cell(value):
    value = html.escape(str(value), quote=False).replace('\n', ' ').replace('\r', ' ')
    for char in ('\\', '|', '`', '*', '_', '[', ']'):
        value = value.replace(char, '\\' + char)
    return value

def write_report(run_dir: Path, out: Path) -> dict:
    manifest, rows = observations(run_dir)
    result = summarize(rows, manifest['mode'])
    if out.exists():
        raise RBSError('Report destination must be new; reports are immutable snapshots')
    out.mkdir(parents=True)
    write_json(out / 'metrics.json', result)
    lines = ['# Review Blind Spot — experiment report', '', '**' + manifest['mode'] + '**', '']
    if manifest['mode'] == MODE_DEMO:
        lines += ['> **Scripted demonstration.** Answers and annotations were generated from known defects. No model was evaluated.', '']
    else:
        lines += ['> **Unverified external reviews.** Complete records do not certify scientific validity.', '']
    lines += ['## At a glance', '',
              '| Protocol | Faulty approvals | Target recall | Control rejection |',
              '| --- | --- | --- | --- |']
    for a in result['arms']:
        lines.append(f"| {_cell(a['arm_id'])} | {a['faulty_approved_groups']}/{a['faulty_groups']} observed; {_range(a['unsafe_approval_bounds_all_scheduled'])} | "
                     f"{a['target_detected_groups']}/{a['faulty_groups']} detected; {_range(a['target_recall_bounds'])} | "
                     f"{a['control_rejected_groups']}/{a['control_groups']} rejected; {_range(a['control_rejection_bounds_all_scheduled'])} |")
    lines += ['', 'Counts use all scheduled groups. Ranges are missing-data bounds, **not confidence intervals**.', '',
              '- **Faulty approvals:** a defective candidate passed the review gate.',
              '- **Target recall:** a finding was separately adjudicated as identifying the target defect.',
              '- **Control rejection:** a control candidate was blocked; this does not by itself prove a false positive.',
              '', '**Read the three together.** Rejecting every candidate can remove faulty approvals while detecting no target defects. '
              'Check unresolved outcomes and actual resources before comparing protocols.', '',
              '## Data quality signals', '']
    drift = [item for item in result['identity_audit'] if item['multiple_identities']]
    exceeded = result['observed_output_cap_exceeded_jobs']
    lines += [f"- Logical model keys with multiple reported model/harness identities: **{len(drift)}**.",
              f"- Jobs exceeding their declared output-token cap: **{len(exceeded)}**.",
              f"- Faulty groups with unresolved target detection: **{sum(a['target_unresolved_groups'] for a in result['arms'])}**."]
    for item in drift:
        identities = '; '.join(_cell(model) + ' / ' + _cell(harness)
                               for model, harness in item['observed_model_and_harness_ids'])
        lines.append(f"  - {_cell(item['model_key'])}: {identities}.")
    if exceeded:
        lines.append('  - Job IDs: ' + ', '.join(_cell(job) for job in exceeded) + '.')
    lines += ['', 'These checks use reported metadata; zero alerts do not verify isolation, provider settings or equal cost.', '',
              '## Validity boundaries', ''] + [f'- {x}' for x in result['warnings']]
    lines += ['', '## Per-arm outcomes', '']
    for a in result['arms']:
        lower, upper = a['unsafe_approval_bounds_all_scheduled']
        recall_l, recall_u = a['target_recall_bounds']
        control_l, control_u = a['control_rejection_bounds_all_scheduled']
        lines += [f"### {a['arm_id']}", '',
                  f"Scheduled: {a['faulty_groups']} faulty groups, {a['control_groups']} controls; {a['review_jobs']} reviewer jobs.",
                  f"Faulty approvals: {a['faulty_approved_groups']}; possible unsafe-approval fraction: {_pct(lower)} to {_pct(upper)}.",
                  f"Complete decisive faulty groups: {a['complete_faulty_groups']}; approval fraction on this selected subset: {_pct(a['unsafe_approval_rate_complete'])}.",
                  f"Adjudicated target-recall bounds: {_pct(recall_l)} to {_pct(recall_u)}; unresolved target groups: {a['target_unresolved_groups']}.",
                  f"Rejection fraction for controls: {_pct(control_l)} to {_pct(control_u)}. This is not adjudicated finding-level false-positive precision.",
                  f"Execution status counts: {a['execution_status_counts']}.",
                  f"Reported cost: {'unknown' if a['usage']['cost_usd']['known_sum'] is None else str(a['usage']['cost_usd']['known_sum']) + ' USD'} across {a['usage']['cost_usd']['known_jobs']} known jobs; {a['usage']['cost_usd']['unknown_jobs']} unknown.", '']
    lines += ['## Paired comparisons', '', 'Exploratory family-cluster bootstrap; missing outcomes excluded here remain visible in the bounds above.', '']
    for c in result['paired_comparisons']:
        lines += [f"- {c['treatment_minus_baseline']}: delta {c['mean_delta']}, 95% percentile interval {c['bootstrap_percentile_95']}; {c['family_count']} families, {c['excluded_case_repeat_pairs']} excluded pairs."]
    lines += ['', '## Shared misses between reviewers', '',
              'For each pair of reviewer slots in an arm, on the faulty candidates where both outcomes are known: '
              'how often each missed the target, how often both did, and the product of the two miss rates. '
              'Shared item difficulty alone can push the joint rate above the product; this describes, it does not test dependence.', '']
    pairs = result['pairwise_joint_misses']
    if pairs:
        lines += ['| Arm | Slots | Known pairs | Miss A | Miss B | Both missed | Product | Excess |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for p in pairs:
            excess = 'unknown' if p['excess_joint_miss'] is None else f"{100 * p['excess_joint_miss']:+.1f} pts"
            lines.append(f"| {_cell(p['arm_id'])} | {_cell(' / '.join(p['slots']))} | {p['paired_known_trials']} | "
                         f"{_pct(p['miss_rate_a'])} | {_pct(p['miss_rate_b'])} | {_pct(p['joint_miss_rate'])} | "
                         f"{_pct(p['product_of_pooled_marginals'])} | {excess} |")
    else:
        lines.append('No arm has two or more reviewer slots.')
    lines += ['', '## Required before a public empirical claim', '',
              'Independent corpus audit, resolved model/settings identities, verified review isolation, frozen protocol, adjudication audit, actual cost accounting, and a new held-out corpus.', '']
    write_text(out / 'REPORT.md', '\n'.join(lines))
    with (out / 'group_outcomes.csv').open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['arm_id','case_id','family_id','variant','repeat','gate','complete_decisive','target','reviewer_count'])
        writer.writeheader()
        writer.writerows(result['groups'])
    write_json(out / 'provenance.json', provenance(run_dir))
    return {'out': str(out.resolve()), 'mode': manifest['mode'], 'report': str((out / 'REPORT.md').resolve())}
