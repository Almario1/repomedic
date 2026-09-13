import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.deliver.pr import LocalFilePRDeliverer
from repomedic.llm.mock import MockRouter
from repomedic.models import FailureEvent, PatchCandidate
from repomedic.orchestrator import Orchestrator
from repomedic.sandbox.local import LocalSandboxProvider

DEMO_REPO = os.path.join(os.path.dirname(__file__), "..", "demo", "demo_repo")
CANDIDATES = os.path.join(os.path.dirname(__file__), "..", "demo", "candidates.json")


def load_candidates():
    with open(CANDIDATES, encoding="utf-8") as fh:
        return [PatchCandidate(**c) for c in json.load(fh)]


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.event = FailureEvent(
            repo_url="https://example.invalid/demo.git",
            branch="main",
            commit_sha="demo000",
            failing_command="sh ci.sh",
        )

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def make(self, candidates):
        return Orchestrator(
            sandbox_provider=LocalSandboxProvider(),
            router=MockRouter(scripted_candidates=candidates),
            deliverer=LocalFilePRDeliverer(self.out),
        )

    def test_full_loop_picks_true_division(self):
        result = self.make(load_candidates()).repair(self.event, DEMO_REPO)
        self.assertEqual(result.status, "REPAIRED")
        self.assertEqual(result.winning_candidate.candidate_id, "cand-true-division")
        by_id = {v.candidate_id: v for v in result.verifications}
        self.assertFalse(by_id["cand-subtract"].passed)
        self.assertFalse(by_id["cand-floor-division"].passed)
        self.assertTrue(by_id["cand-true-division"].passed)
        self.assertTrue(os.path.isfile(result.pr_payload["patch_path"]))
        self.assertTrue(os.path.isfile(result.pr_payload["body_path"]))
        with open(result.pr_payload["patch_path"]) as fh:
            self.assertIn("return a / b", fh.read())

    def test_all_candidates_fail(self):
        bad = [c for c in load_candidates() if c.candidate_id != "cand-true-division"]
        result = self.make(bad).repair(self.event, DEMO_REPO)
        self.assertEqual(result.status, "ALL_CANDIDATES_FAILED")
        self.assertIsNone(result.pr_payload)
        self.assertEqual(os.listdir(self.out), [])

    def test_unappliable_patch_counts_as_failed(self):
        cands = load_candidates()
        cands[2].diff = cands[2].diff.replace("def divide", "def nope")
        result = self.make(cands).repair(self.event, DEMO_REPO)
        self.assertEqual(result.status, "ALL_CANDIDATES_FAILED")
        by_id = {v.candidate_id: v for v in result.verifications}
        self.assertFalse(by_id["cand-true-division"].applied)

    def test_no_failure_reproduced(self):
        event = FailureEvent(
            repo_url="x", branch="main", commit_sha="y", failing_command="true"
        )
        result = self.make(load_candidates()).repair(event, DEMO_REPO)
        self.assertEqual(result.status, "NO_FAILURE_REPRODUCED")


if __name__ == "__main__":
    unittest.main()
