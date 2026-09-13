"""Token Factory Sandboxes (ConTree) provider - production path.

API verified against docs.tokenfactory.nebius.com on 2026-09-13:
- Base URL: https://api.tokenfactory.nebius.com/sandboxes (CONTREE_URL)
- Auth: bearer token (NEBIUS_API_KEY) + project ID
- Packages: `pip install contree-sdk` (pulls in contree-client)
- Usage model (from the SDK docs):
    sdk = ContreeSync(ContreeSyncClient(API_KEY, base_url=...))
    image = sdk.images.use("ubuntu:latest")
    result = image.run(shell="...", disposable=False).wait()
    # result: .uuid .stdout .stderr .exit_code; .run(...) branches
    # image.apply_files(files={dest: uploaded}) bakes files into an image
- Sandboxes are Beta; 7,000+ preloaded SWE-bench environments exist,
  and branching from checkpoints is the intended tournament pattern.

RepoMedic mapping:
- open_session: bake the repo tree into a fresh image state (apply_files)
- run: image.run(shell="cd /work && <cmd>")
- apply_patch: patched content computed LOCALLY with the strict applier
  (no reliance on in-sandbox patch tooling), then baked via apply_files
- cleanup: states are disposable; nothing to tear down

Remaining day-one unknowns to validate against the live API (small):
exact UploadedFile handling in apply_files, per-run timeout support,
and which base image tag carries python3.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from ..models import RunResult
from .base import PatchApplyError, SandboxProvider, SandboxSession
from .local import _copy_tree, apply_unified_diff, split_diff_sections

SANDBOXES_BASE_URL = "https://api.tokenfactory.nebius.com/sandboxes"
WORKDIR = "/work"
DEFAULT_IMAGE_TAG = "ubuntu:latest"


def _load_sdk():
    try:
        from contree_client.httpx import ContreeSyncClient  # type: ignore
        from contree_sdk import ContreeSync  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "TokenFactorySandboxProvider requires `pip install contree-sdk` "
            "and a NEBIUS_API_KEY + project ID from the Nebius console"
        ) from exc
    return ContreeSyncClient, ContreeSync


class TokenFactorySandboxSession(SandboxSession):
    def __init__(self, sdk, image, local_copy: str) -> None:
        self._sdk = sdk
        self._image = image
        self._local_copy = local_copy  # patched state is computed here first

    def run(self, command: str, timeout: int = 120) -> RunResult:
        # TODO(day one): pass a per-run timeout if the live API supports it.
        result = self._image.run(
            shell=f"cd {WORKDIR} && {command}", disposable=False
        ).wait()
        return RunResult(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout if isinstance(result.stdout, str) else "",
            stderr=result.stderr if isinstance(result.stderr, str) else "",
        )

    def apply_patch(self, diff_text: str) -> None:
        for target, section in split_diff_sections(diff_text):
            local_path = os.path.join(self._local_copy, target)
            if not os.path.isfile(local_path):
                raise PatchApplyError(f"Patch target not found: {target}")
            with open(local_path, encoding="utf-8") as fh:
                original = fh.read()
            patched = apply_unified_diff(original, section)
            with open(local_path, "w", encoding="utf-8") as fh:
                fh.write(patched)  # later patches build on earlier ones
            uploaded = self._sdk.files.upload_bytes_file(patched.encode())
            self._image = self._image.apply_files(
                files={f"{WORKDIR}/{target}": uploaded}
            )

    def read_file(self, relpath: str) -> str:
        with open(os.path.join(self._local_copy, relpath), encoding="utf-8") as fh:
            return fh.read()

    def cleanup(self) -> None:
        shutil.rmtree(self._local_copy, ignore_errors=True)


class TokenFactorySandboxProvider(SandboxProvider):
    def __init__(
        self,
        api_key: str = "",
        project: str = "",
        base_url: str = SANDBOXES_BASE_URL,
        image_tag: str = DEFAULT_IMAGE_TAG,
    ) -> None:
        api_key = api_key or os.environ.get("NEBIUS_API_KEY", "")
        project = project or os.environ.get("NEBIUS_PROJECT_ID", "")
        if not api_key or not project:
            raise RuntimeError(
                "NEBIUS_API_KEY and NEBIUS_PROJECT_ID are required "
                "(from the Nebius console)"
            )
        client_cls, sync_cls = _load_sdk()
        self._sdk = sync_cls(client_cls(api_key, base_url=base_url, project=project))
        self._image_tag = image_tag

    def verify_connection(self) -> list:
        """Smoke test: list available images."""
        return list(self._sdk.images())

    def open_session(self, source_dir: str) -> TokenFactorySandboxSession:
        local_copy = tempfile.mkdtemp(prefix="repomedic-tf-")
        _copy_tree(source_dir, local_copy)
        image = self._sdk.images.use(self._image_tag)
        files = {}
        for root, _dirs, names in os.walk(local_copy):
            for name in names:
                local_path = os.path.join(root, name)
                rel = os.path.relpath(local_path, local_copy)
                with open(local_path, "rb") as fh:
                    files[f"{WORKDIR}/{rel}"] = self._sdk.files.upload_bytes_file(
                        fh.read()
                    )
        if files:
            image = image.apply_files(files=files)
        return TokenFactorySandboxSession(self._sdk, image, local_copy)
