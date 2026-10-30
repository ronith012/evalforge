# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Regression detection (TRD §9; EVALUATION_METHODOLOGY §6; DATA_MODELS §12).

Thresholds come from the ``[regression]`` table of the configuration. Without a configuration,
``DEFAULT_THRESHOLDS`` applies. These are the TRD §9.1 proposed defaults, still subject to OD-08.
Every threshold finding names its threshold key, the configured value, and what was observed.

Two rules are fixed by design:

- an infrastructure error is never a ``CASE_REGRESSED_TO_FAIL`` finding (TRD §9.2). A case that
  passed and now errors is ``CASE_REGRESSED_TO_ERROR``;
- a rate check with too little data is skipped with ``RATE_CHECK_SKIPPED`` (TRD-142). It is never
  reported as a regression.

Messages are fixed templates. Golden tests pin them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from evalforge.config import RegressionSettings

if TYPE_CHECKING:
    from evalforge.compare import CaseComparison

DEFAULT_THRESHOLDS: Final = RegressionSettings(
    max_newly_failing=0,
    max_newly_errored=0,
    inconclusive_as_regression=False,
    max_pass_rate_drop=0.0,
    min_executed_for_rate_check=30,
    max_p95_latency_ratio=None,
    missing_case_policy="fail",
)


@dataclass(frozen=True, slots=True)
class Finding:
    """One result of the comparison: a warning, an information note, or a regression (error)."""

    code: str
    severity: str
    message: str
    case_ids: tuple[str, ...] = field(default=())
    threshold: Mapping[str, object] | None = None
    metric: str | None = None
    values: Mapping[str, float] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "case_ids": list(self.case_ids),
            "threshold": None if self.threshold is None else dict(self.threshold),
            "metric": self.metric,
            "values": None if self.values is None else dict(self.values),
        }


def _ids(
    rows: Sequence[CaseComparison], category: str, subtype: str | None = None
) -> tuple[str, ...]:
    return tuple(
        sorted(
            row.case_id
            for row in rows
            if row.category == category and (subtype is None or row.subtype == subtype)
        )
    )


def _listing(ids: Sequence[str]) -> str:
    return ", ".join(ids)


def _cases(count: int) -> str:
    return "case" if count == 1 else "cases"


