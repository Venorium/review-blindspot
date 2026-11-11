import json
from pathlib import Path
import tempfile
import unittest

from rbs.io import RBSError, file_hash
from rbs.packets import load_manifest, prepare
from rbs.store import import_adjudication_batch, import_submission, observations
from test_packets_store import config, submission


class BatchAdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / "run"
        prepare(config(), self.run, self.root / "packets")
        self.lines = []
        for job in load_manifest(self.run)["jobs"][:3]:
            value = submission(job)
            value["review"] = {"verdict": "request_changes", "summary": "Test.", "findings": [
                {"finding_id": "f1", "file": "candidate.py", "line_start": 1, "line_end": 1, "severity": "low",
                 "description": "Test finding.", "evidence": "Test evidence."}]}
            path = import_submission(self.run, value)
            self.lines.append({"schema_version": 1, "job_id": job["job_id"], "submission_sha256": file_hash(path),
                               "target_detection": "not_applicable" if job["variant"] == "correct" else "unresolved",
                               "finding_ids": [], "rationale": "Batch test.", "grader_id": "unit-test",
                               "method": "manual", "evidence_reference": "test_adjudication_batch.py"})

    def write(self, items):
        path = self.root / "batch.jsonl"
        path.write_text("\n".join(json.dumps(x) for x in items) + "\n", encoding="utf-8")
        return path

    def test_valid_batch_is_stored(self):
        self.assertEqual(import_adjudication_batch(self.run, self.write(self.lines))["stored"], 3)
        _, rows = observations(self.run)
        self.assertEqual(sum(r["annotation"] is not None for r in rows), 3)

    def test_one_invalid_line_stores_nothing(self):
        broken = [dict(x) for x in self.lines]
        broken[2]["submission_sha256"] = "0" * 64
        with self.assertRaisesRegex(RBSError, "Item 3"):
            import_adjudication_batch(self.run, self.write(broken))
        self.assertEqual(list((self.run / "adjudications").iterdir()), [])
        with self.assertRaisesRegex(RBSError, "already"):
            import_adjudication_batch(self.run, self.write([self.lines[0], self.lines[0]]))


if __name__ == "__main__":
    unittest.main()
