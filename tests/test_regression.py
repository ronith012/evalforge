# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Regression detection (TEST_STRATEGY §4.7: TST-CM-002, TST-CM-009 to TST-CM-015, TST-CM-017).

Case-level and rate-level checks run on real stored runs built by ``test_compare``. Golden tests pin
each finding message template exactly (TST-CM-015).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from evalforge.compare import CaseComparison, compare_runs
from evalforge.regression import DEFAULT_THRESHOLDS, Finding, latency_finding, regression_findings
from test_compare import MISSING_RECORDS, _make_run

# Lets a run of five cases count as executed for the rate checks (TRD-142).
LOOSE = replace(DEFAULT_THRESHOLDS, min_executed_for_rate_check=1)
NO_EXPECTED = b'{"id": "c1", "input": {"q": "one"}}\n{"id": "c2", "input": {"q": "two"}}\n'
METRICS: dict[str, object] = {"pass_rate": 0.9, "executed": 40, "latency_p95_ms": 10.0}


def _by_code(findings: Sequence[Finding], code: str) -> list[Finding]:
    return [item for item in findings if item.code == code]


def _row(case_id: str, category: str, subtype: str | None = None) -> CaseComparison:
    return CaseComparison(
        case_id=case_id,
        category=category,
        subtype=subtype,
        baseline_status=None,
        candidate_status=None,
        baseline_output_sha256=None,
        candidate_output_sha256=None,
        output_changed=None,
    )


# TST-CM-002 self-comparison -------------------------------------------------------------------


def test_a_run_compared_with_itself_has_no_error_findings(tmp_path: Path) -> None:  # TST-CM-002
    run = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})
    comparison = compare_runs(run, run)
    assert {item.category for item in comparison.cases} == {"unchanged"}
    assert [item for item in comparison.findings if item.severity == "error"] == []
    assert comparison.exit_status == "pass"


# TST-CM-009 missing cases ---------------------------------------------------------------------


def test_missing_case_policy_selects_error_warning_or_nothing(tmp_path: Path) -> None:  # TST-CM-009
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", records=MISSING_RECORDS)

    for policy, severity, exit_status in (
        ("fail", "error", "regression"),
        ("warn", "warning", "pass"),
    ):
        thresholds = replace(DEFAULT_THRESHOLDS, missing_case_policy=policy)
        comparison = compare_runs(
            baseline, candidate, allow_dataset_change=True, thresholds=thresholds
        )
        (finding,) = _by_code(comparison.findings, "CASE_MISSING_IN_CANDIDATE")
        assert finding.severity == severity
        assert finding.case_ids == ("c5",)
        assert comparison.exit_status == exit_status

    ignored = replace(DEFAULT_THRESHOLDS, missing_case_policy="ignore")
    comparison = compare_runs(baseline, candidate, allow_dataset_change=True, thresholds=ignored)
    assert _by_code(comparison.findings, "CASE_MISSING_IN_CANDIDATE") == []


# TST-CM-010 pass-rate boundary ----------------------------------------------------------------


def test_pass_rate_drop_equal_to_the_maximum_is_not_a_finding(tmp_path: Path) -> None:  # TST-CM-010
    baseline = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})  # 3 of 4 executed pass
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "wrong", "c3": "wrong"})  # 2 of 4

    at_limit = replace(LOOSE, max_pass_rate_drop=0.25)
    comparison = compare_runs(baseline, candidate, thresholds=at_limit)
    assert _by_code(comparison.findings, "PASS_RATE_DROP") == []

    below_limit = replace(LOOSE, max_pass_rate_drop=0.2)
    comparison = compare_runs(baseline, candidate, thresholds=below_limit)
    (finding,) = _by_code(comparison.findings, "PASS_RATE_DROP")
    assert finding.severity == "error"
    assert finding.threshold == {
        "key": "regression.max_pass_rate_drop",
        "configured": 0.2,
        "observed": 0.25,
    }
    assert finding.values == {"baseline": 0.75, "candidate": 0.5, "delta": -0.25}


