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

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "..", "demo", "scenarios")


def scenario_names():
    return sorted(
        n for n in os.listdir(SCENARIOS_DIR) if os.path.isdir(os.path.join(SCENARIOS_DIR, n))
    )


class ScenarioPackTests(unittest.TestCase):
    def test_every_scenario_repairs_to_expected_winner(self):
        self.assertGreaterEqual(len(scenario_names()), 4)
        for name in scenario_names():
            with self.subTest(scenario=name):
                out = tempfile.mkdtemp()
                try:
                    sdir = os.path.join(SCENARIOS_DIR, name)
                    with open(os.path.join(sdir, "event.json")) as fh:
                        meta = json.load(fh)
                    with open(os.path.join(sdir, "candidates.json")) as fh:
                        cands = [PatchCandidate(**c) for c in json.load(fh)]
                    orch = Orchestrator(
                        sandbox_provider=LocalSandboxProvider(),
                        router=MockRouter(scripted_candidates=cands),
                        deliverer=LocalFilePRDeliverer(out),
                    )
                    result = orch.repair(
                        FailureEvent(**meta["event"]), os.path.join(sdir, "repo")
                    )
                    self.assertEqual(result.status, "REPAIRED", name)
                    self.assertEqual(
                        result.winning_candidate.candidate_id,
                        meta["expected_winner"],
                        name,
                    )
                    # every losing candidate must have genuinely failed
                    losers = [
                        v for v in result.verifications
                        if v.candidate_id != meta["expected_winner"]
                    ]
                    self.assertTrue(losers)
                    self.assertTrue(all(not v.passed for v in losers), name)
                finally:
                    shutil.rmtree(out, ignore_errors=True)

    def test_stop_on_first_pass_skips_later_candidates(self):
        out = tempfile.mkdtemp()
        try:
            sdir = os.path.join(SCENARIOS_DIR, "multi_file")
            with open(os.path.join(sdir, "event.json")) as fh:
                meta = json.load(fh)
            with open(os.path.join(sdir, "candidates.json")) as fh:
                cands = [PatchCandidate(**c) for c in json.load(fh)]
            # put the winner first; losers should never be verified
            cands.sort(key=lambda c: c.candidate_id != meta["expected_winner"])
            orch = Orchestrator(
                sandbox_provider=LocalSandboxProvider(),
                router=MockRouter(scripted_candidates=cands),
                deliverer=LocalFilePRDeliverer(out),
                stop_on_first_pass=True,
            )
            result = orch.repair(FailureEvent(**meta["event"]), os.path.join(sdir, "repo"))
            self.assertEqual(result.status, "REPAIRED")
            self.assertEqual(len(result.verifications), 1)
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
