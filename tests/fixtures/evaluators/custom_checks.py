# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Synthetic custom evaluators used only by the test suite."""

from __future__ import annotations

from evalforge.canon import JSONValue
from evalforge.models import Case, EvaluatorResult
from evalforge.status import Status


class RefundRule:
    interface_version = "1"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        if isinstance(output, dict) and "45 days" in str(output.get("answer", "")):
            return EvaluatorResult(
                name="x",
                status=Status.FAIL,
                score=0.0,
                reason_code="CUSTOM_FAIL",
                message="Refund window stated as 45 days.",
            )
        return EvaluatorResult(
            name="x", status=Status.PASS, score=1.0, reason_code=None, message="ok"
        )


class Uncertain:
    interface_version = "1"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        return EvaluatorResult(
            name="x",
            status=Status.INCONCLUSIVE,
            score=None,
            reason_code="CUSTOM_UNCERTAIN",
            message="Cannot decide.",
        )


class Raises:
    interface_version = "1"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        raise RuntimeError("evaluator failure")


class ReturnsDict:
    interface_version = "1"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> object:
        return {"status": "PASS"}


class MutatesOutput:
    interface_version = "1"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        if isinstance(output, dict):
            output["changed"] = True
        return EvaluatorResult(
            name="x", status=Status.PASS, score=1.0, reason_code=None, message="ok"
        )


class NoInterfaceVersion:
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        return EvaluatorResult(
            name="x", status=Status.PASS, score=1.0, reason_code=None, message="ok"
        )


class WrongInterfaceVersion:
    interface_version = "2"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        return EvaluatorResult(
            name="x", status=Status.PASS, score=1.0, reason_code=None, message="ok"
        )


class NeedsArguments:
    interface_version = "1"
    version = "1.0"
    requires_expected = False

    def __init__(self, required: int) -> None:
        self.required = required

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        return EvaluatorResult(
            name="x", status=Status.PASS, score=1.0, reason_code=None, message="ok"
        )


not_a_class = 42
