import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repomedic.ingest.github_webhook import parse_check_run, parse_workflow_run


def check_payload(conclusion, action="completed"):
    return {
        "action": action,
        "check_run": {
            "conclusion": conclusion,
            "head_sha": "abc123",
            "check_suite": {"head_branch": "main"},
        },
        "repository": {"clone_url": "https://github.com/x/y.git"},
    }


class WebhookTests(unittest.TestCase):
    def test_check_run_failure_parsed(self):
        ev = parse_check_run(check_payload("failure"))
        self.assertIsNotNone(ev)
        self.assertEqual(ev.commit_sha, "abc123")
        self.assertEqual(ev.branch, "main")
        self.assertEqual(ev.repo_url, "https://github.com/x/y.git")

    def test_check_run_success_ignored(self):
        self.assertIsNone(parse_check_run(check_payload("success")))

    def test_non_completed_action_ignored(self):
        self.assertIsNone(parse_check_run(check_payload("failure", action="created")))

    def test_workflow_run_failure_parsed(self):
        payload = {
            "action": "completed",
            "workflow_run": {
                "conclusion": "failure",
                "head_branch": "dev",
                "head_sha": "def456",
            },
            "repository": {"clone_url": "https://github.com/x/z.git"},
        }
        ev = parse_workflow_run(payload)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.branch, "dev")


if __name__ == "__main__":
    unittest.main()
