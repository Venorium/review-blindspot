from copy import deepcopy
import unittest
import xml.etree.ElementTree as ET

from rbs.io import ROOT, read_json
from tools.render_demo_preview import render


class DemoPreviewTests(unittest.TestCase):
    def setUp(self):
        self.metrics = read_json(ROOT / 'docs/examples/metrics.json')

    def test_committed_artwork_is_reproducible_from_example_metrics(self):
        for compact, name in [(False, 'demo-preview.svg'), (True, 'demo-preview-compact.svg')]:
            svg = render(self.metrics, compact=compact)
            ET.fromstring(svg)
            self.assertEqual(svg, (ROOT / 'docs/assets' / name).read_text(encoding='utf-8'))

    def test_external_results_cannot_be_labelled_as_scripted_artwork(self):
        metrics = deepcopy(self.metrics)
        metrics['results_are_model_evidence'] = 'NOT_AUTOMATICALLY_VALIDATED'
        with self.assertRaises(ValueError):
            render(metrics)

    def test_missing_data_or_different_design_cannot_be_hidden(self):
        for field, value in [('target_unresolved_groups', 1), ('review_jobs', 99),
                             ('control_groups', 0), ('execution_status_counts', {'timeout': 4})]:
            metrics = deepcopy(self.metrics)
            metrics['arms'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                render(metrics)
