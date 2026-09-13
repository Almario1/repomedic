#!/usr/bin/env python3
"""Offline end-to-end demo of the RepoMedic loop.

Simulates: CI fails on demo_repo -> reproduce in a fresh sandbox ->
triage -> tournament 3 scripted candidate patches, each in its own fresh
sandbox -> deliver the verified winner as a PR artifact in demo/output/.

The model is mocked (scripted candidates); everything else - sandboxing,
reproduction, patch application, per-candidate verification, winner
selection, PR rendering - is the real production code path.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.deliver.pr import LocalFilePRDeliverer, result_to_json
from repomedic.llm.mock import MockRouter
from repomedic.models import FailureEvent, PatchCandidate
from repomedic.orchestrator import Orchestrator
from repomedic.sandbox.local import LocalSandboxProvider

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_REPO = os.path.join(HERE, "demo_repo")
OUT_DIR = os.path.join(HERE, "output")


def main() -> int:
    with open(os.path.join(HERE, "candidates.json"), encoding="utf-8") as fh:
        candidates = [PatchCandidate(**c) for c in json.load(fh)]

    event = FailureEvent(
        repo_url="https://example.invalid/demo/demo-repo.git",
        branch="main",
        commit_sha="demo000",
        failing_command="sh ci.sh",
    )

    orchestrator = Orchestrator(
        sandbox_provider=LocalSandboxProvider(),
        router=MockRouter(scripted_candidates=candidates),
        deliverer=LocalFilePRDeliverer(OUT_DIR),
    )

    print("[1/4] Reproducing CI failure in a fresh sandbox ...")
    print("[2/4] Triaging failure log ...")
    print("[3/4] Tournament: verifying each candidate patch in its own sandbox ...")
    result = orchestrator.repair(event, DEMO_REPO)
    print(f"[4/4] Status: {result.status}")

    for ver in result.verifications:
        mark = "PASS" if ver.passed else "FAIL"
        detail = ""
        if ver.run is not None and not ver.run.ok:
            last = [l for l in ver.run.combined_log.splitlines() if l.startswith(("FAIL", "FAILED"))]
            detail = f"  ({last[0] if last else 'tests failed'})"
        print(f"      [{mark}] {ver.candidate_id}{detail}")

    if result.winning_candidate:
        print(f"Winner: {result.winning_candidate.candidate_id}")
        print(f"PR artifacts: {result.pr_payload}")

    report_path = os.path.join(OUT_DIR, "repair_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(result_to_json(result))
    print(f"Full report: {report_path}")
    return 0 if result.status == "REPAIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
