#!/usr/bin/env python3
"""Offline end-to-end demo of the RepoMedic loop, across scenario packs.

Each scenario in demo/scenarios/<name>/ contains a repo/ with a seeded
failure, a candidates.json (scripted model output) and an event.json.
The sandboxing, reproduction, patch application, per-candidate
verification, winner selection and PR rendering are the real production
code path; only the model is mocked.

Usage:
  python3 demo/run_demo.py --scenario division_bug
  python3 demo/run_demo.py --all --stop-on-first-pass
  python3 demo/run_demo.py --all --max-candidates 2 --timeout 60
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.dashboard import load_history, render_dashboard
from repomedic.deliver.pr import LocalFilePRDeliverer, result_to_json
from repomedic.llm.mock import MockRouter
from repomedic.models import FailureEvent, PatchCandidate
from repomedic.orchestrator import Orchestrator
from repomedic.sandbox.local import LocalSandboxProvider

HERE = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_DIR = os.path.join(HERE, "scenarios")
OUT_DIR = os.path.join(HERE, "output")
HISTORY_PATH = os.path.join(OUT_DIR, "history.jsonl")
DASHBOARD_PATH = os.path.join(OUT_DIR, "dashboard.html")


def list_scenarios() -> list[str]:
    return sorted(
        name
        for name in os.listdir(SCENARIOS_DIR)
        if os.path.isdir(os.path.join(SCENARIOS_DIR, name))
    )


def run_scenario(name: str, args: argparse.Namespace) -> dict:
    scenario_dir = os.path.join(SCENARIOS_DIR, name)
    with open(os.path.join(scenario_dir, "event.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    with open(os.path.join(scenario_dir, "candidates.json"), encoding="utf-8") as fh:
        candidates = [PatchCandidate(**c) for c in json.load(fh)]

    event = FailureEvent(**meta["event"])
    run_out = os.path.join(OUT_DIR, name)
    orchestrator = Orchestrator(
        sandbox_provider=LocalSandboxProvider(),
        router=MockRouter(scripted_candidates=candidates),
        deliverer=LocalFilePRDeliverer(run_out),
        max_candidates=args.max_candidates,
        command_timeout=args.timeout,
        stop_on_first_pass=args.stop_on_first_pass,
    )
    result = orchestrator.repair(event, os.path.join(scenario_dir, "repo"))

    print(f"== {name}: {result.status}")
    for ver in result.verifications:
        mark = "PASS" if ver.passed else "FAIL"
        print(f"   [{mark}] {ver.candidate_id}")
    if result.winning_candidate:
        print(f"   winner: {result.winning_candidate.candidate_id}")
        expected = meta.get("expected_winner")
        if expected and result.winning_candidate.candidate_id != expected:
            print(f"   WARNING: expected winner {expected}")

    record = {
        "scenario": name,
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "status": result.status,
        "winner": result.winning_candidate.candidate_id if result.winning_candidate else None,
        "winning_diff": result.winning_candidate.diff if result.winning_candidate else None,
        "diagnosis": result.diagnosis.summary if result.diagnosis else "",
        "category": result.diagnosis.category if result.diagnosis else "",
        "verifications": [
            {"candidate_id": v.candidate_id, "passed": v.passed} for v in result.verifications
        ],
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    with open(os.path.join(OUT_DIR, f"report_{name}.json"), "w", encoding="utf-8") as fh:
        fh.write(result_to_json(result))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", choices=list_scenarios())
    group.add_argument("--all", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--stop-on-first-pass", action="store_true")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    names = list_scenarios() if args.all else [args.scenario]
    records = [run_scenario(name, args) for name in names]

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as fh:
        fh.write(render_dashboard(load_history(HISTORY_PATH)))
    print(f"Dashboard: {DASHBOARD_PATH}")

    return 0 if all(r["status"] == "REPAIRED" for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
