# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Object-level Python API (API_DESIGN §2, §5, §6).

``Suite`` runs evaluators against a dataset and a target. ``Run`` is the result.
``compare`` compares two runs. The same rules as the command line apply: comparisons refuse
incompatible runs unless the override is given, and an in-memory run cannot be compared from disk.

Configuration-driven helpers (``load_config``, ``run_from_config``) use the operations in
``evalforge.api``, so their results match the command line.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast

from evalforge import api
from evalforge.canon import JSONValue
from evalforge.compare import Comparison, compare_runs
from evalforge.config import (
    DatasetSettings,
    EvalForgeConfig,
    EvaluatorSettings,
    RegressionSettings,
    RunSettings,
    TargetSettings,
    load_config_file,
)
from evalforge.datasets import Dataset
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import Evaluator, fingerprint_of
from evalforge.reader import StoredRun, load_run
from evalforge.regression import DEFAULT_THRESHOLDS, Finding
from evalforge.runner import RunOptions, RunOutcome, run_cases
from evalforge.status import RunStatus, Status
from evalforge.store import RunContext, persist_outcome
from evalforge.targets import Target, TargetProtocol, from_callable, resolve_target

# Public names for the regression vocabulary (API_DESIGN §2).
Thresholds = RegressionSettings
RegressionFinding = Finding

