# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Evaluation runner: sequential execution, timeouts, interruption, engine faults, selection.

See EXECUTION_PLAN §3.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from evalforge import timeouts
from evalforge.canon import JSONValue, canonical_sha256
from evalforge.datasets import Dataset, parse_dataset_bytes
from evalforge.errors import EvalForgeError
from evalforge.evaluators.builtin import ExactMatch, Latency, RuleBased
from evalforge.runner import RunOptions, run_cases
from evalforge.status import RunStatus, Status
from evalforge.targets import from_callable

RECORDS = b"".join(
    [
        b'{"id": "c1", "input": {"q": "one"}, "expected": "echo: one", "tags": ["smoke"]}\n',
        b'{"id": "c2", "input": {"q": "two"}, "expected": "echo: two", "tags": ["refunds"]}\n',
        b'{"id": "c3", "input": {"q": "three"}, "expected": "wrong", "tags": ["smoke"]}\n',
        b'{"id": "c4", "input": {"q": "four"}, "tags": ["smoke"]}\n',
        b'{"id": "c5", "input": {"q": "five"}, "expected": "echo: five"}\n',
    ]
)


def dataset() -> Dataset:
    return parse_dataset_bytes(RECORDS, fmt="jsonl", source_label="runner-test")


def echo_target() -> Any:
    def answer(case_input: JSONValue) -> JSONValue:
        assert isinstance(case_input, dict)
        return f"echo: {case_input['q']}"

    return from_callable(answer, name="echo")


EXACT = ExactMatch(name="exact")


# TST-TG-001 ordering and one call per case ----------------------------------------------


def test_each_selected_case_is_called_once_in_dataset_order() -> None:
    calls: list[str] = []

    def record(case_input: JSONValue) -> JSONValue:
        assert isinstance(case_input, dict)
        calls.append(str(case_input["q"]))
        return "ok"

    outcome = run_cases(dataset(), from_callable(record), ())
    assert calls == ["one", "two", "three", "four", "five"]
    assert [item.case_id for item in outcome.cases] == ["c1", "c2", "c3", "c4", "c5"]
    assert outcome.status is RunStatus.COMPLETED


# Status rules through the runner (EVALUATION_METHODOLOGY §3.3) ---------------------------


def test_passing_and_failing_cases_are_reported_with_the_evaluator_name() -> None:
    outcome = run_cases(dataset(), echo_target(), (EXACT,))
    statuses = {item.case_id: (item.status, item.status_reason) for item in outcome.cases}
    assert statuses["c1"] == (Status.PASS, None)
    assert statuses["c3"] == (Status.FAIL, "exact")


def test_case_without_expected_is_skipped_with_no_expected() -> None:
    outcome = run_cases(dataset(), echo_target(), (EXACT,))
    case = next(item for item in outcome.cases if item.case_id == "c4")
    assert case.status is Status.SKIPPED
    assert case.status_reason == "NO_EXPECTED"


def test_target_exception_is_an_error_and_evaluators_are_skipped_with_target_error() -> None:
    def boom(case_input: JSONValue) -> JSONValue:
        raise ValueError("target failed")

    outcome = run_cases(dataset(), from_callable(boom, name="boom"), (EXACT,))
    assert outcome.status is RunStatus.COMPLETED
    first = outcome.cases[0]
    assert first.status is Status.ERROR
    assert first.status_reason == "TARGET_EXCEPTION"
    assert first.target.error is not None
    assert first.target.error.type_name == "ValueError"
    assert [item.reason_code for item in first.evaluators] == ["TARGET_ERROR"]


def test_run_without_evaluators_marks_each_case_no_evaluators() -> None:
    outcome = run_cases(dataset(), echo_target(), ())
    assert {item.status_reason for item in outcome.cases} == {"NO_EVALUATORS"}


def test_one_failing_evaluator_does_not_hide_a_later_passing_one() -> None:
    latency_ok = Latency(name="fast", max_ms=10_000.0)
    outcome = run_cases(dataset(), echo_target(), (EXACT, latency_ok))
    failing = next(item for item in outcome.cases if item.case_id == "c3")
    assert failing.status is Status.FAIL
    assert [item.status for item in failing.evaluators] == [Status.FAIL, Status.PASS]


def test_hashes_identify_the_input_and_output_in_memory() -> None:
    outcome = run_cases(dataset(), echo_target(), (EXACT,))
    first = outcome.cases[0]
    assert first.input_sha256 == canonical_sha256({"q": "one"})
    assert first.output_sha256 == canonical_sha256("echo: one")
    assert first.case_sha256 == dataset().cases[0].case_sha256()


def test_rule_based_evaluator_runs_through_the_runner() -> None:
    rule = RuleBased(name="no_todo", not_contains=("two",))
    outcome = run_cases(dataset(), echo_target(), (rule,))
    second = next(item for item in outcome.cases if item.case_id == "c2")
    assert second.status is Status.FAIL
    assert second.status_reason == "no_todo"


# TST-TG-004 / TST-TG-009 timeouts (best-effort) -----------------------------------------


def test_timed_out_target_is_recorded_and_the_run_continues() -> None:
    release = threading.Event()

    def blocker(case_input: JSONValue) -> JSONValue:
        if case_input == {"q": "one"}:
            release.wait(10)
        return "ok"

    try:
        outcome = run_cases(
            dataset(), from_callable(blocker, name="blocker"), (), RunOptions(timeout_seconds=0.05)
        )
    finally:
        release.set()
    first, second = outcome.cases[0], outcome.cases[1]
    assert first.status is Status.ERROR
    assert first.status_reason == "TARGET_TIMEOUT"
    assert first.target.duration_ms == pytest.approx(50.0)
    assert second.status_reason == "NO_EVALUATORS"  # the run continued past the timeout


