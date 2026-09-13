"""Core data structures shared across RepoMedic stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FailureEvent:
    """A CI failure worth investigating."""

    repo_url: str
    branch: str
    commit_sha: str
    failing_command: str
    log_hint: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """Outcome of running one command inside a sandbox."""

    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    @property
    def combined_log(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()


@dataclass
class Diagnosis:
    """Structured read of a failure produced by the triage model."""

    summary: str
    failing_tests: list[str] = field(default_factory=list)
    suspected_files: list[str] = field(default_factory=list)
    category: str = "unknown"  # import | assertion | lint | error | unknown


@dataclass
class PatchCandidate:
    """One proposed fix, expressed as a unified diff."""

    candidate_id: str
    diff: str
    rationale: str = ""


@dataclass
class Verification:
    """How one candidate fared against the failing command."""

    candidate_id: str
    applied: bool
    run: Optional[RunResult] = None
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.applied and self.run is not None and self.run.ok


@dataclass
class RepairResult:
    """End-to-end outcome of one repair attempt."""

    status: str  # REPAIRED | NO_FAILURE_REPRODUCED | ALL_CANDIDATES_FAILED | ERROR
    diagnosis: Optional[Diagnosis] = None
    verifications: list[Verification] = field(default_factory=list)
    winning_candidate: Optional[PatchCandidate] = None
    pr_payload: Optional[dict[str, Any]] = None
    error: str = ""
