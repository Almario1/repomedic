# RepoMedic

An autonomous CI-repair agent. When a repository's CI fails, RepoMedic
reproduces the failure inside an isolated Nebius Token Factory Sandbox,
diagnoses the root cause with NVIDIA Nemotron models, generates several
candidate patches, runs the full test command against EACH candidate in
its OWN branched sandbox state, and opens a pull request only for a fix
that is verified green. Bad patches never reach a reviewer.

Built for the Nebius x NVIDIA Global AI Hackathon (Coding and Agentic
Engineering Track).

## Why it is not "just AI writes code"

- Every repair claim is proven by execution: candidates are tournamented
  in parallel, each in its own sandbox branch forked from the same
  seeded repo state (Token Factory Sandboxes' Git-like branching).
- Cost-aware model routing on Token Factory: Nemotron-3-Nano triages the
  failure log, Nemotron-3-Ultra reasons about the patch.
- The dashboard shows live sandbox runs, per-candidate verdicts and the
  winning diff - a complete product, not a proof of concept.

## Architecture

```
GitHub webhook (check_run / workflow_run failure)
  -> ingest (repomedic/ingest)
  -> reproduce in a fresh sandbox (repomedic/sandbox/token_factory)
  -> triage (repomedic/llm/nemotron, Nano)
  -> candidate patches (Nemotron Ultra)
  -> parallel tournament, one sandbox branch per candidate
  -> verified winner -> pull request (repomedic/deliver)
  -> live dashboard (repomedic/dashboard)
```

## Repository layout

- `repomedic/orchestrator.py` - the repair loop (providers injected)
- `repomedic/sandbox/` - sandbox seam: Token Factory Sandboxes provider
  (production) + local provider (development/tests)
- `repomedic/llm/` - model seam: Nemotron router + deterministic mock
- `repomedic/ingest/` - GitHub webhook parsing
- `repomedic/deliver/` - pull-request delivery
- `demo/` - five seeded-failure scenario packs + offline end-to-end demo
- `tests/` - unittest suite (38 tests)

## Try the offline demo

No accounts or dependencies needed (Python 3.10+, stdlib only):

```sh
python3 demo/run_demo.py --all
```

Five seeded failure scenarios (logic bug, import error, lint gate,
multi-file bug, dependency conflict) are repaired end-to-end by the real
loop with a mocked model; PR artifacts, reports and a live dashboard
land in `demo/output/`.

## Production setup

Requires `pip install contree-sdk`, `NEBIUS_API_KEY`, and
`NEBIUS_PROJECT_ID` from Nebius Token Factory. See
`repomedic/sandbox/token_factory.py` for the exact API mapping.

## AI-assistance disclosure

RepoMedic's codebase was prepared by an AI coding assistant (Instinct)
working with the repository owner's authorization and review. Fittingly,
it is also a tool whose entire purpose is that AI-generated patches must
prove themselves by execution before a human ever sees them.

## License

MIT (see LICENSE).
