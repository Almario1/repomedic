import json
import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeResult:
    def __init__(self, exit_code=0, stdout="", stderr="", uuid="u1"):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.uuid = uuid

    def wait(self):
        return self


class FakeImage:
    def __init__(self, sdk, tag="ubuntu:latest"):
        self.sdk = sdk
        self.tag = tag
        self.files = {}

    def run(self, shell, disposable=True):
        self.sdk.run_calls.append(shell)
        if "sh ci.sh" in shell:
            failing = self.sdk.fail_ci
            text = self.files.get("/work/calc.py", "")
            if "return a / b" in text:
                failing = False
            return FakeResult(exit_code=1 if failing else 0, stdout="ran ci")
        return FakeResult(exit_code=0, stdout="ok")

    def apply_files(self, files):
        for dest, uploaded in files.items():
            self.files[dest] = uploaded.data.decode()
        return self


class FakeFiles:
    def __init__(self, sdk):
        self.sdk = sdk

    def upload_bytes_file(self, data):
        self.sdk.uploads.append(data)
        return types.SimpleNamespace(data=data)


class FakeImagesManager:
    def __init__(self, sdk):
        self.sdk = sdk

    def __call__(self, *a, **kw):
        return []

    def use(self, tag, **kw):
        return FakeImage(self.sdk, tag)


class FakeSDK:
    def __init__(self):
        self.run_calls = []
        self.uploads = []
        self.fail_ci = True
        self.files = FakeFiles(self)
        self.images = FakeImagesManager(self)


def install_fake_contree(sdk):
    client_mod = types.ModuleType("contree_client")
    httpx_mod = types.ModuleType("contree_client.httpx")
    httpx_mod.ContreeSyncClient = lambda *a, **kw: types.SimpleNamespace()
    client_mod.httpx = httpx_mod
    sdk_mod = types.ModuleType("contree_sdk")
    sdk_mod.ContreeSync = lambda client: sdk
    saved = sys.modules.copy()
    sys.modules["contree_client"] = client_mod
    sys.modules["contree_client.httpx"] = httpx_mod
    sys.modules["contree_sdk"] = sdk_mod
    return saved


class TokenFactoryProviderTests(unittest.TestCase):
    def setUp(self):
        self.sdk = FakeSDK()
        self.saved = install_fake_contree(self.sdk)
        self.out = tempfile.mkdtemp()

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self.saved)
        shutil.rmtree(self.out, ignore_errors=True)

    def make_provider(self):
        from repomedic.sandbox.token_factory import TokenFactorySandboxProvider

        return TokenFactorySandboxProvider(api_key="k", project="p")

    def test_requires_credentials(self):
        from repomedic.sandbox.token_factory import TokenFactorySandboxProvider

        with self.assertRaises(RuntimeError):
            TokenFactorySandboxProvider(api_key="", project="")

    def test_session_run_and_patch(self):
        provider = self.make_provider()
        src = os.path.join(os.path.dirname(__file__), "..", "demo", "scenarios", "division_bug", "repo")
        with provider.open_session(src) as session:
            bad = session.run("sh ci.sh")
            self.assertEqual(bad.exit_code, 1)
            with open(os.path.join(os.path.dirname(__file__), "..", "demo", "scenarios", "division_bug", "candidates.json")) as fh:
                cands = json.load(fh)
            good = [c for c in cands if c["candidate_id"] == "cand-true-division"][0]
            session.apply_patch(good["diff"])
            ok = session.run("sh ci.sh")
            self.assertEqual(ok.exit_code, 0)
        # the source tree was never modified
        with open(os.path.join(src, "calc.py")) as fh:
            self.assertIn("BUG", fh.read())

    def test_full_orchestrator_loop_against_fake_sandboxes(self):
        from repomedic.deliver.pr import LocalFilePRDeliverer
        from repomedic.llm.mock import MockRouter
        from repomedic.models import FailureEvent, PatchCandidate
        from repomedic.orchestrator import Orchestrator

        scen_dir = os.path.join(os.path.dirname(__file__), "..", "demo", "scenarios", "division_bug")
        src_dir = os.path.join(scen_dir, "repo")
        with open(os.path.join(scen_dir, "event.json")) as fh:
            meta = json.load(fh)
        with open(os.path.join(scen_dir, "candidates.json")) as fh:
            cands = [PatchCandidate(**c) for c in json.load(fh)]
        orch = Orchestrator(
            sandbox_provider=self.make_provider(),
            router=MockRouter(scripted_candidates=cands),
            deliverer=LocalFilePRDeliverer(self.out),
        )
        result = orch.repair(FailureEvent(**meta["event"]), src_dir)
        self.assertEqual(result.status, "REPAIRED")
        self.assertEqual(result.winning_candidate.candidate_id, "cand-true-division")


if __name__ == "__main__":
    unittest.main()