def _choose(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def _threshold(key: str, configured: object, observed: object) -> dict[str, object]:
    return {"key": f"regression.{key}", "configured": configured, "observed": observed}


def _case_findings(rows: Sequence[CaseComparison], thresholds: RegressionSettings) -> list[Finding]:
    findings: list[Finding] = []

    to_fail = _ids(rows, "regressed", "to_fail")
    if len(to_fail) > thresholds.max_newly_failing:
        findings.append(
            Finding(
                "CASE_REGRESSED_TO_FAIL",
                "error",
                f"{len(to_fail)} {_cases(len(to_fail))} that passed in the baseline now "
                f"{_choose(len(to_fail), 'fails', 'fail')}: {_listing(to_fail)}.",
                case_ids=to_fail,
                threshold=_threshold(
                    "max_newly_failing", thresholds.max_newly_failing, len(to_fail)
                ),
            )
        )

    to_error = _ids(rows, "regressed", "to_error")
    if len(to_error) > thresholds.max_newly_errored:
        findings.append(
            Finding(
                "CASE_REGRESSED_TO_ERROR",
                "error",
                f"{len(to_error)} {_cases(len(to_error))} that passed in the baseline now "
                f"{_choose(len(to_error), 'errors', 'error')}: {_listing(to_error)}.",
                case_ids=to_error,
                threshold=_threshold(
                    "max_newly_errored", thresholds.max_newly_errored, len(to_error)
                ),
            )
        )

    to_inconclusive = _ids(rows, "regressed", "to_inconclusive")
    if to_inconclusive:
        as_error = thresholds.inconclusive_as_regression
        findings.append(
            Finding(
                "CASE_REGRESSED_TO_INCONCLUSIVE",
                "error" if as_error else "warning",
                f"{len(to_inconclusive)} {_cases(len(to_inconclusive))} that passed in the "
                f"baseline {_choose(len(to_inconclusive), 'is', 'are')} now inconclusive: "
                f"{_listing(to_inconclusive)}.",
                case_ids=to_inconclusive,
                threshold=(
                    _threshold("inconclusive_as_regression", as_error, len(to_inconclusive))
                    if as_error
                    else None
                ),
            )
        )

    missing = _ids(rows, "missing_in_candidate")
    if missing and thresholds.missing_case_policy != "ignore":
        severity = "error" if thresholds.missing_case_policy == "fail" else "warning"
        findings.append(
            Finding(
                "CASE_MISSING_IN_CANDIDATE",
                severity,
                f"{len(missing)} {_cases(len(missing))} in the baseline "
                f"{_choose(len(missing), 'is', 'are')} missing from the candidate: "
                f"{_listing(missing)}.",
                case_ids=missing,
                threshold=_threshold(
                    "missing_case_policy", thresholds.missing_case_policy, len(missing)
                ),
            )
        )

    new = _ids(rows, "new_in_candidate")
    if new:
        findings.append(
            Finding(
                "CASE_NEW_IN_CANDIDATE",
                "warning",
                f"{len(new)} {_cases(len(new))} {_choose(len(new), 'is', 'are')} new in the "
                f"candidate: {_listing(new)}.",
                case_ids=new,
            )
        )

    recovered = _ids(rows, "recovered")
    if recovered:
        findings.append(
            Finding(
                "CASE_RECOVERED",
                "info",
                f"{len(recovered)} {_cases(len(recovered))} recovered: {_listing(recovered)}.",
                case_ids=recovered,
            )
        )
    return findings


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _executed(metrics: Mapping[str, object]) -> int:
    value = metrics.get("executed", 0)
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _pass_rate_findings(
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
    thresholds: RegressionSettings,
) -> list[Finding]:
    base_rate = _number(baseline.get("pass_rate"))
    cand_rate = _number(candidate.get("pass_rate"))
    if base_rate is None or cand_rate is None:
        return [
            Finding(
                "RATE_CHECK_SKIPPED",
                "warning",
                "Rate check skipped: a run has no executed cases.",
                metric="pass_rate",
            )
        ]
    smallest = min(_executed(baseline), _executed(candidate))
    if smallest < thresholds.min_executed_for_rate_check:
        return [
            Finding(
                "RATE_CHECK_SKIPPED",
                "warning",
                f"Rate check skipped: fewer than {thresholds.min_executed_for_rate_check} "
                f"executed cases in a run (smallest: {smallest}).",
                metric="pass_rate",
                threshold=_threshold(
                    "min_executed_for_rate_check",
                    thresholds.min_executed_for_rate_check,
                    smallest,
                ),
            )
        ]
    # Rounding to 12 places removes binary error, so a drop equal to the limit is not a finding.
    drop = round(base_rate - cand_rate, 12)
    if drop > thresholds.max_pass_rate_drop:
        return [
            Finding(
                "PASS_RATE_DROP",
                "error",
                f"Pass rate fell from {base_rate:.3f} to {cand_rate:.3f} (drop {drop:.3f}), "
                f"above the configured maximum of {thresholds.max_pass_rate_drop:.3f}.",
                threshold=_threshold(
                    "max_pass_rate_drop", thresholds.max_pass_rate_drop, round(drop, 6)
                ),
                metric="pass_rate",
                values={"baseline": base_rate, "candidate": cand_rate, "delta": -drop},
            )
        ]
    return []


def latency_finding(
    baseline_p95: float | None,
    candidate_p95: float | None,
    max_ratio: float,
) -> Finding | None:
    """p95 latency check (TRD-143).

    Skipped with a warning when either p95 is missing or the baseline p95 is zero.
    """
    if baseline_p95 is None or candidate_p95 is None or baseline_p95 <= 0:
        return Finding(
            "RATE_CHECK_SKIPPED",
            "warning",
            "Latency check skipped: a p95 latency is missing or the baseline p95 is zero.",
            metric="latency_p95_ms",
        )
    ratio = candidate_p95 / baseline_p95
    if ratio > max_ratio:
        return Finding(
            "LATENCY_P95_INCREASE",
            "error",
            f"p95 latency rose from {baseline_p95:.1f} ms to {candidate_p95:.1f} ms "
            f"(ratio {ratio:.2f}), above the configured maximum of {max_ratio:.2f}.",
            threshold=_threshold("max_p95_latency_ratio", max_ratio, round(ratio, 6)),
            metric="latency_p95_ms",
            values={"baseline": baseline_p95, "candidate": candidate_p95, "ratio": ratio},
        )
    return None


def regression_findings(
    rows: Sequence[CaseComparison],
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
    thresholds: RegressionSettings = DEFAULT_THRESHOLDS,
) -> tuple[Finding, ...]:
    """All regression findings for one comparison, in a fixed order."""
    findings = _case_findings(rows, thresholds)
    findings.extend(_pass_rate_findings(baseline, candidate, thresholds))
    if thresholds.max_p95_latency_ratio is not None:
        latency = latency_finding(
            _number(baseline.get("latency_p95_ms")),
            _number(candidate.get("latency_p95_ms")),
            thresholds.max_p95_latency_ratio,
        )
        if latency is not None:
            findings.append(latency)
    return tuple(findings)
