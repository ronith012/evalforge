# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Operations shared by the command line and the Python API (API_DESIGN §2; CLI_SPECIFICATION §3).

Each function validates its inputs, does the work, and returns data. Failures raise
``EvalForgeError`` with a registered code, and the code decides the exit status (``ERROR_CODES``).
The CLI turns results into text or JSON; the Python API returns them directly. Both use these
functions, so the two interfaces cannot disagree about a result (Milestone 11 parity tests).

Decisions in this module that the owner has not yet confirmed are marked ``OD-25`` or ``OD-26``
where they apply.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast

from evalforge.compare import Comparison, compare_runs
from evalforge.config import EvalForgeConfig, RegressionSettings, load_config_file
from evalforge.datasets import Dataset, load_dataset
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import fingerprint_of
from evalforge.evaluators.registry import build_evaluators
from evalforge.models import CaseResult, _Absent
from evalforge.reader import StoredRun, load_run
from evalforge.regression import DEFAULT_THRESHOLDS
from evalforge.reporting.comparison_text import render_comparison
from evalforge.reporting.json_report import build_run_report, report_bytes
from evalforge.reporting.text import render_case_detail, render_case_list, render_run
from evalforge.runner import RunOptions, run_cases
from evalforge.serialise import case_result_to_dict
from evalforge.status import RunStatus, Status
from evalforge.store import MANIFEST_NAME, RunContext, persist_outcome
from evalforge.targets import resolve_target

DEFAULT_CONFIG_NAME: Final = "evalforge.toml"
DEFAULT_RUN_ROOT: Final = ".evalforge/runs"
IO_MODES: Final = ("full", "hashes", "none")
FAIL_ON_TO_STATUS: Final[Mapping[str, Status]] = {
    "fail": Status.FAIL,
    "error": Status.ERROR,
    "inconclusive": Status.INCONCLUSIVE,
}
RUN_ID_MIN_PREFIX: Final = 8
INSPECT_LIMIT_MAX: Final = 1000
INSPECT_LIMIT_DEFAULT: Final = 50
COMPARISON_KEYS: Final = frozenset({"schema_version", "baseline", "candidate", "cases", "findings"})


def dataset_path_for(config: EvalForgeConfig, config_path: Path) -> Path:
    """The dataset path in a configuration is relative to the configuration file's directory."""
    base = config.config_dir if config.config_dir is not None else config_path.parent
    return base / config.dataset.path


def config_run_root(config: EvalForgeConfig) -> Path:
    base = config.config_dir if config.config_dir is not None else Path.cwd()
    return base / config.run.run_root


def tag_counts(dataset: Dataset) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in dataset.cases:
        for tag in case.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items()))


def dataset_document(dataset: Dataset) -> dict[str, object]:
    return {
        "valid": True,
        "format": dataset.format,
        "cases": dataset.case_count,
        "tags": tag_counts(dataset),
        "sha256": dataset.sha256,
        "canonical_sha256": dataset.canonical_sha256,
        "warnings": list(dataset.warnings),
    }


def validate_dataset(path: str | Path) -> Dataset:
    """Load and validate a dataset file.

    Raises ``DatasetValidationError`` with every error found.
    """
    return load_dataset(path)


def validate_config(
    path: str | Path,
    *,
    check_imports: bool = False,
    check_dataset: bool = False,
) -> dict[str, object]:
    """Validate a configuration file. Imports run only with ``check_imports`` (THR-004)."""
    config_path = Path(path)
    config = load_config_file(config_path)
    document: dict[str, object] = {
        "valid": True,
        "config": str(config_path),
        "target": config.target.callable_ref,
        "evaluators": [item.name for item in config.evaluators],
        "imports_checked": check_imports,
        "dataset_checked": check_dataset,
    }
    if check_imports:
        resolve_target(config.target.callable_ref, name=config.target.name)
        build_evaluators(config.evaluators)
    if check_dataset:
        document["dataset"] = dataset_document(load_dataset(dataset_path_for(config, config_path)))
    return document


