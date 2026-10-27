# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Frozen data models with validation (DATA_MODELS §2, §7, §8; TRD §4, §5, §7).

Every model validates itself on construction and raises ``ValidationError`` with a field name
when it is given invalid data. Loaders convert these into registered error codes.

Absence and JSON ``null`` are distinct: ``ABSENT`` means the field was not present.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from evalforge import limits
from evalforge.canon import (
    JSONValue,
    JsonValueError,
    canonical_json,
    canonical_sha256,
    check_json_value,
)
from evalforge.errors import SchemaVersionError, reason_status
from evalforge.status import Status

SCHEMA_VERSION: Final = "1.0"

CASE_ID_RE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
EVALUATOR_NAME_RE: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")
HASH_RE: Final = re.compile(r"sha256:[0-9a-f]{64}")
SCHEMA_RE: Final = re.compile(r"([0-9]+)\.([0-9]+)")

TARGET_ERROR_CODES: Final = frozenset(
    {"TARGET_EXCEPTION", "TARGET_TIMEOUT", "TARGET_OUTPUT_INVALID", "TARGET_CRASHED"}
)


class ValidationError(ValueError):
    """A model received invalid data. ``field_name`` names the offending field."""

    def __init__(self, message: str, *, field_name: str | None = None) -> None:
        text = message if field_name is None else f"{field_name}: {message}"
        super().__init__(text)
        self.field_name = field_name


