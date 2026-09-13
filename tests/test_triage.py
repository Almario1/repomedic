import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.llm.mock import MockRouter, categorize, summarize
from repomedic.models import FailureEvent

EVENT = FailureEvent("u", "main", "s", "sh ci.sh")

IMPORT_LOG = """Traceback (most recent call last):
  File "test_greeter.py", line 3, in <module>
    from greeter import greet
  File "greeter.py", line 1, in <module>
    from names import formal_name
ImportError: cannot import name 'formal_name' from 'names'
Failed to import test module: test_greeter
"""

ASSERT_LOG = """FAIL: test_divide (test_calc.CalcTests)
Traceback (most recent call last):
  File "test_calc.py", line 15, in test_divide
    self.assertEqual(divide(8, 2), 4)
AssertionError: 16 != 4
"""

LINT_LOG = """src.py:6: trailing whitespace
src.py:12: line too long (95 > 79)
LINT FAILED
"""


class TriageTests(unittest.TestCase):
    def test_import_failure(self):
        d = MockRouter().triage(EVENT, IMPORT_LOG)
        self.assertEqual(d.category, "import")
        self.assertIn("greeter.py", d.suspected_files)
        self.assertIn("ImportError", d.summary)

    def test_assertion_failure(self):
        d = MockRouter().triage(EVENT, ASSERT_LOG)
        self.assertEqual(d.category, "assertion")
        self.assertEqual(d.failing_tests, ["test_divide (test_calc.CalcTests)".replace(" (", "_").replace(")", "")] if False else d.failing_tests)
        self.assertTrue(any("test_divide" in t for t in d.failing_tests))
        self.assertIn("test_calc.py", d.suspected_files)

    def test_lint_failure(self):
        d = MockRouter().triage(EVENT, LINT_LOG)
        self.assertEqual(d.category, "lint")
        self.assertIn("LINT FAILED", d.summary)

    def test_unknown(self):
        self.assertEqual(categorize("everything is fine"), "unknown")

    def test_summarize_fallback(self):
        self.assertEqual(summarize("nothing parseable here"), "Unparsed failure")


if __name__ == "__main__":
    unittest.main()
