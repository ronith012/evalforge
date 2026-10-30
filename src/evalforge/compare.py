# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Run comparison (EVALUATION_METHODOLOGY §5; TRD §8; ARTIFACT_INTEGRITY §6; DATA_MODELS §11).

Comparing two stored runs:

1. Both runs must be COMPLETED (TRD-130). The reader checks integrity before this module is called.
2. Dataset and evaluator definitions must match. A difference refuses the comparison unless the
   matching explicit flag is given (OD-09). Refusals list every problem found (TRD-135).
3. A flag that was needed is recorded as an override, with what was observed. An overridden
   comparison carries a ``COMPARISON_OVERRIDDEN`` warning. ``strict=True`` refuses any overridden
   comparison (TRD-137, TRD-138).
4. Each case is classified (TRD §8.2). A FAIL to ERROR change is ``changed``, not a regression
   (OD-13, recommended and applied).

5. Regression findings are computed from the case categories and metrics with the ``[regression]``
   thresholds (TRD §9; see ``evalforge.regression``). ``exit_status`` is ``"refused"``,
   ``"regression"`` (a finding of severity ``error`` exists), or ``"pass"``.

Output is deterministic: cases are sorted by case ID by code point. Only ``comparison_id`` and
``created_at`` vary.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, cast

from evalforge.config import RegressionSettings
from evalforge.reader import StoredRun
from evalforge.regression import DEFAULT_THRESHOLDS, Finding, regression_findings
from evalforge.status import RunStatus, Status
from evalforge.store import utc_now

COMPARISON_SCHEMA_VERSION: Final = "1.0"
FLAG_DATASET: Final = "--allow-dataset-change"
FLAG_EVALUATORS: Final = "--allow-evaluator-change"
REGRESSED_TO: Final = {
    Status.FAIL: "to_fail",
    Status.ERROR: "to_error",
    Status.INCONCLUSIVE: "to_inconclusive",
}


@dataclass(frozen=True, slots=True)
class Override:
    """A flag that was needed to compare two runs, and what it overrode."""

    flag: str
    scope: str
    observed: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "flag": self.flag,
            "scope": self.scope,
            "observed": dict(self.observed),
        }


@dataclass(frozen=True, slots=True)
class Refusal:
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class CaseComparison:
    case_id: str
    category: str
    subtype: str | None
    baseline_status: str | None
    candidate_status: str | None
    baseline_output_sha256: str | None
    candidate_output_sha256: str | None
    output_changed: bool | None
    evaluators_changed: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "subtype": self.subtype,
            "baseline_status": self.baseline_status,
            "candidate_status": self.candidate_status,
            "baseline_output_sha256": self.baseline_output_sha256,
            "candidate_output_sha256": self.candidate_output_sha256,
            "output_changed": self.output_changed,
            "evaluators_changed": list(self.evaluators_changed),
        }


@dataclass(frozen=True, slots=True)
class RunRef:
    run_id: str
    path: str
    dataset_sha256: str
    canonical_sha256: str
    target_name: str
    io_mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "path": self.path,
            "dataset_sha256": self.dataset_sha256,
            "canonical_sha256": self.canonical_sha256,
            "target_name": self.target_name,
            "io_mode": self.io_mode,
        }


