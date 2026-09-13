"""Delivery seam: turn a verified RepairResult into a pull request.

LocalFilePRDeliverer writes the PR body and patch to disk (demo/tests).
GitHubPRDeliverer is a stub pending Mario's GitHub credentials.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from ..models import FailureEvent, RepairResult


class PRDeliverer(ABC):
    @abstractmethod
    def deliver(self, result: RepairResult, event: FailureEvent) -> dict[str, Any]:
        """Publish the verified fix. Returns a record of what was published."""


class LocalFilePRDeliverer(PRDeliverer):
    def __init__(self, out_dir: str) -> None:
        self.out_dir = out_dir

    def deliver(self, result: RepairResult, event: FailureEvent) -> dict[str, Any]:
        os.makedirs(self.out_dir, exist_ok=True)
        if result.winning_candidate is None:
            raise ValueError("No winning candidate to deliver")
        body = self._render_body(result, event)
        patch_path = os.path.join(self.out_dir, "winning_patch.diff")
        body_path = os.path.join(self.out_dir, "pr.md")
        with open(patch_path, "w", encoding="utf-8") as fh:
            fh.write(result.winning_candidate.diff + "\n")
        with open(body_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return {"patch_path": patch_path, "body_path": body_path, "mode": "local-file"}

    @staticmethod
    def _render_body(result: RepairResult, event: FailureEvent) -> str:
        lines = [
            "# RepoMedic automated repair",
            "",
            f"- Commit: `{event.commit_sha}` on `{event.branch}`",
            f"- Failing command: `{event.failing_command}`",
            "",
            "## Diagnosis",
            "",
            (result.diagnosis.summary if result.diagnosis else "n/a"),
            "",
            "## Verification",
            "",
        ]
        for v in result.verifications:
            mark = "PASS" if v.passed else "FAIL"
            lines.append(f"- [{mark}] candidate `{v.candidate_id}`")
        lines += [
            "",
            "The attached patch is the candidate that made the failing command pass",
            "inside an isolated sandbox.",
        ]
        return "\n".join(lines)


class GitHubPRDeliverer(PRDeliverer):
    """Opens a real PR via the GitHub API. NOT FUNCTIONAL YET.

    Needs Mario's GitHub account (a GitHub App installation token or a
    fine-grained PAT scoped to the target repo). Implementation: create a
    branch, apply the patch, commit, push, open the PR with the same body
    LocalFilePRDeliverer renders.
    """

    def __init__(self, token: str = "") -> None:
        self.token = token

    def deliver(self, result: RepairResult, event: FailureEvent) -> dict[str, Any]:
        raise NotImplementedError(
            "GitHub delivery requires Mario's GitHub credentials - see class docstring"
        )


def result_to_json(result: RepairResult) -> str:
    def _default(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: v for k, v in vars(obj).items()}
        raise TypeError(type(obj).__name__)

    return json.dumps(result, default=_default, indent=2)