# TST-CM-011 newly failing cases ---------------------------------------------------------------


def test_newly_failing_cases_above_the_count_are_listed_sorted(
    tmp_path: Path,
) -> None:  # TST-CM-011
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", behaviour={"c2": "wrong", "c1": "wrong"})

    limited = replace(LOOSE, max_newly_failing=1)
    (finding,) = _by_code(
        compare_runs(baseline, candidate, thresholds=limited).findings, "CASE_REGRESSED_TO_FAIL"
    )
    assert finding.case_ids == ("c1", "c2")
    assert finding.threshold == {
        "key": "regression.max_newly_failing",
        "configured": 1,
        "observed": 2,
    }

    tolerated = replace(LOOSE, max_newly_failing=2)
    comparison = compare_runs(baseline, candidate, thresholds=tolerated)
    assert _by_code(comparison.findings, "CASE_REGRESSED_TO_FAIL") == []


# TST-CM-012 infrastructure errors -------------------------------------------------------------


def test_an_infrastructure_error_is_never_a_regression_to_fail(
    tmp_path: Path,
) -> None:  # TST-CM-012
    baseline = _make_run(tmp_path, "base")
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "raise"})

    comparison = compare_runs(baseline, candidate, thresholds=LOOSE)
    assert _by_code(comparison.findings, "CASE_REGRESSED_TO_FAIL") == []
    (finding,) = _by_code(comparison.findings, "CASE_REGRESSED_TO_ERROR")
    assert finding.case_ids == ("c1",)
    assert comparison.exit_status == "regression"

    tolerated = replace(LOOSE, max_newly_errored=1)
    comparison = compare_runs(baseline, candidate, thresholds=tolerated)
    assert _by_code(comparison.findings, "CASE_REGRESSED_TO_ERROR") == []


# TST-CM-013 rate check skipped below the minimum ----------------------------------------------


def test_rate_check_is_skipped_below_the_minimum_but_case_checks_still_apply(
    tmp_path: Path,
) -> None:  # TST-CM-013
    baseline = _make_run(tmp_path, "base", behaviour={"c3": "wrong"})
    candidate = _make_run(tmp_path, "cand", behaviour={"c1": "wrong", "c2": "wrong"})

    comparison = compare_runs(baseline, candidate)  # Default minimum is 30; four cases executed.
    codes = [item.code for item in comparison.findings]
    assert "RATE_CHECK_SKIPPED" in codes
    assert "PASS_RATE_DROP" not in codes
    assert "CASE_REGRESSED_TO_FAIL" in codes

    (skipped,) = _by_code(comparison.findings, "RATE_CHECK_SKIPPED")
    assert skipped.severity == "warning"
    assert skipped.threshold == {
        "key": "regression.min_executed_for_rate_check",
        "configured": 30,
        "observed": 4,
    }


# TST-CM-014 latency ---------------------------------------------------------------------------


def test_latency_ratio_above_the_maximum_is_a_finding() -> None:  # TST-CM-014
    finding = latency_finding(10.0, 20.0, 1.5)
    assert finding is not None
    assert finding.code == "LATENCY_P95_INCREASE"
    assert finding.severity == "error"
    assert finding.values == {"baseline": 10.0, "candidate": 20.0, "ratio": 2.0}


def test_latency_ratio_at_the_maximum_is_not_a_finding() -> None:  # TST-CM-014
    assert latency_finding(10.0, 15.0, 1.5) is None


@pytest.mark.parametrize("baseline_p95", [None, 0.0])
def test_latency_check_is_skipped_when_the_baseline_p95_is_missing_or_zero(
    baseline_p95: float | None,
) -> None:  # TST-CM-014
    finding = latency_finding(baseline_p95, 20.0, 1.5)
    assert finding is not None
    assert finding.code == "RATE_CHECK_SKIPPED"
    assert finding.severity == "warning"
    assert (
        finding.message
        == "Latency check skipped: a p95 latency is missing or the baseline p95 is zero."
    )


