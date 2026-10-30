# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""The evaluation runner (TRD §6; EXECUTION_PLAN §3; DATA_MODELS §7, §9).

The runner executes cases sequentially, in dataset order. For each case it calls the target
(best-effort timeout), applies every evaluator, and aggregates the case status. Results are
returned in memory. Persistence arrives in Milestone 7.

Behaviour that must hold:

- A case excluded by selection is listed as SKIPPED with reason ``USER_FILTER`` (decision D-6).
- A target failure never stops the run; the case is recorded as ERROR.
- ``KeyboardInterrupt`` is given a grace period to finish the current case. If the case does not
  finish, it is not recorded. The run is then ``ABORTED``.
- An unexpected exception in the engine itself stops the run as ``FAILED`` with ``ENGINE_ERROR``.
  Only the exception type is recorded.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Final, cast

from evalforge import timeouts
from evalforge.canon import JSONValue, canonical_sha256
from evalforge.datasets import Dataset
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import Evaluator, apply_evaluator, make_result
from evalforge.models import (
    ABSENT,
    Case,
    CaseResult,
    ErrorObject,
    TargetResult,
    _Absent,
    aggregate_case_status,
)
from evalforge.status import RunStatus, Status
from evalforge.targets import TargetInvocation, TargetProtocol

MAX_TIMEOUT_SECONDS: Final = 3600.0
COUNTED_STATUSES: Final = (
    Status.PASS,
    Status.FAIL,
    Status.ERROR,
    Status.SKIPPED,
    Status.INCONCLUSIVE,
)


@dataclass(frozen=True, slots=True)
class RunOptions:
    """Options for one run. Validation happens on construction."""

    timeout_seconds: float = 30.0
    grace_seconds: float = 5.0
    case_ids: frozenset[str] | None = None
    tags: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"timeout_seconds must be greater than 0 and at most {MAX_TIMEOUT_SECONDS:g}"
            )
        if self.grace_seconds < 0.0:
            raise ValueError("grace_seconds must not be negative")
        if self.case_ids is not None and self.tags is not None:
            raise ValueError("select either case IDs or tags, not both")


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """The in-memory result of one run."""

    run_id: str
    status: RunStatus
    cases: tuple[CaseResult, ...]
    not_executed: int
    threads_possibly_running: int
    error: ErrorObject | None = None
    notes: tuple[str, ...] = field(default=())

    def counts(self) -> dict[str, int]:
        """Counts per status, plus ``executed`` (PASS + FAIL + ERROR + INCONCLUSIVE)."""
        tally = Counter(item.status for item in self.cases)
        result = {status.value: tally.get(status, 0) for status in COUNTED_STATUSES}
        result["executed"] = sum(
            tally.get(status, 0) for status in COUNTED_STATUSES if status is not Status.SKIPPED
        )
        return result


def _check_selection(dataset: Dataset, options: RunOptions) -> None:
    if options.case_ids is None:
        return
    known = {case.id for case in dataset.cases}
    unknown = sorted(options.case_ids - known)
    if unknown:
        raise EvalForgeError("USAGE_ERROR", f"unknown case IDs: {', '.join(unknown)}")


def _selected(case: Case, options: RunOptions) -> bool:
    if options.case_ids is not None:
        return case.id in options.case_ids
    if options.tags is not None:
        return bool(options.tags.intersection(case.tags))
    return True


def _not_run(run_id: str, case: Case) -> CaseResult:
    target = TargetResult(status="NOT_RUN", error_code=None, error=None, duration_ms=0.0)
    return CaseResult(
        run_id=run_id,
        case_id=case.id,
        case_sha256=case.case_sha256(),
        status=Status.SKIPPED,
        status_reason="USER_FILTER",
        target=target,
        evaluators=(),
        input=case.input,
        expected=case.expected,
    )


def _timed_out(duration_ms: float) -> TargetInvocation:
    result = TargetResult(
        status="ERROR",
        error_code="TARGET_TIMEOUT",
        error=ErrorObject(
            type_name="TimeoutError", message="the target did not finish within its timeout"
        ),
        duration_ms=duration_ms,
    )
    return TargetInvocation(result=result, output=ABSENT)


