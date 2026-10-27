# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Model validation and the case-status aggregation table (EVALUATION_METHODOLOGY §3.3)."""

from __future__ import annotations

import pytest

from evalforge.errors import SchemaVersionError
from evalforge.models import (
    ABSENT,
    Case,
    CaseResult,
    ErrorObject,
    EvaluatorResult,
    TargetResult,
    ValidationError,
    aggregate_case_status,
    check_schema_version,
)
from evalforge.status import Status

RUN_ID = "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90"  # UUIDv4 literal
CASE_HASH = "sha256:" + "a" * 64

OK = TargetResult(status="OK", error_code=None, error=None, duration_ms=12.0)
TIMEOUT = TargetResult(
    status="ERROR",
    error_code="TARGET_TIMEOUT",
    error=ErrorObject(type_name="TimeoutError", message="Target exceeded 30.0 s"),
    duration_ms=30000.0,
)


def ev(name: str, status: Status, reason: str | None = None) -> EvaluatorResult:
    """Build an evaluator result with a valid reason for its status."""
    if status is Status.PASS:
        return EvaluatorResult(name=name, status=status, score=1.0, reason_code=None, message="ok")
    if status is Status.FAIL:
        return EvaluatorResult(
            name=name, status=status, score=0.0, reason_code=reason or "VALUE_MISMATCH", message="m"
        )
    if status is Status.ERROR:
        return EvaluatorResult(
            name=name,
            status=status,
            score=None,
            reason_code=reason or "EVALUATOR_EXCEPTION",
            message="m",
        )
    if status is Status.INCONCLUSIVE:
        return EvaluatorResult(
            name=name,
            status=status,
            score=None,
            reason_code=reason or "CUSTOM_UNCERTAIN",
            message="m",
        )
    return EvaluatorResult(
        name=name, status=status, score=None, reason_code=reason or "NO_EXPECTED", message="m"
    )


# Table from EVALUATION_METHODOLOGY §3.3 (hand-written expectations).
AGGREGATION_TABLE = [
    # (id, target, evaluators, expected status, expected reason)
    ("T1", TIMEOUT, [ev("exact", Status.SKIPPED, "TARGET_ERROR")], Status.ERROR, "TARGET_TIMEOUT"),
    ("T2", OK, [], Status.SKIPPED, "NO_EVALUATORS"),
    (
        "T3",
        OK,
        [
            ev("exact", Status.ERROR, "EVALUATOR_EXCEPTION"),
            ev("rule", Status.FAIL, "RULE_CONTAINS_MISSING"),
        ],
        Status.ERROR,
        "EVALUATOR_EXCEPTION",
    ),
    (
        "T4",
        OK,
        [
            ev("custom", Status.INCONCLUSIVE, "CUSTOM_UNCERTAIN"),
            ev("rule", Status.FAIL, "RULE_CONTAINS_MISSING"),
        ],
        Status.INCONCLUSIVE,
        "CUSTOM_UNCERTAIN",
    ),
    (
        "T5",
        OK,
        [ev("exact", Status.FAIL, "VALUE_MISMATCH"), ev("latency", Status.PASS)],
        Status.FAIL,
        "exact",
    ),
    (
        "T6",
        OK,
        [ev("exact", Status.SKIPPED, "NO_EXPECTED"), ev("rule", Status.SKIPPED, "NO_EXPECTED")],
        Status.SKIPPED,
        "NO_EXPECTED",
    ),
    (
        "T7",
        OK,
        [ev("exact", Status.PASS), ev("latency", Status.SKIPPED, "NO_EXPECTED")],
        Status.PASS,
        None,
    ),
    ("T8", OK, [ev("exact", Status.PASS), ev("rule", Status.PASS)], Status.PASS, None),
    (
        "T9",
        TIMEOUT,
        [ev("exact", Status.SKIPPED, "TARGET_ERROR")],
        Status.ERROR,
        "TARGET_TIMEOUT",
    ),
    (
        "T10",
        OK,
        [
            ev("exact", Status.ERROR, "EVALUATOR_EXCEPTION"),
            ev("rule", Status.FAIL, "VALUE_MISMATCH"),
        ],
        Status.ERROR,
        "EVALUATOR_EXCEPTION",
    ),
]


@pytest.mark.parametrize(("case_id", "target", "evaluators", "status", "reason"), AGGREGATION_TABLE)
def test_status_aggregation_table(
    case_id: str,
    target: TargetResult,
    evaluators: list[EvaluatorResult],
    status: Status,
    reason: str | None,
) -> None:
    assert aggregate_case_status(target, evaluators) == (status, reason), case_id