def test_timed_out_thread_is_counted_as_possibly_running() -> None:
    release = threading.Event()

    def blocker(case_input: JSONValue) -> JSONValue:
        release.wait(10)
        return "ok"

    try:
        outcome = run_cases(
            dataset(), from_callable(blocker, name="b"), (), RunOptions(timeout_seconds=0.05)
        )
        assert outcome.threads_possibly_running == 5  # five blocked threads, all still alive
    finally:
        release.set()


def test_finished_threads_are_not_counted() -> None:
    outcome = run_cases(dataset(), echo_target(), ())
    assert outcome.threads_possibly_running == 0


# TST-TG-012 interruption and the grace period -------------------------------------------


def _interrupt_on_second_wait(monkeypatch: pytest.MonkeyPatch, grace_finishes: bool) -> list[float]:
    real_wait = timeouts.wait_for
    seconds_seen: list[float] = []

    def scripted(worker: timeouts.Worker, seconds: float) -> bool:
        seconds_seen.append(seconds)
        index = len(seconds_seen)
        if index == 2:
            raise KeyboardInterrupt
        if index == 3:
            if grace_finishes:
                real_wait(worker, seconds)  # let the worker finish, as a real grace wait would
            return grace_finishes
        return real_wait(worker, seconds)

    monkeypatch.setattr(timeouts, "wait_for", scripted)
    return seconds_seen


def test_interruption_with_grace_completion_records_the_case_and_aborts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _interrupt_on_second_wait(monkeypatch, grace_finishes=True)
    outcome = run_cases(dataset(), echo_target(), (EXACT,), RunOptions(grace_seconds=5.0))
    assert outcome.status is RunStatus.ABORTED
    assert [item.case_id for item in outcome.cases] == ["c1", "c2"]
    assert outcome.not_executed == 3
    assert seen[2] == 5.0  # the grace wait used the configured grace period


def test_interruption_without_grace_completion_drops_the_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _interrupt_on_second_wait(monkeypatch, grace_finishes=False)
    outcome = run_cases(dataset(), echo_target(), (EXACT,))
    assert outcome.status is RunStatus.ABORTED
    assert [item.case_id for item in outcome.cases] == ["c1"]
    assert outcome.not_executed == 4


# Engine faults (TRD-104) ----------------------------------------------------------------


def test_unexpected_engine_fault_is_recorded_and_the_run_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from evalforge.evaluators.base import apply_evaluator as real_apply

    calls: list[int] = []

    def faulty(evaluator: Any, case: Any, output: Any, duration: float) -> Any:
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("engine bug")
        return real_apply(evaluator, case, output, duration)

    monkeypatch.setattr("evalforge.runner.apply_evaluator", faulty)
    outcome = run_cases(dataset(), echo_target(), (EXACT,))
    assert outcome.status is RunStatus.FAILED
    assert outcome.error is not None
    assert outcome.error.type_name == "RuntimeError"
    assert outcome.error.message == "unexpected RuntimeError; no further detail is recorded"
    assert len(outcome.cases) == 1
    assert outcome.not_executed == 4


# Selection (decision D-6) ---------------------------------------------------------------


def test_case_selection_lists_excluded_cases_as_user_filter_skips() -> None:
    outcome = run_cases(dataset(), echo_target(), (EXACT,), RunOptions(case_ids=frozenset({"c2"})))
    by_id = {item.case_id: item for item in outcome.cases}
    assert by_id["c2"].status is Status.PASS
    for other in ("c1", "c3", "c4", "c5"):
        assert by_id[other].status is Status.SKIPPED
        assert by_id[other].status_reason == "USER_FILTER"
        assert by_id[other].target.status == "NOT_RUN"
    assert outcome.counts()["SKIPPED"] == 4


def test_tag_selection_matches_any_listed_tag() -> None:
    outcome = run_cases(
        dataset(), echo_target(), (EXACT,), RunOptions(tags=frozenset({"refunds", "smoke"}))
    )
    selected = {item.case_id for item in outcome.cases if item.status_reason != "USER_FILTER"}
    assert selected == {"c1", "c2", "c3", "c4"}


def test_selecting_both_ids_and_tags_is_refused() -> None:
    with pytest.raises(ValueError, match="either case IDs or tags"):
        RunOptions(case_ids=frozenset({"c1"}), tags=frozenset({"smoke"}))


def test_unknown_case_ids_are_a_usage_error() -> None:
    with pytest.raises(EvalForgeError) as info:
        run_cases(dataset(), echo_target(), (), RunOptions(case_ids=frozenset({"c1", "nope"})))
    assert info.value.code == "USAGE_ERROR"
    assert "nope" in info.value.message


def test_zero_timeout_is_refused() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        RunOptions(timeout_seconds=0.0)


def test_timeout_above_one_hour_is_refused() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        RunOptions(timeout_seconds=3601.0)


def test_negative_grace_is_refused() -> None:
    with pytest.raises(ValueError, match="grace_seconds"):
        RunOptions(grace_seconds=-1.0)


def test_in_memory_run_is_stable_across_repeated_calls() -> None:
    first = run_cases(dataset(), echo_target(), (EXACT,))
    second = run_cases(dataset(), echo_target(), (EXACT,))
    assert [(c.case_id, c.status, c.status_reason) for c in first.cases] == [
        (c.case_id, c.status, c.status_reason) for c in second.cases
    ]
    assert first.run_id != second.run_id
