"""Experiment planning and separation of reviewer inputs from assessor state."""
from __future__ import annotations
from datetime import datetime, timezone
import difflib
from pathlib import Path
import platform
import random
import re
import shutil
import sys
import uuid
from . import __version__
from .fixtures import catalog, FILES
from .io import ROOT, RBSError, digest, file_hash, integer, keys, nested, read_json, text, write_json, write_text

MODE_EXTERNAL = "EXTERNAL_REVIEWS_UNVERIFIED"
MODE_DEMO = "SYNTHETIC_DEMO_NOT_MODEL_RESULTS"
ID = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")

def validate_config(config: dict, available: dict) -> list[str]:
    keys(config, {"schema_version", "protocol_id", "seed", "repeats", "case_ids", "aggregation", "track", "arms"})
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise RBSError("Unsupported configuration version")
    text(config["protocol_id"], "protocol_id", maximum=100)
    integer(config["seed"], "seed")
    integer(config["repeats"], "repeats", minimum=1)
    if config["repeats"] > 100:
        raise RBSError("Starter limits repeats to 100; expand only after auditing the design")
    if config["aggregation"] != "any_block" or config["track"] != "text_only":
        raise RBSError("Starter implements only any_block aggregation and text_only review")
    selected = config["case_ids"]
    if not isinstance(selected, list) or any(not isinstance(x, str) for x in selected):
        raise RBSError("case_ids must be an array of strings")
    if len(set(selected)) != len(selected) or any(x not in available for x in selected):
        raise RBSError("Duplicate or unknown case_ids")
    selected = selected or sorted(available)
    if not isinstance(config["arms"], list) or not config["arms"]:
        raise RBSError("At least one experimental arm is required")
    arms = set()
    for arm in config["arms"]:
        keys(arm, {"arm_id", "author_note", "reviewers"})
        name = text(arm["arm_id"], "arm_id")
        if not ID.fullmatch(name) or name in arms:
            raise RBSError("Duplicate or unsafe arm ID")
        arms.add(name)
        if type(arm["author_note"]) is not bool:
            raise RBSError("author_note must be a boolean")
        if not isinstance(arm["reviewers"], list) or not 1 <= len(arm["reviewers"]) <= 10:
            raise RBSError("Each arm needs 1 to 10 reviewer slots")
        slots = set()
        for slot in arm["reviewers"]:
            keys(slot, {"slot", "model_key", "output_token_cap"})
            for key in ("slot", "model_key"):
                if not ID.fullmatch(text(slot[key], key)):
                    raise RBSError(f"Unsafe {key}")
            if slot["slot"] in slots:
                raise RBSError("Duplicate reviewer slot")
            slots.add(slot["slot"])
            integer(slot["output_token_cap"], "output_token_cap", minimum=1)
    return selected

def plan(config: dict) -> dict:
    cases = validate_config(config, catalog())
    n = len(cases) * 2 * config["repeats"]
    rows = [{"arm_id": a["arm_id"], "reviews": n * len(a["reviewers"]),
             "max_output_tokens": n * sum(s["output_token_cap"] for s in a["reviewers"])}
            for a in config["arms"]]
    return {"protocol_id": config["protocol_id"], "pairs": len(cases), "repeats": config["repeats"],
            "review_jobs": sum(r["reviews"] for r in rows),
            "max_output_tokens": sum(r["max_output_tokens"] for r in rows),
            "arms": rows, "network_calls_made": 0,
            "warning": "Output caps are not equal actual compute, input tokens, reasoning tokens or cost. No provider is invoked or budget enforced by this offline planner."}

