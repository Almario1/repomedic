"""The repair loop: reproduce -> diagnose -> tournament -> deliver."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from .deliver.pr import PRDeliverer, result_to_json
from .llm.base import LLMRouter
from .models import FailureEvent, PatchCandidate, RepairResult, Verification
from .sandbox.base import PatchApplyError, SandboxProvider

log = logging.getLogger("repomedic")


def _rank(candidate: PatchCandidate, verification: Verification) -> tuple[int, int]:
    changed = sum(
        1
        for line in candidate.diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )
    return (0 if verification.passed else 1, changed)


class Orchestrator:
    def __init__(
        self,
        sandbox_provider: SandboxProvider,
        router: LLMRouter,
        deliverer: PRDeliverer,
        max_candidates: int = 3,
        command_timeout: int = 120,
        stop_on_first_pass: bool = False,
        parallel: bool = True,
        max_workers: int = 4,
        reporter: Optional[Callable[..., None]] = None,
    ) -> None:
        self.sandbox_provider = sandbox_provider
        self.router = router
        self.deliverer = deliverer
        self.max_candidates = max_candidates
        self.command_timeout = command_timeout
        self.stop_on_first_pass = stop_on_first_pass
        self.parallel = parallel
        self.max_workers = max_workers
        self.reporter = reporter

    def repair(self, event: FailureEvent, source_dir: str) -> RepairResult:
        """Attempt one end-to-end repair against a local checkout at source_dir."""
        # 1. Reproduce the failure in a clean sandbox.
        with self.sandbox_provider.open_session(source_dir) as session:
            repro = session.run(event.failing_command, timeout=self.command_timeout)
        self._emit("reproduced", ok=repro.ok, command=event.failing_command)
        if repro.ok:
            log.info("failure did not reproduce")
            return RepairResult(status="NO_FAILURE_REPRODUCED")

        # 2. Diagnose.
        diagnosis = self.router.triage(event, repro.combined_log)
        self._emit("diagnosed", category=diagnosis.category, summary=diagnosis.summary[:300])
        log.info("diagnosis: %s", diagnosis.summary[:200])

        # 3. Generate candidates, using a probe sandbox for file reads.
        with self.sandbox_provider.open_session(source_dir) as probe:
            candidates = self.router.generate_candidates(
                diagnosis, probe.read_file, max_candidates=self.max_candidates
            )

        # 4. Tournament: every candidate gets a FRESH sandbox. Candidates
        # are verified in parallel unless early-stop semantics apply.
        verifications = self._tournament(candidates, source_dir, event.failing_command)

        passing = [
            (cand, ver)
            for cand, ver in zip(candidates, verifications)
            if ver.passed
        ]
        if not passing:
            return RepairResult(
                status="ALL_CANDIDATES_FAILED",
                diagnosis=diagnosis,
                verifications=verifications,
            )

        winner, _ = sorted(passing, key=lambda pair: _rank(pair[0], pair[1]))[0]
        self._emit("delivered", winner=winner.candidate_id)
        result = RepairResult(
            status="REPAIRED",
            diagnosis=diagnosis,
            verifications=verifications,
            winning_candidate=winner,
        )

        # 5. Deliver.
        result.pr_payload = self.deliverer.deliver(result, event)
        log.info("repaired: %s", result_to_json(result)[:400])
        return result

    def _emit(self, stage: str, **payload: object) -> None:
        if self.reporter is not None:
            try:
                self.reporter(stage, **payload)
            except Exception:  # reporting must never break a repair
                log.warning("reporter failed for stage %s", stage, exc_info=True)

    def _tournament(
        self, candidates: list[PatchCandidate], source_dir: str, command: str
    ) -> list[Verification]:
        if self.stop_on_first_pass or not self.parallel or len(candidates) <= 1:
            verifications: list[Verification] = []
            for cand in candidates:
                ver = self._verify(source_dir, cand, command)
                verifications.append(ver)
                self._emit("candidate_verified", candidate_id=cand.candidate_id, passed=ver.passed)
                if self.stop_on_first_pass and ver.passed:
                    log.info("stopping tournament early: %s passed", cand.candidate_id)
                    break
            return verifications

        results: dict[int, Verification] = {}
        workers = min(len(candidates), self.max_workers)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._verify, source_dir, cand, command): idx
                for idx, cand in enumerate(candidates)
            }
            for future in as_completed(futures):
                idx = futures[future]
                ver = future.result()
                results[idx] = ver
                self._emit(
                    "candidate_verified",
                    candidate_id=candidates[idx].candidate_id,
                    passed=ver.passed,
                )
        return [results[i] for i in range(len(candidates))]

    def _verify(self, source_dir: str, cand: PatchCandidate, command: str) -> Verification:
        try:
            with self.sandbox_provider.open_session(source_dir) as session:
                try:
                    session.apply_patch(cand.diff)
                except PatchApplyError as exc:
                    return Verification(candidate_id=cand.candidate_id, applied=False, error=str(exc))
                run = session.run(command, timeout=self.command_timeout)
                return Verification(candidate_id=cand.candidate_id, applied=True, run=run)
        except Exception as exc:  # sandbox-level failure must not kill the loop
            log.warning("verification error for %s: %s", cand.candidate_id, exc)
            return Verification(candidate_id=cand.candidate_id, applied=False, error=str(exc))
