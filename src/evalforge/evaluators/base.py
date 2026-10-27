# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Evaluator protocol, fingerprints, and the single place where evaluator outcomes are recorded.

TRD-080 to TRD-085. An evaluator judges one case's output. ``apply_evaluator`` is the only function
the runner calls. It enforces the rules that must hold for every evaluator:

- NO_EXPECTED: an evaluator that needs an expected value is skipped without being called when the
  case has none (TRD-083);
- the evaluator receives a private copy of the output, so it cannot change the stored
  output (TRD-081);
- an exception becomes ``EVALUATOR_EXCEPTION`` and a malformed return becomes
  ``EVALUATOR_RESULT_INVALID``. The run continues (TRD-084). ``KeyboardInterrupt`` propagates.

Exception text is not stored, only the exception type. This is stricter than DATA_HANDLING §4
requires, so it cannot leak content that redaction has not yet covered.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Protocol

from evalforge.canon import JSONValue, canonical_sha256
from evalforge.models import Case, EvaluatorResult
from evalforge.status import Status

INTERFACE_VERSION: Final = "1"


class Evaluator(Protocol):
    """Contract every evaluator meets (TRD-080).

    ``evaluate`` may return anything. ``apply_evaluator`` checks that it is an ``EvaluatorResult``.
    """

    @property
    def name(self) -> str: ...

    @property
    def type_name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def requires_expected(self) -> bool: ...

    @property
    def parameters(self) -> Mapping[str, JSONValue]: ...

    def identity(self) -> Mapping[str, str]: ...

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> object: ...


@dataclass(frozen=True, slots=True)
class EvaluatorFingerprint:
    """Identity of an evaluator as recorded in a run manifest (TRD-085; DATA_MODELS §4.1)."""

    name: str
    type_name: str
    version: str
    requires_expected: bool
    parameters: Mapping[str, JSONValue]
    fingerprint: str
    module: str | None = None
    qualname: str | None = None
    source_sha256: str | None = None
    identity: Mapping[str, str] = field(default_factory=dict)


def fingerprint_of(evaluator: Evaluator) -> EvaluatorFingerprint:
    """Hash the evaluator's type, version, parameters, and identity. The name is excluded.

    The name is compared separately, so renaming an evaluator is visible without changing what it
    computes. Custom evaluators add their module, qualified name, and source file hash to the
    identity.
    """
    identity = dict(evaluator.identity())
    payload: dict[str, object] = {
        "type": evaluator.type_name,
        "version": evaluator.version,
        "requires_expected": evaluator.requires_expected,
        "parameters": dict(evaluator.parameters),
        "identity": identity,
    }
    return EvaluatorFingerprint(
        name=evaluator.name,
        type_name=evaluator.type_name,
        version=evaluator.version,
        requires_expected=evaluator.requires_expected,
        parameters=MappingProxyType(dict(evaluator.parameters)),
        fingerprint=canonical_sha256(payload),
        module=identity.get("module"),
        qualname=identity.get("qualname"),
        source_sha256=identity.get("source_sha256"),
        identity=MappingProxyType(identity),
    )


def make_result(
    name: str,
    status: Status,
    reason_code: str | None,
    message: str,
    details: Mapping[str, JSONValue] | None = None,
) -> EvaluatorResult:
    score: float | None
    if status is Status.PASS:
        score = 1.0
    elif status is Status.FAIL:
        score = 0.0
    else:
        score = None
    return EvaluatorResult(
        name=name,
        status=status,
        score=score,
        reason_code=reason_code,
        message=message,
        details=dict(details or {}),
    )


def apply_evaluator(
    evaluator: Evaluator,
    case: Case,
    output: JSONValue,
    duration_ms: float,
) -> EvaluatorResult:
    """Run one evaluator on one case and return the recorded result.

    Never raises for evaluator faults.
    """
    name = evaluator.name
    if evaluator.requires_expected and not case.has_expected():
        return make_result(name, Status.SKIPPED, "NO_EXPECTED", "The case has no expected value.")
    try:
        raw = evaluator.evaluate(case, copy.deepcopy(output), duration_ms)
    except (Exception, SystemExit) as exc:
        return make_result(
            name,
            Status.ERROR,
            "EVALUATOR_EXCEPTION",
            "The evaluator raised an exception.",
            {"exception_type": type(exc).__name__},
        )
    if not isinstance(raw, EvaluatorResult):
        return make_result(
            name,
            Status.ERROR,
            "EVALUATOR_RESULT_INVALID",
            "The evaluator did not return an EvaluatorResult.",
            {"returned_type": type(raw).__name__},
        )
    if raw.name != name:
        return make_result(
            name,
            Status.ERROR,
            "EVALUATOR_RESULT_INVALID",
            "The evaluator result carries a different name.",
        )
    return raw


__all__ = [
    "INTERFACE_VERSION",
    "Evaluator",
    "EvaluatorFingerprint",
    "apply_evaluator",
    "fingerprint_of",
]
