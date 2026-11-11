import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from rbs.demo import run_demo
from rbs.packets import load_manifest, prepare
from test_packets_store import config

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("render_blindspot_map", ROOT / "tools/render_blindspot_map.py")
mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapper)
SVG = "{http://www.w3.org/2000/svg}"


class BlindSpotMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_demo_map_is_labelled_deterministic_and_complete(self):
        run = self.root / "demo"
        run_demo(config(), run, self.root / "packets")
        svg = mapper.render(run)
        self.assertEqual(svg, mapper.render(run))
        tree = ET.fromstring(svg)
        self.assertIn("SCRIPTED DEMO", tree.find(SVG + "desc").text)
        manifest = load_manifest(run)
        slots = sum(len(a["reviewers"]) for a in manifest["config"]["arms"])
        cells = [r for r in tree.iter(SVG + "rect") if r.get("width") == "28"]
        self.assertEqual(len(cells), slots * len({j["case_id"] for j in manifest["jobs"]}))

    def test_unreviewed_external_run_shows_missing_cells_not_outcomes(self):
        run = self.root / "run"
        prepare(config(), run, self.root / "packets")
        svg = mapper.render(run, "correct")
        self.assertIn("Exploratory pilot", svg)
        tree = ET.fromstring(svg)
        cells = [r for r in tree.iter(SVG + "rect") if r.get("width") == "28"]
        self.assertEqual({r.get("fill") for r in cells}, {"#ffffff"})
        self.assertIn(">0/4<", svg)


if __name__ == "__main__":
    unittest.main()
