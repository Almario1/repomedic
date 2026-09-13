import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.dashboard import load_history, render_dashboard


class DashboardTests(unittest.TestCase):
    def test_renders_runs_and_escapes_html(self):
        reports = [
            {
                "scenario": "division_bug",
                "ts": "2026-09-13T21:00:00+00:00",
                "status": "REPAIRED",
                "winner": "cand-true-division",
                "winning_diff": "--- a/calc.py\n+++ b/calc.py\n+<script>alert(1)</script>",
                "diagnosis": "FAIL: test_divide",
                "verifications": [{"candidate_id": "cand-true-division", "passed": True}],
            }
        ]
        page = render_dashboard(reports)
        self.assertIn("division_bug", page)
        self.assertIn("REPAIRED", page)
        self.assertIn("cand-true-division", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_empty_history(self):
        self.assertIn("No repair runs", render_dashboard([]))

    def test_load_history_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "history.jsonl")
            with open(path, "w") as fh:
                fh.write('{"scenario": "a", "status": "REPAIRED"}\n')
                fh.write("\n")
                fh.write('{"scenario": "b", "status": "ALL_CANDIDATES_FAILED"}\n')
            reports = load_history(path)
            self.assertEqual([r["scenario"] for r in reports], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
