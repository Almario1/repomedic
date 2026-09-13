"""Parse GitHub webhook payloads into FailureEvents.

Pure functions over the decoded JSON body so they are trivially testable.
Signature verification and the HTTP server belong to the deployment layer
(Nebius Serverless Endpoints), not here.
"""

from __future__ import annotations

from typing import Any, Optional

from ..models import FailureEvent

DEFAULT_FAILING_COMMAND = "sh ci.sh"


def _event_from(repo: dict[str, Any], branch: str, sha: str, raw: dict[str, Any]) -> FailureEvent:
    return FailureEvent(
        repo_url=repo.get("clone_url", ""),
        branch=branch,
        commit_sha=sha,
        failing_command=DEFAULT_FAILING_COMMAND,
        raw=raw,
    )


def parse_check_run(payload: dict[str, Any]) -> Optional[FailureEvent]:
    """Handle a check_run webhook. Returns None unless it is a completed failure."""
    if payload.get("action") != "completed":
        return None
    check_run = payload.get("check_run", {})
    if check_run.get("conclusion") != "failure":
        return None
    repo = payload.get("repository", {})
    suite = check_run.get("check_suite", {})
    return _event_from(
        repo=repo,
        branch=suite.get("head_branch", ""),
        sha=check_run.get("head_sha", ""),
        raw=payload,
    )


def parse_workflow_run(payload: dict[str, Any]) -> Optional[FailureEvent]:
    """Handle a workflow_run webhook. Returns None unless it is a completed failure."""
    if payload.get("action") != "completed":
        return None
    run = payload.get("workflow_run", {})
    if run.get("conclusion") != "failure":
        return None
    repo = payload.get("repository", {})
    return _event_from(
        repo=repo,
        branch=run.get("head_branch", ""),
        sha=run.get("head_sha", ""),
        raw=payload,
    )