_INLINE_TARGET_REF: Final = "<api>"
_INLINE_DATASET_LABEL: Final = "<inline>"


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Counts and rates for one run (DATA_MODELS §10).

    ``pass_rate`` is None when no case was executed.
    """

    counts: Mapping[str, int]
    executed: int
    pass_rate: float | None

    @classmethod
    def from_counts(cls, counts: Mapping[str, int], pass_rate: float | None = None) -> RunSummary:
        executed = int(counts.get("executed", 0))
        rate = pass_rate
        if rate is None and executed:
            rate = counts.get("PASS", 0) / executed
        return cls(counts=dict(counts), executed=executed, pass_rate=rate)


@dataclass(frozen=True, slots=True)
class Run:
    """A finished run. ``path`` is None for an in-memory run, which is not stored on disk."""

    run_id: str
    status: RunStatus
    summary: RunSummary
    path: Path | None
    _stored: StoredRun | None = field(default=None, repr=False, compare=False)

    @classmethod
    def _in_memory(cls, outcome: RunOutcome) -> Run:
        return cls(
            run_id=outcome.run_id,
            status=outcome.status,
            summary=RunSummary.from_counts(outcome.counts()),
            path=None,
        )

    @classmethod
    def from_stored(cls, stored: StoredRun) -> Run:
        raw = stored.summary or {}
        counts = raw.get("counts")
        rate = raw.get("pass_rate")
        summary = RunSummary.from_counts(
            {str(key): int(value) for key, value in counts.items()}
            if isinstance(counts, dict)
            else {},
            pass_rate=float(rate) if isinstance(rate, int | float) else None,
        )
        return cls(
            run_id=str(stored.manifest.get("run_id", "")),
            status=stored.status,
            summary=summary,
            path=stored.path,
            _stored=stored,
        )

    @property
    def stored(self) -> StoredRun:
        """The stored form. Raises ``RUN_NOT_FOUND`` for an in-memory run."""
        if self._stored is None:
            raise EvalForgeError(
                "RUN_NOT_FOUND", "this run is in memory only; it has no stored form on disk."
            )
        return self._stored


def _as_target(target: object) -> TargetProtocol:
    """A target object, a plain callable, or a ``module:attribute`` reference (trusted code)."""
    if isinstance(target, str):
        return resolve_target(target)
    if not callable(target):
        raise EvalForgeError(
            "TARGET_LOAD_FAILED", "a target must be callable or a module:attribute string."
        )
    if isinstance(getattr(target, "name", None), str):
        return cast(TargetProtocol, target)
    return from_callable(cast(Callable[[JSONValue], object], target))


def _options(
    timeout_seconds: float,
    grace_seconds: float,
    case_ids: Iterable[str] | None,
    tags: Iterable[str] | None,
) -> RunOptions:
    try:
        return RunOptions(
            timeout_seconds=timeout_seconds,
            grace_seconds=grace_seconds,
            case_ids=None if case_ids is None else frozenset(case_ids) or None,
            tags=None if tags is None else frozenset(tags) or None,
        )
    except ValueError as exc:
        raise EvalForgeError("USAGE_ERROR", str(exc)) from exc


class Suite:
    """Evaluators and run settings.

    ``run`` executes them against a dataset and a target (API_DESIGN §6).
    """

    def __init__(
        self,
        evaluators: Sequence[Evaluator],
        *,
        timeout_seconds: float = 30.0,
        grace_seconds: float = 5.0,
        io_mode: str = "full",
        redaction: bool = True,
    ) -> None:
        if not evaluators:
            raise EvalForgeError("USAGE_ERROR", "a suite needs at least one evaluator.")
        names = [item.name for item in evaluators]
        if len(set(names)) != len(names):
            raise EvalForgeError("USAGE_ERROR", "evaluator names must be unique within a suite.")
        if io_mode not in api.IO_MODES:
            raise EvalForgeError(
                "USAGE_ERROR", f"io_mode must be one of {', '.join(api.IO_MODES)}."
            )
        _options(timeout_seconds, grace_seconds, None, None)
        self.evaluators: tuple[Evaluator, ...] = tuple(evaluators)
        self.timeout_seconds = timeout_seconds
        self.grace_seconds = grace_seconds
        self.io_mode = io_mode
        self.redaction = redaction

    def run(
        self,
        dataset: Dataset,
        target: TargetProtocol | Callable[[JSONValue], object] | str,
        *,
        run_root: str | Path | None = None,
        case_ids: Iterable[str] | None = None,
        tags: Iterable[str] | None = None,
    ) -> Run:
        """Run the selected cases. Without ``run_root`` the run stays in memory (not comparable)."""
        resolved = _as_target(target)
        options = _options(self.timeout_seconds, self.grace_seconds, case_ids, tags)
        outcome = run_cases(dataset, resolved, self.evaluators, options)
        if run_root is None:
            return Run._in_memory(outcome)
        root = Path(run_root)
        context = RunContext(
            dataset=dataset,
            config=self._snapshot(dataset, resolved, root),
            options=options,
            io_mode=self.io_mode,
            redaction=self.redaction,
            target_name=resolved.name,
            fingerprints=tuple(fingerprint_of(item) for item in self.evaluators),
        )
        run_dir = persist_outcome(outcome, context, root)
        return Run.from_stored(load_run(run_dir))

    def _snapshot(self, dataset: Dataset, target: TargetProtocol, root: Path) -> EvalForgeConfig:
        """The configuration record for an API run. It states that the run was built in code."""
        return EvalForgeConfig(
            schema_version="1.0",
            run=RunSettings(
                io_mode=self.io_mode,
                redaction=self.redaction,
                timeout_seconds=self.timeout_seconds,
                fail_on=(),
                run_root=str(root),
            ),
            dataset=DatasetSettings(path=dataset.source_label or _INLINE_DATASET_LABEL),
            target=TargetSettings(callable_ref=_INLINE_TARGET_REF, name=target.name),
            evaluators=tuple(
                EvaluatorSettings(
                    name=item.name,
                    type_name=item.type_name,
                    requires_expected=item.requires_expected,
                    params=dict(item.parameters),
                )
                for item in self.evaluators
            ),
            regression=DEFAULT_THRESHOLDS,
            config_dir=None,
        )


def compare(
    baseline: Run | str | Path,
    candidate: Run | str | Path,
    *,
    run_root: str | Path | None = None,
    allow_dataset_change: bool = False,
    allow_evaluator_change: bool = False,
    strict: bool = False,
    thresholds: RegressionSettings = DEFAULT_THRESHOLDS,
) -> Comparison:
    """Compare two runs (EVALUATION_METHODOLOGY §5). Refusals are returned as data, not raised."""
    return compare_runs(
        _stored_of(baseline, run_root),
        _stored_of(candidate, run_root),
        allow_dataset_change=allow_dataset_change,
        allow_evaluator_change=allow_evaluator_change,
        strict=strict,
        thresholds=thresholds,
    )


def _stored_of(reference: Run | str | Path, run_root: str | Path | None) -> StoredRun:
    if isinstance(reference, Run):
        return reference.stored
    return api.inspect_run(
        str(reference), run_root if run_root is not None else api.DEFAULT_RUN_ROOT
    )


def load_config(path: str | Path) -> EvalForgeConfig:
    """Read and validate a configuration file. Target and evaluator modules are not imported."""
    return load_config_file(path)


def run_from_config(
    path: str | Path,
    *,
    run_root: str | Path | None = None,
    case_ids: Iterable[str] | None = None,
    tags: Iterable[str] | None = None,
    timeout_seconds: float | None = None,
    io_mode: str | None = None,
    redaction: bool | None = None,
    fail_on: Sequence[str] | None = None,
) -> Run:
    """Run a configuration file and return the stored run (same behaviour as ``evalforge run``)."""
    result = api.run_configured(
        path,
        run_root=run_root,
        case_ids=case_ids,
        tags=tags,
        timeout_seconds=timeout_seconds,
        io_mode=io_mode,
        redaction=redaction,
        fail_on=fail_on,
    )
    return Run.from_stored(result.stored)


__all__ = [
    "Comparison",
    "RegressionFinding",
    "Run",
    "RunSummary",
    "Status",
    "Suite",
    "Target",
    "Thresholds",
    "compare",
    "load_config",
    "run_from_config",
]
