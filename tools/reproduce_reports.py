"""Recompute every published run report from its raw records and compare the metrics.

For each results/<run>/run with a report/metrics.json, write a fresh report in a temporary
directory through the harness's own integrity checks and require identical metrics.
No model is called. Exit 1 if any run differs or fails its integrity checks.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from check_reproduction import differences  # noqa: E402
from rbs.io import RBSError  # noqa: E402
from rbs.report import write_report  # noqa: E402


def main() -> int:
    results, failed = [], False
    for published in sorted((ROOT / "results").glob("*/run/report/metrics.json")):
        run = published.parents[1]
        with tempfile.TemporaryDirectory(prefix="rbs-reproduce-") as temp:
            try:
                write_report(run, Path(temp) / "report")
                found = differences(json.loads(published.read_text(encoding="utf-8")),
                                    json.loads((Path(temp) / "report/metrics.json").read_text(encoding="utf-8")))
                provenance = json.loads((Path(temp) / "report/provenance.json").read_text(encoding="utf-8"))
            except (RBSError, OSError, ValueError) as exc:
                found, provenance = [f"error: {exc}"], {}
        failed |= bool(found)
        results.append({"run": run.relative_to(ROOT).as_posix(), "identical": not found, "differences": found[:20],
                        "responses": provenance.get("responses"), "adjudications": provenance.get("adjudications")})
    print(json.dumps({"runs": results, "ok": bool(results) and not failed}, indent=2))
    return 0 if results and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
