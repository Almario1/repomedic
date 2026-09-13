"""LLM seam.

All model calls go through LLMRouter so the deterministic MockRouter
(tests/demo) and the NemotronRouter (production, via Token Factory's
OpenAI-compatible endpoint) are interchangeable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from ..models import Diagnosis, FailureEvent, PatchCandidate


class LLMRouter(ABC):
    @abstractmethod
    def triage(self, event: FailureEvent, failure_log: str) -> Diagnosis:
        """Turn a raw failure log into a structured Diagnosis."""

    @abstractmethod
    def generate_candidates(
        self,
        diagnosis: Diagnosis,
        read_file: Callable[[str], str],
        max_candidates: int = 3,
    ) -> list[PatchCandidate]:
        """Propose up to max_candidates unified-diff patches.

        read_file gives the model access to the sandboxed repo contents.
        """
