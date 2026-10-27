# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Loading custom evaluators from ``module:attribute`` references (TRD-080, TRD-085, TRD §10.3).

Custom evaluators are **trusted code** (SECURITY §10.1). Loading one imports its module, which runs
module-level code. Dataset content never selects or imports an evaluator.

The reference may name a class or an instance:

- a class is instantiated once with no arguments;
- an instance is used as it is.

The object must provide ``evaluate``, ``version`` (string), ``requires_expected`` (boolean), and
``interface_version`` equal to ``"1"``.

The configured name is authoritative. A result whose name differs is re-labelled with the configured
name. The evaluator cannot choose its own identity.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final, cast

from evalforge.canon import JSONValue, bytes_sha256
from evalforge.config import CALLABLE_RE
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import INTERFACE_VERSION
from evalforge.models import Case, EvaluatorResult

_LOAD_FAILED: Final = "EVALUATOR_LOAD_FAILED"


def _fail(message: str) -> EvalForgeError:
    return EvalForgeError(_LOAD_FAILED, message)


@dataclass(frozen=True, slots=True)
class LoadedCustomEvaluator:
    """A custom evaluator that has passed the load checks."""

    name: str
    reference: str
    module: str
    qualname: str
    source_sha256: str
    version: str
    requires_expected: bool
    call: Callable[[Case, JSONValue, float], object]

    type_name: str = "custom"

    @property
    def parameters(self) -> MappingProxyType[str, JSONValue]:
        return MappingProxyType({"callable": self.reference})

    def identity(self) -> MappingProxyType[str, str]:
        return MappingProxyType(
            {
                "interface_version": INTERFACE_VERSION,
                "module": self.module,
                "qualname": self.qualname,
                "source_sha256": self.source_sha256,
            }
        )

    def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> object:
        raw = self.call(case, output, duration_ms)
        if isinstance(raw, EvaluatorResult) and raw.name != self.name:
            return replace(raw, name=self.name)
        return raw


def _source_hash(module_name: str) -> str:
    module = sys.modules.get(module_name)
    path = getattr(module, "__file__", None)
    if not isinstance(path, str):
        raise _fail(f"module {module_name!r} has no source file to fingerprint.")
    with open(path, "rb") as handle:
        return bytes_sha256(handle.read())


def load_custom_evaluator(reference: str, *, name: str) -> LoadedCustomEvaluator:
    """Import, check, and wrap a custom evaluator.

    Raises ``EVALUATOR_LOAD_FAILED`` on any problem.
    """
    if CALLABLE_RE.fullmatch(reference) is None:
        raise _fail(f"{reference!r} is not a module:attribute reference.")
    module_name, _, attribute = reference.partition(":")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise _fail(f"cannot import module {module_name!r}: {type(exc).__name__}.") from exc
    try:
        obj: object = getattr(module, attribute)
    except AttributeError as exc:
        raise _fail(f"module {module_name!r} has no attribute {attribute!r}.") from exc

    if isinstance(obj, type):
        try:
            instance: object = obj()
        except Exception as exc:
            raise _fail(
                f"class {reference!r} could not be constructed without arguments: "
                f"{type(exc).__name__}."
            ) from exc
    else:
        instance = obj

    evaluate = getattr(instance, "evaluate", None)
    if not callable(evaluate):
        raise _fail(f"{reference!r} has no callable evaluate method.")

    interface = getattr(instance, "interface_version", None)
    if interface is None:
        raise _fail(
            f"{reference!r} does not declare interface_version (expected {INTERFACE_VERSION!r})."
        )
    if interface != INTERFACE_VERSION:
        raise _fail(
            f"{reference!r} declares interface_version {interface!r}; "
            f"supported: {INTERFACE_VERSION!r}."
        )

    version = getattr(instance, "version", None)
    if not isinstance(version, str) or not version:
        raise _fail(f"{reference!r} must declare a non-empty string version.")
    requires_expected = getattr(instance, "requires_expected", None)
    if not isinstance(requires_expected, bool):
        raise _fail(f"{reference!r} must declare requires_expected as true or false.")

    concrete_module = type(instance).__module__
    return LoadedCustomEvaluator(
        name=name,
        reference=reference,
        module=concrete_module,
        qualname=type(instance).__qualname__,
        source_sha256=_source_hash(concrete_module),
        version=version,
        requires_expected=requires_expected,
        call=cast(Callable[[Case, JSONValue, float], object], evaluate),
    )
