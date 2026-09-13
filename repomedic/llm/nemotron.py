"""Nemotron router via Nebius Token Factory.

Verified against Token Factory docs/model catalog on 2026-09-13:
- base URL https://api.tokenfactory.nebius.com/v1 (OpenAI-compatible)
- model IDs from https://tokenfactory.nebius.com/model-catalog.md
- machine-readable catalog: /api/public/models_info
Routing policy (cost-aware, mirrors the track guidance):
  triage              -> Nemotron-3-Nano (cheap classification)
  generate_candidates -> Nemotron-3-Ultra (deep patch reasoning)
The candidate tournament that verifies each patch needs no model calls.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Callable, Optional

from ..models import Diagnosis, FailureEvent, PatchCandidate
from .base import LLMRouter

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"

# Live model IDs (model catalog, 2026-09-13).
MODEL_TRIAGE = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
MODEL_REASONING = "nvidia/Nemotron-3-Ultra-550b-a55b"
MODEL_MID = "nvidia/nemotron-3-super-120b-a12b"  # reserved for test generation

_PATCH_INSTRUCTION = (
    "You are repairing a failing CI run. Reply with a unified diff only, "
    "in a fenced ```diff block, using a/ and b/ path prefixes. The diff "
    "must apply cleanly with git apply."
)


class NemotronRouter(LLMRouter):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        model_triage: str = MODEL_TRIAGE,
        model_reasoning: str = MODEL_REASONING,
    ) -> None:
        self.api_key = api_key or os.environ.get("NEBIUS_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model_triage = model_triage
        self.model_reasoning = model_reasoning
        self.last_request_models: list[str] = []  # introspection for tests

    def _chat(self, model: str, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("NEBIUS_API_KEY is not set")
        self.last_request_models.append(model)
        body = json.dumps({"model": model, "messages": messages}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            payload: dict[str, Any] = json.loads(resp.read().decode())
        return payload["choices"][0]["message"]["content"]

    def triage(self, event: FailureEvent, failure_log: str) -> Diagnosis:
        text = self._chat(
            self.model_triage,
            [
                {
                    "role": "user",
                    "content": (
                        "Summarise this CI failure in <=3 lines, then list the "
                        "failing test names, then the suspect files.\n\n"
                        + failure_log[-6000:]
                    ),
                }
            ],
        )
        return Diagnosis(summary=text.strip())

    def generate_candidates(
        self,
        diagnosis: Diagnosis,
        read_file: Callable[[str], str],
        max_candidates: int = 3,
    ) -> list[PatchCandidate]:
        snippets = "\n\n".join(
            f"### {path}\n{read_file(path)}" for path in diagnosis.suspected_files[:3]
        )
        text = self._chat(
            self.model_reasoning,
            [
                {"role": "system", "content": _PATCH_INSTRUCTION},
                {
                    "role": "user",
                    "content": f"Diagnosis:\n{diagnosis.summary}\n\nFiles:\n{snippets}",
                },
            ],
        )
        diff = _extract_diff(text)
        if not diff:
            return []
        return [PatchCandidate(candidate_id="nemotron-1", diff=diff, rationale=diagnosis.summary)]


def _extract_diff(text: str) -> str:
    in_block = False
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.strip().startswith("```diff"):
            in_block = True
            continue
        if raw.strip().startswith("```") and in_block:
            break
        if in_block:
            lines.append(raw)
    return "\n".join(lines)
