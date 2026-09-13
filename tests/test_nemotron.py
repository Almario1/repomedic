import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.llm.nemotron import (
    MODEL_REASONING,
    MODEL_TRIAGE,
    NemotronRouter,
    _extract_diff,
)
from repomedic.models import Diagnosis, FailureEvent


class FakeNemotron(NemotronRouter):
    def __init__(self, reply):
        super().__init__(api_key="test-key")
        self.reply = reply
        self.calls = []

    def _chat(self, model, messages):
        self.calls.append(model)
        self.last_request_models.append(model)
        return self.reply


class NemotronRoutingTests(unittest.TestCase):
    def test_triage_uses_small_model(self):
        r = FakeNemotron("1 test failed")
        d = r.triage(FailureEvent("u", "main", "s", "cmd"), "log")
        self.assertEqual(r.calls, [MODEL_TRIAGE])
        self.assertEqual(d.summary, "1 test failed")

    def test_candidates_use_reasoning_model(self):
        reply = "Here is the fix:\n```diff\n--- a/calc.py\n+++ b/calc.py\n@@ -1,1 +1,1 @@\n-x\n+y\n```"
        r = FakeNemotron(reply)
        diag = Diagnosis(summary="boom", suspected_files=["calc.py"])
        cands = r.generate_candidates(diag, lambda p: "file body")
        self.assertEqual(r.calls, [MODEL_REASONING])
        self.assertEqual(len(cands), 1)
        self.assertIn("+y", cands[0].diff)

    def test_extract_diff_without_fence_returns_empty(self):
        self.assertEqual(_extract_diff("no code here"), "")

    def test_missing_api_key_raises(self):
        r = NemotronRouter(api_key="")
        with self.assertRaises(RuntimeError):
            r.triage(FailureEvent("u", "b", "s", "c"), "log")


if __name__ == "__main__":
    unittest.main()
