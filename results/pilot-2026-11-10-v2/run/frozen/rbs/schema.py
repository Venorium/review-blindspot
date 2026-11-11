"""Runtime contracts; deliberately strict, with missingness kept explicit."""
from __future__ import annotations
from .io import RBSError, integer, keys, nonnegative_or_none, text

STATUSES = {"ok", "timeout", "provider_error", "invalid_output"}
VERDICTS = {"approve", "request_changes", "abstain"}

def validate_submission(obj: dict, job: dict) -> None:
    keys(obj, {"schema_version", "job_id", "packet_sha256", "execution", "review"})
    if type(obj["schema_version"]) is not int or obj["schema_version"] != 1:
        raise RBSError("Unsupported submission schema")
    if obj["job_id"] != job["job_id"] or obj["packet_sha256"] != job["packet_sha256"]:
        raise RBSError("Submission is not bound to this job and packet")
    execution = obj["execution"]
    keys(execution, {"status", "model_id", "harness_id", "input_tokens", "output_tokens",
                     "cost_usd", "latency_seconds", "isolation_attested", "trace_reference"})
    if not isinstance(execution["status"], str) or execution["status"] not in STATUSES:
        raise RBSError("Unknown execution status")
    for label in ("model_id", "harness_id"):
        text(execution[label], label, maximum=300)
        if execution[label].startswith("REPLACE_"):
            raise RBSError("Resolve model and harness identifiers before import")
    for label in ("input_tokens", "output_tokens"):
        nonnegative_or_none(execution[label], label, integer_only=True)
    for label in ("cost_usd", "latency_seconds"):
        nonnegative_or_none(execution[label], label)
    if type(execution["isolation_attested"]) is not bool:
        raise RBSError("isolation_attested must be boolean (an attestation, not enforcement)")
    if execution["trace_reference"] is not None:
        text(execution["trace_reference"], "trace_reference")
    review = obj["review"]
    if execution["status"] != "ok":
        if review is not None:
            raise RBSError("Failed executions must have review=null; never convert them to approval")
        return
    keys(review, {"verdict", "findings", "summary"})
    if not isinstance(review["verdict"], str) or review["verdict"] not in VERDICTS:
        raise RBSError("Unknown verdict")
    text(review["summary"], "review.summary")
    if not isinstance(review["findings"], list) or len(review["findings"]) > 100:
        raise RBSError("findings must be a list with at most 100 entries")
    findings = review["findings"]
    if (review["verdict"] == "request_changes") != bool(findings):
        raise RBSError("Only request_changes contains findings, and it must contain at least one")
    seen = set()
    for finding in findings:
        keys(finding, {"finding_id", "file", "line_start", "line_end", "severity", "description", "evidence"})
        fid = text(finding["finding_id"], "finding_id", maximum=80)
        if fid in seen:
            raise RBSError("Duplicate finding ID")
        seen.add(fid)
        if finding["file"] != "candidate.py":
            raise RBSError("Starter findings refer only to candidate.py")
        integer(finding["line_start"], "line_start", minimum=1)
        integer(finding["line_end"], "line_end", minimum=finding["line_start"])
        if finding["line_end"] > job["candidate_lines"]:
            raise RBSError("Finding line range exceeds candidate.py")
        if not isinstance(finding["severity"], str) or finding["severity"] not in {"low", "medium", "high", "critical"}:
            raise RBSError("Unsupported severity")
        text(finding["description"], "description")
        text(finding["evidence"], "evidence")

def validate_adjudication(obj: dict, job: dict, submission: dict, submission_hash: str, mode: str) -> None:
    keys(obj, {"schema_version", "job_id", "submission_sha256", "target_detection", "finding_ids",
               "rationale", "grader_id", "method", "evidence_reference"})
    if type(obj["schema_version"]) is not int or obj["schema_version"] != 1:
        raise RBSError("Unsupported adjudication schema")
    if obj["job_id"] != job["job_id"] or obj["submission_sha256"] != submission_hash:
        raise RBSError("Adjudication does not match the frozen submission")
    if submission["execution"]["status"] != "ok":
        raise RBSError("Cannot adjudicate a failed execution")
    if submission["review"]["verdict"] != "request_changes":
        raise RBSError("Only blocking reviews require target adjudication")
    detection = obj["target_detection"]
    if not isinstance(detection, str) or detection not in {"detected", "missed", "unresolved", "not_applicable"}:
        raise RBSError("Unknown adjudication outcome")
    if (job["variant"] == "correct") != (detection == "not_applicable"):
        raise RBSError("Correct controls require not_applicable; faulty variants require a target outcome")
    if (not isinstance(obj["finding_ids"], list)
        or any(not isinstance(fid, str) for fid in obj["finding_ids"])
        or len(set(obj["finding_ids"])) != len(obj["finding_ids"])):
        raise RBSError("finding_ids must be a list of unique strings")
    valid = {f["finding_id"] for f in submission["review"]["findings"]}
    if any(fid not in valid for fid in obj["finding_ids"]):
        raise RBSError("Adjudication references an unknown finding")
    if detection == "detected" and not obj["finding_ids"]:
        raise RBSError("Detection must identify a matching finding")
    if detection != "detected" and obj["finding_ids"]:
        raise RBSError("Non-detection must not mark a matching finding")
    for name in ("rationale", "grader_id", "evidence_reference"):
        text(obj[name], name)
        if obj[name].startswith("REPLACE_"):
            raise RBSError("Complete the annotation template before import")
    if obj["method"] not in {"manual", "external_judge", "mock_demo"}:
        raise RBSError("Unsupported adjudication method")
    if obj["method"] == "mock_demo" and mode != "SYNTHETIC_DEMO_NOT_MODEL_RESULTS":
        raise RBSError("Mock adjudication is forbidden in external runs")
