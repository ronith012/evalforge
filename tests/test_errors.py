# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Registry and error-type checks (DATA_MODELS §9; TRD §9.2)."""

from __future__ import annotations

import pytest

from evalforge.errors import (
    ERROR_CODES,
    FINDING_CODES,
    REASON_CODES,
    ConfigError,
    ErrorInfo,
    EvalForgeError,
    reason_status,
    truncate,
)
from evalforge.status import Status

# Hand-written from DATA_MODELS §9.1: every reason code and its status.
EXPECTED_REASON_STATUS = {
    "VALUE_MISMATCH": Status.FAIL,
    "OUTPUT_NOT_TEXT": Status.FAIL,
    "NOT_JSON": Status.FAIL,
    "JSON_TYPE_MISMATCH": Status.FAIL,
    "REQUIRED_FIELD_MISSING": Status.FAIL,
    "RULE_CONTAINS_MISSING": Status.FAIL,
    "RULE_NOT_CONTAINS_PRESENT": Status.FAIL,
    "RULE_REGEX_NO_MATCH": Status.FAIL,
    "RULE_LENGTH_OUT_OF_BOUNDS": Status.FAIL,
    "LATENCY_EXCEEDED": Status.FAIL,
    "CUSTOM_FAIL": Status.FAIL,
    "CUSTOM_UNCERTAIN": Status.INCONCLUSIVE,
    "TARGET_EXCEPTION": Status.ERROR,
    "TARGET_TIMEOUT": Status.ERROR,
    "TARGET_CRASHED": Status.ERROR,
    "TARGET_OUTPUT_INVALID": Status.ERROR,
    "EVALUATOR_EXCEPTION": Status.ERROR,
    "EVALUATOR_RESULT_INVALID": Status.ERROR,
    "NO_EXPECTED": Status.SKIPPED,
    "TARGET_ERROR": Status.SKIPPED,
    "NO_EVALUATORS": Status.SKIPPED,
    "USER_FILTER": Status.SKIPPED,
    "NOT_APPLICABLE": Status.SKIPPED,
    "NOT_EXECUTED": Status.SKIPPED,
}


def test_reason_registry_matches_the_hand_written_table() -> None:
    assert {code: info.status for code, info in REASON_CODES.items()} == EXPECTED_REASON_STATUS


def test_every_reason_code_has_a_status_and_no_exit_code() -> None:
    for info in REASON_CODES.values():
        assert info.status is not None
        assert info.exit_code is None


def test_error_codes_have_exit_codes_in_the_documented_range() -> None:
    for info in ERROR_CODES.values():
        assert info.status is None
        assert info.exit_code in {2, 3, 4, 5}


def test_reason_and_error_registries_do_not_overlap() -> None:
    assert set(REASON_CODES).isdisjoint(ERROR_CODES)


def test_finding_codes_overlap_error_codes_only_where_the_specification_says() -> None:
    # DATASET_CHANGED and EVALUATOR_CHANGED are both a refusal error (exit 5) and a warning finding
    # when a comparison is overridden (DATA_MODELS §9.2; TRD §9.2). No other overlap is allowed.
    assert set(FINDING_CODES) & set(ERROR_CODES) == {"DATASET_CHANGED", "EVALUATOR_CHANGED"}


def test_reason_status_returns_the_registered_status() -> None:
    assert reason_status("TARGET_TIMEOUT") is Status.ERROR


def test_unregistered_reason_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="unregistered reason code"):
        reason_status("NOT_A_CODE")


def test_evalforge_error_rejects_unregistered_codes() -> None:
    with pytest.raises(ValueError, match="unregistered error code"):
        EvalForgeError("NOT_A_CODE", "message")


def test_evalforge_error_truncates_long_messages() -> None:
    error = ConfigError("CONFIG_INVALID", "x" * 600)
    assert len(error.message) == 500
    assert error.message.endswith("...")


def test_error_info_truncates_and_checks_code() -> None:
    info = ErrorInfo(code="DATASET_INVALID", message="y" * 600, line=3)
    assert len(info.message) == 500
    with pytest.raises(ValueError, match="unregistered error code"):
        ErrorInfo(code="NOT_A_CODE", message="m")


def test_truncate_keeps_short_text_and_rejects_tiny_limits() -> None:
    assert truncate("short") == "short"
    with pytest.raises(ValueError):
        truncate("abc", limit=3)
