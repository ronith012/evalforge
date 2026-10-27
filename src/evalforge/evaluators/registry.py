# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Maps configured evaluator types to evaluator objects (DATA_MODELS §4.1; TRD §5.4).

The configuration model has already checked parameters (Milestone 2). The registry checks again,
because it is also the entry point for code that builds evaluators without a configuration file.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final, cast

from evalforge.canon import JSONValue
from evalforge.config import EvaluatorSettings
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import Evaluator
from evalforge.evaluators.builtin import (
    ExactMatch,
    JsonStructure,
    Latency,
    NormalizedText,
    RequiredFields,
    RuleBased,
)
from evalforge.evaluators.custom import load_custom_evaluator


def _text(params: dict[str, JSONValue], key: str) -> str | None:
    value = params.get(key)
    return value if isinstance(value, str) else None


def _flag(params: dict[str, JSONValue], key: str, default: bool) -> bool:
    value = params.get(key, default)
    return value if isinstance(value, bool) else default


def _strings(params: dict[str, JSONValue], key: str) -> tuple[str, ...]:
    value = params.get(key, [])
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _integer(params: dict[str, JSONValue], key: str) -> int | None:
    value = params.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _number(params: dict[str, JSONValue], key: str) -> float | None:
    value = params.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _exact(name: str, params: dict[str, JSONValue]) -> Evaluator:
    return ExactMatch(name=name)


def _normalized(name: str, params: dict[str, JSONValue]) -> Evaluator:
    return NormalizedText(
        name=name,
        nfc=_flag(params, "nfc", True),
        casefold=_flag(params, "casefold", True),
        collapse_whitespace=_flag(params, "collapse_whitespace", True),
        strip=_flag(params, "strip", True),
    )


def _json(name: str, params: dict[str, JSONValue]) -> Evaluator:
    return JsonStructure(name=name, top_level_type=_text(params, "top_level_type"))


def _required(name: str, params: dict[str, JSONValue]) -> Evaluator:
    paths = _strings(params, "paths")
    if not paths:
        raise EvalForgeError(
            "EVALUATOR_LOAD_FAILED", f"evaluator {name!r} needs at least one path."
        )
    return RequiredFields(name=name, paths=paths)


def _rule(name: str, params: dict[str, JSONValue]) -> Evaluator:
    return RuleBased(
        name=name,
        contains=_strings(params, "contains"),
        not_contains=_strings(params, "not_contains"),
        regex=_strings(params, "regex"),
        min_length=_integer(params, "min_length"),
        max_length=_integer(params, "max_length"),
    )


def _latency(name: str, params: dict[str, JSONValue]) -> Evaluator:
    max_ms = _number(params, "max_ms")
    if max_ms is None or max_ms <= 0:
        raise EvalForgeError(
            "EVALUATOR_LOAD_FAILED", f"evaluator {name!r} needs a positive max_ms."
        )
    return Latency(name=name, max_ms=max_ms)


_BUILTIN_FACTORIES: Final[dict[str, Callable[[str, dict[str, JSONValue]], Evaluator]]] = {
    "exact_match": _exact,
    "normalized_text": _normalized,
    "json_structure": _json,
    "required_fields": _required,
    "rule_based": _rule,
    "latency": _latency,
}


def build_evaluator(settings: EvaluatorSettings) -> Evaluator:
    """Build one evaluator from its configuration. Unknown types raise ``EVALUATOR_LOAD_FAILED``."""
    params = dict(settings.params)
    if settings.type_name == "custom":
        reference = _text(params, "callable")
        if reference is None:
            raise EvalForgeError(
                "EVALUATOR_LOAD_FAILED", f"evaluator {settings.name!r} needs a callable."
            )
        return cast(Evaluator, load_custom_evaluator(reference, name=settings.name))
    factory = _BUILTIN_FACTORIES.get(settings.type_name)
    if factory is None:
        raise EvalForgeError(
            "EVALUATOR_LOAD_FAILED",
            f"unknown evaluator type {settings.type_name!r} for evaluator {settings.name!r}.",
        )
    return factory(settings.name, params)


def build_evaluators(settings: Sequence[EvaluatorSettings]) -> tuple[Evaluator, ...]:
    """Build evaluators in configured order."""
    return tuple(build_evaluator(item) for item in settings)
