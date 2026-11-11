"""Send prepared reviewer jobs to a declared transport, one fresh request per job.

Supported backends: a local or remote Ollama HTTP endpoint (text only, no tools), and
an operator-declared command that reads the prompt on stdin. Raw requests/responses
are kept in <run>/transport; execution metadata comes from the harness, never from
the model. No silent retry: an interrupted or failed first attempt stays visible.
A fresh process or temporary directory is not a security sandbox.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

from . import __version__
from .io import RBSError, _no_constant, _no_duplicates, digest, keys, read_json, text, write_json
from .packets import MODE_DEMO, check_packet, load_manifest
from .schema import validate_submission
from .store import import_submission

ORDER = ("review_prompt.txt", "SPEC.md", "AUTHOR_NOTE.md", "before.py", "candidate.py",
         "patch.diff", "test_public.py", "review.schema.json")
MAX_OUTPUT_BYTES = 4_000_000
FENCE = re.compile(r"\x60{3}(?:json)?[ \t]*\r?\n(.*?)\x60{3}", re.S)
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def build_prompt(packet: Path) -> str:
    """Deterministic text rendering of exactly the files of one reviewer packet."""
    instructions = (packet / "review_prompt.txt").read_text(encoding="utf-8").strip()
    parts = [instructions, "",
             "The files of this job follow. Numbers before '|' are line references added by the "
             "harness; they are not part of the Python files. Respond with only the JSON review object."]
    for name in ORDER[1:]:
        path = packet / name
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if name.endswith(".py"):
            lines = content.splitlines()
            width = len(str(max(len(lines), 1)))
            content = "\n".join(f"{n:>{width}}| {line}" for n, line in enumerate(lines, 1))
        parts += ["", f"===== {name} =====", content.rstrip("\n"), f"===== end of {name} ====="]
    return "\n".join(parts) + "\n"


def format_schema(packet: Path) -> dict:
    """Review schema without keywords many constrained decoders reject.
    The harness still applies the full contract after decoding."""
    schema = read_json(packet / "review.schema.json")
    return {k: v for k, v in schema.items() if k not in ("$schema", "title", "allOf")}


def extract_review(raw: str) -> tuple[dict, str]:
    """Parse the review object without rewriting it; report the extraction method."""
    stripped = raw.strip()
    candidates = [("whole_output", stripped)]
    candidates += [("last_json_fence", fence) for fence in reversed(FENCE.findall(stripped))]
    if "{" in stripped and "}" in stripped:
        candidates.append(("outer_braces", stripped[stripped.find("{"): stripped.rfind("}") + 1]))
    for method, candidate in candidates:
        try:
            value = json.loads(candidate, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
        except (json.JSONDecodeError, RBSError):
            continue
        if isinstance(value, dict):
            return value, method
    raise RBSError("No JSON review object found in reviewer output")


def _seed(job_id: str) -> int:
    return int(hashlib.sha256(job_id.encode()).hexdigest()[:8], 16) % (2 ** 31)


def _number(value, label: str, low: float, high: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low < value <= high:
        raise RBSError(f"{label} must be a number in ({low}, {high}]")
    return value


def load_transport(path: Path) -> dict:
    config = read_json(path)
    keys(config, {"schema_version", "models"}, {"description"})
    if config["schema_version"] != 1 or not isinstance(config["models"], dict) or not config["models"]:
        raise RBSError("Transport needs schema_version 1 and at least one model_key")
    for key, spec in config["models"].items():
        if not isinstance(spec, dict) or spec.get("backend") not in ("ollama", "command"):
            raise RBSError(f"{key}: backend must be 'ollama' or 'command'")
        if spec["backend"] == "ollama":
            keys(spec, {"backend", "model", "timeout_seconds"},
                 {"endpoint", "think", "options", "structured_output", "keep_alive"})
            text(spec["model"], f"{key}.model", maximum=200)
            endpoint = spec.get("endpoint", "http://127.0.0.1:11434")
            if not isinstance(endpoint, str) or not re.fullmatch(r"https?://[^\s/]+/?", endpoint):
                raise RBSError(f"{key}: endpoint must be an http(s) origin")
            options = spec.get("options", {})
            if not isinstance(options, dict) or {"num_predict", "seed"} & options.keys():
                raise RBSError(f"{key}: options must be an object; num_predict and seed are set per job")
            if spec.get("think") not in (None, True, False, "low", "medium", "high"):
                raise RBSError(f"{key}: unsupported think value")
            if type(spec.get("structured_output", True)) is not bool:
                raise RBSError(f"{key}: structured_output must be boolean")
        else:
            keys(spec, {"backend", "argv", "model_id", "timeout_seconds"},
                 {"version_argv", "isolation_attested"})
            for name in ("argv",) + (("version_argv",) if "version_argv" in spec else ()):
                value = spec[name]
                if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value):
                    raise RBSError(f"{key}.{name} must be a non-empty list of strings")
            text(spec["model_id"], f"{key}.model_id", maximum=200)
            if type(spec.get("isolation_attested", False)) is not bool:
                raise RBSError(f"{key}: isolation_attested must be boolean")
        _number(spec["timeout_seconds"], f"{key}.timeout_seconds", 0, 7200)
        if str(spec.get("model") or spec.get("model_id")).startswith("REPLACE_"):
            raise RBSError(f"{key}: replace the template placeholder with a real model identifier")
    return config


def _http(url: str, *, body: bytes | None = None, timeout: float = 20) -> bytes:
    request = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_OUTPUT_BYTES + 1)


def resolve_identities(config: dict) -> dict:
    """Resolve exact model identities before any job runs."""
    resolved = {}
    for key, spec in sorted(config["models"].items()):
        if spec["backend"] == "ollama":
            endpoint = spec.get("endpoint", "http://127.0.0.1:11434").rstrip("/")
            try:
                tags = json.loads(_http(endpoint + "/api/tags"))
                version = json.loads(_http(endpoint + "/api/version"))
            except (OSError, ValueError) as exc:
                raise RBSError(f"{key}: Ollama endpoint unavailable ({exc})") from exc
            models = {m.get("name"): m for m in tags.get("models", [])}
            if spec["model"] not in models:
                raise RBSError(f"{key}: model {spec['model']!r} is not available at {endpoint}")
            resolved[key] = {"backend": "ollama", "model": spec["model"],
                             "digest": models[spec["model"]].get("digest"),
                             "details": models[spec["model"]].get("details"),
                             "server_version": version.get("version"), "endpoint": endpoint}
        else:
            version = None
            if "version_argv" in spec:
                argv = [shutil.which(spec["version_argv"][0]) or spec["version_argv"][0], *spec["version_argv"][1:]]
                try:
                    done = subprocess.run(argv, capture_output=True, timeout=60, shell=False)
                    version = done.stdout.decode("utf-8", "replace").strip()[:200] or None
                except (OSError, subprocess.SubprocessError) as exc:
                    raise RBSError(f"{key}: version command failed ({exc})") from exc
            resolved[key] = {"backend": "command", "declared_model_id": spec["model_id"],
                             "executable": Path(shutil.which(spec["argv"][0]) or spec["argv"][0]).name,
                             "client_version": version}
    return resolved


def _call_ollama(spec: dict, identity: dict, prompt: str, job: dict, schema: dict, folder: Path) -> dict:
    body = {"model": spec["model"], "messages": [{"role": "user", "content": prompt}], "stream": False,
            "options": {**spec.get("options", {}), "num_predict": job["output_token_cap"], "seed": _seed(job["job_id"])},
            "keep_alive": spec.get("keep_alive", "30m")}
    if spec.get("think") is not None:
        body["think"] = spec["think"]
    if spec.get("structured_output", True):
        body["format"] = schema
    request = json.dumps(body, ensure_ascii=False).encode("utf-8")
    _write_bytes(folder / "request.json", request)
    result = {"request_sha256": _sha(request), "input_tokens": None, "output_tokens": None, "content": None}
    start = time.monotonic()
    try:
        raw, status = _http(identity["endpoint"] + "/api/chat", body=request, timeout=spec["timeout_seconds"]), "ok"
    except urllib.error.HTTPError as exc:
        with exc:
            raw, status, result["error"] = exc.read(MAX_OUTPUT_BYTES + 1), "provider_error", f"HTTP {exc.code}"
    except (TimeoutError, socket.timeout):
        raw, status = b"", "timeout"
    except urllib.error.URLError as exc:
        timed_out = isinstance(exc.reason, (TimeoutError, socket.timeout))
        raw, status, result["error"] = b"", "timeout" if timed_out else "provider_error", str(exc.reason)
    except OSError as exc:
        raw, status, result["error"] = b"", "provider_error", str(exc)
    result["latency_seconds"] = round(time.monotonic() - start, 3)
    _write_bytes(folder / "response.json", raw)
    result["response_sha256"] = _sha(raw)
    if status != "ok":
        return result | {"status": status}
    if len(raw) > MAX_OUTPUT_BYTES:
        return result | {"status": "invalid_output", "error": "response exceeds size limit"}
    try:
        data = json.loads(raw)
        message = data["message"]
    except (ValueError, KeyError, TypeError):
        return result | {"status": "provider_error", "error": "unreadable Ollama response"}
    result.update(input_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"),
                  observed_model=data.get("model"), done_reason=data.get("done_reason"),
                  content=message.get("content"), thinking_chars=len(message.get("thinking") or ""))
    if data.get("done_reason") == "length":
        return result | {"status": "invalid_output", "error": "generation stopped at the output-token cap"}
    return result | {"status": "ok"}


def _call_command(spec: dict, prompt: str, schema: dict, folder: Path) -> dict:
    stdin = prompt.encode("utf-8")
    _write_bytes(folder / "request.txt", stdin)
    result = {"request_sha256": _sha(stdin), "input_tokens": None, "output_tokens": None, "content": None}
    with tempfile.TemporaryDirectory(prefix="rbs-reviewer-") as cwd:
        schema_path = Path(cwd) / "review.schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        argv = [a.replace("{schema_path}", str(schema_path)).replace("{cwd}", cwd) for a in spec["argv"]]
        argv[0] = shutil.which(argv[0]) or argv[0]
        start = time.monotonic()
        try:
            done = subprocess.run(argv, input=stdin, capture_output=True, cwd=cwd,
                                  timeout=spec["timeout_seconds"], shell=False)
            stdout, stderr = done.stdout, done.stderr
            status = "ok" if done.returncode == 0 else "provider_error"
            if done.returncode:
                result["error"] = f"exit code {done.returncode}"
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, status = exc.stdout or b"", exc.stderr or b"", "timeout"
        except OSError as exc:
            stdout, stderr, status, result["error"] = b"", str(exc).encode(), "provider_error", str(exc)
        result["latency_seconds"] = round(time.monotonic() - start, 3)
    _write_bytes(folder / "stdout.txt", stdout)
    _write_bytes(folder / "stderr.txt", stderr)
    result["response_sha256"] = _sha(stdout)
    if status == "ok" and len(stdout) > MAX_OUTPUT_BYTES:
        return result | {"status": "invalid_output", "error": "output exceeds size limit"}
    if status == "ok":
        result["content"] = stdout.decode("utf-8", "replace")
    return result | {"status": status}


def _review_one(run_dir: Path, manifest: dict, job: dict, config: dict, identities: dict,
                trace: Path, attempt: int) -> dict:
    spec, identity = config["models"][job["model_key"]], identities[job["model_key"]]
    packet = Path(manifest["packet_root"]) / job["job_id"]
    check_packet(manifest, job)
    folder = trace / "raw" / job["job_id"] / f"attempt-{attempt}"
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder / "started.json", {"job_id": job["job_id"], "model_key": job["model_key"],
                                         "attempt": attempt, "started_at": _now()})
    prompt, schema = build_prompt(packet), format_schema(packet)
    if spec["backend"] == "ollama":
        result = _call_ollama(spec, identity, prompt, job, schema, folder)
        observed = result.get("observed_model") or spec["model"]
        model_id = f"ollama:{observed}@{(identity.get('digest') or 'unknown')[:12]}"
        harness = f"rbs-transport/{__version__} ollama/{identity.get('server_version')}"
        attested = True
    else:
        result = _call_command(spec, prompt, schema, folder)
        model_id = "declared:" + spec["model_id"]
        harness = f"rbs-transport/{__version__} command/{identity['executable']}" + (
            f" {identity['client_version']}" if identity.get("client_version") else "")
        attested = spec.get("isolation_attested", False)
    review, extraction = None, None
    if result["status"] == "ok":
        try:
            review, extraction = extract_review(result["content"] or "")
        except RBSError as exc:
            result.update(status="invalid_output", error=str(exc))
    execution = {"status": result["status"], "model_id": model_id[:300], "harness_id": harness[:300],
                 "input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"],
                 "cost_usd": None, "latency_seconds": result.get("latency_seconds"),
                 "isolation_attested": attested,
                 "trace_reference": f"transport/raw/{job['job_id']}/attempt-{attempt}"}
    payload = {"schema_version": 1, "job_id": job["job_id"], "packet_sha256": job["packet_sha256"],
               "execution": execution, "review": review if result["status"] == "ok" else None}
    if result["status"] == "ok":
        try:
            validate_submission(payload, job)
        except RBSError as exc:
            result.update(status="invalid_output", error="schema: " + str(exc))
            payload["execution"]["status"], payload["review"] = "invalid_output", None
    import_submission(run_dir, payload)
    record = {"job_id": job["job_id"], "model_key": job["model_key"], "attempt": attempt,
              "backend": spec["backend"], "finished_at": _now(), "status": payload["execution"]["status"],
              "verdict": (payload["review"] or {}).get("verdict"), "extraction": extraction,
              "latency_seconds": result.get("latency_seconds"), "input_tokens": result["input_tokens"],
              "output_tokens": result["output_tokens"], "request_sha256": result["request_sha256"],
              "response_sha256": result["response_sha256"], "done_reason": result.get("done_reason"),
              "thinking_chars": result.get("thinking_chars"), "error": result.get("error")}
    with _LOCK:
        with (trace / "attempts.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _freeze(trace: Path, config: dict, identities: dict) -> None:
    path = trace / "transport.json"
    current = {"config": config, "config_sha256": digest(config), "identities": identities}
    if not path.exists():
        write_json(path, current | {"frozen_at": _now(), "rbs_version": __version__})
        return
    previous = read_json(path)
    if previous["config_sha256"] != current["config_sha256"]:
        raise RBSError("Transport configuration differs from the one frozen for this run; use a new run")
    for key, value in identities.items():
        old = previous["identities"].get(key, {})
        for field in ("digest", "declared_model_id", "model"):
            if old.get(field) != value.get(field):
                raise RBSError(f"{key}: resolved model identity changed since this run started; use a new run")


def review_jobs(run_dir: Path, transport_path: Path, *, confirm_jobs: int | None = None,
                limit: int | None = None, workers: int = 1, retry_interrupted: bool = False,
                progress=None) -> dict:
    run_dir = run_dir.resolve()
    manifest = load_manifest(run_dir)
    if manifest["mode"] == MODE_DEMO:
        raise RBSError("Scripted demonstration runs cannot receive transport reviews")
    config = load_transport(transport_path)
    missing = sorted({j["model_key"] for j in manifest["jobs"]} - config["models"].keys())
    if missing:
        raise RBSError("Transport lacks model keys used by this run: " + ", ".join(missing))
    if not 1 <= workers <= 16:
        raise RBSError("workers must be between 1 and 16")
    trace = run_dir / "transport"
    pending, interrupted, done = [], [], 0
    for job in manifest["jobs"]:
        if (run_dir / "responses" / f"{job['job_id']}.json").exists():
            done += 1
            continue
        attempts = sorted((trace / "raw" / job["job_id"]).glob("attempt-*")) if trace.exists() else []
        if attempts and not retry_interrupted:
            interrupted.append(job["job_id"])
            continue
        pending.append((job, len(attempts) + 1))
    if limit is not None:
        if limit < 1:
            raise RBSError("limit must be positive")
        pending = pending[:limit]
    by_model = {}
    for job, _ in pending:
        by_model[job["model_key"]] = by_model.get(job["model_key"], 0) + 1
    summary = {"run": str(run_dir), "already_recorded": done, "interrupted_not_retried": interrupted,
               "to_run": len(pending), "jobs_by_model_key": by_model,
               "models": {k: {"backend": s["backend"], "target": s.get("model") or s.get("model_id")}
                          for k, s in config["models"].items()},
               "executed": False}
    if not pending or confirm_jobs != len(pending):
        summary["message"] = ("Nothing to run." if not pending else
                              f"Dry run: nothing sent. Re-run with --confirm-jobs {len(pending)} to send these reviews.")
        return summary
    identities = resolve_identities(config)
    trace.mkdir(exist_ok=True)
    _freeze(trace, config, identities)
    started, counts, records = time.monotonic(), {}, []

    def task(item):
        job, attempt = item
        try:
            record = _review_one(run_dir, manifest, job, config, identities, trace, attempt)
        except (RBSError, OSError) as exc:
            record = {"job_id": job["job_id"], "status": "harness_error", "error": str(exc)}
        with _LOCK:
            records.append(record)
            counts[record["status"]] = counts.get(record["status"], 0) + 1
            if progress:
                progress(f"[{len(records)}/{len(pending)}] {job['job_id'][:12]} {job['model_key']} "
                         f"{record['status']} {record.get('verdict') or '-'} {record.get('latency_seconds')}s")
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(task, pending))
    summary.update(executed=True, status_counts=counts, elapsed_seconds=round(time.monotonic() - started, 1),
                   message="Attempts are final. Failed or invalid outputs stay recorded; see transport/attempts.jsonl.")
    return summary


def format_summary(summary: dict) -> str:
    lines = [f"Run: {summary['run']}",
             f"Already recorded: {summary['already_recorded']} | to run: {summary['to_run']} | "
             f"interrupted, not retried: {len(summary['interrupted_not_retried'])}"]
    for key, count in sorted(summary["jobs_by_model_key"].items()):
        spec = summary["models"][key]
        lines.append(f"  {key}: {count} reviews via {spec['backend']} ({spec['target']})")
    if summary["executed"]:
        lines.append("Status counts: " + ", ".join(f"{k}={v}" for k, v in sorted(summary["status_counts"].items())))
        lines.append(f"Elapsed: {summary['elapsed_seconds']} s")
    lines.append(summary["message"])
    return "\n".join(lines)


def progress_to_stderr(line: str) -> None:
    print(line, file=sys.stderr, flush=True)
