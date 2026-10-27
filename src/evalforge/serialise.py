# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""JSON encoding and decoding of persisted records (DATA_MODELS §7–§8; CO-2).

Decoding re-runs every model validation. A stored record that is malformed, has an unknown reason
code, or contradicts its own evaluator results is rejected, never silently repaired.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

from evalforge.canon import JSONValue
from evalforge.evaluators.base import EvaluatorFingerprint
from evalforge.models import (
    ABSENT,
    CaseResult,
    ErrorObject,
    EvaluatorResult,
    TargetResult,
    ValidationError,
    _Absent,
)
from evalforge.status import Status


def _require(data: Mapping[str, object], key: str, kind: type | tuple[type, ...]) -> object:
    if key not in data:
        raise ValidationError(f"missing required field {key!r}", field_name=key)
    value = data[key]
    if not isinstance(value, kind):
        raise ValidationError(f"field {key!r} has the wrong type", field_name=key)
    return value


def _optional(data: Mapping[str, object], key: str, kind: type | tuple[type, ...]) -> object | None:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, kind):
        raise ValidationError(f"field {key!r} has the wrong type", field_name=key)
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError("must be a number")
    return float(value)


def error_to_dict(error: ErrorObject) -> dict[str, object]:
    return {"type": error.type_name, "message": error.message}


def error_from_dict(data: Mapping[str, object]) -> ErrorObject:
    return ErrorObject(
        type_name=cast(str, _require(data, "type", str)),
        message=cast(str, _require(data, "message", str)),
    )


def target_to_dict(target: TargetResult) -> dict[str, object]:
    return {
        "status": target.status,
        "error_code": target.error_code,
        "error": None if target.error is None else error_to_dict(target.error),
        "duration_ms": target.duration_ms,
    }


def target_from_dict(data: Mapping[str, object]) -> TargetResult:
    status = cast(str, _require(data, "status", str))
    error_data = _optional(data, "error", dict)
    error = None if error_data is None else error_from_dict(cast(Mapping[str, object], error_data))
    return TargetResult(
        status=cast(Literal["OK", "ERROR", "NOT_RUN"], status),
        error_code=cast("str | None", _optional(data, "error_code", str)),
        error=error,
        duration_ms=_number(_require(data, "duration_ms", (int, float))),
    )


def evaluator_to_dict(result: EvaluatorResult) -> dict[str, object]:
    return {
        "name": result.name,
        "status": result.status.value,
        "score": result.score,
        "reason_code": result.reason_code,
        "message": result.message,
        "details": dict(result.details),
    }


def evaluator_from_dict(data: Mapping[str, object]) -> EvaluatorResult:
    details = _optional(data, "details", dict)
    score = _optional(data, "score", (int, float))
    return EvaluatorResult(
        name=cast(str, _require(data, "name", str)),
        status=Status(cast(str, _require(data, "status", str))),
        score=None if score is None else _number(score),
        reason_code=cast("str | None", _optional(data, "reason_code", str)),
        message=cast(str, _require(data, "message", str)),
        details=cast("dict[str, JSONValue]", details if details is not None else {}),
    )


def fingerprint_to_dict(fingerprint: EvaluatorFingerprint) -> dict[str, object]:
    return {
        "name": fingerprint.name,
        "type": fingerprint.type_name,
        "version": fingerprint.version,
        "requires_expected": fingerprint.requires_expected,
        "parameters": dict(fingerprint.parameters),
        "fingerprint": fingerprint.fingerprint,
        "module": fingerprint.module,
        "qualname": fingerprint.qualname,
        "source_sha256": fingerprint.source_sha256,
    }


def case_result_to_dict(result: CaseResult) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": result.schema_version,
        "run_id": result.run_id,
        "case_id": result.case_id,
        "case_sha256": result.case_sha256,
        "status": result.status.value,
        "status_reason": result.status_reason,
        "target": target_to_dict(result.target),
        "evaluators": [evaluator_to_dict(item) for item in result.evaluators],
        "input_sha256": result.input_sha256,
        "expected_sha256": result.expected_sha256,
        "output_sha256": result.output_sha256,
        "redactions": result.redactions,
    }
    for name in ("input", "expected", "output"):
        value = getattr(result, name)
        if not isinstance(value, _Absent):
            record[name] = value
    return record


def case_result_from_dict(data: Mapping[str, object]) -> CaseResult:
    def present(key: str) -> JSONValue | _Absent:
        return cast(JSONValue, data[key]) if key in data else ABSENT

    evaluators = _require(data, "evaluators", list)
    target = _require(data, "target", dict)
    return CaseResult(
        run_id=cast(str, _require(data, "run_id", str)),
        case_id=cast(str, _require(data, "case_id", str)),
        case_sha256=cast(str, _require(data, "case_sha256", str)),
        status=Status(cast(str, _require(data, "status", str))),
        status_reason=cast("str | None", _optional(data, "status_reason", str)),
        target=target_from_dict(cast(Mapping[str, object], target)),
        evaluators=tuple(
            evaluator_from_dict(cast(Mapping[str, object], item))
            for item in cast(list[object], evaluators)
        ),
        input=present("input"),
        expected=present("expected"),
        output=present("output"),
        input_sha256=cast("str | None", _optional(data, "input_sha256", str)),
        expected_sha256=cast("str | None", _optional(data, "expected_sha256", str)),
        output_sha256=cast("str | None", _optional(data, "output_sha256", str)),
        redactions=cast(int, _require(data, "redactions", int)),
        schema_version=cast(str, _require(data, "schema_version", str)),
    )
