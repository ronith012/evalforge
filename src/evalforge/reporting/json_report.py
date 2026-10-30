# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""JSON run reports (PRD-F-025; DATA_HANDLING §8).

Defaults: no case content, no evaluator messages, no details. ``include_io=True`` adds the
stored input, expected, and output values, with evaluator messages and details. It is refused
unless the run stored ``io_mode = full``. The stored values are already redacted when redaction
was on, and there is no way to export the unredacted values (DATA_HANDLING §8.2).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import cast

from evalforge.canon import JSONValue
from evalforge.errors import EvalForgeError
from evalforge.models import CaseResult, _Absent
from evalforge.reader import StoredRun
from evalforge.reporting.footer import FOOTER_TEXT

REPORT_SCHEMA_VERSION = "1.0"


def _case_entry(case: CaseResult, include_io: bool) -> dict[str, object]:
    entry: dict[str, object] = {
        "case_id": case.case_id,
        "status": case.status.value,
        "status_reason": case.status_reason,
        "target_status": case.target.status,
        "error_code": case.target.error_code,
        "evaluators": [
            {
                "name": item.name,
                "status": item.status.value,
                "reason_code": item.reason_code,
                **({"message": item.message, "details": dict(item.details)} if include_io else {}),
            }
            for item in case.evaluators
        ],
    }
    if include_io:
        for name in ("input", "expected", "output"):
            value = getattr(case, name)
            if not isinstance(value, _Absent):
                entry[name] = cast(JSONValue, value)
    return entry


def build_run_report(stored: StoredRun, *, include_io: bool = False) -> dict[str, object]:
    """Build the JSON report for a stored run. The result validates against run-report-1.0."""
    io_mode = str(stored.manifest.get("io_mode", ""))
    if include_io and io_mode != "full":
        raise EvalForgeError(
            "IO_NOT_STORED",
            f"the run was stored with io_mode {io_mode!r}; case content is not available",
        )
    dataset = cast(Mapping[str, object], stored.manifest.get("dataset", {}))
    summary = stored.summary
    counts = summary.get("counts") if summary is not None else None
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": "run",
        "run_id": str(stored.manifest.get("run_id", "")),
        "status": stored.status.value,
        "integrity": {"ok": stored.integrity_ok, "problems": list(stored.problems)},
        "io_mode": io_mode,
        "redaction": bool(stored.manifest.get("redaction", False)),
        "dataset": {
            "source_label": str(dataset.get("source_label", "")),
            "format": str(dataset.get("format", "")),
            "canonical_sha256": str(dataset.get("canonical_sha256", "")),
            "case_count": int(cast(int, dataset.get("case_count", 0))),
        },
        "counts": counts,
        "summary": summary,
        "footer": FOOTER_TEXT,
        "cases": [_case_entry(case, include_io) for case in stored.cases()],
    }


def report_bytes(report: Mapping[str, object]) -> bytes:
    """Deterministic UTF-8 encoding: sorted keys, two-space indentation, a final newline."""
    text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")