@dataclass(frozen=True, slots=True)
class RunResult:
    """A finished run: its stored form, and how many cases matched ``fail_on``."""

    stored: StoredRun
    fail_on: tuple[str, ...]
    fail_on_matches: int
    redaction: bool
    dataset_warnings: tuple[str, ...] = field(default=())


def _progress_hook(
    dataset: Dataset,
    options: RunOptions,
    on_progress: Callable[[int, int, CaseResult], None] | None,
) -> Callable[[CaseResult], None] | None:
    """Adapt ``on_progress`` to the runner's callback, counting the cases selected for this run."""
    if on_progress is None:
        return None
    if options.case_ids is not None:
        total = sum(1 for case in dataset.cases if case.id in options.case_ids)
    elif options.tags is not None:
        total = sum(1 for case in dataset.cases if options.tags.intersection(case.tags))
    else:
        total = dataset.case_count
    position = 0

    def hook(result: CaseResult) -> None:
        nonlocal position
        position += 1
        on_progress(position, total, result)

    return hook


def run_configured(
    config_path: str | Path,
    *,
    run_root: str | Path | None = None,
    case_ids: Iterable[str] | None = None,
    tags: Iterable[str] | None = None,
    timeout_seconds: float | None = None,
    io_mode: str | None = None,
    redaction: bool | None = None,
    fail_on: Sequence[str] | None = None,
    on_progress: Callable[[int, int, CaseResult], None] | None = None,
) -> RunResult:
    """Run the configured target over the selected cases and store the run.

    ``on_progress(position, total, result)`` is called after each executed case (CLI progress).

    Nothing is executed when the configuration or dataset is invalid. Selection, timeout, and
    I/O overrides are validated here; an invalid value raises ``USAGE_ERROR``.
    """
    path = Path(config_path)
    config = load_config_file(path)
    dataset = load_dataset(dataset_path_for(config, path))
    target = resolve_target(config.target.callable_ref, name=config.target.name)
    evaluators = build_evaluators(config.evaluators)

    try:
        options = RunOptions(
            timeout_seconds=timeout_seconds
            if timeout_seconds is not None
            else config.run.timeout_seconds,
            case_ids=None if case_ids is None else frozenset(case_ids) or None,
            tags=None if tags is None else frozenset(tags) or None,
        )
    except ValueError as exc:
        raise EvalForgeError("USAGE_ERROR", str(exc)) from exc

    effective_io = io_mode if io_mode is not None else config.run.io_mode
    if effective_io not in IO_MODES:
        raise EvalForgeError("USAGE_ERROR", f"io_mode must be one of {', '.join(IO_MODES)}.")
    effective_redaction = config.run.redaction if redaction is None else redaction
    effective_fail_on = tuple(fail_on) if fail_on is not None else config.run.fail_on
    for value in effective_fail_on:
        if value not in FAIL_ON_TO_STATUS:
            raise EvalForgeError("USAGE_ERROR", f"unknown --fail-on status {value!r}.")

    context = RunContext(
        dataset=dataset,
        config=config,
        options=options,
        io_mode=effective_io,
        redaction=effective_redaction,
        target_name=config.target.name,
        fingerprints=tuple(fingerprint_of(item) for item in evaluators),
    )
    outcome = run_cases(
        dataset, target, evaluators, options, on_case=_progress_hook(dataset, options, on_progress)
    )
    root = Path(run_root) if run_root is not None else config_run_root(config)
    run_dir = persist_outcome(outcome, context, root)
    stored = load_run(run_dir)

    wanted = {FAIL_ON_TO_STATUS[value] for value in effective_fail_on}
    matches = sum(1 for case in outcome.cases if case.status in wanted)
    return RunResult(
        stored=stored,
        fail_on=effective_fail_on,
        fail_on_matches=matches,
        redaction=effective_redaction,
        dataset_warnings=dataset.warnings,
    )


