# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Run comparison (TEST_STRATEGY §4.7: TST-CM-001 to TST-CM-022, the Milestone 9 subset).

Runs are real stored runs made with the runner and the storage writer. Each case's
behaviour is set by name: "ok" returns the expected value, "wrong" returns a value that
fails, "raise" raises.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from evalforge.canon import JSONValue
from evalforge.compare import Comparison, compare_runs
from evalforge.config import config_from_mapping
from evalforge.datasets import parse_dataset_bytes
from evalforge.errors import IntegrityError
from evalforge.evaluators.base import Evaluator, fingerprint_of
from evalforge.evaluators.builtin import ExactMatch, Latency
from evalforge.reader import StoredRun, load_run
from evalforge.runner import RunOptions, run_cases
from evalforge.store import RunContext, persist_outcome
from evalforge.targets import from_callable

CASES = {"c1": "one", "c2": "two", "c3": "three", "c4": "four", "c5": "five"}
BASE_RECORDS = (
    b'{"id": "c1", "input": {"q": "one"}, "expected": "echo: one"}\n'
    b'{"id": "c2", "input": {"q": "two"}, "expected": "echo: two"}\n'
    b'{"id": "c3", "input": {"q": "three"}, "expected": "echo: three"}\n'
    b'{"id": "c4", "input": {"q": "four"}}\n'
    b'{"id": "c5", "input": {"q": "five"}, "expected": "echo: five"}\n'
)
EXACT: tuple[Evaluator, ...] = (ExactMatch(name="exact"),)


def _behaviour_target(behaviour: dict[str, str]) -> Any:
    def target(case_input: JSONValue) -> JSONValue:
        assert isinstance(case_input, dict)
        query = str(case_input["q"])
        case_id = next((key for key, value in CASES.items() if value == query), "")
        mode = behaviour.get(case_id, "ok")
        if mode == "raise":
            raise ValueError("boom")
        if mode == "wrong":
            return "x"
        return f"echo: {query}"

    return target


def _make_run(
    root: Path,
    name: str,
    *,
    records: bytes = BASE_RECORDS,
    behaviour: dict[str, str] | None = None,
    evaluators: tuple[Evaluator, ...] = EXACT,
    io_mode: str = "full",
) -> StoredRun:
    run_root = root / name
    config = config_from_mapping(
        {
            "schema_version": "1.0",
            "run": {"io_mode": io_mode, "redaction": True},
            "dataset": {"path": "datasets/cmp.jsonl"},
            "target": {"callable": "example:answer", "name": "echo"},
            "evaluators": [{"name": "exact", "type": "exact_match"}],
        },
        config_dir=run_root,
    )
    dataset = parse_dataset_bytes(records, fmt="jsonl", source_label="datasets/cmp.jsonl")
    context = RunContext(
        dataset=dataset,
        config=config,
        options=RunOptions(),
        io_mode=io_mode,
        redaction=True,
        target_name="echo",
        fingerprints=tuple(fingerprint_of(item) for item in evaluators),
    )
    target = from_callable(_behaviour_target(behaviour or {}), name="echo")
    outcome = run_cases(dataset, target, evaluators, context.options)
    run_dir = persist_outcome(outcome, context, run_root / "runs")
    return load_run(run_dir)


def _by_id(comparison: Comparison) -> dict[str, Any]:
    return {item.case_id: item for item in comparison.cases}


# TST-CM-001 categories ----------------------------------------------------------------------


def test_each_status_transition_is_classified(tmp_path: Path) -> None:
    baseline = _make_run(
        tmp_path, "base", behaviour={"c3": "wrong"}
    )  # c1 c2 PASS, c3 FAIL, c4 SKIPPED, c5 PASS
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "wrong", "c2": "raise"})
    comparison = compare_runs(baseline, candidate)
    rows = _by_id(comparison)
    assert (rows["c1"].category, rows["c1"].subtype) == ("regressed", "to_fail")
    assert (rows["c2"].category, rows["c2"].subtype) == ("regressed", "to_error")
    assert (rows["c3"].category, rows["c3"].baseline_status, rows["c3"].candidate_status) == (
        "recovered",
        "FAIL",
        "PASS",
    )
    assert rows["c4"].category == "unchanged"
    assert rows["c5"].category == "unchanged"
    assert comparison.exit_status == "regression"  # c1 and c2 regressed (Milestone 10)


def test_fail_to_error_is_changed_not_a_regression(tmp_path: Path) -> None:  # OD-13
    baseline = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})
    candidate = _make_run(tmp_path, "cand", behaviour={"c3": "raise"})
    assert _by_id(compare_runs(baseline, candidate))["c3"].category == "changed"


