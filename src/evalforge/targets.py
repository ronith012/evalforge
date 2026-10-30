# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Target interface and invocation (TRD §5.2; PRD-F-005 to PRD-F-007, PRD-F-028).

A target is the application function under evaluation. It receives one case input (a JSON value)
and returns a JSON-serialisable output.

Trust: targets are **trusted code** (SECURITY §10.1). Resolving a ``module:attribute`` reference
imports that module, which runs its module-level code. Only configure references you trust.
Dataset content never selects or imports a target.

Timeouts are not part of this module. They are added by the runner in Milestone 6, and they are
best-effort there as well (TRD-072).
"""

from __future__ import annotations

import copy
import importlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from evalforge import limits
from evalforge.canon import JSONValue, JsonValueError, check_json_value
from evalforge.config import CALLABLE_RE
from evalforge.errors import TargetLoadError, truncate
from evalforge.models import ABSENT, ErrorObject, TargetResult, _Absent


class TargetProtocol(Protocol):
    """Anything callable with one case input that exposes a display ``name``."""

    @property
    def name(self) -> str: ...

    def __call__(self, case_input: JSONValue) -> object: ...


class Target:
    """Constructors for targets (API_DESIGN §4). Each returns a ``TargetProtocol``."""

    @classmethod
    def from_callable(
        cls,
        func: Callable[[JSONValue], object],
        *,
        name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> TargetProtocol:
        """Wrap a plain callable.

        ``timeout_seconds`` overrides the run's timeout for this target.
        """
        return _with_timeout(from_callable(func, name=name), timeout_seconds)

    @classmethod
    def from_reference(
        cls,
        reference: str,
        *,
        name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> TargetProtocol:
        """Import a ``module:attribute`` target. Trusted code: importing runs module code."""
        return _with_timeout(resolve_target(reference, name=name), timeout_seconds)


@dataclass(frozen=True, slots=True)
class CallableTarget:
    """Adapter that gives a plain callable the ``Target`` shape."""

    name: str
    func: Callable[[JSONValue], object]

    def __call__(self, case_input: JSONValue) -> object:
        return self.func(case_input)


@dataclass(frozen=True, slots=True)
class TimedTarget:
    """A target with its own timeout (TRD-070). Calls and the reported name are unchanged."""

    inner: TargetProtocol
    timeout_seconds: float

    @property
    def name(self) -> str:
        return self.inner.name

    def __call__(self, case_input: JSONValue) -> object:
        return self.inner(case_input)


def _with_timeout(target: TargetProtocol, timeout_seconds: float | None) -> TargetProtocol:
    if timeout_seconds is None:
        return target
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int | float):
        raise TargetLoadError("TARGET_LOAD_FAILED", "timeout_seconds must be a number.")
    if not 0.0 < float(timeout_seconds) <= limits.MAX_TIMEOUT_SECONDS:
        raise TargetLoadError(
            "TARGET_LOAD_FAILED",
            f"timeout_seconds must be greater than 0 and at most {limits.MAX_TIMEOUT_SECONDS}.",
        )
    return TimedTarget(inner=target, timeout_seconds=float(timeout_seconds))


@dataclass(frozen=True, slots=True)
class TargetInvocation:
    """Result of one target call: the recorded outcome and, if the call succeeded, its output."""

    result: TargetResult
    output: JSONValue | _Absent


def _check_name(name: str) -> str:
    if not name or len(name) > limits.MAX_TARGET_NAME_CHARS:
        raise TargetLoadError(
            "TARGET_LOAD_FAILED",
            f"target name must be 1 to {limits.MAX_TARGET_NAME_CHARS} characters.",
        )
    return name


def from_callable(
    func: Callable[[JSONValue], object], *, name: str | None = None
) -> CallableTarget:
    """Wrap a plain callable as a target. The default name is the function's qualified name."""
    if not callable(func):
        raise TargetLoadError("TARGET_LOAD_FAILED", "target must be callable.")
    default = getattr(func, "__qualname__", None) or getattr(func, "__name__", None) or repr(func)
    return CallableTarget(name=_check_name(name if name is not None else str(default)), func=func)


def resolve_target(reference: str, *, name: str | None = None) -> TargetProtocol:
    """Import a ``module:attribute`` reference and return it as a target.

    Importing runs the module's top-level code. This is trusted-code loading (SECURITY §10.1).
    Raises ``TargetLoadError`` when the module, attribute, or object is unusable.

    Name precedence: the ``name`` argument, then a string ``name`` declared by the object, then the
    reference text.
    """
    if CALLABLE_RE.fullmatch(reference) is None:
        raise TargetLoadError(
            "TARGET_LOAD_FAILED", f"{reference!r} is not a module:attribute reference."
        )
    module_name, _, attribute = reference.partition(":")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise TargetLoadError(
            "TARGET_LOAD_FAILED",
            f"cannot import module {module_name!r}: {type(exc).__name__}: {exc}",
        ) from exc
    try:
        obj: object = getattr(module, attribute)
    except AttributeError as exc:
        raise TargetLoadError(
            "TARGET_LOAD_FAILED", f"module {module_name!r} has no attribute {attribute!r}."
        ) from exc
    if isinstance(obj, type):
        raise TargetLoadError(
            "TARGET_LOAD_FAILED",
            f"{reference!r} is a class; reference an instance or a function.",
        )
    if not callable(obj):
        raise TargetLoadError("TARGET_LOAD_FAILED", f"{reference!r} is not callable.")
    if name is None:
        declared = getattr(obj, "name", None)
        if isinstance(declared, str):
            _check_name(declared)
            return cast(TargetProtocol, obj)
        name = reference
    return CallableTarget(name=_check_name(name), func=cast(Callable[[JSONValue], object], obj))


def invoke_target(target: TargetProtocol, case_input: JSONValue) -> TargetInvocation:
    """Call the target once with a private copy of the input and record the outcome.

    - The input is deep-copied, so a target that mutates its argument cannot change the case
      (TRD-064).
    - Any ``Exception`` or ``SystemExit`` raised by the target is recorded as ``TARGET_EXCEPTION``.
      ``KeyboardInterrupt`` propagates, so the runner can stop the run.
    - The return value must be JSON-serialisable (TRD-062); otherwise the outcome is
      ``TARGET_OUTPUT_INVALID``.
    - Duration is measured with ``time.perf_counter`` (TRD-063).
    """
    payload = copy.deepcopy(case_input)
    started = time.perf_counter()
    try:
        raw = target(payload)
    except (Exception, SystemExit) as exc:
        duration = _elapsed_ms(started)
        error = ErrorObject(
            type_name=truncate(type(exc).__name__, 100),
            message=truncate(str(exc)),
        )
        return TargetInvocation(
            result=TargetResult(
                status="ERROR", error_code="TARGET_EXCEPTION", error=error, duration_ms=duration
            ),
            output=ABSENT,
        )
    duration = _elapsed_ms(started)
    try:
        check_json_value(raw)
    except JsonValueError as exc:
        error = ErrorObject(type_name="TargetOutputInvalid", message=truncate(str(exc)))
        return TargetInvocation(
            result=TargetResult(
                status="ERROR",
                error_code="TARGET_OUTPUT_INVALID",
                error=error,
                duration_ms=duration,
            ),
            output=ABSENT,
        )
    return TargetInvocation(
        result=TargetResult(status="OK", error_code=None, error=None, duration_ms=duration),
        output=cast(JSONValue, raw),
    )


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0