def prepare(config: dict, run_dir: Path, packet_root: Path, *, mode: str = MODE_EXTERNAL) -> dict:
    data = catalog()
    selected = validate_config(config, data)
    run_dir, packet_root = run_dir.resolve(), packet_root.resolve()
    if mode not in (MODE_EXTERNAL, MODE_DEMO):
        raise RBSError("Unknown run mode")
    if nested(run_dir, packet_root) or nested(ROOT, packet_root):
        raise RBSError("Reviewer packets must be outside the repository and separate from assessor storage")
    if run_dir.exists() or packet_root.exists():
        raise RBSError("Run and packet directories must both be new; never overwrite a prior experiment")
    run_dir.mkdir(parents=True)
    packet_root.mkdir(parents=True)
    (run_dir / "responses").mkdir()
    (run_dir / "adjudications").mkdir()
    (run_dir / "integrity").mkdir()
    prompt_path = ROOT / "prompts/reviewer.txt"
    prompt = prompt_path.read_text(encoding="utf-8")
    # Frozen source + corpus let later reports avoid silently reading modified fixtures.
    for cid in selected:
        target = run_dir / "frozen" / "fixtures" / cid
        target.mkdir(parents=True)
        for filename in FILES:
            shutil.copyfile(data[cid]["path"] / filename, target / filename)
    for folder in ("rbs", "prompts", "schemas", "research"):
        target = run_dir / "frozen" / folder
        target.mkdir(parents=True, exist_ok=True)
        for src in sorted((ROOT / folder).iterdir()):
            if src.is_file() and src.suffix in (".py", ".txt", ".json", ".md"):
                shutil.copyfile(src, target / src.name)
    write_json(run_dir / "frozen/config.json", config)
    frozen_hashes = {str(p.relative_to(run_dir / "frozen")).replace("\\", "/"): file_hash(p)
                     for p in sorted((run_dir / "frozen").rglob("*")) if p.is_file()}
    jobs = []
    for cid in selected:
        item, meta = data[cid], data[cid]["meta"]
        for variant in ("correct", "faulty"):
            for repeat in range(config["repeats"]):
                for arm in config["arms"]:
                    for slot in arm["reviewers"]:
                        job_id = "job-" + uuid.uuid4().hex
                        folder = packet_root / job_id
                        folder.mkdir()
                        base = (item["path"] / "before.py").read_text(encoding="utf-8")
                        candidate = (item["path"] / f"{variant}.py").read_text(encoding="utf-8")
                        write_text(folder / "before.py", base)
                        write_text(folder / "candidate.py", candidate)
                        write_text(folder / "SPEC.md", "# Required behavior\n\n" + meta["spec"] + "\n")
                        write_text(folder / "review_prompt.txt", prompt)
                        patch = "".join(difflib.unified_diff(base.splitlines(True), candidate.splitlines(True),
                                                         fromfile="before.py", tofile="candidate.py"))
                        write_text(folder / "patch.diff", patch)
                        shutil.copyfile(item["path"] / "test_public.py", folder / "test_public.py")
                        shutil.copyfile(ROOT / "schemas/review.schema.json", folder / "review.schema.json")
                        if arm["author_note"]:
                            write_text(folder / "AUTHOR_NOTE.md", "# Author commentary\n\n" + meta["author_rationale"] + "\n")
                        artifacts = {p.name: file_hash(p) for p in sorted(folder.iterdir())}
                        packet_hash = digest(artifacts)
                        write_json(folder / "job.json", {"schema_version": 1, "job_id": job_id,
                                  "packet_sha256": packet_hash, "artifacts": artifacts,
                                  "output_token_cap": slot["output_token_cap"], "track": "text_only"})
                        jobs.append({"job_id": job_id, "packet_sha256": packet_hash,
                                     "packet_files": {p.name: file_hash(p) for p in sorted(folder.iterdir())},
                                     "case_id": cid, "family_id": meta["family_id"], "variant": variant,
                                     "repeat": repeat, "arm_id": arm["arm_id"], "slot": slot["slot"],
                                     "model_key": slot["model_key"], "output_token_cap": slot["output_token_cap"],
                                     "candidate_lines": len(candidate.splitlines())})
    random.Random(config["seed"]).shuffle(jobs)
    manifest = {"schema_version": 1, "kit_version": __version__, "mode": mode,
                "created_at": datetime.now(timezone.utc).isoformat(), "config": config,
                "packet_root": str(packet_root), "jobs": jobs, "frozen_hashes": frozen_hashes,
                "environment": {"python": sys.version, "platform": platform.platform()},
                "blinding": "Artifact minimization only. External isolation must enforce access boundaries."}
    write_json(run_dir / "manifest.json", manifest)
    write_text(run_dir / "manifest.sha256", file_hash(run_dir / "manifest.json") + "\n")
    return {"run": str(run_dir), "packets": str(packet_root), "mode": mode, **plan(config)}

def load_manifest(run_dir: Path) -> dict:
    path = run_dir / "manifest.json"
    if file_hash(path) != (run_dir / "manifest.sha256").read_text().strip():
        raise RBSError("Manifest integrity mismatch")
    manifest = read_json(path)
    for name, expected in manifest["frozen_hashes"].items():
        path = run_dir / "frozen" / name
        if not path.is_file() or path.is_symlink() or file_hash(path) != expected:
            raise RBSError(f"Frozen source/corpus was modified: {name}")
    return manifest

def get_job(manifest: dict, job_id: str) -> dict:
    # An allowlisted manifest lookup, never a user-controlled filesystem path.
    for job in manifest["jobs"]:
        if job["job_id"] == job_id:
            return job
    raise RBSError(f"Unknown job ID: {job_id!r}")

def check_packet(manifest: dict, job: dict) -> None:
    folder = Path(manifest["packet_root"]) / job["job_id"]
    if not folder.is_dir() or folder.is_symlink():
        raise RBSError("Reviewer packet directory is missing or symlinked")
    # Extra files might disclose an answer key; submission files belong elsewhere.
    if set(p.name for p in folder.iterdir()) != set(job["packet_files"]):
        raise RBSError("Reviewer packet files changed; do not write responses inside an input packet")
    for name, expected in job["packet_files"].items():
        path = folder / name
        if path.is_symlink() or not path.is_file() or file_hash(path) != expected:
            raise RBSError(f"Reviewer packet changed: {job['job_id']}/{name}")
