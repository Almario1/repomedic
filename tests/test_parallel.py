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

SCEN = os.path.join(os.path.dirname(__file__), "..", "demo", "scenarios", "division_bug")


def load():
    with open(os.path.join(SCEN, "event.json")) as fh:
        meta = json.load(fh)
    with open(os.path.join(SCEN, "candidates.json")) as fh:
        cands = [PatchCandidate(**c) for c in json.load(fh)]
    return meta, cands


class ParallelTournamentTests(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def make(self, cands, events=None, **kw):
        reporter = (lambda stage, **payload: events.append((stage, payload))) if events is not None else None
        return Orchestrator(
            sandbox_provider=LocalSandboxProvider(),
            router=MockRouter(scripted_candidates=cands),
            deliverer=LocalFilePRDeliverer(self.out),
            reporter=reporter,
            **kw,
        )

    def test_parallel_matches_sequential(self):
        meta, cands = load()
        event = FailureEvent(**meta["event"])
        seq = self.make(cands, parallel=False).repair(event, os.path.join(SCEN, "repo"))
        par = self.make(cands, parallel=True).repair(event, os.path.join(SCEN, "repo"))
        self.assertEqual(seq.status, par.status)
        self.assertEqual(
            seq.winning_candidate.candidate_id, par.winning_candidate.candidate_id
        )
        seq_map = {v.candidate_id: v.passed for v in seq.verifications}
        par_map = {v.candidate_id: v.passed for v in par.verifications}
        self.assertEqual(seq_map, par_map)
        # order preserved despite concurrent completion
        self.assertEqual(
            [v.candidate_id for v in par.verifications],
            [c.candidate_id for c in cands],
        )

    def test_reporter_receives_stage_events(self):
        meta, cands = load()
        events = []
        self.make(cands, events=events, parallel=True).repair(
            FailureEvent(**meta["event"]), os.path.join(SCEN, "repo")
        )
        stages = [s for s, _ in events]
        self.assertIn("reproduced", stages)
        self.assertIn("diagnosed", stages)
        self.assertIn("delivered", stages)
        verified = [p for s, p in events if s == "candidate_verified"]
        self.assertEqual(len(verified), 3)
        self.assertTrue(any(p["passed"] for p in verified))

    def test_reporter_failure_does_not_break_repair(self):
        meta, cands = load()

        def bad_reporter(stage, **payload):
            raise RuntimeError("boom")

        orch = Orchestrator(
            sandbox_provider=LocalSandboxProvider(),
            router=MockRouter(scripted_candidates=cands),
            deliverer=LocalFilePRDeliverer(self.out),
            reporter=bad_reporter,
        )
        result = orch.repair(FailureEvent(**meta["event"]), os.path.join(SCEN, "repo"))
        self.assertEqual(result.status, "REPAIRED")


if __name__ == "__main__":
    unittest.main()