@dataclass(frozen=True, slots=True)
class Comparison:
    baseline: RunRef
    candidate: RunRef
    refusals: tuple[Refusal, ...]
    overrides: tuple[Override, ...]
    findings: tuple[Finding, ...]
    dataset_status: str
    evaluators_status: str
    io_available: Mapping[str, bool]
    counts: Mapping[str, Mapping[str, int]] | None
    cases: tuple[CaseComparison, ...]
    metrics: Mapping[str, object] | None
    comparison_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)

    @property
    def refused(self) -> bool:
        return bool(self.refusals)

    @property
    def exit_status(self) -> str:
        if self.refused:
            return "refused"
        if any(item.severity == "error" for item in self.findings):
            return "regression"
        return "pass"

    def to_dict(self) -> dict[str, object]:
        """Deterministic JSON form (DATA_MODELS §11).

        Only ``comparison_id`` and ``created_at`` vary between runs of the same comparison.
        """
        return {
            "schema_version": COMPARISON_SCHEMA_VERSION,
            "comparison_id": self.comparison_id,
            "created_at": self.created_at,
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "compatibility": {
                "dataset": self.dataset_status,
                "evaluators": self.evaluators_status,
                "allowed": sorted({item.flag for item in self.overrides}),
                "overrides": [item.to_dict() for item in self.overrides],
                "io_available": dict(self.io_available),
                "warnings": [item.code for item in self.findings if item.severity == "warning"],
                "refusals": [item.code for item in self.refusals],
            },
            "refusals": [item.to_dict() for item in self.refusals],
            "counts": None
            if self.counts is None
            else {key: dict(value) for key, value in self.counts.items()},
            "cases": [item.to_dict() for item in self.cases],
            "metrics": None if self.metrics is None else dict(self.metrics),
            "findings": [item.to_dict() for item in self.findings],
            "exit_status": self.exit_status,
        }


def _cases_by_id(run: StoredRun) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for case in run.cases():
        result[case.case_id] = {
            "status": case.status,
            "case_sha256": case.case_sha256,
            "output_sha256": case.output_sha256,
            "evaluators": {item.name: item.status for item in case.evaluators},
        }
    return result


def _run_ref(run: StoredRun) -> RunRef:
    manifest = run.manifest
    dataset = cast(Mapping[str, object], manifest.get("dataset", {}))
    target = cast(Mapping[str, object], manifest.get("target", {}))
    return RunRef(
        run_id=str(manifest.get("run_id", "")),
        path=str(run.path.name),
        dataset_sha256=str(dataset.get("sha256", "")),
        canonical_sha256=str(dataset.get("canonical_sha256", "")),
        target_name=str(target.get("name", "")),
        io_mode=str(manifest.get("io_mode", "")),
    )


def _fingerprints(run: StoredRun) -> dict[str, str]:
    result: dict[str, str] = {}
    raw = run.manifest.get("evaluators", [])
    for item in cast(list[object], raw if isinstance(raw, list) else []):
        record = cast(Mapping[str, object], item)
        result[str(record.get("name", ""))] = str(record.get("fingerprint", ""))
    return result


def _category(base: Status, cand: Status) -> tuple[str, str | None]:
    """Status categories for a case present in both runs (TRD §8.2)."""
    if base is Status.PASS and cand in REGRESSED_TO:
        return "regressed", REGRESSED_TO[cand]
    if base in REGRESSED_TO and cand is Status.PASS:
        return "recovered", None
    if base is cand:
        return "unchanged", None
    return "changed", None


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _metrics(run: StoredRun) -> dict[str, object]:
    summary = cast(Mapping[str, object], run.summary or {})
    counts = cast(Mapping[str, int], summary.get("counts", {}))
    executed = int(cast(int, summary.get("executed", 0)))
    latency = cast(Mapping[str, object], summary.get("latency_ms") or {})
    return {
        "pass_rate": summary.get("pass_rate"),
        "error_rate": _rate(int(counts.get("ERROR", 0)), executed),
        "inconclusive_rate": _rate(int(counts.get("INCONCLUSIVE", 0)), executed),
        "counts": dict(counts),
        "latency_p50_ms": latency.get("p50"),
        "latency_p95_ms": latency.get("p95"),
        "executed": executed,
    }


def _delta(base: object, cand: object) -> float | None:
    if isinstance(base, int | float) and isinstance(cand, int | float):
        return float(cand) - float(base)
    return None


