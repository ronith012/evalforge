# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Persisted record builders: manifest, summary, configuration snapshot, storage preparation.

Storage preparation applies the rules in DATA_HANDLING §3 and §7 to a copy of each case result.
The in-memory result is never changed. Hashes are computed before redaction, so they describe the
value the target returned (ARTIFACT_INTEGRITY §2).
"""

from __future__ import annotations

import platform
import re
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final, cast

from evalforge import __version__
from evalforge.canon import JSONValue, bytes_sha256
from evalforge.config import EvalForgeConfig
from evalforge.datasets import Dataset
from evalforge.errors import truncate
from evalforge.evaluators.base import EvaluatorFingerprint
from evalforge.models import (
    ABSENT,
    CaseResult,
    ErrorObject,
    EvaluatorResult,
    TargetResult,
    _Absent,
)
from evalforge.redaction import redact_config, redact_text, redact_value
from evalforge.runner import RunOutcome
from evalforge.stats import nearest_rank_percentile, wilson_interval
from evalforge.status import Status

IO_MODES: Final = frozenset({"full", "hashes", "none"})
MESSAGE_LIMIT: Final = 500


def portable_path(path: str, base: Path | None) -> str:
    """Return a path that can be stored (DATA_HANDLING §5).

    Paths inside the configuration directory are stored relative to it. Other absolute paths are
    replaced by ``<external>/<basename>``.
    """
    # Both POSIX and Windows absolute forms count, whatever the platform running the code.
    if not (PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute()):
        return path
    if base is not None and Path(path).is_absolute():
        try:
            return str(Path(path).relative_to(base))
        except ValueError:
            pass
    basename = re.split(r"[\\/]", path)[-1]
    return f"<external>/{basename}"


def prepare_for_storage(result: CaseResult, io_mode: str, redaction: bool) -> CaseResult:
    """Return the copy of ``result`` that may be written to disk.

    - ``io_mode`` ``full`` keeps input, expected, and output (redacted when enabled).
    - ``io_mode`` ``hashes`` keeps the hashes only.
    - ``io_mode`` ``none`` keeps neither the content nor the I/O hashes.
    - Evaluator messages, details, target error text, and stored values are redacted when enabled.
    - Redaction counts are stored; the replaced text is not.
    """
    if io_mode not in IO_MODES:
        raise ValueError(f"unknown io_mode {io_mode!r}")
    total = 0

    evaluators: list[EvaluatorResult] = []
    for item in result.evaluators:
        message = item.message
        details: Mapping[str, JSONValue] = item.details
        if redaction:
            message, made = redact_text(message)
            total += made
            new_details, extra = redact_value(dict(details))
            total += extra
            details = cast(dict[str, JSONValue], new_details)
        evaluators.append(
            replace(item, message=truncate(message, MESSAGE_LIMIT), details=dict(details))
        )

    target: TargetResult = result.target
    if redaction and target.error is not None:
        error_text, made = redact_text(target.error.message)
        total += made
        target = replace(
            target,
            error=ErrorObject(
                type_name=target.error.type_name, message=truncate(error_text, MESSAGE_LIMIT)
            ),
        )

    values: dict[str, JSONValue | _Absent] = {}
    for name in ("input", "expected", "output"):
        value = getattr(result, name)
        if io_mode != "full" or isinstance(value, _Absent):
            values[name] = ABSENT
        elif redaction:
            redacted, made = redact_value(value)
            total += made
            values[name] = redacted
        else:
            values[name] = value

    keep_hashes = io_mode != "none"
    return replace(
        result,
        target=target,
        evaluators=tuple(evaluators),
        input=values["input"],
        expected=values["expected"],
        output=values["output"],
        input_sha256=result.input_sha256 if keep_hashes else None,
        expected_sha256=result.expected_sha256 if keep_hashes else None,
        output_sha256=result.output_sha256 if keep_hashes else None,
        redactions=total,
    )


def summary_record(run_id: str, outcome: RunOutcome) -> dict[str, object]:
    """Aggregates derived from the case results (DATA_MODELS §10)."""
    counts = outcome.counts()
    executed = counts["executed"]
    passes = counts[Status.PASS.value]
    interval = wilson_interval(passes, executed) if executed else None
    fails: Counter[str] = Counter()
    for case in outcome.cases:
        for item in case.evaluators:
            if item.status is Status.FAIL:
                fails[item.name] += 1
    error_codes: Counter[str] = Counter(
        case.status_reason or "UNKNOWN" for case in outcome.cases if case.status is Status.ERROR
    )
    durations = [case.target.duration_ms for case in outcome.cases if case.target.status == "OK"]
    latency: dict[str, object] | None = None
    if durations:
        latency = {
            "p50": nearest_rank_percentile(durations, 50),
            "p95": nearest_rank_percentile(durations, 95),
            "max": max(durations),
        }
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "counts": {key: value for key, value in counts.items() if key != "executed"},
        "executed": executed,
        "pass_rate": (passes / executed) if executed else None,
        "pass_rate_ci95": list(interval) if interval is not None else None,
        "error_codes": dict(error_codes),
        "fail_by_evaluator": dict(fails),
        "latency_ms": latency,
        "not_executed": outcome.not_executed,
    }


def environment_record() -> dict[str, object]:
    """Minimal environment metadata (DATA_HANDLING §6). No host name, user, path, or variables."""
    return {
        "evalforge_version": __version__,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os_family": platform.system() or "unknown",
        "machine": platform.machine() or "unknown",
    }


def dataset_record(dataset: Dataset, base: Path | None) -> dict[str, object]:
    return {
        "source_label": portable_path(dataset.source_label, base),
        "format": dataset.format,
        "sha256": dataset.sha256,
        "canonical_sha256": dataset.canonical_sha256,
        "case_count": dataset.case_count,
    }


def config_record(config: EvalForgeConfig) -> tuple[dict[str, object], int]:
    """Configuration snapshot with secret-like values removed (DATA_HANDLING §5)."""
    base = config.config_dir
    raw: dict[str, object] = {
        "run": {
            "io_mode": config.run.io_mode,
            "redaction": config.run.redaction,
            "timeout_seconds": config.run.timeout_seconds,
            "fail_on": list(config.run.fail_on),
            "run_root": portable_path(config.run.run_root, base),
        },
        "dataset": {"path": portable_path(config.dataset.path, base)},
        "target": {"callable": config.target.callable_ref, "name": config.target.name},
        "evaluators": [
            {
                "name": item.name,
                "type": item.type_name,
                "requires_expected": item.requires_expected,
                "params": dict(item.params),
            }
            for item in config.evaluators
        ],
        "regression": {
            "max_newly_failing": config.regression.max_newly_failing,
            "max_newly_errored": config.regression.max_newly_errored,
            "inconclusive_as_regression": config.regression.inconclusive_as_regression,
            "max_pass_rate_drop": config.regression.max_pass_rate_drop,
            "min_executed_for_rate_check": config.regression.min_executed_for_rate_check,
            "max_p95_latency_ratio": config.regression.max_p95_latency_ratio,
            "missing_case_policy": config.regression.missing_case_policy,
        },
    }
    return redact_config(raw)


def fingerprint_record(fingerprint: EvaluatorFingerprint) -> dict[str, object]:
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


def content_hash(data: bytes) -> str:
    """SHA-256 of raw file bytes, in the same ``sha256:`` form as every other artifact hash."""
    return bytes_sha256(data)
