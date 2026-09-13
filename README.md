# RepoMedic (private scaffold)

Autonomous CI-repair agent being built for the Nebius x NVIDIA Global AI
Hackathon (Coding and Agentic Engineering Track). This is the private
development scaffold; the public competition repo, README, and license
top-matter come later, once the owner's GitHub account exists.

## What it does

Watch repo -> CI fails -> reproduce the failure in an isolated sandbox
-> diagnose -> generate candidate patches -> run the full test command
against EACH candidate in its OWN fresh sandbox -> deliver only a
verified fix as a pull request.

## Layout

- `repomedic/orchestrator.py` - the repair loop (provider/router/deliverer injected)
- `repomedic/sandbox/base.py` - sandbox seam; `local.py` works today,
  `token_factory.py` is the marked seam for the unverified Sandboxes API
- `repomedic/llm/` - `mock.py` (deterministic, tests/demo) and
  `nemotron.py` (Token Factory OpenAI-compatible client, model IDs are
  placeholders pending the live model list)
- `repomedic/ingest/github_webhook.py` - check_run / workflow_run parsing
- `repomedic/deliver/pr.py` - local-file delivery works; GitHub delivery
  stubbed pending credentials
- `demo/scenarios/` - four seeded-failure packs (logic bug, import error,
  lint gate, multi-file bug). Run all:
  `python3 demo/run_demo.py --all`
  Controls: `--scenario NAME`, `--max-candidates N`, `--timeout S`,
  `--stop-on-first-pass`. Each run appends to `demo/output/history.jsonl`
  and regenerates `demo/output/dashboard.html`.
- `repomedic/dashboard.py` - static dashboard renderer (skeleton for the
  hackathon UI)
- `tests/` - stdlib unittest suite (`python3 -m unittest discover tests`)

## Constraints

Python 3.10+, stdlib only (no pip installs needed). The real deployment
targets Token Factory Sandboxes + Nemotron models + Nebius Serverless;
each external dependency sits behind an interface so the unverified
pieces can be filled in without touching the loop.
