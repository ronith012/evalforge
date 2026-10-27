# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""The six built-in deterministic evaluators (TRD §5.5; EVALUATION_METHODOLOGY §4).

Every built-in is pure and returns PASS, FAIL, ERROR, or SKIPPED. None returns INCONCLUSIVE
(TST-EV-029). Messages are fixed text and carry no case content (DATA_HANDLING §3.3). Details hold
only structural facts: rule names, paths, and limits.

Limitations, which the documentation states and the tests assert:

- none of these judges meaning; a correct answer worded differently FAILs;
- ``casefold`` is not locale-aware;
- code fences around JSON are not JSON (a real format violation, not a bug).
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar, Final, cast

from evalforge.canon import JSONValue, canonical_json
from evalforge.evaluators.base import make_result
from evalforge.models import Case, EvaluatorResult
from evalforge.status import Status

BUILTIN_VERSION: Final = "1.0"
REGEX_INPUT_LIMIT_BYTES: Final = 1024 * 1024  # TRD-091; decision D-5 in EXECUTION_PLAN §2.6


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-finite number {name}")


def _parse_json_text(text: str) -> JSONValue | None:
    """Parse text as JSON. Returns ``None`` on any failure, including deep nesting."""
    try:
        return cast(
            JSONValue,
            json.loads(text, parse_constant=_reject_constant),
        )
    except (ValueError, RecursionError):
        return None