def test_latency_check_runs_only_when_a_ratio_is_configured() -> None:  # TST-CM-014
    base = {"pass_rate": 0.9, "executed": 40, "latency_p95_ms": 10.0}
    cand = {"pass_rate": 0.9, "executed": 40, "latency_p95_ms": 30.0}
    assert (
        _by_code(regression_findings((), base, cand, DEFAULT_THRESHOLDS), "LATENCY_P95_INCREASE")
        == []
    )
    configured = replace(DEFAULT_THRESHOLDS, max_p95_latency_ratio=1.5)
    (finding,) = _by_code(regression_findings((), base, cand, configured), "LATENCY_P95_INCREASE")
    assert finding.threshold == {
        "key": "regression.max_p95_latency_ratio",
        "configured": 1.5,
        "observed": 3.0,
    }


# TST-CM-015 golden messages -------------------------------------------------------------------

GOLDEN_ROWS = (
    _row("c2", "regressed", "to_fail"),
    _row("c1", "regressed", "to_fail"),
    _row("c3", "regressed", "to_error"),
    _row("c4", "regressed", "to_inconclusive"),
    _row("c5", "missing_in_candidate"),
    _row("c6", "new_in_candidate"),
    _row("c7", "recovered"),
)


def test_case_finding_messages_match_the_golden_templates() -> None:  # TST-CM-015
    findings = regression_findings(GOLDEN_ROWS, METRICS, METRICS, DEFAULT_THRESHOLDS)
    assert [item.message for item in findings] == [
        "2 cases that passed in the baseline now fail: c1, c2.",
        "1 case that passed in the baseline now errors: c3.",
        "1 case that passed in the baseline is now inconclusive: c4.",
        "1 case in the baseline is missing from the candidate: c5.",
        "1 case is new in the candidate: c6.",
        "1 case recovered: c7.",
    ]
    assert [item.severity for item in findings] == [
        "error",
        "error",
        "warning",
        "error",
        "warning",
        "info",
    ]


def test_rate_and_latency_messages_match_the_golden_templates() -> None:  # TST-CM-015
    base = {"pass_rate": 0.9, "executed": 40, "latency_p95_ms": 10.0}
    cand = {"pass_rate": 0.7, "executed": 40, "latency_p95_ms": 20.0}
    thresholds = replace(DEFAULT_THRESHOLDS, max_p95_latency_ratio=1.5)
    findings = regression_findings((), base, cand, thresholds)
    assert [item.message for item in findings] == [
        "Pass rate fell from 0.900 to 0.700 (drop 0.200), above the configured maximum of 0.000.",
        "p95 latency rose from 10.0 ms to 20.0 ms (ratio 2.00), "
        "above the configured maximum of 1.50.",
    ]


def test_rate_check_skipped_message_matches_the_golden_template() -> None:  # TST-CM-015
    small = {"pass_rate": 0.9, "executed": 5}
    (finding,) = regression_findings((), small, small, DEFAULT_THRESHOLDS)
    assert finding.message == (
        "Rate check skipped: fewer than 30 executed cases in a run (smallest: 5)."
    )


# TST-CM-017 zero executed cases ---------------------------------------------------------------


def test_zero_executed_cases_report_rate_check_skipped(tmp_path: Path) -> None:  # TST-CM-017
    baseline = _make_run(tmp_path, "base", records=NO_EXPECTED)
    candidate = _make_run(tmp_path, "cand", records=NO_EXPECTED)
    comparison = compare_runs(baseline, candidate)
    assert [item.code for item in comparison.findings] == ["RATE_CHECK_SKIPPED"]
    assert comparison.findings[0].message == "Rate check skipped: a run has no executed cases."
    assert comparison.exit_status == "pass"
