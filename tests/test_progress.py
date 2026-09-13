import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.dashboard import render_dashboard
from repomedic.progress import ProgressReporter


class ProgressReporterTests(unittest.TestCase):
    def test_roundtrip_and_on_update(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []
            rep = ProgressReporter(os.path.join(d, "live", "run.json"),
                                   on_update=lambda: calls.append(1))
            rep("started", scenario="x")
            rep("candidate_verified", candidate_id="c1", passed=True)
            events = ProgressReporter.load(os.path.join(d, "live", "run.json"))
            self.assertEqual([e["stage"] for e in events], ["started", "candidate_verified"])
            self.assertEqual(events[1]["candidate_id"], "c1")
            self.assertEqual(len(calls), 2)

    def test_load_missing_file(self):
        self.assertEqual(ProgressReporter.load("/nonexistent/x.json"), [])

    def test_dashboard_renders_live_section(self):
        live = [{
            "scenario": "multi_file",
            "events": [
                {"ts": "t", "stage": "reproduced", "ok": True},
                {"ts": "t", "stage": "candidate_verified", "candidate_id": "c1", "passed": False},
            ],
        }]
        page = render_dashboard([], live=live)
        self.assertIn("IN PROGRESS", page)
        self.assertIn("multi_file", page)
        self.assertIn("candidate_verified", page)


if __name__ == "__main__":
    unittest.main()
