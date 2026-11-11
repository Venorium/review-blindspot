from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rbs import report
from rbs.demo import run_demo
from rbs.io import read_json
from test_packets_store import config


class ReportProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / "run"
        run_demo(config(), self.run, self.root / "packets")

    def test_report_records_inputs_and_matching_frozen_code(self):
        value = read_json(self.run / "report/provenance.json")
        self.assertTrue(value["computed_with_frozen_code"])
        self.assertEqual(value["modules_differing_from_frozen_code"], [])
        self.assertEqual(value["responses"], 8)
        self.assertEqual(value["computing_code_sha256"], value["frozen_run_code_sha256"])

    def test_code_drift_is_named_and_metrics_are_unchanged(self):
        drifted = report._current_code() | {"metrics.py": "0" * 64}
        with patch.object(report, "_current_code", return_value=drifted):
            report.write_report(self.run, self.run / "report-002")
        value = read_json(self.run / "report-002/provenance.json")
        self.assertFalse(value["computed_with_frozen_code"])
        self.assertEqual(value["modules_differing_from_frozen_code"], ["metrics.py"])
        self.assertEqual(read_json(self.run / "report/metrics.json"), read_json(self.run / "report-002/metrics.json"))
        self.assertEqual(value["inputs_sha256"], read_json(self.run / "report/provenance.json")["inputs_sha256"])


if __name__ == "__main__":
    unittest.main()