def resolve_run(reference: str, run_root: str | Path) -> Path:
    """Find a run directory from a path or from an ID (or unique ID prefix within ``run_root``).

    Ambiguous or unknown references raise ``RUN_NOT_FOUND`` and list the matches (CLI §1.5).
    """
    as_path = Path(reference)
    if as_path.is_dir() and (as_path / MANIFEST_NAME).exists():
        return as_path
    root = Path(run_root)
    if not root.is_dir():
        raise EvalForgeError("RUN_NOT_FOUND", f"no run directory at {root}")
    # A run ID is a plain name. A separator or a dot segment would reach outside the run root
    # (THR-007); such a reference is accepted only as a path to a run directory, checked above.
    if _is_plain_name(reference):
        exact = root / reference
        if exact.is_dir():
            return exact
    if not _is_plain_name(reference):
        raise EvalForgeError(
            "RUN_NOT_FOUND",
            f"no run matches {reference!r}; a run ID is a name, "
            "or give a path to the run directory.",
        )
    if len(reference) < RUN_ID_MIN_PREFIX:
        raise EvalForgeError(
            "RUN_NOT_FOUND",
            f"no run matches {reference!r}; a run ID prefix needs at least "
            f"{RUN_ID_MIN_PREFIX} characters.",
        )
    matches = sorted(
        item.name for item in root.iterdir() if item.is_dir() and item.name.startswith(reference)
    )
    if not matches:
        raise EvalForgeError("RUN_NOT_FOUND", f"no run matches {reference!r}.")
    if len(matches) > 1:
        raise EvalForgeError(
            "RUN_NOT_FOUND",
            f"{reference!r} is ambiguous; matches: {', '.join(matches)}.",
        )
    return root / matches[0]


def _is_plain_name(reference: str) -> bool:
    return (
        bool(reference)
        and reference not in {".", ".."}
        and not any(separator in reference for separator in ("/", "\\"))
    )


def inspect_run(reference: str, run_root: str | Path) -> StoredRun:
    """Load a stored run with integrity checks. An incomplete run loads and is reported as such."""
    return load_run(resolve_run(reference, run_root), strict=True)


def find_case(stored: StoredRun, case_id: str) -> CaseResult:
    for case in stored.cases():
        if case.case_id == case_id:
            return case
    raise EvalForgeError(
        "USAGE_ERROR", f"case {case_id!r} is not in run {stored.manifest.get('run_id')}."
    )


def checked_limit(limit: int) -> int:
    """``0`` means the maximum (CLI §3.4)."""
    if limit < 0 or limit > INSPECT_LIMIT_MAX:
        raise EvalForgeError("USAGE_ERROR", f"--limit must be between 0 and {INSPECT_LIMIT_MAX}.")
    return limit or INSPECT_LIMIT_MAX


def inspect_document(
    stored: StoredRun,
    *,
    case_id: str | None = None,
    status: str | None = None,
    limit: int = INSPECT_LIMIT_DEFAULT,
    show_io: bool = False,
) -> dict[str, object]:
    """Structured form of ``inspect``.

    Case content appears only with ``show_io`` or a case detail.
    """
    counts = None if stored.summary is None else stored.summary.get("counts")
    document: dict[str, object] = {
        "run_id": stored.manifest.get("run_id"),
        "status": stored.status.value,
        "incomplete": stored.status is RunStatus.RUNNING,
        "integrity_ok": stored.integrity_ok,
        "problems": list(stored.problems),
        "counts": counts,
    }
    if case_id is not None:
        document["case"] = case_result_to_dict(find_case(stored, case_id))
        return document
    wanted = status.upper() if status is not None else None
    rows: list[dict[str, object]] = []
    for case in stored.cases():
        if wanted is not None and case.status.value != wanted:
            continue
        if len(rows) >= checked_limit(limit):
            break
        row: dict[str, object] = {
            "case_id": case.case_id,
            "status": case.status.value,
            "status_reason": case.status_reason,
        }
        if show_io:
            row["input"] = case.input if not isinstance(case.input, _Absent) else None
            row["expected"] = case.expected if not isinstance(case.expected, _Absent) else None
            row["output"] = case.output if not isinstance(case.output, _Absent) else None
        rows.append(row)
    document["cases"] = rows
    return document


