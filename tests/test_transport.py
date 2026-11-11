from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

from rbs.cli import main
from rbs.demo import run_demo
from rbs.io import RBSError, read_json
from rbs.packets import load_manifest, prepare
from rbs.status import run_status
from rbs.transport import _seed, build_prompt, extract_review, review_jobs
from test_packets_store import config

FENCE = "\x60" * 3
APPROVE = {"verdict": "approve", "findings": [], "summary": "Fake reviewer: no defect reported."}
BLOCK = {"verdict": "request_changes", "summary": "Fake reviewer blocks.", "findings": [
    {"finding_id": "f1", "file": "candidate.py", "line_start": 1, "line_end": 1, "severity": "high",
     "description": "Fake finding.", "evidence": "Fake evidence."}]}


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send(200, {"models": [{"name": "fake:1b", "digest": "0123456789abcdef" * 4,
                                        "details": {"family": "fake"}}]})
        else:
            self._send(200, {"version": "0.0-test"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        server = self.server
        with server.lock:
            server.requests.append(body)
            behavior = server.behaviors.pop(0) if server.behaviors else server.default
        if behavior == "http500":
            return self._send(500, {"error": "fake failure"})
        if behavior == "slow":
            time.sleep(2)
        content = {"approve": json.dumps(APPROVE), "block": json.dumps(BLOCK), "slow": json.dumps(APPROVE),
                   "malformed": "not json at all", "length": json.dumps(APPROVE)[:20],
                   "bad_schema": json.dumps({**APPROVE, "findings": BLOCK["findings"]})}[behavior]
        self._send(200, {"model": body["model"], "message": {"role": "assistant", "content": content, "thinking": "t"},
                         "done": True, "done_reason": "length" if behavior == "length" else "stop",
                         "prompt_eval_count": 321, "eval_count": 45})


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rbs-transport-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run, self.packets = self.root / "run", self.root / "packets"
        prepare(config(), self.run, self.packets)
        self.manifest = load_manifest(self.run)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.daemon_threads = True
        self.server.lock, self.server.requests, self.server.behaviors = threading.Lock(), [], []
        self.server.default = "approve"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.transport = self.write_transport()

    def write_transport(self, name="transport.json", **override):
        spec = {"backend": "ollama", "model": "fake:1b", "timeout_seconds": 10, "think": "low",
                "endpoint": f"http://127.0.0.1:{self.server.server_address[1]}"} | override
        path = self.root / name
        path.write_text(json.dumps({"schema_version": 1, "models": {"model_a": spec}}), encoding="utf-8")
        return path

    def responses(self):
        return [read_json(p) for p in sorted((self.run / "responses").glob("*.json"))]

    def test_dry_run_sends_nothing(self):
        summary = review_jobs(self.run, self.transport)
        self.assertFalse(summary["executed"])
        self.assertEqual(summary["to_run"], 8)
        self.assertIn("--confirm-jobs 8", summary["message"])
        self.assertEqual(self.server.requests, [])
        self.assertFalse((self.run / "transport").exists())

    def test_reviews_are_imported_with_bound_trace_and_harness_metadata(self):
        summary = review_jobs(self.run, self.transport, confirm_jobs=8, workers=2)
        self.assertEqual(summary["status_counts"], {"ok": 8})
        self.assertEqual(run_status(self.run)["state"], "records_complete")
        jobs = {j["job_id"]: j for j in self.manifest["jobs"]}
        for response in self.responses():
            execution = response["execution"]
            self.assertTrue(execution["model_id"].startswith("ollama:fake:1b@0123456789ab"))
            self.assertEqual((execution["input_tokens"], execution["output_tokens"]), (321, 45))
            self.assertIsNone(execution["cost_usd"])
            folder = self.run / execution["trace_reference"]
            request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
            job = jobs[response["job_id"]]
            self.assertEqual(request["options"], {"num_predict": job["output_token_cap"], "seed": _seed(job["job_id"])})
            prompt = request["messages"][0]["content"]
            self.assertNotIn(job["job_id"], prompt)
            self.assertNotIn("target_defect", prompt)
            self.assertNotIn("exact expiration timestamp", prompt)
            self.assertIn("candidate.py", prompt)
            self.assertNotIn("allOf", json.dumps(request["format"]))
        frozen = read_json(self.run / "transport/transport.json")
        self.assertEqual(frozen["identities"]["model_a"]["server_version"], "0.0-test")
        lines = (self.run / "transport/attempts.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 8)
        self.assertEqual(review_jobs(self.run, self.transport)["to_run"], 0)

    def test_failures_stay_recorded_and_are_never_retried(self):
        self.server.behaviors = ["malformed", "length", "http500", "bad_schema"]
        summary = review_jobs(self.run, self.transport, confirm_jobs=4, limit=4)
        self.assertEqual(summary["status_counts"], {"invalid_output": 3, "provider_error": 1})
        self.assertTrue(all(r["review"] is None for r in self.responses()))
        self.assertEqual(run_status(self.run)["reviews"]["failed"], 4)
        follow_up = review_jobs(self.run, self.transport)
        self.assertEqual((follow_up["already_recorded"], follow_up["to_run"]), (4, 4))

    def test_timeout_is_recorded_as_timeout(self):
        self.server.default = "slow"
        path = self.write_transport("slow.json", timeout_seconds=0.5)
        summary = review_jobs(self.run, path, confirm_jobs=1, limit=1)
        self.assertEqual(summary["status_counts"], {"timeout": 1})
        self.assertEqual(self.responses()[0]["execution"]["status"], "timeout")

    def test_interrupted_attempt_requires_explicit_retry(self):
        job = self.manifest["jobs"][0]
        (self.run / "transport/raw" / job["job_id"] / "attempt-1").mkdir(parents=True)
        summary = review_jobs(self.run, self.transport)
        self.assertEqual(summary["interrupted_not_retried"], [job["job_id"]])
        self.assertEqual(summary["to_run"], 7)
        summary = review_jobs(self.run, self.transport, confirm_jobs=1, limit=1, retry_interrupted=True)
        record = json.loads((self.run / "transport/attempts.jsonl").read_text(encoding="utf-8"))
        self.assertEqual((record["job_id"], record["attempt"]), (job["job_id"], 2))

    def test_changed_transport_or_missing_model_is_refused(self):
        review_jobs(self.run, self.transport, confirm_jobs=1, limit=1)
        changed = self.write_transport("changed.json", timeout_seconds=11)
        with self.assertRaisesRegex(RBSError, "differs"):
            review_jobs(self.run, changed, confirm_jobs=1, limit=1)
        other = self.root / "other"
        prepare(config(), other, self.root / "other-packets")
        before = len(self.server.requests)
        with self.assertRaisesRegex(RBSError, "not available"):
            review_jobs(other, self.write_transport("absent.json", model="absent:1b"), confirm_jobs=1, limit=1)
        self.assertEqual(len(self.server.requests), before)

    def test_demo_runs_and_unknown_model_keys_are_refused(self):
        demo = self.root / "demo"
        run_demo(config(), demo, self.root / "demo-packets")
        with self.assertRaisesRegex(RBSError, "Scripted"):
            review_jobs(demo, self.transport)
        path = self.root / "keys.json"
        path.write_text(json.dumps({"schema_version": 1, "models": {"model_z": {
            "backend": "ollama", "model": "fake:1b", "timeout_seconds": 5}}}), encoding="utf-8")
        with self.assertRaisesRegex(RBSError, "lacks model keys"):
            review_jobs(self.run, path)

    def command_transport(self, mode, timeout=20):
        script = self.root / "fake_reviewer.py"
        script.write_text("\n".join([
            "import json, os, sys",
            "prompt = sys.stdin.read()",
            "assert 'candidate.py' in prompt and os.path.isfile(sys.argv[1])",
            "assert sorted(os.listdir('.')) == ['review.schema.json'], os.listdir('.')",
            "mode = sys.argv[2]",
            "if mode == 'fail': sys.exit(3)",
            "if mode == 'sleep':",
            "    import time; time.sleep(5)",
            "print('Review follows.')",
            "print('" + FENCE + "json')",
            "print(json.dumps(" + repr(BLOCK) + "))",
            "print('" + FENCE + "')"]), encoding="utf-8")
        path = self.root / f"command-{mode}.json"
        path.write_text(json.dumps({"schema_version": 1, "models": {"model_a": {
            "backend": "command", "argv": [sys.executable, str(script), "{schema_path}", mode],
            "model_id": "fake-cli-model", "timeout_seconds": timeout}}}), encoding="utf-8")
        return path

    def test_command_backend_uses_fresh_directory_and_declared_identity(self):
        summary = review_jobs(self.run, self.command_transport("ok"), confirm_jobs=2, limit=2)
        self.assertEqual(summary["status_counts"], {"ok": 2})
        response = self.responses()[0]
        self.assertEqual(response["execution"]["model_id"], "declared:fake-cli-model")
        self.assertFalse(response["execution"]["isolation_attested"])
        self.assertEqual(response["review"]["verdict"], "request_changes")
        record = json.loads((self.run / "transport/attempts.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["extraction"], "last_json_fence")

    def test_command_failures_are_classified(self):
        self.assertEqual(review_jobs(self.run, self.command_transport("fail"), confirm_jobs=1, limit=1)["status_counts"],
                         {"provider_error": 1})
        other = self.root / "other"
        prepare(config(), other, self.root / "other-packets")
        self.assertEqual(review_jobs(other, self.command_transport("sleep", timeout=1), confirm_jobs=1, limit=1)["status_counts"],
                         {"timeout": 1})

    def test_extraction_keeps_object_and_rejects_ambiguous_json(self):
        self.assertEqual(extract_review(json.dumps(APPROVE)), (APPROVE, "whole_output"))
        self.assertEqual(extract_review("x " + json.dumps(APPROVE) + " y")[1], "outer_braces")
        with self.assertRaises(RBSError):
            extract_review('{"verdict": "approve", "verdict": "request_changes"}')
        with self.assertRaises(RBSError):
            extract_review("no object")

    def test_prompt_is_deterministic_and_numbers_python_lines(self):
        packet = self.packets / self.manifest["jobs"][0]["job_id"]
        prompt = build_prompt(packet)
        self.assertEqual(prompt, build_prompt(packet))
        self.assertIn("===== candidate.py =====\n1| ", prompt)
        self.assertNotIn("job.json", prompt)

    def test_cli_dry_run_is_readable_and_json(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["review", "--run", str(self.run), "--transport", str(self.transport)]), 0)
        self.assertIn("Dry run: nothing sent", out.getvalue())
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            self.assertEqual(main(["review", "--run", str(self.run), "--transport", str(self.transport), "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue())["to_run"], 8)


if __name__ == "__main__":
    unittest.main()
