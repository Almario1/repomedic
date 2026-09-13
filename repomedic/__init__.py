"""RepoMedic - autonomous CI-repair agent.

Watches a repository for CI failures, reproduces them in an isolated
sandbox, diagnoses the root cause, tournaments candidate patches, and
opens a pull request containing a verified fix.
"""

__version__ = "0.1.0"