def test_case_result_accepts_a_consistent_record() -> None:
    result = CaseResult(
        run_id=RUN_ID,
        case_id="refund-001",
        case_sha256=CASE_HASH,
        status=Status.FAIL,
        status_reason="exact",
        target=OK,
        evaluators=(ev("exact", Status.FAIL, "VALUE_MISMATCH"), ev("latency", Status.PASS)),
    )
    assert result.status is Status.FAIL


def test_case_result_rejects_a_status_that_contradicts_its_evaluators() -> None:
    with pytest.raises(ValidationError, match="inconsistent"):
        CaseResult(
            run_id=RUN_ID,
            case_id="refund-001",
            case_sha256=CASE_HASH,
            status=Status.PASS,
            status_reason=None,
            target=OK,
            evaluators=(ev("exact", Status.FAIL, "VALUE_MISMATCH"),),
        )


def test_case_result_rejects_an_evaluator_error_recorded_as_fail() -> None:
    with pytest.raises(ValidationError, match="inconsistent"):
        CaseResult(
            run_id=RUN_ID,
            case_id="c1",
            case_sha256=CASE_HASH,
            status=Status.FAIL,
            status_reason="exact",
            target=OK,
            evaluators=(ev("exact", Status.ERROR, "EVALUATOR_EXCEPTION"), ev("rule", Status.FAIL)),
        )


def test_case_result_rejects_target_error_with_non_skipped_evaluators() -> None:
    with pytest.raises(ValidationError, match="when the target failed"):
        CaseResult(
            run_id=RUN_ID,
            case_id="c1",
            case_sha256=CASE_HASH,
            status=Status.ERROR,
            status_reason="TARGET_TIMEOUT",
            target=TIMEOUT,
            evaluators=(ev("exact", Status.FAIL, "VALUE_MISMATCH"),),
        )


def test_case_result_rejects_target_error_reason_when_target_succeeded() -> None:
    with pytest.raises(ValidationError, match="only valid when the target failed"):
        CaseResult(
            run_id=RUN_ID,
            case_id="c1",
            case_sha256=CASE_HASH,
            status=Status.SKIPPED,
            status_reason="TARGET_ERROR",
            target=OK,
            evaluators=(ev("exact", Status.SKIPPED, "TARGET_ERROR"),),
        )


def test_case_result_rejects_a_non_v4_run_id() -> None:
    with pytest.raises(ValidationError, match="UUIDv4"):
        CaseResult(
            run_id="00000000-0000-1000-8000-000000000000",
            case_id="c1",
            case_sha256=CASE_HASH,
            status=Status.PASS,
            status_reason=None,
            target=OK,
            evaluators=(ev("exact", Status.PASS),),
        )


def test_case_result_rejects_an_unsupported_schema_major() -> None:
    with pytest.raises(SchemaVersionError) as info:
        CaseResult(
            run_id=RUN_ID,
            case_id="c1",
            case_sha256=CASE_HASH,
            status=Status.PASS,
            status_reason=None,
            target=OK,
            evaluators=(ev("exact", Status.PASS),),
            schema_version="2.0",
        )
    assert info.value.code == "SCHEMA_VERSION_UNSUPPORTED"


@pytest.mark.parametrize("version", ["1.0", "1.7"])
def test_schema_major_one_is_accepted(version: str) -> None:
    check_schema_version(version)


@pytest.mark.parametrize("version", ["1", "v1.0", "one", 1.0])
def test_malformed_schema_versions_are_rejected(version: object) -> None:
    with pytest.raises(ValidationError):
        check_schema_version(version)


@pytest.mark.parametrize("case_id", ["refund-001", "a.b_c", "A1", "x" * 128])
def test_valid_case_ids(case_id: str) -> None:
    assert Case(id=case_id, input={"q": "x"}).id == case_id


@pytest.mark.parametrize("case_id", ["", " a", "../x", "-a", "x" * 129, "a\n", "a/b"])
def test_invalid_case_ids(case_id: str) -> None:
    with pytest.raises(ValidationError, match="1 to 128"):
        Case(id=case_id, input={})


def test_expected_absent_is_distinct_from_expected_null() -> None:
    absent = Case(id="c1", input={"q": 1})
    null = Case(id="c1", input={"q": 1}, expected=None)
    assert not absent.has_expected()
    assert null.has_expected()
    assert absent.expected is ABSENT
    assert absent.case_sha256() != null.case_sha256()


def test_case_tags_must_be_unique_and_bounded() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Case(id="c1", input={}, tags=("smoke", "smoke"))
    with pytest.raises(ValidationError, match="at most 32"):
        Case(id="c1", input={}, tags=tuple(f"t{i}" for i in range(33)))


def test_case_rejects_non_json_input() -> None:
    with pytest.raises(ValidationError, match="unsupported type"):
        Case(id="c1", input={"x": {1, 2}})  # type: ignore[dict-item]


