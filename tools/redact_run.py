"""Redact a finished run for publication without touching its observations.

Replaces the local packet directory recorded in the manifest, removes selected frozen
copies (for example internal planning notes), re-seals the manifest and rebuilds the
report, which must keep byte-identical metrics. Reviews, judgments, transport records and
their hashes are not modified. Every change is listed, with original hashes, in
<run>/PUBLICATION_REDACTION.json. A run can be redacted once.

Example:
  python tools/redact_run.py --run results/x/run --drop-frozen research/ --keep-frozen research/PILOT_PLAN.md
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rbs.io import RBSError, file_hash, write_json, write_text  # noqa: E402
from rbs.packets import load_manifest  # noqa: E402
from rbs.report import write_report  # noqa: E402

REDACTED_PACKETS = "<redacted: reviewer packets were kept outside the repository and are not published>"


def redact(run: Path, drop: list[str], keep: list[str], reason: str) -> dict:
    run = run.resolve()
    record_path = run / "PUBLICATION_REDACTION.json"
    if record_path.exists():
        raise RBSError("This run was already redacted; a run is redacted once")
    manifest = load_manifest(run)
    original_manifest = file_hash(run / "manifest.json")
    frozen = manifest["frozen_hashes"]
    unknown = [k for k in keep if k not in frozen]
    if unknown:
        raise RBSError("Unknown --keep-frozen paths: " + ", ".join(unknown))
    removed = {name: digest for name, digest in sorted(frozen.items())
               if any(name.startswith(prefix) for prefix in drop) and name not in keep}
    report = run / "report"
    old_metrics = file_hash(report / "metrics.json") if (report / "metrics.json").is_file() else None
    for name in removed:
        (run / "frozen" / name).unlink()
    for folder in sorted({(run / "frozen" / n).parent for n in removed}, key=lambda p: len(p.parts), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    changed_fields = []
    if manifest.get("packet_root") != REDACTED_PACKETS:
        manifest["packet_root"] = REDACTED_PACKETS
        changed_fields.append("packet_root")
    manifest["frozen_hashes"] = {k: v for k, v in frozen.items() if k not in removed}
    (run / "manifest.json").unlink()
    (run / "manifest.sha256").unlink()
    write_json(run / "manifest.json", manifest)
    write_text(run / "manifest.sha256", file_hash(run / "manifest.json") + "\n")
    load_manifest(run)
    rebuilt = None
    if old_metrics:
        with tempfile.TemporaryDirectory(prefix="rbs-redact-") as temp:
            write_report(run, Path(temp) / "report")
            new_metrics = file_hash(Path(temp) / "report/metrics.json")
            if new_metrics != old_metrics:
                raise RBSError("Rebuilt metrics differ from the published metrics; report left unchanged")
            shutil.rmtree(report)
            shutil.copytree(Path(temp) / "report", report)
        rebuilt = {"metrics_sha256": old_metrics, "metrics_identical": True}
    record = {"schema_version": 1, "redacted_at": datetime.now(timezone.utc).isoformat(), "reason": reason,
              "original_manifest_sha256": original_manifest, "manifest_fields_replaced": changed_fields,
              "frozen_files_removed": removed, "report_rebuilt": rebuilt,
              "unchanged": "responses, adjudications, integrity seals, transport records, frozen code, prompts, schemas, corpus"}
    write_json(record_path, record)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--drop-frozen", action="append", default=[], help="Frozen path prefix to remove")
    parser.add_argument("--keep-frozen", action="append", default=[], help="Frozen file to keep despite a prefix")
    parser.add_argument("--reason", default="Privacy: local paths and internal planning notes are not published.")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(redact(args.run, args.drop_frozen, args.keep_frozen, args.reason), indent=2))
        return 0
    except (RBSError, OSError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
