"""Append-only (by API contract) submission and adjudication storage."""
from __future__ import annotations
from pathlib import Path
from .io import RBSError, file_hash, read_json, write_json, write_text
from .packets import MODE_DEMO, check_packet, get_job, load_manifest
from .schema import validate_adjudication, validate_submission


def _record(run_dir: Path, kind: str, job_id: str, payload: dict) -> Path:
    destination = run_dir / kind / f"{job_id}.json"
    seal = run_dir / "integrity" / f"{kind}-{job_id}.sha256"
    if destination.exists() or seal.exists():
        raise RBSError(f"{kind} already recorded for this job; create a new run, never overwrite")
    write_json(destination, payload)
    write_text(seal, file_hash(destination) + "\n")
    return destination

def _read_record(run_dir: Path, kind: str, job_id: str) -> dict | None:
    path = run_dir / kind / f"{job_id}.json"
    seal = run_dir / "integrity" / f"{kind}-{job_id}.sha256"
    if not path.exists():
        if seal.exists():
            raise RBSError(f"Recorded {kind} was removed: {job_id}")
        return None
    if not seal.exists() or file_hash(path) != seal.read_text().strip():
        raise RBSError(f"Recorded {kind} integrity mismatch: {job_id}")
    return read_json(path)

def import_submission(run_dir: Path, payload: dict) -> Path:
    if not isinstance(payload, dict):
        raise RBSError("Expected a JSON result object")
    manifest = load_manifest(run_dir)
    job = get_job(manifest, payload.get("job_id", ""))
    check_packet(manifest, job)
    validate_submission(payload, job)
    if manifest["mode"] != MODE_DEMO and payload["execution"]["model_id"].startswith("mock-"):
        raise RBSError("Mock submissions cannot be imported as external reviews")
    return _record(run_dir, "responses", job["job_id"], payload)

def import_adjudication(run_dir: Path, payload: dict) -> Path:
    if not isinstance(payload, dict):
        raise RBSError("Expected a JSON result object")
    manifest = load_manifest(run_dir)
    job = get_job(manifest, payload.get("job_id", ""))
    response = _read_record(run_dir, "responses", job["job_id"])
    if response is None:
        raise RBSError("Import the submission before its adjudication")
    response_path = run_dir / "responses" / f"{job['job_id']}.json"
    validate_adjudication(payload, job, response, file_hash(response_path), manifest["mode"])
    return _record(run_dir, "adjudications", job["job_id"], payload)

def observations(run_dir: Path) -> tuple[dict, list[dict]]:
    manifest = load_manifest(run_dir)
    rows = []
    known_ids = {j["job_id"] for j in manifest["jobs"]}
    for kind in ("responses", "adjudications"):
        if any(p.stem not in known_ids for p in (run_dir / kind).glob("*.json")):
            raise RBSError(f"Unexpected {kind} not listed in manifest")
    for job in manifest["jobs"]:
        response = _read_record(run_dir, "responses", job["job_id"])
        annotation = _read_record(run_dir, "adjudications", job["job_id"])
        if response is not None:
            validate_submission(response, job)
        if annotation is not None:
            if response is None:
                raise RBSError("Adjudication without submission")
            validate_adjudication(annotation, job, response,
                                  file_hash(run_dir / "responses" / f"{job['job_id']}.json"), manifest["mode"])
        rows.append({**job, "submission": response, "annotation": annotation})
    return manifest, rows

def export_grading_packets(run_dir: Path, out: Path) -> dict:
    manifest, rows = observations(run_dir)
    out = out.resolve()
    from .io import ROOT, nested
    if nested(out, Path(manifest["packet_root"])) or nested(out, run_dir) or nested(out, ROOT):
        raise RBSError("Grader packets need a separate directory outside reviewer packets, run and repository")
    if out.exists():
        raise RBSError("Grader output directory must be new")
    out.mkdir(parents=True)
    count = 0
    for row in rows:
        sub = row["submission"]
        if not sub or sub["execution"]["status"] != "ok" or sub["review"]["verdict"] != "request_changes":
            continue
        folder = out / row["job_id"]
        folder.mkdir()
        fixture = run_dir / "frozen/fixtures" / row["case_id"]
        meta = read_json(fixture / "metadata.json")
        write_text(folder / "SPEC.md", meta["spec"] + "\n")
        write_text(folder / "candidate.py", (fixture / f"{row['variant']}.py").read_text(encoding="utf-8"))
        write_json(folder / "review.json", sub["review"])
        write_text(folder / "grader_prompt.txt", (run_dir / "frozen/prompts/grader.txt").read_text(encoding="utf-8"))
        write_text(folder / "test_witness.py", (fixture / "test_oracle.py").read_text(encoding="utf-8"))
        write_json(folder / "rubric.json", {"target": meta["target_defect"] if row["variant"] == "faulty" else None,
                   "control": row["variant"] == "correct", "limitations": meta["limitations"]})
        write_json(folder / "annotation.TEMPLATE.json", {"schema_version": 1, "job_id": row["job_id"],
                   "submission_sha256": file_hash(run_dir / "responses" / f"{row['job_id']}.json"),
                   "target_detection": "not_applicable" if row["variant"] == "correct" else "unresolved",
                   "finding_ids": [], "rationale": "REPLACE_WITH_AUDITABLE_RATIONALE",
                   "grader_id": "REPLACE_WITH_GRADER_ID", "method": "manual",
                   "evidence_reference": "REPLACE_WITH_CHECK_OR_COUNTEREXAMPLE_REFERENCE"})
        count += 1
    return {"grading_packets": count, "out": str(out),
            "warning": "Targets are disclosed only to assessors. Independent adjudication remains required; templates are not judgments."}