def test_identical_runs_have_only_unchanged_cases(
    tmp_path: Path,
) -> None:  # TST-CM-002 (categories)
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand")
    comparison = compare_runs(baseline, candidate)
    assert {item.category for item in comparison.cases} == {"unchanged"}
    assert comparison.refusals == ()
    # Four executed cases is below min_executed_for_rate_check (TRD-142): only the warning remains.
    assert [item.code for item in comparison.findings] == ["RATE_CHECK_SKIPPED"]
    assert comparison.exit_status == "pass"


def test_category_counts_are_reported(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "wrong"})
    counts = compare_runs(baseline, candidate).counts
    assert counts is not None
    assert counts["categories"]["regressed"] == 1
    assert counts["categories"]["recovered"] == 1


# TST-CM-003 / 004 dataset changes -------------------------------------------------------------

CHANGED_INPUT_RECORDS = BASE_RECORDS.replace(b'"q": "two"', b'"q": "two-changed"', 1)
MISSING_RECORDS = b"".join(BASE_RECORDS.splitlines(keepends=True)[:4])


def test_changed_dataset_is_refused_by_default(tmp_path: Path) -> None:  # TST-CM-003
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", records=CHANGED_INPUT_RECORDS)
    comparison = compare_runs(baseline, candidate)
    assert comparison.exit_status == "refused"
    assert [item.code for item in comparison.refusals] == ["DATASET_CHANGED"]
    assert comparison.cases == ()
    assert comparison.overrides == ()


def test_allowed_dataset_change_is_an_override_with_a_warning(tmp_path: Path) -> None:  # TST-CM-004
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", records=CHANGED_INPUT_RECORDS)
    comparison = compare_runs(baseline, candidate, allow_dataset_change=True)
    assert comparison.exit_status == "pass"
    assert [item.flag for item in comparison.overrides] == ["--allow-dataset-change"]
    codes = {item.code for item in comparison.findings}
    assert {"DATASET_CHANGED", "COMPARISON_OVERRIDDEN"} <= codes
    assert _by_id(comparison)["c2"].category == "changed_input"


