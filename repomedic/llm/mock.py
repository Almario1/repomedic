"""Deterministic router for tests and the offline demo.

Triage is heuristic (parses unittest/pytest failure lines). Candidate
generation returns a scripted list, simulating what Nemotron would
produce - the tournament that follows is fully real, which is what the
demo needs to prove.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from ..models import Diagnosis, FailureEvent, PatchCandidate
from .base import LLMRouter

_FAIL_RE = re.compile(r"^(?:FAIL|FAILED)[:\s]+(\S+)", re.MULTILINE)
_FILE_RE = re.compile(r'File "([^"]+)"', re.MULTILINE)


class MockRouter(LLMRouter):
    def __init__(self, scripted_candidates: Optional[list[PatchCandidate]] = None) -> None:
        self.scripted_candidates = scripted_candidates or []

    def triage(self, event: FailureEvent, failure_log: str) -> Diagnosis:
        tests = _FAIL_RE.findall(failure_log)
        files = sorted(set(_FILE_RE.findall(failure_log)))
        summary_lines = [
            line.strip()
            for line in failure_log.splitlines()
            if line.strip().startswith(("FAIL", "FAILED", "AssertionError"))
        ]
        return Diagnosis(
            summary="; ".join(summary_lines[:3]) or "Unparsed failure",
            failing_tests=tests,
            suspected_files=files,
        )

    def generate_candidates(
        self,
        diagnosis: Diagnosis,
        read_file: Callable[[str], str],
        max_candidates: int = 3,
    ) -> list[PatchCandidate]:
        return self.scripted_candidates[:max_candidates]
