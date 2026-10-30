# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Text view of a comparison (CLI_SPECIFICATION §3.5; PRD-F-024; SECURITY §6).

The renderer reads the JSON form of a comparison (``Comparison.to_dict`` with
``thresholds_source``).
It is the same for a fresh comparison and for a comparison file read back, so the two always agree.
Every value shown passes through ``sanitize_text``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from evalforge.reporting.sanitize import sanitize_text


def _map(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, dict) else {}


def _items(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(Mapping[str, object], item) for item in value if isinstance(item, dict)]


def _rate(value: object) -> str:
    return (
        f"{value:.3f}" if isinstance(value, float | int) and not isinstance(value, bool) else "n/a"
    )


def _text(value: object) -> str:
    return "n/a" if value is None else str(value)


def render_comparison(document: Mapping[str, object]) -> str:
    """Text form of a comparison document. Refusals, overrides, findings, and the verdict."""
    baseline = _map(document.get("baseline"))
    candidate = _map(document.get("candidate"))
    compatibility = _map(document.get("compatibility"))
    lines = [
        f"Comparison: baseline {_text(baseline.get('run_id'))} -> "
        f"candidate {_text(candidate.get('run_id'))}",
        f"Thresholds: {_text(document.get('thresholds_source'))}",
        f"Dataset: {_text(compatibility.get('dataset'))}   "
        f"Evaluators: {_text(compatibility.get('evaluators'))}",
    ]
    overrides = _items(compatibility.get("overrides"))
    if overrides:
        lines.append("COMPARISON OVERRIDDEN")
        for item in overrides:
            lines.append(f"  {_text(item.get('flag'))}: {_text(item.get('scope'))} differs")
    for refusal in _items(document.get("refusals")):
        lines.append(f"refused {_text(refusal.get('code'))}: {_text(refusal.get('message'))}")
    counts = _map(document.get("counts"))
    if counts:
        categories = _map(counts.get("categories"))
        lines.append("Cases: " + "  ".join(f"{name} {count}" for name, count in categories.items()))
    metrics = _map(document.get("metrics"))
    if metrics:
        base_rate = _map(metrics.get("baseline")).get("pass_rate")
        cand_rate = _map(metrics.get("candidate")).get("pass_rate")
        lines.append(f"Pass rate: {_rate(base_rate)} -> {_rate(cand_rate)}")
    findings = _items(document.get("findings"))
    for finding in findings:
        lines.append(
            f"{_text(finding.get('severity')):<8} {_text(finding.get('code'))}: "
            f"{_text(finding.get('message'))}"
        )
        threshold = finding.get("threshold")
        if isinstance(threshold, dict):
            lines.append(
                f"           threshold: {_text(threshold.get('key'))} = "
                f"{_text(threshold.get('configured'))}, observed {_text(threshold.get('observed'))}"
            )
    errors = sum(1 for item in findings if item.get("severity") == "error")
    status = document.get("exit_status")
    verdict = {
        "refused": "REFUSED",
        "regression": f"REGRESSION ({errors} error finding(s))",
        "pass": "PASS",
    }.get(str(status), "UNKNOWN")
    lines.append(f"Result: {verdict}")
    return "\n".join(sanitize_text(line) for line in lines) + "\n"