def _json_type_name(value: JSONValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


class _Builtin:
    """Shared behaviour: built-ins have no extra identity beyond their type and parameters."""

    __slots__ = ()
    version: ClassVar[str] = BUILTIN_VERSION

    def identity(self) -> Mapping[str, str]:
        return {}


@dataclass(frozen=True, slots=True)
class ExactMatch(_Builtin):
    """Canonical JSON of the output equals canonical JSON of the expected value."""

    name: str
    type_name: ClassVar[str] = "exact_match"
    requires_expected: ClassVar[bool] = True

    @property
    def parameters(self) -> Mapping[str, JSONValue]:
        return MappingProxyType({})

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        expected = cast(JSONValue, case.expected)
        if canonical_json(output) == canonical_json(expected):
            return make_result(self.name, Status.PASS, None, "Output equals the expected value.")
        return make_result(
            self.name, Status.FAIL, "VALUE_MISMATCH", "Output differs from the expected value."
        )


@dataclass(frozen=True, slots=True)
class NormalizedText(_Builtin):
    """Text equality after Unicode NFC, optional case folding, and whitespace normalisation."""

    name: str
    nfc: bool = True
    casefold: bool = True
    collapse_whitespace: bool = True
    strip: bool = True
    type_name: ClassVar[str] = "normalized_text"
    requires_expected: ClassVar[bool] = True

    @property
    def parameters(self) -> Mapping[str, JSONValue]:
        return MappingProxyType(
            {
                "nfc": self.nfc,
                "casefold": self.casefold,
                "collapse_whitespace": self.collapse_whitespace,
                "strip": self.strip,
            }
        )

    def _normalise(self, text: str) -> str:
        if self.nfc:
            text = unicodedata.normalize("NFC", text)
        if self.casefold:
            text = text.casefold()
        if self.collapse_whitespace:
            return " ".join(text.split())
        if self.strip:
            return text.strip()
        return text

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        expected = cast(JSONValue, case.expected)
        if not isinstance(output, str):
            return make_result(self.name, Status.FAIL, "OUTPUT_NOT_TEXT", "Output is not text.")
        if not isinstance(expected, str):
            return make_result(
                self.name, Status.SKIPPED, "NOT_APPLICABLE", "The expected value is not text."
            )
        if self._normalise(output) == self._normalise(expected):
            return make_result(
                self.name, Status.PASS, None, "Normalised text equals the expected text."
            )
        return make_result(
            self.name, Status.FAIL, "VALUE_MISMATCH", "Output differs from the expected value."
        )


@dataclass(frozen=True, slots=True)
class JsonStructure(_Builtin):
    """Output parses as JSON, with an optional check on its top-level type."""

    name: str
    top_level_type: str | None = None
    type_name: ClassVar[str] = "json_structure"
    requires_expected: ClassVar[bool] = False

    @property
    def parameters(self) -> Mapping[str, JSONValue]:
        if self.top_level_type is None:
            return MappingProxyType({})
        return MappingProxyType({"top_level_type": self.top_level_type})

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        value: JSONValue | None = output
        if isinstance(output, str):
            value = _parse_json_text(output)
            if value is None:
                return make_result(self.name, Status.FAIL, "NOT_JSON", "Output is not valid JSON.")
        if self.top_level_type is not None:
            actual = _json_type_name(value)
            if actual != self.top_level_type:
                return make_result(
                    self.name,
                    Status.FAIL,
                    "JSON_TYPE_MISMATCH",
                    "The top-level JSON type differs from the configured type.",
                    {"expected_type": self.top_level_type, "actual_type": actual},
                )
        return make_result(self.name, Status.PASS, None, "Output has the expected JSON structure.")


_MISSING: Final = object()


def _lookup(document: JSONValue, dotted: str) -> object:
    current: object = document
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


@dataclass(frozen=True, slots=True)
class RequiredFields(_Builtin):
    """Each dotted path resolves to a non-null value in the parsed output."""

    name: str
    paths: tuple[str, ...]
    type_name: ClassVar[str] = "required_fields"
    requires_expected: ClassVar[bool] = False

    @property
    def parameters(self) -> Mapping[str, JSONValue]:
        return MappingProxyType({"paths": list(self.paths)})

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        document: JSONValue | None = output
        if isinstance(output, str):
            document = _parse_json_text(output)
            if document is None:
                return make_result(self.name, Status.FAIL, "NOT_JSON", "Output is not valid JSON.")
        missing = []
        for path in self.paths:
            found = _lookup(document, path)
            if found is _MISSING or found is None:
                missing.append(path)
        if missing:
            return make_result(
                self.name,
                Status.FAIL,
                "REQUIRED_FIELD_MISSING",
                "A required field is absent or null.",
                {"missing": list(missing)},
            )
        return make_result(self.name, Status.PASS, None, "All required fields are present.")


@dataclass(frozen=True, slots=True)
class RuleBased(_Builtin):
    """Contains, not-contains, regex, and length rules. The first failing rule is reported.

    Checks run in this fixed order: contains, not-contains, regex, length.
    """

    name: str
    contains: tuple[str, ...] = ()
    not_contains: tuple[str, ...] = ()
    regex: tuple[str, ...] = ()
    min_length: int | None = None
    max_length: int | None = None
    compiled: tuple[re.Pattern[str], ...] = field(default=(), init=False, repr=False, compare=False)
    type_name: ClassVar[str] = "rule_based"
    requires_expected: ClassVar[bool] = False

    def __post_init__(self) -> None:
        patterns = tuple(re.compile(pattern) for pattern in self.regex)
        object.__setattr__(self, "compiled", patterns)

    @property
    def parameters(self) -> Mapping[str, JSONValue]:
        values: dict[str, JSONValue] = {}
        if self.contains:
            values["contains"] = list(self.contains)
        if self.not_contains:
            values["not_contains"] = list(self.not_contains)
        if self.regex:
            values["regex"] = list(self.regex)
        if self.min_length is not None:
            values["min_length"] = self.min_length
        if self.max_length is not None:
            values["max_length"] = self.max_length
        return MappingProxyType(values)

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        if not isinstance(output, str):
            return make_result(self.name, Status.FAIL, "OUTPUT_NOT_TEXT", "Output is not text.")
        if self.regex and len(output.encode("utf-8")) > REGEX_INPUT_LIMIT_BYTES:
            # Decision D-5: a resource limit is an error, never a quality FAIL.
            return make_result(
                self.name,
                Status.ERROR,
                "EVALUATOR_EXCEPTION",
                "The output is too long for the regular-expression rule.",
                {"input_too_long": True},
            )
        for needle in self.contains:
            if needle not in output:
                return make_result(
                    self.name,
                    Status.FAIL,
                    "RULE_CONTAINS_MISSING",
                    "A required substring is absent.",
                    {"rule": "contains"},
                )
        for needle in self.not_contains:
            if needle in output:
                return make_result(
                    self.name,
                    Status.FAIL,
                    "RULE_NOT_CONTAINS_PRESENT",
                    "A forbidden substring is present.",
                    {"rule": "not_contains"},
                )
        for pattern in self.compiled:
            if pattern.search(output) is None:
                return make_result(
                    self.name,
                    Status.FAIL,
                    "RULE_REGEX_NO_MATCH",
                    "A regular expression did not match.",
                    {"rule": "regex"},
                )
        length = len(output)
        if (self.min_length is not None and length < self.min_length) or (
            self.max_length is not None and length > self.max_length
        ):
            return make_result(
                self.name,
                Status.FAIL,
                "RULE_LENGTH_OUT_OF_BOUNDS",
                "Output length is outside the configured bounds.",
                {"rule": "length"},
            )
        return make_result(self.name, Status.PASS, None, "All rules pass.")


@dataclass(frozen=True, slots=True)
class Latency(_Builtin):
    """The target's measured duration is at most ``max_ms`` milliseconds."""

    name: str
    max_ms: float
    type_name: ClassVar[str] = "latency"
    requires_expected: ClassVar[bool] = False

    @property
    def parameters(self) -> Mapping[str, JSONValue]:
        return MappingProxyType({"max_ms": float(self.max_ms)})

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
        if duration_ms <= self.max_ms:
            return make_result(self.name, Status.PASS, None, "Duration is within the limit.")
        return make_result(
            self.name,
            Status.FAIL,
            "LATENCY_EXCEEDED",
            "Duration is above the configured maximum.",
            {"duration_ms": round(duration_ms, 3), "max_ms": float(self.max_ms)},
        )


BUILTIN_CLASSES: Final[Sequence[type]] = (
    ExactMatch,
    NormalizedText,
    JsonStructure,
    RequiredFields,
    RuleBased,
    Latency,
)