def test_case_metadata_is_read_only() -> None:
    case = Case(id="c1", input={}, metadata={"category": "refunds"})
    with pytest.raises(TypeError):
        case.metadata["category"] = "other"  # type: ignore[index]


def test_case_content_hash_does_not_depend_on_tag_order() -> None:
    first = Case(id="c1", input={}, tags=("a", "b"))
    second = Case(id="c1", input={}, tags=("b", "a"))
    assert first.case_sha256() == second.case_sha256()


def test_evaluator_pass_must_not_carry_a_reason() -> None:
    with pytest.raises(ValidationError, match="PASS carries no reason"):
        EvaluatorResult(
            name="exact", status=Status.PASS, score=1.0, reason_code="VALUE_MISMATCH", message="x"
        )


def test_evaluator_fail_needs_a_fail_reason() -> None:
    with pytest.raises(ValidationError, match="belongs to"):
        EvaluatorResult(
            name="exact", status=Status.FAIL, score=0.0, reason_code="TARGET_TIMEOUT", message="x"
        )


def test_evaluator_fail_without_reason_is_rejected() -> None:
    with pytest.raises(ValidationError, match="requires a reason code"):
        EvaluatorResult(name="exact", status=Status.FAIL, score=0.0, reason_code=None, message="x")


def test_evaluator_score_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError, match=r"\[0, 1\]"):
        EvaluatorResult(name="exact", status=Status.PASS, score=1.5, reason_code=None, message="x")


def test_evaluator_message_is_bounded() -> None:
    with pytest.raises(ValidationError, match="at most 500"):
        EvaluatorResult(
            name="exact", status=Status.PASS, score=1.0, reason_code=None, message="x" * 501
        )


def test_evaluator_details_size_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceed"):
        EvaluatorResult(
            name="exact",
            status=Status.PASS,
            score=1.0,
            reason_code=None,
            message="ok",
            details={"blob": "x" * (16 * 1024 + 1)},
        )


def test_evaluator_name_pattern_is_enforced() -> None:
    with pytest.raises(ValidationError, match="pattern"):
        EvaluatorResult(
            name="Exact-Match", status=Status.PASS, score=1.0, reason_code=None, message="ok"
        )


def test_target_ok_must_not_carry_an_error() -> None:
    with pytest.raises(ValidationError, match="OK results carry no error"):
        TargetResult(status="OK", error_code="TARGET_TIMEOUT", error=None, duration_ms=1.0)


def test_target_error_needs_a_target_error_code() -> None:
    with pytest.raises(ValidationError, match="target error code"):
        TargetResult(status="ERROR", error_code="VALUE_MISMATCH", error=None, duration_ms=1.0)


def test_target_duration_must_be_non_negative_and_finite() -> None:
    with pytest.raises(ValidationError, match="duration_ms"):
        TargetResult(status="OK", error_code=None, error=None, duration_ms=-1.0)


def test_error_object_bounds_its_message() -> None:
    with pytest.raises(ValidationError, match="at most 500"):
        ErrorObject(type_name="ValueError", message="x" * 501)


def test_data_models_failure_example_is_accepted() -> None:
    """DATA_MODELS §7 (FAIL example). Hashes are abbreviated in the document, so full-length
    placeholders of the same shape are used here."""
    result = CaseResult(
        run_id="3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
        case_id="refund-001",
        case_sha256="sha256:" + "a" * 64,
        status=Status.FAIL,
        status_reason="exact",
        target=TargetResult(status="OK", error_code=None, error=None, duration_ms=412.337),
        evaluators=(
            EvaluatorResult(
                name="exact",
                status=Status.FAIL,
                score=0.0,
                reason_code="VALUE_MISMATCH",
                message="Output differs from expected value.",
                details={},
            ),
            EvaluatorResult(
                name="has_answer",
                status=Status.PASS,
                score=1.0,
                reason_code=None,
                message="All required paths present.",
                details={"paths": ["answer"]},
            ),
        ),
        input={"question": "Can I get a refund after 30 days?"},
        expected={"answer": "No, refunds are available within 30 days."},
        output={"answer": "Yes, within 45 days."},
        output_sha256="sha256:" + "b" * 64,
    )
    assert result.output == {"answer": "Yes, within 45 days."}


def test_data_models_timeout_example_is_accepted() -> None:
    """DATA_MODELS §7 (ERROR, timeout example)."""
    result = CaseResult(
        run_id="3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
        case_id="slow-017",
        case_sha256="sha256:" + "c" * 64,
        status=Status.ERROR,
        status_reason="TARGET_TIMEOUT",
        target=TIMEOUT,
        evaluators=(
            EvaluatorResult(
                name="exact",
                status=Status.SKIPPED,
                score=None,
                reason_code="TARGET_ERROR",
                message="Target did not produce output.",
                details={},
            ),
        ),
    )
    assert result.status is Status.ERROR
