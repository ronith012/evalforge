# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Terminal text views (PRD-F-024; SECURITY §6).

Every value shown comes from stored data and passes through ``sanitize_text``. The footer
appears once per run summary.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Final, cast

from evalforge.canon import JSONValue
from evalforge.models import CaseResult, _Absent
from evalforge.reader import StoredRun
from evalforge.reporting.footer import FOOTER_TEXT
from evalforge.reporting.sanitize import sanitize_text

COUNT_KEYS: Final = ("PASS", "FAIL", "ERROR", "SKIPPED", "INCONCLUSIVE")
IO_DESCRIPTIONS: Final = {
    "full": "full (redacted when redaction is on)",
    "hashes": "hashes only (no case content)",
    "none": "none (status and reasons only)",
}


def _text(value: object) -> str:
    return sanitize_text(str(value))


def _json_text(value: JSONValue) -> str:
    return sanitize_text(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _mapping(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def render_run(stored: StoredRun) -> str:
    """Summary of a stored run.

    Covers status, integrity, counts, rate, errors, latency, warnings, and the footer.
    """
    manifest = stored.manifest
    summary = stored.summary
    dataset = _mapping(manifest.get("dataset"))
    counts_record = _mapping(manifest.get("counts"))
    lines: list[str] = [f"Run {_text(manifest.get('run_id', '?'))}"]
    lines.append(f"Status: {_text(stored.status.value)}")
    lines.append("Integrity: ok" if stored.integrity_ok else "Integrity: FAILED")
    for problem in stored.problems:
        lines.append(f"  - {_text(problem)}")
    lines.append(
        f"Dataset: {_text(dataset.get('source_label', '?'))} "
        f"({_text(dataset.get('case_count', '?'))} cases, "
        f"canonical {_text(dataset.get('canonical_sha256', '?'))})"
    )
    if summary is None:
        lines.append("Summary: not available (the run did not complete).")
    else:
        counts = _mapping(summary.get("counts"))
        tally = "   ".join(f"{key} {counts.get(key, 0)}" for key in COUNT_KEYS)
        lines.append(f"Executed: {summary.get('executed', 0)}   {tally}")
        rate = _number(summary.get("pass_rate"))
        interval = summary.get("pass_rate_ci95")
        if rate is None:
            lines.append("Pass rate: not available (no executed cases)")
        else:
            low, high = (
                (interval[0], interval[1])
                if isinstance(interval, list) and len(interval) == 2
                else (None, None)
            )
            low_f, high_f = _number(low), _number(high)
            band = (
                f" (95% interval {low_f:.3f}–{high_f:.3f}; n = {summary.get('executed', 0)})"
                if low_f is not None and high_f is not None
                else ""
            )
            lines.append(f"Pass rate: {rate:.3f}{band}")
        errors = _mapping(summary.get("error_codes"))
        lines.append(
            "Errors: " + ", ".join(f"{_text(code)} ({count})" for code, count in errors.items())
            if errors
            else "Errors: none"
        )
        fails = _mapping(summary.get("fail_by_evaluator"))
        lines.append(
            "Failures by evaluator: "
            + ", ".join(f"{_text(name)} ({count})" for name, count in fails.items())
            if fails
            else "Failures by evaluator: none"
        )
        latency = _mapping(summary.get("latency_ms"))
        if latency:
            lines.append(
                f"Latency ms: p50 {_text(latency.get('p50'))}  p95 {_text(latency.get('p95'))}  "
                f"max {_text(latency.get('max'))}"
            )
        not_executed = summary.get("not_executed", 0)
        if isinstance(not_executed, int) and not_executed > 0:
            lines.append(f"Not executed: {not_executed} (the run was interrupted)")
    threads = counts_record.get("threads_possibly_running", 0)
    if isinstance(threads, int) and threads > 0:
        lines.append(
            f"Warning: {threads} timed-out target thread(s) may still be running "
            "(timeouts are best-effort)."
        )
    if manifest.get("redaction") is False:
        lines.append("Warning: redaction was disabled for this run.")
    io_mode = _text(manifest.get("io_mode", "?"))
    lines.append(f"Stored content: {IO_DESCRIPTIONS.get(io_mode, io_mode)}.")
    lines.append("")
    lines.append(FOOTER_TEXT)
    return "\n".join(lines) + "\n"


def _status_row(case: CaseResult) -> str:
    reason = case.status_reason or "-"
    return (
        f"{_text(case.case_id):<24} {case.status.value:<12} "
        f"{_text(reason):<26} {case.target.status}"
    )


def render_case_list(
    cases: Iterable[CaseResult],
    *,
    status: str | None = None,
    limit: int = 50,
    show_io: bool = False,
) -> str:
    """Case table. Content is shown only when ``show_io`` is set (SECURITY §5; TST-SEC-014)."""
    rows: list[str] = [f"{'CASE':<24} {'STATUS':<12} {'REASON':<26} TARGET"]
    shown = 0
    for case in cases:
        if status is not None and case.status.value != status.upper():
            continue
        if shown >= limit:
            break
        rows.append(_status_row(case))
        if show_io:
            for name in ("input", "expected", "output"):
                value = getattr(case, name)
                if not isinstance(value, _Absent):
                    rows.append(f"    {name}: {_json_text(value)}")
        shown += 1
    return "\n".join(rows) + "\n"


def render_case_detail(case: CaseResult) -> str:
    """One case in full: target, evaluators, stored content (when present), and hashes."""
    lines = [
        f"Case {_text(case.case_id)}",
        f"  status: {case.status.value} (reason: {_text(case.status_reason or '-')})",
        f"  target: {case.target.status}"
        + (f" ({_text(case.target.error_code)})" if case.target.error_code else ""),
    ]
    if case.target.error is not None:
        lines.append(
            f"  target error: {_text(case.target.error.type_name)}: "
            f"{_text(case.target.error.message)}"
        )
    for name in ("input", "expected", "output"):
        value = getattr(case, name)
        if isinstance(value, _Absent):
            lines.append(f"  {name}: not stored")
        else:
            lines.append(f"  {name}: {_json_text(value)}")
    lines.append("  evaluators:")
    for item in case.evaluators:
        reason = item.reason_code or "-"
        lines.append(
            f"    {_text(item.name)}: {item.status.value} ({_text(reason)}) {_text(item.message)}"
        )
    return "\n".join(lines) + "\n"


__all__ = ["render_case_detail", "render_case_list", "render_run"]