def _metrics_block(baseline: StoredRun, candidate: StoredRun) -> dict[str, object]:
    base = _metrics(baseline)
    cand = _metrics(candidate)
    delta = {
        key: _delta(base[key], cand[key])
        for key in (
            "pass_rate",
            "error_rate",
            "inconclusive_rate",
            "latency_p50_ms",
            "latency_p95_ms",
        )
    }
    return {"baseline": base, "candidate": cand, "delta": delta}


def compare_runs(
    baseline: StoredRun,
    candidate: StoredRun,
    *,
    allow_dataset_change: bool = False,
    allow_evaluator_change: bool = False,
    strict: bool = False,
    thresholds: RegressionSettings = DEFAULT_THRESHOLDS,
) -> Comparison:
    """Compare two stored runs. Refusals and overrides are returned as data, never raised."""
    refusals: list[Refusal] = []
    overrides: list[Override] = []
    findings: list[Finding] = []

    for label, run in (("baseline", baseline), ("candidate", candidate)):
        if run.status is not RunStatus.COMPLETED:
            refusals.append(
                Refusal(
                    "RUN_INCOMPLETE",
                    f"the {label} run is {run.status.value}; only COMPLETED runs can be compared",
                )
            )

    base_ref = _run_ref(baseline)
    cand_ref = _run_ref(candidate)

    dataset_status = "same"
    if base_ref.canonical_sha256 != cand_ref.canonical_sha256:
        dataset_status = "changed"
        observed = {"baseline": base_ref.canonical_sha256, "candidate": cand_ref.canonical_sha256}
        if allow_dataset_change:
            overrides.append(Override(FLAG_DATASET, "dataset", observed))
            findings.append(
                Finding("DATASET_CHANGED", "warning", "The canonical dataset hashes differ.")
            )
        else:
            refusals.append(
                Refusal(
                    "DATASET_CHANGED",
                    "the canonical dataset hashes differ; "
                    "use --allow-dataset-change to compare anyway",
                )
            )
    elif base_ref.dataset_sha256 != cand_ref.dataset_sha256:
        findings.append(
            Finding(
                "RAW_BYTES_CHANGED", "info", "The dataset bytes differ but its cases are identical."
            )
        )

    base_fp = _fingerprints(baseline)
    cand_fp = _fingerprints(candidate)
    changed_evaluators = tuple(
        sorted(
            name for name in set(base_fp) | set(cand_fp) if base_fp.get(name) != cand_fp.get(name)
        )
    )
    evaluators_status = "changed" if changed_evaluators else "same"
    if changed_evaluators:
        observed_fp = {
            "baseline": ",".join(sorted(base_fp)),
            "candidate": ",".join(sorted(cand_fp)),
            "changed": ",".join(changed_evaluators),
        }
        if allow_evaluator_change:
            overrides.append(Override(FLAG_EVALUATORS, "evaluators", observed_fp))
            findings.append(
                Finding(
                    "EVALUATOR_CHANGED",
                    "warning",
                    "The evaluator definitions differ: " + ", ".join(changed_evaluators),
                )
            )
        else:
            refusals.append(
                Refusal(
                    "EVALUATOR_CHANGED",
                    "the evaluator definitions differ ("
                    + ", ".join(changed_evaluators)
                    + "); use --allow-evaluator-change to compare anyway",
                )
            )

    io_available = {
        "baseline": base_ref.io_mode != "none",
        "candidate": cand_ref.io_mode != "none",
    }
    if not all(io_available.values()):
        findings.append(
            Finding(
                "IO_UNAVAILABLE",
                "warning",
                "At least one run stored no output; output changes are unknown.",
            )
        )

    if overrides and strict:
        refusals.append(
            Refusal(
                "COMPARISON_OVERRIDDEN",
                "an override was needed and strict mode refuses overridden comparisons",
            )
        )
    if overrides and not strict:
        findings.append(
            Finding(
                "COMPARISON_OVERRIDDEN",
                "warning",
                "The comparison was overridden: " + ", ".join(item.flag for item in overrides),
            )
        )

    if refusals:
        return Comparison(
            baseline=base_ref,
            candidate=cand_ref,
            refusals=tuple(refusals),
            overrides=tuple(overrides),
            findings=tuple(findings),
            dataset_status=dataset_status,
            evaluators_status=evaluators_status,
            io_available=io_available,
            counts=None,
            cases=(),
            metrics=None,
        )

    base_cases = _cases_by_id(baseline)
    cand_cases = _cases_by_id(candidate)
    rows: list[CaseComparison] = []
    for case_id in sorted(set(base_cases) | set(cand_cases)):
        before = base_cases.get(case_id)
        after = cand_cases.get(case_id)
        if before is None and after is not None:
            rows.append(_one_sided(case_id, "new_in_candidate", after, "candidate"))
            continue
        if after is None and before is not None:
            rows.append(_one_sided(case_id, "missing_in_candidate", before, "baseline"))
            continue
        if before is None or after is None:
            continue
        base_status = cast(Status, before["status"])
        cand_status = cast(Status, after["status"])
        base_out = cast("str | None", before["output_sha256"])
        cand_out = cast("str | None", after["output_sha256"])
        output_changed = None if base_out is None or cand_out is None else base_out != cand_out
        case_changed = tuple(
            name
            for name in changed_evaluators
            if name in cast(Mapping[str, object], before["evaluators"])
            or name in cast(Mapping[str, object], after["evaluators"])
        )
        if allow_dataset_change and before["case_sha256"] != after["case_sha256"]:
            category, subtype = "changed_input", None
        else:
            category, subtype = _category(base_status, cand_status)
        rows.append(
            CaseComparison(
                case_id=case_id,
                category=category,
                subtype=subtype,
                baseline_status=base_status.value,
                candidate_status=cand_status.value,
                baseline_output_sha256=base_out,
                candidate_output_sha256=cand_out,
                output_changed=output_changed,
                evaluators_changed=case_changed,
            )
        )

    counts = {
        "baseline": _tally(base_cases),
        "candidate": _tally(cand_cases),
    }
    tally = _category_tally(rows)
    counts_block: dict[str, Mapping[str, int]] = {"categories": tally, **counts}
    metrics = _metrics_block(baseline, candidate)
    findings.extend(
        regression_findings(
            rows,
            cast(Mapping[str, object], metrics["baseline"]),
            cast(Mapping[str, object], metrics["candidate"]),
            thresholds,
        )
    )

    return Comparison(
        baseline=base_ref,
        candidate=cand_ref,
        refusals=(),
        overrides=tuple(overrides),
        findings=tuple(findings),
        dataset_status=dataset_status,
        evaluators_status=evaluators_status,
        io_available=io_available,
        counts=counts_block,
        cases=tuple(rows),
        metrics=metrics,
    )


def _one_sided(
    case_id: str,
    category: str,
    record: Mapping[str, object],
    side: str,
) -> CaseComparison:
    """A case present in only one run: no status category applies, only that side is filled."""
    status = cast(Status, record["status"]).value
    output = cast("str | None", record["output_sha256"])
    return CaseComparison(
        case_id=case_id,
        category=category,
        subtype=None,
        baseline_status=status if side == "baseline" else None,
        candidate_status=status if side == "candidate" else None,
        baseline_output_sha256=output if side == "baseline" else None,
        candidate_output_sha256=output if side == "candidate" else None,
        output_changed=None,
    )


def _tally(cases: Mapping[str, Mapping[str, object]]) -> dict[str, int]:
    counts = {status.value: 0 for status in Status}
    for record in cases.values():
        counts[cast(Status, record["status"]).value] += 1
    return counts


def _category_tally(rows: list[CaseComparison]) -> dict[str, int]:
    names = (
        "regressed",
        "recovered",
        "unchanged",
        "changed",
        "missing_in_candidate",
        "new_in_candidate",
        "changed_input",
    )
    tally = {name: 0 for name in names}
    for row in rows:
        tally[row.category] += 1
    return tally