def inspect_text(
    stored: StoredRun,
    *,
    case_id: str | None = None,
    status: str | None = None,
    limit: int = INSPECT_LIMIT_DEFAULT,
    show_io: bool = False,
) -> str:
    if case_id is not None:
        return render_case_detail(find_case(stored, case_id))
    parts = [render_run(stored)]
    parts.append(
        render_case_list(stored.cases(), status=status, limit=checked_limit(limit), show_io=show_io)
    )
    return "\n".join(parts)


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    comparison: Comparison
    thresholds_source: str

    def to_dict(self) -> dict[str, object]:
        document = self.comparison.to_dict()
        document["thresholds_source"] = self.thresholds_source
        return document


def compare_stored(
    baseline: str,
    candidate: str,
    *,
    run_root: str | Path,
    config_path: str | Path | None = None,
    allow_dataset_change: bool = False,
    allow_evaluator_change: bool = False,
    strict: bool = False,
) -> ComparisonResult:
    """Compare two stored runs. Refusals and findings are returned as data, not raised."""
    thresholds: RegressionSettings = DEFAULT_THRESHOLDS
    source = "built-in defaults (TRD §9.1 proposed; OD-08)"
    if config_path is not None:
        config = load_config_file(config_path)
        thresholds = config.regression
        source = f"configuration {config_path}"
    base_run = inspect_run(baseline, run_root)
    cand_run = inspect_run(candidate, run_root)
    comparison = compare_runs(
        base_run,
        cand_run,
        allow_dataset_change=allow_dataset_change,
        allow_evaluator_change=allow_evaluator_change,
        strict=strict,
        thresholds=thresholds,
    )
    return ComparisonResult(comparison=comparison, thresholds_source=source)


def comparison_exit_status(result: ComparisonResult) -> str:
    return result.comparison.exit_status


def is_comparison_document(data: object) -> bool:
    return isinstance(data, dict) and COMPARISON_KEYS.issubset(cast(dict[str, object], data))


def export_bytes(
    source: str,
    *,
    run_root: str | Path,
    fmt: str,
    include_io: bool,
) -> bytes:
    """Bytes of a report export from a run reference or a comparison JSON file (CLI §3.6)."""
    path = Path(source)
    if path.is_file():
        if include_io:
            raise EvalForgeError(
                "IO_NOT_STORED", "comparison files never contain case inputs or outputs."
            )
        try:
            data: object = json.loads(path.read_bytes().decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise EvalForgeError("USAGE_ERROR", f"{source} is not valid JSON.") from exc
        if not is_comparison_document(data):
            raise EvalForgeError("USAGE_ERROR", f"{source} is not a comparison file.")
        if fmt == "text":
            return render_comparison(cast(Mapping[str, object], data)).encode("utf-8")
        return report_bytes(cast(Mapping[str, object], data))

    stored = inspect_run(source, run_root)
    if fmt == "text":
        if include_io:
            raise EvalForgeError("USAGE_ERROR", "--include-io applies to JSON exports only.")
        return render_run(stored).encode("utf-8")
    return report_bytes(build_run_report(stored, include_io=include_io))


def write_new(path: str | Path, data: bytes) -> Path:
    """Write a new file.

    An existing file is never overwritten, and parent directories are not created.
    """
    target = Path(path)
    if target.exists():
        raise EvalForgeError("STORAGE_ERROR", f"{target} already exists; nothing was written.")
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except OSError as exc:
        raise EvalForgeError("STORAGE_ERROR", f"cannot write {target}: {exc.strerror}") from exc
    return target
