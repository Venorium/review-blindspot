import importlib.util
from pathlib import Path
import tempfile
import unittest

from rbs.demo import run_demo
from rbs.io import RBSError, file_hash, read_json
from rbs.packets import load_manifest
from rbs.store import observations
from test_packets_store import config

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("redact_run", ROOT / "tools/redact_run.py")
redactor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redactor)


class RedactRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.run = root / "run"
        run_demo(config(), self.run, root / "packets")

    def test_redaction_keeps_observations_and_metrics(self):
        frozen = load_manifest(self.run)["frozen_hashes"]
        keep = sorted(n for n in frozen if n.startswith("research/"))[0]
        responses_before = {p.name: file_hash(p) for p in (self.run / "responses").iterdir()}
        metrics_before = file_hash(self.run / "report/metrics.json")
        record = redactor.redact(self.run, ["research/"], [keep], "test")
        manifest = load_manifest(self.run)
        self.assertEqual(manifest["packet_root"], redactor.REDACTED_PACKETS)
        self.assertTrue(all(not n.startswith("research/") or n == keep for n in manifest["frozen_hashes"]))
        self.assertTrue((self.run / "frozen" / keep).is_file())
        self.assertGreater(len(record["frozen_files_removed"]), 0)
        self.assertEqual(record["frozen_files_removed"], {n: h for n, h in frozen.items()
                                                          if n.startswith("research/") and n != keep})
        self.assertEqual(file_hash(self.run / "report/metrics.json"), metrics_before)
        self.assertEqual({p.name: file_hash(p) for p in (self.run / "responses").iterdir()}, responses_before)
        self.assertEqual(read_json(self.run / "report/provenance.json")["manifest_sha256"],
                         file_hash(self.run / "manifest.json"))
        observations(self.run)

    def test_second_redaction_and_unknown_keep_are_refused(self):
        with self.assertRaisesRegex(RBSError, "Unknown"):
            redactor.redact(self.run, ["research/"], ["research/absent.md"], "test")
        redactor.redact(self.run, [], [], "test")
        with self.assertRaisesRegex(RBSError, "already redacted"):
            redactor.redact(self.run, [], [], "test")


if __name__ == "__main__":
    unittest.main()
