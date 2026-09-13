"""Deterministic router for tests and the offline demo.

Triage is heuristic but realistic: it parses unittest/pytest failure
lines, import/collection errors, assertion messages and lint output, and
classifies the failure category. Candidate generation returns a scripted
list, simulating what Nemotron would produce - the tournament that
follows is fully real, which is what the demo needs to prove.
"""

from __future__ import annotations

import os
import re
from typing import Callable, Optional

from ..models import Diagnosis, FailureEvent, PatchCandidate
from .base import LLMRouter

_UNITTEST_RE = re.compile(r"^(?:FAIL|ERROR)[:\s]+(\S+)", re.MULTILINE)
_PYTEST_RE = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)
_TRACEBACK_FILE_RE = re.compile(r'File "(?:\./)?([^"]+\.py)"', re.MULTILINE)
_EXCEPTION_RE = re.compile(r"^((?:\w+\.)?\w*(?:Error|Exception|Exit|Interrupt))\b:?\s*(.*)$", re.MULTILINE)


def categorize(log: str) -> str:
    if re.search(r"(ModuleNotFoundError|ImportError|Failed to import)", log):
        return "import"
    if re.search(r"(?im)^lint\b|lint failed|trailing whitespace", log):
        return "lint"
    if "AssertionError" in log:
        return "assertion"
    if _EXCEPTION_RE.search(log):
        return "error"
    return "unknown"


def summarize(log: str, max_lines: int = 4) -> str:
    interesting = []
    for line in log.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(FAIL|FAILED|ERROR|AssertionError|\w*Error|LINT|.*lint failed)", stripped
        ):
            interesting.append(stripped)
    return "; ".join(interesting[:max_lines]) or "Unparsed failure"


class MockRouter(LLMRouter):
    def __init__(self, scripted_candidates: Optional[list[PatchCandidate]] = None) -> None:
        self.scripted_candidates = scripted_candidates or []

    def triage(self, event: FailureEvent, failure_log: str) -> Diagnosis:
        tests = sorted(set(_UNITTEST_RE.findall(failure_log) + _PYTEST_RE.findall(failure_log)))
        files = sorted(
            {os.path.basename(p) for p in _TRACEBACK_FILE_RE.findall(failure_log)}
        )
        return Diagnosis(
            summary=summarize(failure_log),
            failing_tests=tests,
            suspected_files=files,
            category=categorize(failure_log),
        )

    def generate_candidates(
        self,
        diagnosis: Diagnosis,
        read_file: Callable[[str], str],
        max_candidates: int = 3,
    ) -> list[PatchCandidate]:
        return self.scripted_candidates[:max_candidates]