def _build_result(
    run_id: str,
    case: Case,
    invocation: TargetInvocation,
    evaluators: Sequence[Evaluator],
) -> CaseResult:
    target = invocation.result
    output: JSONValue | _Absent = invocation.output
    if target.status == "OK":
        value = cast(JSONValue, invocation.output)
        evaluator_results = tuple(
            apply_evaluator(item, case, value, target.duration_ms) for item in evaluators
        )
        output_sha256 = canonical_sha256(value)
    else:
        evaluator_results = tuple(
            make_result(
                item.name, Status.SKIPPED, "TARGET_ERROR", "The target did not produce output."
            )
            for item in evaluators
        )
        output = ABSENT
        output_sha256 = None
    status, reason = aggregate_case_status(target, evaluator_results)
    return CaseResult(
        run_id=run_id,
        case_id=case.id,
        case_sha256=case.case_sha256(),
        status=status,
        status_reason=reason,
        target=target,
        evaluators=evaluator_results,
        input=case.input,
        expected=case.expected,
        output=output,
        input_sha256=canonical_sha256(case.input),
        expected_sha256=canonical_sha256(case.expected) if case.has_expected() else None,
        output_sha256=output_sha256,
    )


def target_timeout(target: object, options: RunOptions) -> float:
    """The timeout for one target (TRD-070).

    A target's own ``timeout_seconds`` applies when it declares one; otherwise the run's timeout.
    """
    declared = getattr(target, "timeout_seconds", None)
    if declared is None:
        return options.timeout_seconds
    if isinstance(declared, bool) or not isinstance(declared, int | float):
        raise EvalForgeError("USAGE_ERROR", "a target's timeout_seconds must be a number.")
    if not 0.0 < float(declared) <= MAX_TIMEOUT_SECONDS:
        raise EvalForgeError(
            "USAGE_ERROR",
            "a target's timeout_seconds must be greater than 0 and at most "
            f"{MAX_TIMEOUT_SECONDS:g}.",
        )
    return float(declared)


def _execute(
    run_id: str,
    case: Case,
    target: TargetProtocol,
    evaluators: Sequence[Evaluator],
    options: RunOptions,
    timed_out: list[timeouts.Worker],
) -> tuple[CaseResult, bool]:
    """Run one selected case.

    Returns the result and whether the user interrupted the run while it was in progress. If the
    interruption came and the case did not finish within the grace period, ``KeyboardInterrupt`` is
    raised and the case is not recorded.
    """
    timeout = target_timeout(target, options)
    worker = timeouts.Worker(target, case.input)
    worker.start()
    interrupted = False
    try:
        finished = timeouts.wait_for(worker, timeout)
    except KeyboardInterrupt:
        if not timeouts.wait_for(worker, options.grace_seconds):
            raise
        finished = True
        interrupted = True
    if not finished:
        timed_out.append(worker)
        invocation = _timed_out(timeout * 1000.0)
    else:
        if worker.error is not None:
            raise worker.error
        if worker.invocation is None:
            raise RuntimeError("target worker finished without an outcome")
        invocation = worker.invocation
    return _build_result(run_id, case, invocation, evaluators), interrupted


def run_cases(
    dataset: Dataset,
    target: TargetProtocol,
    evaluators: Sequence[Evaluator],
    options: RunOptions | None = None,
    on_case: Callable[[CaseResult], None] | None = None,
) -> RunOutcome:
    """Run the selected cases of ``dataset`` against ``target`` and return the in-memory outcome.

    ``on_case`` is called with each recorded result, in dataset order, as soon as it is recorded.
    """
    opts = options if options is not None else RunOptions()
    _check_selection(dataset, opts)
    run_id = str(uuid.uuid4())
    cases = dataset.cases
    results: list[CaseResult] = []
    timed_out: list[timeouts.Worker] = []
    status = RunStatus.COMPLETED
    error: ErrorObject | None = None

    for case in cases:
        if not _selected(case, opts):
            results.append(_not_run(run_id, case))
            continue
        try:
            result, interrupted = _execute(run_id, case, target, evaluators, opts, timed_out)
            results.append(result)
            if on_case is not None:
                on_case(result)
            if interrupted:
                status = RunStatus.ABORTED
                break
        except KeyboardInterrupt:
            status = RunStatus.ABORTED
            break
        except Exception as exc:
            status = RunStatus.FAILED
            error = ErrorObject(
                type_name=type(exc).__name__,
                message=f"unexpected {type(exc).__name__}; no further detail is recorded",
            )
            break

    threads_alive = sum(1 for worker in timed_out if worker.thread.is_alive())
    return RunOutcome(
        run_id=run_id,
        status=status,
        cases=tuple(results),
        not_executed=len(cases) - len(results),
        threads_possibly_running=threads_alive,
        error=error,
    )


__all__ = ["RunOptions", "RunOutcome", "run_cases"]
