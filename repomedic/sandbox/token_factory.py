"""Token Factory sandbox provider - SEAM, NOT YET FUNCTIONAL.

The Coding and Agentic Engineering track calls for agents that "write,
run, and test code in Token Factory Sandboxes". The exact Token Factory
Sandboxes API (endpoints, auth scheme, session lifecycle) has NOT been
verified against Nebius documentation yet; verifying it requires Mario's
Nebius account. This module exists so that:

  1. the orchestrator's provider seam is exercised end to end today, and
  2. the day-one integration work is confined to this file.

Day-one checklist once credentials exist:
  [ ] confirm the Sandboxes base URL and auth header format
  [ ] confirm how a session/sandbox is created and seeded with a repo
  [ ] confirm command execution request/response shape (stdout/stderr/code)
  [ ] confirm filesystem write support for patch application (or apply
      patches before upload and re-seed per candidate)
  [ ] confirm teardown + cost/quota behaviour for parallel candidate runs
Fallback if Sandboxes disappoints: run the same loop on Nebius AI Cloud
(Serverless Jobs / DevPods), which still satisfies the hackathon rules
("runs on ... Nebius AI Cloud compute").
"""

from __future__ import annotations

from ..models import RunResult
from .base import SandboxProvider, SandboxSession


class SandboxAPIUnverifiedError(NotImplementedError):
    pass


class TokenFactorySandboxSession(SandboxSession):
    def __init__(self, endpoint: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def run(self, command: str, timeout: int = 120) -> RunResult:
        raise SandboxAPIUnverifiedError(
            "Token Factory Sandboxes API not verified yet - see module docstring"
        )

    def apply_patch(self, diff_text: str) -> None:
        raise SandboxAPIUnverifiedError(
            "Token Factory Sandboxes API not verified yet - see module docstring"
        )

    def read_file(self, relpath: str) -> str:
        raise SandboxAPIUnverifiedError(
            "Token Factory Sandboxes API not verified yet - see module docstring"
        )

    def cleanup(self) -> None:
        return None


class TokenFactorySandboxProvider(SandboxProvider):
    def __init__(self, endpoint: str, api_key: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def open_session(self, source_dir: str) -> TokenFactorySandboxSession:
        return TokenFactorySandboxSession(self.endpoint, self.api_key)
