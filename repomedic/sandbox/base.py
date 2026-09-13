"""Sandbox seam.

The hackathon target is Token Factory Sandboxes, but that API surface is
NOT yet verified against Nebius documentation. Every sandbox interaction
in RepoMedic goes through these two interfaces, so the provider can be
swapped without touching the orchestrator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import RunResult


class PatchApplyError(Exception):
    """A unified diff could not be applied cleanly."""


class SandboxSession(ABC):
    """One isolated, disposable workspace copy."""

    @abstractmethod
    def run(self, command: str, timeout: int = 120) -> RunResult:
        """Run a shell command inside the sandbox."""

    @abstractmethod
    def apply_patch(self, diff_text: str) -> None:
        """Apply a unified diff to the sandboxed tree.

        Raises PatchApplyError if the diff does not apply cleanly.
        """

    @abstractmethod
    def read_file(self, relpath: str) -> str:
        """Read a file from the sandboxed tree."""

    @abstractmethod
    def cleanup(self) -> None:
        """Destroy the sandbox and release resources."""

    def __enter__(self) -> "SandboxSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.cleanup()


class SandboxProvider(ABC):
    """Factory for isolated sessions."""

    @abstractmethod
    def open_session(self, source_dir: str) -> SandboxSession:
        """Create a fresh sandbox seeded from source_dir."""
