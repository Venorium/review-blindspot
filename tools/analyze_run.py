"""Derived, reviewer-level descriptives for a run, recomputed from its raw records.

Usage: python tools/analyze_run.py --run results/pilot-2026-11-10/run [--json]

Reads the run through rbs.store.observations (integrity checked). The unit here is a
single reviewer request, which is NOT an independent sample: requests on the same case
share its difficulty. Use these numbers to describe where misses concentrate, never as
model rankings or significance tests.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rbs.io import read_json  # noqa: E402
from rbs.store import observations  # noqa: E402


def state(row: dict) -> str:
    sub = row.get("submission")
    if sub is None:
        return "missing"
    if sub["execution"]["status"] != "ok":
        return "no_valid_review"
    verdict = sub["review"]["verdict"]
    if verdict == "abstain":
        return "abstain"
    if row["variant"] == "correct":
        return "control_approved" if verdict == "approve" else "control_blocked"
    if verdict == "approve":
        return "approved"
    note = row.get("annotation")
    if note is None or note["target_detection"] == "unresolved":
        return "blocked_unresolved"
    return "detected" if note["target_detection"] == "detected" else "blocked_wrong_reason"


def analyze(run: Path) -> dict:
    manifest, rows = observations(run)
    names = {}
    transport = run / "transport/transport.json"
    if transport.is_file():
        names = {k: v.get("model") or v.get("declared_model_id") for k, v in read_json(transport)["identities"].items()}
    per_model = defaultdict(Counter)
    tokens = defaultdict(list)
    by_case = defaultdict(list)
    for row in rows:
        s = state(row)
        per_model[row["model_key"]][(row["variant"], s)] += 1
        sub = row.get("submission")
        if sub and sub["execution"]["output_tokens"] is not None:
            tokens[row["model_key"]].append(sub["execution"]["output_tokens"])
        if row["variant"] == "faulty":
            by_case[row["case_id"]].append((row["arm_id"], row["slot"], row["model_key"], s))
    models = {}
    for key, counts in sorted(per_model.items()):
        faulty = sum(v for (variant, _), v in counts.items() if variant == "faulty")
        control = sum(v for (variant, _), v in counts.items() if variant == "correct")
        values = sorted(tokens[key])
        models[key] = {"model": names.get(key, key), "faulty_requests": faulty, "control_requests": control,
                       "faulty": {s: counts[("faulty", s)] for s in ("detected", "blocked_wrong_reason", "blocked_unresolved",
                                                                     "approved", "abstain", "no_valid_review", "missing")},
                       "control": {s: counts[("correct", s)] for s in ("control_approved", "control_blocked", "abstain",
                                                                       "no_valid_review", "missing")},
                       "output_tokens_median": values[len(values) // 2] if values else None,
                       "output_tokens_total": sum(values) if values else None}
    cases = {}
    for case, cells in sorted(by_case.items()):
        detected = [c for c in cells if c[3] == "detected"]
        unknown = [c for c in cells if c[3] in ("blocked_unresolved", "abstain", "no_valid_review", "missing")]
        cases[case] = {"requests": len(cells), "detected": len(detected), "not_established": len(unknown),
                       "detected_by_models": sorted({c[2] for c in detected}),
                       "missed_by_every_request": not detected and not unknown}
    a_keys = {k for k in models if models[k]["faulty_requests"] > 30} or set(models)
    only_others = [c for c, v in cases.items() if v["detected_by_models"] and not set(v["detected_by_models"]) & a_keys]
    root = Path(__file__).resolve().parents[1]
    shown = run.relative_to(root).as_posix() if run.is_relative_to(root) else run.name
    return {"run": shown, "mode": manifest["mode"], "protocol_id": manifest["config"]["protocol_id"],
            "unit_warning": "Reviewer requests on the same case are not independent samples.",
            "per_model_requests": models, "faulty_cases": cases,
            "cases_missed_by_every_request": [c for c, v in cases.items() if v["missed_by_every_request"]],
            "cases_caught_only_by_other_models": only_others,
            "majority_model_keys": sorted(a_keys)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="Write the JSON to this file (LF line endings)")
    args = parser.parse_args(argv)
    text = json.dumps(analyze(args.run.resolve()), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