class _Absent:
    """Sentinel type for a field that was not present in the input."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "ABSENT"


ABSENT: Final = _Absent()


def check_schema_version(version: object) -> None:
    """Accept ``1.x`` artifacts only (PRD-NF-009). Other majors raise ``SchemaVersionError``."""
    if not isinstance(version, str):
        raise ValidationError(
            "must be a string of the form MAJOR.MINOR", field_name="schema_version"
        )
    match = SCHEMA_RE.fullmatch(version)
    if match is None:
        raise ValidationError(
            "must be a string of the form MAJOR.MINOR", field_name="schema_version"
        )
    if int(match.group(1)) != 1:
        raise SchemaVersionError(
            "SCHEMA_VERSION_UNSUPPORTED",
            f"schema_version {version!r} is not supported; this release reads major version 1.",
        )


def _require_json(value: object, field_name: str) -> None:
    try:
        check_json_value(value)
    except JsonValueError as exc:
        raise ValidationError(str(exc), field_name=field_name) from exc


def _require_uuid4(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValidationError("must be a UUIDv4 string", field_name=field_name)
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValidationError("must be a UUIDv4 string", field_name=field_name) from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValidationError("must be a canonical UUIDv4 string", field_name=field_name)


def _require_hash(value: object, field_name: str) -> None:
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        raise ValidationError(
            "must be 'sha256:' followed by 64 lowercase hex digits", field_name=field_name
        )


def _require_text(value: object, field_name: str, *, max_chars: int) -> None:
    if not isinstance(value, str):
        raise ValidationError("must be a string", field_name=field_name)
    if len(value) > max_chars:
        raise ValidationError(f"must be at most {max_chars} characters", field_name=field_name)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class Case:
    """One evaluation case (DATA_MODELS §2)."""

    id: str
    input: JSONValue
    expected: JSONValue | _Absent = ABSENT
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or CASE_ID_RE.fullmatch(self.id) is None:
            raise ValidationError(
                "must be 1 to 128 characters: a letter or digit, then letters, digits, "
                "'.', '_', or '-'",
                field_name="id",
            )
        _require_json(self.input, "input")
        if not isinstance(self.expected, _Absent):
            _require_json(self.expected, "expected")
        if not isinstance(self.metadata, Mapping):
            raise ValidationError("must be an object", field_name="metadata")
        for key, item in self.metadata.items():
            if not isinstance(key, str):
                raise ValidationError("keys must be strings", field_name="metadata")
            _require_json(item, f"metadata.{key}")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

        tags = tuple(self.tags)
        if len(tags) > limits.MAX_TAGS:
            raise ValidationError(f"at most {limits.MAX_TAGS} tags are allowed", field_name="tags")
        for tag in tags:
            if not isinstance(tag, str) or not 1 <= len(tag) <= limits.MAX_TAG_CHARS:
                raise ValidationError(
                    f"each tag must be a string of 1 to {limits.MAX_TAG_CHARS} characters",
                    field_name="tags",
                )
        if len(set(tags)) != len(tags):
            raise ValidationError("tags must be unique", field_name="tags")
        object.__setattr__(self, "tags", tags)

    def has_expected(self) -> bool:
        return not isinstance(self.expected, _Absent)

    def canonical_content(self) -> dict[str, object]:
        """Content that identifies a case for comparison (TRD §4.4; ARTIFACT_INTEGRITY §2)."""
        content: dict[str, object] = {
            "id": self.id,
            "input": self.input,
            "metadata": dict(self.metadata),
            "tags": sorted(self.tags),
        }
        if self.has_expected():
            content["expected"] = self.expected
        return content

    def case_sha256(self) -> str:
        return canonical_sha256(self.canonical_content())


@dataclass(frozen=True, slots=True)
class ErrorObject:
    """Exception type and truncated message (DATA_MODELS §7; DATA_HANDLING §4)."""

    type_name: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.type_name, str) or not 1 <= len(self.type_name) <= 100:
            raise ValidationError("must be 1 to 100 characters", field_name="type_name")
        _require_text(self.message, "message", max_chars=limits.MAX_ERROR_MESSAGE_CHARS)


@dataclass(frozen=True, slots=True)
class TargetResult:
    """Outcome of one target call (DATA_MODELS §7)."""

    status: Literal["OK", "ERROR", "NOT_RUN"]
    error_code: str | None
    error: ErrorObject | None
    duration_ms: float

    def __post_init__(self) -> None:
        if self.status not in ("OK", "ERROR", "NOT_RUN"):
            raise ValidationError("must be 'OK', 'ERROR', or 'NOT_RUN'", field_name="status")
        if not _is_number(self.duration_ms) or not float(self.duration_ms) >= 0.0:
            raise ValidationError("must be a non-negative finite number", field_name="duration_ms")
        if self.status == "NOT_RUN":
            # Decision D-6: the target was never called (case excluded by selection).
            if self.error_code is not None or self.error is not None or self.duration_ms != 0.0:
                raise ValidationError(
                    "NOT_RUN results carry no error and no duration", field_name="status"
                )
        elif self.status == "OK":
            if self.error_code is not None or self.error is not None:
                raise ValidationError("OK results carry no error", field_name="status")
        else:
            if self.error_code not in TARGET_ERROR_CODES:
                raise ValidationError(
                    "ERROR results need a target error code (TARGET_EXCEPTION, TARGET_TIMEOUT, "
                    "TARGET_OUTPUT_INVALID, or TARGET_CRASHED)",
                    field_name="error_code",
                )


@dataclass(frozen=True, slots=True)
class EvaluatorResult:
    """Outcome of one evaluator on one case (DATA_MODELS §8)."""

    name: str
    status: Status
    score: float | None
    reason_code: str | None
    message: str
    details: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or EVALUATOR_NAME_RE.fullmatch(self.name) is None:
            raise ValidationError("evaluator name pattern is invalid", field_name="name")
        if not isinstance(self.status, Status):
            raise ValidationError("must be a Status value", field_name="status")
        if self.score is not None:
            if not _is_number(self.score) or not 0.0 <= float(self.score) <= 1.0:
                raise ValidationError("must be a number in [0, 1] or null", field_name="score")
        _require_text(self.message, "message", max_chars=limits.MAX_EVALUATOR_MESSAGE_CHARS)

        if self.status is Status.PASS:
            if self.reason_code is not None:
                raise ValidationError("PASS carries no reason code", field_name="reason_code")
        else:
            if not isinstance(self.reason_code, str):
                raise ValidationError(
                    f"{self.status} requires a reason code", field_name="reason_code"
                )
            try:
                expected_status = reason_status(self.reason_code)
            except ValueError as exc:
                raise ValidationError(str(exc), field_name="reason_code") from exc
            if expected_status is not self.status:
                raise ValidationError(
                    f"reason {self.reason_code} belongs to {expected_status}, not {self.status}",
                    field_name="reason_code",
                )

        if not isinstance(self.details, Mapping):
            raise ValidationError("must be an object", field_name="details")
        _require_json(dict(self.details), "details")
        size = len(canonical_json(dict(self.details)).encode("utf-8"))
        if size > limits.MAX_EVALUATOR_DETAILS_BYTES:
            raise ValidationError(
                f"serialised details exceed {limits.MAX_EVALUATOR_DETAILS_BYTES} bytes",
                field_name="details",
            )
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


def aggregate_case_status(
    target: TargetResult,
    evaluators: Sequence[EvaluatorResult],
) -> tuple[Status, str | None]:
    """Apply the case-status rules of EVALUATION_METHODOLOGY §3.3, in order.

    1. Target ERROR: the case is ERROR with the target's code.
    2. No evaluators configured: SKIPPED with NO_EVALUATORS.
    3. Any evaluator ERROR: ERROR with that evaluator's code.
    4. Any evaluator INCONCLUSIVE: INCONCLUSIVE with its code.
    5. Any evaluator FAIL: FAIL, recorded as the first failing evaluator's name.
    6. Every evaluator SKIPPED: SKIPPED with the first skip reason.
    7. Otherwise: PASS.
    """
    if target.status == "NOT_RUN":
        return Status.SKIPPED, "USER_FILTER"
    if target.status == "ERROR":
        return Status.ERROR, target.error_code
    if not evaluators:
        return Status.SKIPPED, "NO_EVALUATORS"
    for item in evaluators:
        if item.status is Status.ERROR:
            return Status.ERROR, item.reason_code
    for item in evaluators:
        if item.status is Status.INCONCLUSIVE:
            return Status.INCONCLUSIVE, item.reason_code
    for item in evaluators:
        if item.status is Status.FAIL:
            return Status.FAIL, item.name
    if all(item.status is Status.SKIPPED for item in evaluators):
        return Status.SKIPPED, next(item.reason_code for item in evaluators)
    return Status.PASS, None


@dataclass(frozen=True, slots=True)
class CaseResult:
    """Recorded result of one case (DATA_MODELS §7). Written once and never edited."""

    run_id: str
    case_id: str
    case_sha256: str
    status: Status
    status_reason: str | None
    target: TargetResult
    evaluators: tuple[EvaluatorResult, ...]
    input: JSONValue | _Absent = ABSENT
    expected: JSONValue | _Absent = ABSENT
    output: JSONValue | _Absent = ABSENT
    input_sha256: str | None = None
    expected_sha256: str | None = None
    output_sha256: str | None = None
    redactions: int = 0
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        check_schema_version(self.schema_version)
        _require_uuid4(self.run_id, "run_id")
        if not isinstance(self.case_id, str) or CASE_ID_RE.fullmatch(self.case_id) is None:
            raise ValidationError("case identifier pattern is invalid", field_name="case_id")
        _require_hash(self.case_sha256, "case_sha256")
        for name in ("input_sha256", "expected_sha256", "output_sha256"):
            value = getattr(self, name)
            if value is not None:
                _require_hash(value, name)
        if (
            not isinstance(self.redactions, int)
            or isinstance(self.redactions, bool)
            or self.redactions < 0
        ):
            raise ValidationError("must be a non-negative integer", field_name="redactions")
        for name in ("input", "expected", "output"):
            value = getattr(self, name)
            if not isinstance(value, _Absent):
                _require_json(value, name)

        evaluators = tuple(self.evaluators)
        names = [item.name for item in evaluators]
        if len(set(names)) != len(names):
            raise ValidationError(
                "evaluator names must be unique within a case", field_name="evaluators"
            )
        object.__setattr__(self, "evaluators", evaluators)

        if self.target.status == "NOT_RUN" and evaluators:
            raise ValidationError(
                "a case that was not run has no evaluator results", field_name="evaluators"
            )
        if self.target.status == "ERROR":
            for item in evaluators:
                if item.status is not Status.SKIPPED or item.reason_code != "TARGET_ERROR":
                    raise ValidationError(
                        "when the target failed, every evaluator must be SKIPPED with TARGET_ERROR",
                        field_name="evaluators",
                    )
        elif any(item.reason_code == "TARGET_ERROR" for item in evaluators):
            raise ValidationError(
                "TARGET_ERROR is only valid when the target failed", field_name="evaluators"
            )

        expected_status, expected_reason = aggregate_case_status(self.target, evaluators)
        if self.status is not expected_status or self.status_reason != expected_reason:
            raise ValidationError(
                f"recorded {self.status} / {self.status_reason!r} is inconsistent with the "
                f"evaluator results; the rules require {expected_status} / {expected_reason!r}",
                field_name="status",
            )
