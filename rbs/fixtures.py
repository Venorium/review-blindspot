"""Ground-truth checks for the bundled trusted examples, never a sandbox."""
from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
from .io import ROOT, RBSError, file_hash, read_json

FILES = ("metadata.json", "before.py", "correct.py", "faulty.py", "test_public.py", "test_oracle.py")
_RUNNER = r'''
import importlib.util, json, sys, unittest
from io import StringIO
candidate_path, tests_path = sys.argv[1:]
spec = importlib.util.spec_from_file_location("candidate", candidate_path)
module = importlib.util.module_from_spec(spec)
sys.modules["candidate"] = module
spec.loader.exec_module(module)
test_spec = importlib.util.spec_from_file_location("fixture_checks", tests_path)
tests = importlib.util.module_from_spec(test_spec)
test_spec.loader.exec_module(tests)
stream = StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromModule(tests))
print(json.dumps({"tests": result.testsRun, "failures": len(result.failures),
 "errors": len(result.errors), "skipped": len(result.skipped),
 "log": stream.getvalue()}))
'''

def catalog(root: Path = ROOT / "fixtures") -> dict[str, dict]:
    found = {}
    if not root.is_dir():
        raise RBSError("Bundled fixtures not found. Review Blind Spot runs from a source checkout; "
                       "clone the repository and use 'python -m rbs' or 'pip install -e .'")
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        if folder.is_symlink():
            raise RBSError(f"Symlink fixture directory forbidden: {folder}")
        for name in FILES:
            path = folder / name
            if not path.is_file() or path.is_symlink():
                raise RBSError(f"Missing or symlink fixture file: {path}")
        meta = read_json(folder / "metadata.json")
        if meta.get("case_id") != folder.name or meta.get("schema_version") != 1:
            raise RBSError(f"Fixture identity/version mismatch: {folder}")
        for name in ("spec", "target_defect", "author_rationale", "family_id"):
            if not isinstance(meta.get(name), str) or not meta[name].strip():
                raise RBSError(f"Missing fixture field {name}: {folder}")
        found[folder.name] = {"meta": meta, "path": folder,
                              "hashes": {name: file_hash(folder / name) for name in FILES}}
    if not found:
        raise RBSError("No fixtures found")
    return found

def run_checks(candidate: Path, tests: Path, timeout: float = 8.0) -> dict:
    """Isolated import process for trusted code; no OS/network confinement."""
    try:
        result = subprocess.run([sys.executable, "-I", "-B", "-c", _RUNNER,
                                 str(candidate.resolve()), str(tests.resolve())],
                                capture_output=True, text=True, encoding="utf-8",
                                timeout=timeout, cwd=candidate.parent)
    except subprocess.TimeoutExpired as exc:
        raise RBSError(f"Fixture timed out after {timeout}s: {candidate}") from exc
    if result.returncode != 0:
        raise RBSError(f"Fixture infrastructure/import failure: {candidate}\n{result.stderr[-4000:]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RBSError(f"Unexpected fixture output: {candidate}") from exc
    if payload["tests"] < 1 or payload["errors"] or payload["skipped"]:
        raise RBSError(f"Fixture must execute assertions without errors/skips: {candidate}\n{payload['log']}")
    return payload

def _verify_case(entry: tuple[str, dict]) -> dict:
    cid, item = entry
    folder = item["path"]
    checks = {}
    for variant in ("before", "correct", "faulty"):
        for suite in ("public", "oracle"):
            result = run_checks(folder / f"{variant}.py", folder / f"test_{suite}.py")
            checks[f"{variant}_{suite}"] = result
    base = (folder / "before.py").read_bytes()
    nonempty = all((folder / f"{v}.py").read_bytes() != base for v in ("correct", "faulty"))
    ok = (nonempty and checks["correct_public"]["failures"] == 0
          and checks["correct_oracle"]["failures"] == 0
          and checks["faulty_public"]["failures"] == 0
          and checks["faulty_oracle"]["failures"] > 0
          and checks["before_public"]["failures"] == 0)
    return {"case_id": cid, "ok": ok, "checks": checks, "hashes": item["hashes"]}

def verify_all(root: Path = ROOT / "fixtures") -> dict:
    entries = list(catalog(root).items())
    # Independent trusted fixture processes; parallelism reduces startup cost.
    with ThreadPoolExecutor(max_workers=min(4, len(entries))) as pool:
        rows = list(pool.map(_verify_case, entries))
    return {"scope": "trusted_synthetic_fixture_validation_not_model_evaluation",
            "ok": all(row["ok"] for row in rows), "pairs": len(rows), "rows": rows}
