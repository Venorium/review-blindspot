"""Draw a 'blind-spot map': one row per case, one column per reviewer slot.

Reads a run through the harness's own integrity checks (rbs.store.observations) and
writes a deterministic, dependency-free SVG. Every cell carries a glyph as well as a
colour. Simulated runs are labelled as such in the image itself.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rbs.io import read_json  # noqa: E402
from rbs.packets import MODE_DEMO  # noqa: E402
from rbs.store import observations  # noqa: E402

STATES = {  # key: (fill, glyph, legend)
    "detected": ("#2f9e6e", "\u2713", "planted defect identified"),
    "wrong_reason": ("#e3a33b", "~", "blocked for another reason"),
    "unjudged": ("#f3dca6", "?", "blocked, target not adjudicated"),
    "approved": ("#d64545", "\u2717", "approved the faulty change"),
    "control_pass": ("#cfe9dc", "\u2713", "control approved"),
    "control_block": ("#e3a33b", "!", "control blocked"),
    "abstain": ("#9aa5b1", "\u2013", "abstained"),
    "failed": ("#4b5563", "\u00d7", "no valid review"),
    "missing": ("#ffffff", "", "not yet reviewed"),
}
ARM_LABELS = {"solo_blind": "Solo", "solo_budget": "Solo, larger budget", "panel_blind": "Panel of 3",
              "panel_informed": "Panel + author note", "panel_mixed": "Mixed panel"}


def cell_state(row: dict) -> str:
    sub = row.get("submission")
    if sub is None:
        return "missing"
    if sub["execution"]["status"] != "ok":
        return "failed"
    verdict = sub["review"]["verdict"]
    if verdict == "abstain":
        return "abstain"
    if row["variant"] == "correct":
        return "control_pass" if verdict == "approve" else "control_block"
    if verdict == "approve":
        return "approved"
    annotation = row.get("annotation")
    if annotation is None or annotation["target_detection"] == "unresolved":
        return "unjudged"
    return "detected" if annotation["target_detection"] == "detected" else "wrong_reason"


def collect(run: Path, variant: str):
    manifest, rows = observations(run)
    arms = [(a["arm_id"], [(s["slot"], s["model_key"]) for s in a["reviewers"]]) for a in manifest["config"]["arms"]]
    cases = sorted({r["case_id"] for r in rows})
    grid = {(r["case_id"], r["arm_id"], r["slot"]): cell_state(r)
            for r in rows if r["variant"] == variant and r["repeat"] == 0}
    titles = {c: read_json(run / "frozen/fixtures" / c / "metadata.json")["title"] for c in cases}
    letters = {}
    for _, slots in arms:
        for _, key in slots:
            letters.setdefault(key, chr(ord("A") + len(letters)))
    names = {}
    transport = run / "transport/transport.json"
    if transport.is_file():
        for key, value in read_json(transport)["identities"].items():
            names[key] = value.get("model") or value.get("declared_model_id") or key
    return manifest, arms, cases, grid, titles, letters, names


def render(run: Path, variant: str = "faulty", subtitle: str | None = None) -> str:
    manifest, arms, cases, grid, titles, letters, names = collect(run, variant)
    cell, gap, left, top = 30, 14, 330, 118
    columns = []
    x = left
    for arm, slots in arms:
        start = x
        for slot, key in slots:
            columns.append((arm, slot, key, x))
            x += cell
        columns.append((arm, None, None, start))
        x += gap
    width = max(x + 96, 800)
    height = top + len(cases) * cell + 150
    demo = manifest["mode"] == MODE_DEMO
    title = ("Who caught each planted bug" if variant == "faulty"
             else "Who blocked a correct control")
    note = subtitle or ("SCRIPTED DEMO, generated from answer keys. No model evaluated." if demo
                        else "Exploratory pilot on small synthetic fixtures. Not a benchmark.")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'role="img" aria-labelledby="t d" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
           f'<title id="t">{escape(title)}</title>',
           f'<desc id="d">{escape(note)} Rows are cases; columns are individual reviewer requests grouped by protocol.</desc>',
           f'<rect width="{width}" height="{height}" rx="14" fill="#f7f8f6"/>',
           f'<text x="24" y="38" font-size="21" font-weight="700" fill="#10232e">{escape(title)}</text>',
           f'<text x="24" y="62" font-size="13" fill="{"#a33" if demo else "#4b5563"}">{escape(note)}</text>']
    for arm, slots in arms:
        xs = [c[3] for c in columns if c[0] == arm and c[1] is not None]
        mid = (xs[0] + xs[-1] + cell) / 2
        out.append(f'<text x="{mid:.1f}" y="{top - 34}" font-size="12" font-weight="600" text-anchor="middle" fill="#10232e">'
                   f'{escape(ARM_LABELS.get(arm, arm))}</text>')
    for arm, slot, key, cx in columns:
        if slot is not None:
            out.append(f'<text x="{cx + cell / 2:.1f}" y="{top - 12}" font-size="12" text-anchor="middle" fill="#4b5563">{letters[key]}</text>')
    caught_x = x + 8
    out.append(f'<text x="{caught_x + 30}" y="{top - 12}" font-size="11" text-anchor="middle" fill="#4b5563">'
               f'{"caught" if variant == "faulty" else "blocked"}</text>')
    for i, case in enumerate(cases):
        y = top + i * cell
        label = f"{case} \u00b7 {titles[case]}"
        label = label if len(label) <= 46 else label[:45].rstrip() + "\u2026"
        out.append(f'<text x="{left - 10}" y="{y + 20}" font-size="12.5" text-anchor="end" fill="#10232e">{escape(label)}</text>')
        hits = total = 0
        for arm, slot, key, cx in columns:
            if slot is None:
                continue
            state = grid.get((case, arm, slot), "missing")
            fill, glyph, _ = STATES[state]
            total += 1
            hits += state in ("detected", "control_block")
            out.append(f'<rect x="{cx + 1}" y="{y + 1}" width="{cell - 2}" height="{cell - 2}" rx="5" fill="{fill}" stroke="#d6dbd3"/>')
            if glyph:
                ink = "#ffffff" if state in ("detected", "approved", "failed") else "#10232e"
                out.append(f'<text x="{cx + cell / 2:.1f}" y="{y + 20}" font-size="14" font-weight="700" text-anchor="middle" fill="{ink}">{escape(glyph)}</text>')
        out.append(f'<text x="{caught_x + 30}" y="{y + 20}" font-size="12.5" text-anchor="middle" fill="#10232e">{hits}/{total}</text>')
    legend_y = top + len(cases) * cell + 30
    keys = (["detected", "wrong_reason", "unjudged", "approved"] if variant == "faulty"
            else ["control_pass", "control_block"]) + ["abstain", "failed"]
    lx = 24
    for i, key in enumerate(keys):
        fill, glyph, label = STATES[key]
        px, py = lx + (i % 3) * 245, legend_y + (i // 3) * 26
        out.append(f'<rect x="{px}" y="{py}" width="18" height="18" rx="4" fill="{fill}" stroke="#d6dbd3"/>')
        out.append(f'<text x="{px + 9}" y="{py + 14}" font-size="11" font-weight="700" text-anchor="middle" '
                   f'fill="{"#ffffff" if key in ("detected", "approved", "failed") else "#10232e"}">{escape(glyph)}</text>')
        out.append(f'<text x="{px + 26}" y="{py + 14}" font-size="12" fill="#10232e">{escape(label)}</text>')
    models = " \u00b7 ".join(f"{letters[k]} = {names.get(k, k)}" for k in sorted(letters, key=letters.get))
    out.append(f'<text x="24" y="{height - 20}" font-size="12" fill="#4b5563">{escape(models)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New SVG file")
    parser.add_argument("--variant", choices=("faulty", "correct"), default="faulty")
    parser.add_argument("--subtitle")
    args = parser.parse_args(argv)
    svg = render(args.run.resolve(), args.variant, args.subtitle)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(svg)
    print(json.dumps({"out": str(args.out.resolve()), "variant": args.variant}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
