import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.sandbox.local import LocalSandboxProvider


class LocalSandboxTests(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.mkdtemp()
        with open(os.path.join(self.src, "app.txt"), "w") as fh:
            fh.write("hello\n")
        self.provider = LocalSandboxProvider()

    def test_run_captures_output_and_code(self):
        with self.provider.open_session(self.src) as s:
            ok = s.run("echo hi")
            self.assertTrue(ok.ok)
            self.assertIn("hi", ok.stdout)
            bad = s.run("exit 3")
            self.assertEqual(bad.exit_code, 3)

    def test_patch_then_read(self):
        diff = "--- a/app.txt\n+++ b/app.txt\n@@ -1,1 +1,1 @@\n-hello\n+goodbye"
        with self.provider.open_session(self.src) as s:
            s.apply_patch(diff)
            self.assertEqual(s.read_file("app.txt"), "goodbye\n")
        with open(os.path.join(self.src, "app.txt")) as fh:
            self.assertEqual(fh.read(), "hello\n")  # source untouched

    def test_sessions_are_isolated(self):
        s1 = self.provider.open_session(self.src)
        s2 = self.provider.open_session(self.src)
        try:
            s1.apply_patch("--- a/app.txt\n+++ b/app.txt\n@@ -1,1 +1,1 @@\n-hello\n+changed")
            self.assertEqual(s2.read_file("app.txt"), "hello\n")
        finally:
            s1.cleanup()
            s2.cleanup()


if __name__ == "__main__":
    unittest.main()
