"""Render a labelled README illustration from actual scripted-demo metrics.

Python standard library only. Documentation tooling, not experiment code.
"""
import argparse
import html
import json
from pathlib import Path


def render(metrics: dict, *, compact: bool = False) -> str:
    if metrics.get('results_are_model_evidence') is not False or metrics.get('mode') != 'SYNTHETIC_DEMO_NOT_MODEL_RESULTS':
        raise ValueError('This illustration accepts only explicitly labelled scripted-demo data')
    arms = metrics['arms']
    if {a['arm_id'] for a in arms} != {'solo_blind', 'panel_blind'} or len(arms) != 2:
        raise ValueError('Use the standard solo/panel smoke demo')
    if any(a['target_unresolved_groups'] or a['faulty_unresolved_gate_groups'] or
           a['faulty_groups'] != 2 or a['control_groups'] != 2 or
           a['review_jobs'] != (4 if a['arm_id'] == 'solo_blind' else 12) or
           a['execution_status_counts'] != {'ok': a['review_jobs']} for a in arms):
        raise ValueError('Use the complete two-case smoke demo; do not hide missing data in this preview')
    arms = sorted(arms, key=lambda a: (a['arm_id'] != 'solo_blind', a['arm_id']))
    labels = {'solo_blind': 'One reviewer', 'panel_blind': 'Three reviewers'}
    if compact:
        out = ['<svg xmlns="http://www.w3.org/2000/svg" width="600" height="704" viewBox="0 0 600 704" role="img" aria-labelledby="title desc">',
               '<title id="title">Scripted demo outcomes, not model results</title>',
               '<desc id="desc">Approval, detection and control rejection are separate measures. Counts are available as text in the linked example report.</desc>',
               '<rect width="600" height="704" rx="22" fill="#f2f5f3"/>',
               '<g font-family="Segoe UI, Arial, sans-serif">',
               '<rect x="24" y="24" width="242" height="38" rx="19" fill="#eadbbf"/>',
               '<text x="44" y="51" font-size="22" font-weight="700" fill="#5d431e">SCRIPTED DEMO</text>',
               '<text x="24" y="98" font-size="25" fill="#465f6b">No model was evaluated.</text>']
        for i, arm in enumerate(arms):
            y = 127 + i * 249
            out += [f'<rect x="18" y="{y}" width="564" height="231" rx="14" fill="#fff"/>',
                    f'<text x="40" y="{y+43}" font-size="31" font-weight="700" fill="#10232e">{labels[arm["arm_id"]]}</text>']
            for n, (label, numerator, denominator) in enumerate([
                ('Faulty approvals', arm['faulty_approved_groups'], arm['faulty_groups']),
                ('Target detections', arm['target_detected_groups'], arm['faulty_groups']),
                ('Controls rejected', arm['control_rejected_groups'], arm['control_groups'])]):
                pos = y + 96 + n * 51
                out.append(f'<text x="40" y="{pos}" font-size="27" fill="#465f6b">{label}</text>')
                out.append(f'<text x="537" y="{pos}" text-anchor="end" font-size="33" font-weight="600" fill="#173e49">{numerator} / {denominator}</text>')
        out += ['<text x="24" y="661" font-size="24" fill="#465f6b">A blocked candidate is not necessarily</text>',
                '<text x="24" y="691" font-size="24" fill="#465f6b">a detected defect.</text>', '</g></svg>']
        return '\n'.join(out) + '\n'
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="454" viewBox="0 0 1200 454" role="img" aria-labelledby="title desc">',
           '<title id="title">Scripted demo: approval and detection are different outcomes</title>',
           '<desc id="desc">Counts from the bundled two-case scripted demonstration. No real model was evaluated. The same values are available in the linked example report and JSON.</desc>',
           '<rect width="1200" height="454" rx="20" fill="#f2f5f3"/>',
           '<g font-family="Segoe UI, Arial, sans-serif">',
           '<rect x="32" y="27" width="196" height="32" rx="16" fill="#eadbbf"/>',
           '<text x="48" y="49" font-size="17" font-weight="700" fill="#5d431e">SCRIPTED DEMO</text>',
           '<text x="245" y="49" font-size="18" fill="#465f6b">Pipeline illustration · no model evaluated</text>',
           '<text x="32" y="108" font-size="35" font-weight="700" fill="#10232e">What passed? What was actually detected?</text>']
    for x, title in [(370, 'Faulty approvals'), (667, 'Target detections'), (964, 'Controls rejected')]:
        out.append(f'<text x="{x}" y="164" text-anchor="middle" font-size="21" fill="#465f6b">{title}</text>')
    for i, arm in enumerate(arms):
        y = 185 + i * 105
        out += [f'<rect x="24" y="{y}" width="1152" height="92" rx="12" fill="#ffffff"/>',
                f'<text x="44" y="{y+39}" font-size="23" font-weight="600" fill="#10232e">{html.escape(labels.get(arm["arm_id"], arm["arm_id"]))}</text>',
                f'<text x="44" y="{y+65}" font-size="16" fill="#465f6b">{html.escape(arm["arm_id"])}</text>']
        for x, n, d in [(370, arm['faulty_approved_groups'], arm['faulty_groups']),
                         (667, arm['target_detected_groups'], arm['faulty_groups']),
                         (964, arm['control_rejected_groups'], arm['control_groups'])]:
            out.append(f'<text x="{x}" y="{y+60}" text-anchor="middle" font-size="44" font-weight="600" fill="#173e49">{n}<tspan font-size="25" fill="#607580"> / {d}</tspan></text>')
    out += ['<text x="32" y="426" font-size="19" fill="#465f6b">Read all three measures together. A blocked candidate is not necessarily a detected defect.</text>', '</g></svg>']
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--compact', action='store_true', help='Readable stacked layout for narrow screens')
    args = parser.parse_args()
    svg = render(json.loads(args.metrics.read_text(encoding='utf-8')), compact=args.compact)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(svg)


if __name__ == '__main__':
    main()
