"""Local sandbox provider.

Copies the source tree into a temporary directory and runs commands with
subprocess. Used for development, tests and the offline demo. Production
runs should use TokenFactorySandboxProvider once its API is verified.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from ..models import RunResult
from .base import PatchApplyError, SandboxProvider, SandboxSession

_IGNORE = {".git", "__pycache__", ".pytest_cache", "node_modules"}


def _copy_tree(source_dir: str, dest_dir: str) -> None:
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in _IGNORE]
        rel = os.path.relpath(root, source_dir)
        target_root = dest_dir if rel == "." else os.path.join(dest_dir, rel)
        os.makedirs(target_root, exist_ok=True)
        for name in files:
            shutil.copy2(os.path.join(root, name), os.path.join(target_root, name))


def apply_unified_diff(original: str, diff_text: str) -> str:
    """Apply a small unified diff to file text.

    Handles single-file diffs with one or more hunks. Each hunk's "from"
    image (context + removed lines) must appear exactly once in the file;
    it is replaced by the hunk's "to" image (context + added lines).
    Deliberately strict: ambiguous patches are rejected instead of being
    misapplied.
    """
    lines = original.splitlines(keepends=False)
    hunks: list[tuple[list[str], list[str]]] = []
    from_img: list[str] = []
    to_img: list[str] = []
    in_hunk = False

    def flush() -> None:
        nonlocal from_img, to_img, in_hunk
        if in_hunk:
            hunks.append((from_img, to_img))
        from_img, to_img, in_hunk = [], [], False

    for raw in diff_text.splitlines():
        if raw.startswith("--- ") or raw.startswith("+++ "):
            continue
        if raw.startswith("@@"):
            flush()
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith(" "):
            from_img.append(raw[1:])
            to_img.append(raw[1:])
        elif raw.startswith("-"):
            from_img.append(raw[1:])
        elif raw.startswith("+"):
            to_img.append(raw[1:])
        elif raw.startswith("\\"):
            continue
        else:
            raise PatchApplyError(f"Malformed diff line: {raw!r}")
    flush()

    if not hunks:
        raise PatchApplyError("No hunks found in diff")

    for frm, to in hunks:
        joined = "\n".join(lines)
        needle = "\n".join(frm)
        if joined.count(needle) == 0:
            raise PatchApplyError(f"Hunk context not found: {frm!r}")
        if joined.count(needle) > 1:
            raise PatchApplyError(f"Hunk context ambiguous: {frm!r}")
        joined = joined.replace(needle, "\n".join(to), 1)
        lines = joined.split("\n")
    return "\n".join(lines) + ("\n" if original.endswith("\n") else "")


class LocalSandboxSession(SandboxSession):
    def __init__(self, workdir: str) -> None:
        self.workdir = workdir

    def run(self, command: str, timeout: int = 120) -> RunResult:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=self.workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return RunResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def apply_patch(self, diff_text: str) -> None:
        target = self._target_file(diff_text)
        path = os.path.join(self.workdir, target)
        if not os.path.isfile(path):
            raise PatchApplyError(f"Patch target not found: {target}")
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
        patched = apply_unified_diff(original, diff_text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(patched)

    def read_file(self, relpath: str) -> str:
        with open(os.path.join(self.workdir, relpath), encoding="utf-8") as fh:
            return fh.read()

    def cleanup(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)

    @staticmethod
    def _target_file(diff_text: str) -> str:
        for raw in diff_text.splitlines():
            if raw.startswith("+++ b/"):
                return raw[len("+++ b/"):]
            if raw.startswith("+++ "):
                return raw[len("+++ "):]
        raise PatchApplyError("Diff has no +++ target header")


class LocalSandboxProvider(SandboxProvider):
    def open_session(self, source_dir: str) -> LocalSandboxSession:
        workdir = tempfile.mkdtemp(prefix="repomedic-")
        _copy_tree(source_dir, workdir)
        return LocalSandboxSession(workdir)