def test_case_missing_from_the_candidate_is_listed(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", records=MISSING_RECORDS)
    comparison = compare_runs(baseline, candidate, allow_dataset_change=True)
    assert _by_id(comparison)["c5"].category == "missing_in_candidate"


def test_case_new_in_the_candidate_is_listed(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base", records=MISSING_RECORDS)
    candidate = _make_run(tmp_path, "cand")
    comparison = compare_runs(baseline, candidate, allow_dataset_change=True)
    assert _by_id(comparison)["c5"].category == "new_in_candidate"


def test_raw_byte_change_with_identical_cases_is_information_only(
    tmp_path: Path,
) -> None:  # TST-CM-006
    spaced = BASE_RECORDS.replace(b'"id": "c1"', b'"id":   "c1"', 1)
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", records=spaced)
    comparison = compare_runs(baseline, candidate)
    assert comparison.refusals == ()
    assert [item.code for item in comparison.findings] == [
        "RAW_BYTES_CHANGED",
        "RATE_CHECK_SKIPPED",
    ]
    assert comparison.findings[0].severity == "info"


# TST-CM-005 evaluators ---------------------------------------------------------------------


def test_changed_evaluator_definitions_are_refused_by_default(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(
        tmp_path, "cand", evaluators=(ExactMatch(name="exact"), Latency(name="fast", max_ms=5.0))
    )
    comparison = compare_runs(baseline, candidate)
    assert [item.code for item in comparison.refusals] == ["EVALUATOR_CHANGED"]
    assert "fast" in comparison.refusals[0].message


def test_allowed_evaluator_change_is_an_override(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(
        tmp_path, "cand", evaluators=(ExactMatch(name="exact"), Latency(name="fast", max_ms=5.0))
    )
    comparison = compare_runs(baseline, candidate, allow_evaluator_change=True)
    # The latency verdict depends on machine speed, so only the refusal state is asserted here.
    assert comparison.refusals == ()
    assert comparison.exit_status in {"pass", "regression"}
    assert [item.flag for item in comparison.overrides] == ["--allow-evaluator-change"]


# TST-CM-007 / 008 / 019 refusals ---------------------------------------------------------------


def test_incomplete_run_is_refused(tmp_path: Path) -> None:  # TST-CM-007
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand")
    manifest_path = candidate.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "ABORTED"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    aborted = load_run(candidate.path, strict=False)
    comparison = compare_runs(baseline, aborted)
    assert [item.code for item in comparison.refusals] == ["RUN_INCOMPLETE"]


def test_every_refusal_is_listed_not_only_the_first(tmp_path: Path) -> None:  # TST-CM-008
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(
        tmp_path,
        "cand",
        records=CHANGED_INPUT_RECORDS,
        evaluators=(ExactMatch(name="exact"), Latency(name="fast", max_ms=5.0)),
    )
    codes = [item.code for item in compare_runs(baseline, candidate).refusals]
    assert codes == ["DATASET_CHANGED", "EVALUATOR_CHANGED"]


def test_strict_refuses_an_overridden_comparison(tmp_path: Path) -> None:  # TST-CM-021
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", records=CHANGED_INPUT_RECORDS)
    comparison = compare_runs(baseline, candidate, allow_dataset_change=True, strict=True)
    assert comparison.exit_status == "refused"
    assert "COMPARISON_OVERRIDDEN" in [item.code for item in comparison.refusals]


# TST-CM-016 determinism ----------------------------------------------------------------------


def test_output_is_identical_apart_from_the_comparison_id_and_timestamp(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "wrong"})
    first = compare_runs(baseline, candidate).to_dict()
    second = compare_runs(baseline, candidate).to_dict()
    for volatile in ("comparison_id", "created_at"):
        first.pop(volatile)
        second.pop(volatile)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_cases_are_sorted_by_case_id(tmp_path: Path) -> None:
    comparison = compare_runs(_make_run(tmp_path, "b"), _make_run(tmp_path, "c"))
    ids = [item.case_id for item in comparison.cases]
    assert ids == sorted(ids)


# Output-level and I/O-level behaviour -------------------------------------------------------


def test_output_change_with_the_same_status_is_detected(tmp_path: Path) -> None:
    latency = (Latency(name="fast", max_ms=10_000.0),)
    baseline = _make_run(tmp_path, "base", evaluators=latency)
    candidate = _make_run(tmp_path, "cand", evaluators=latency, behaviour={"c1": "wrong"})
    row = _by_id(compare_runs(baseline, candidate))["c1"]
    assert row.category == "unchanged"
    assert row.output_changed is True


def test_io_none_makes_output_changes_unknown(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base", io_mode="none")
    candidate = _make_run(tmp_path, "cand", io_mode="none")
    comparison = compare_runs(baseline, candidate)
    assert {item.code for item in comparison.findings} == {"IO_UNAVAILABLE", "RATE_CHECK_SKIPPED"}
    assert all(item.output_changed is None for item in comparison.cases)
    assert comparison.io_available == {"baseline": False, "candidate": False}


# TST-CM-017 zero executed cases -----------------------------------------------------------


def test_comparison_with_no_executed_cases_has_no_rates(tmp_path: Path) -> None:
    no_expected = b'{"id": "c1", "input": {"q": "one"}}\n{"id": "c2", "input": {"q": "two"}}\n'
    baseline = _make_run(tmp_path, "base", records=no_expected)
    candidate = _make_run(tmp_path, "cand", records=no_expected)
    comparison = compare_runs(baseline, candidate)
    assert comparison.metrics is not None
    metrics = cast(dict[str, Any], comparison.metrics)
    assert metrics["baseline"]["pass_rate"] is None
    assert metrics["delta"]["pass_rate"] is None


def test_metrics_report_both_runs_and_the_delta(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "wrong", "c3": "wrong"})
    metrics = cast(dict[str, Any], compare_runs(baseline, candidate).metrics)
    # Baseline: c1 PASS, c2 PASS, c3 FAIL, c5 PASS (c4 skipped) -> 3 of 4.
    # Candidate: c1 FAIL, c2 PASS, c3 FAIL, c5 PASS -> 2 of 4.
    assert metrics["baseline"]["pass_rate"] == pytest.approx(0.75)
    assert metrics["candidate"]["pass_rate"] == pytest.approx(0.5)
    assert metrics["delta"]["pass_rate"] == pytest.approx(-0.25)


# TST-CM-022 and integrity (TST-CM-018) -----------------------------------------------------


def test_tampered_candidate_is_refused_by_the_reader(tmp_path: Path) -> None:  # TST-CM-018
    candidate = _make_run(tmp_path, "cand")
    cases = candidate.path / "cases.jsonl"
    cases.write_bytes(cases.read_bytes().replace(b'"PASS"', b'"FAIL"', 1))
    with pytest.raises(IntegrityError):
        load_run(candidate.path)


def test_the_comparison_record_names_both_runs(tmp_path: Path) -> None:
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand")
    record = compare_runs(baseline, candidate).to_dict()
    assert cast(dict[str, Any], record["baseline"])["run_id"] == baseline.manifest["run_id"]
    assert cast(dict[str, Any], record["candidate"])["run_id"] == candidate.manifest["run_id"]
    assert record["schema_version"] == "1.0"
