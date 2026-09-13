import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.sandbox.base import PatchApplyError
from repomedic.sandbox.local import apply_unified_diff

CALC = '''"""doc"""


def divide(a, b):
    return a * b  # BUG: should be a / b
'''

CORRECT = """--- a/calc.py
+++ b/calc.py
@@ -3,3 +3,3 @@
 
 def divide(a, b):
-    return a * b  # BUG: should be a / b
+    return a / b
"""

WRONG_OP = """--- a/calc.py
+++ b/calc.py
@@ -3,3 +3,3 @@
 
 def divide(a, b):
-    return a * b  # BUG: should be a / b
+    return a - b
"""


class ApplyUnifiedDiffTests(unittest.TestCase):
    def test_applies_correct_patch(self):
        out = apply_unified_diff(CALC, CORRECT)
        self.assertIn("return a / b", out)
        self.assertNotIn("BUG", out)

    def test_applies_alternative_patch(self):
        out = apply_unified_diff(CALC, WRONG_OP)
        self.assertIn("return a - b", out)

    def test_missing_context_rejected(self):
        bad = CORRECT.replace("def divide", "def nonexistent")
        with self.assertRaises(PatchApplyError):
            apply_unified_diff(CALC, bad)

    def test_empty_diff_rejected(self):
        with self.assertRaises(PatchApplyError):
            apply_unified_diff(CALC, "--- a/x\n+++ b/x\n")


if __name__ == "__main__":
    unittest.main()
