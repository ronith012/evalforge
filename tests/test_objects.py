# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Object-level Python API (API_DESIGN §2 to §6): datasets, targets, evaluators, suites,
comparisons.

Covers the surface deferred from Milestone 11 (see docs/MILESTONE_11_RECORD.md) and checks it
against the same runner, storage, and comparison code the command line uses.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import evalforge
from cli_project import Project
from evalforge.canon import JSONValue
from evalforge.config import RegressionSettings
from evalforge.datasets import Dataset, parse_dataset_bytes
from evalforge.errors import DatasetValidationError, EvalForgeError, TargetLoadError
from evalforge.evaluators.builtin import ExactMatch
from evalforge.evaluators.custom import CustomEvaluator
from evalforge.models import Case, EvaluatorResult, ValidationError
from evalforge.objects import Run, Suite, compare, load_config, run_from_config
from evalforge.regression import DEFAULT_THRESHOLDS
from evalforge.status import Status
from evalforge.targets import Target, TimedTarget


def _echo(case_input: JSONValue) -> JSONValue:
    assert isinstance(case_input, dict)
    return case_input["q"]


def _cases() -> list[Case]:
    return [
        Case(id="c1", input={"q": "one"}, expected="one"),
        Case(id="c2", input={"q": "two"}, expected="two"),
        Case(id="c3", input={"q": "three"}, expected="wrong"),
    ]


# Dataset ----------------------------------------------------------------------------------------


def test_dataset_from_cases_matches_the_canonical_hash_of_a_file_with_the_same_cases() -> None:
    jsonl = (
        b'{"id": "c1", "input": {"q": "one"}, "expected": "one"}\n'
        b'{"id": "c2", "input": {"q": "two"}, "expected": "two"}\n'
        b'{"id": "c3", "input": {"q": "three"}, "expected": "wrong"}\n'
    )
    built = Dataset.from_cases(_cases())
    filed = parse_dataset_bytes(jsonl, fmt="jsonl")
    assert built.canonical_sha256 == filed.canonical_sha256
    assert built.sha256 == built.canonical_sha256  # no raw file; documented in API_DESIGN §3
    assert built.case_count == 3
    assert built.source_label == "<inline>"


def test_dataset_from_cases_rejects_duplicate_ids() -> None:
    duplicated = [Case(id="same", input={"q": "a"}), Case(id="same", input={"q": "b"})]
    with pytest.raises(DatasetValidationError) as exc:
        Dataset.from_cases(duplicated)
    assert exc.value.code == "DATASET_DUPLICATE_ID"


def test_dataset_load_reads_a_file(tmp_path: Path) -> None:
    path = tmp_path / "d.jsonl"
    path.write_text('{"id": "c1", "input": {"q": "one"}, "expected": "one"}\n', encoding="utf-8")
    assert Dataset.load(path).case_count == 1


# Evaluator results ------------------------------------------------------------------------------


def test_result_factories_set_status_score_and_reason() -> None:
    assert EvaluatorResult.passed("ok").status is Status.PASS
    assert EvaluatorResult.passed("ok").score == 1.0
    failed = EvaluatorResult.fail("CUSTOM_FAIL", "bad")
    assert (failed.status, failed.score, failed.reason_code) == (Status.FAIL, 0.0, "CUSTOM_FAIL")
    errored = EvaluatorResult.error("EVALUATOR_EXCEPTION", "broke")
    assert (errored.status, errored.score) == (Status.ERROR, None)
    assert EvaluatorResult.inconclusive("CUSTOM_UNCERTAIN", "unsure").status is Status.INCONCLUSIVE
    assert EvaluatorResult.skipped("NO_EXPECTED", "none").status is Status.SKIPPED


def test_result_factory_rejects_an_unregistered_reason() -> None:
    with pytest.raises(ValidationError):
        EvaluatorResult.fail("NOT_A_REAL_CODE", "bad")


def test_custom_evaluator_loads_by_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = Path(__file__).parent / "fixtures" / "evaluators"
    monkeypatch.syspath_prepend(str(fixtures))
    evaluator = CustomEvaluator.from_reference("custom_checks:RefundRule", name="domain_rule")
    assert evaluator.name == "domain_rule"


# Targets ----------------------------------------------------------------------------------------


def test_target_from_callable_takes_its_qualified_name() -> None:
    target = Target.from_callable(_echo)
    assert target.name == "_echo"


def test_target_from_reference_resolves_a_module_attribute() -> None:
    target = Target.from_reference("json:dumps")
    assert target.name == "json:dumps"


def test_target_timeout_must_be_in_range() -> None:
    with pytest.raises(TargetLoadError):
        Target.from_callable(_echo, timeout_seconds=0)
    with pytest.raises(TargetLoadError):
        Target.from_callable(_echo, timeout_seconds=True)
    assert isinstance(Target.from_callable(_echo, timeout_seconds=2.0), TimedTarget)


def test_a_target_timeout_overrides_the_run_timeout() -> None:
    def slow(case_input: JSONValue) -> JSONValue:
        time.sleep(0.5)
        return "late"

    suite = Suite([ExactMatch(name="exact")], timeout_seconds=30.0)
    run = suite.run(
        Dataset.from_cases(_cases()[:1]), Target.from_callable(slow, timeout_seconds=0.05)
    )
    counts = run.summary.counts
    assert counts["ERROR"] == 1
    assert run.status.value == "COMPLETED"


# Suite and Run ----------------------------------------------------------------------------------


def test_suite_in_memory_run_has_no_path_and_is_not_comparable() -> None:
    run = Suite([ExactMatch(name="exact")]).run(Dataset.from_cases(_cases()), _echo)
    assert run.path is None
    assert run.summary.counts["PASS"] == 2
    assert run.summary.counts["FAIL"] == 1
    assert run.summary.pass_rate == pytest.approx(2 / 3)
    with pytest.raises(EvalForgeError) as exc:
        _ = run.stored
    assert exc.value.code == "RUN_NOT_FOUND"
    with pytest.raises(EvalForgeError):
        compare(run, run)


def test_suite_stored_run_can_be_compared(tmp_path: Path) -> None:
    dataset = Dataset.from_cases(_cases())
    suite = Suite([ExactMatch(name="exact")])
    baseline = suite.run(dataset, _echo, run_root=tmp_path)
    candidate = suite.run(dataset, _echo, run_root=tmp_path)
    assert baseline.path is not None and baseline.path.is_dir()
    result = compare(baseline, candidate)
    assert result.exit_status == "pass"
    assert result.to_dict()["schema_version"] == "1.0"


def test_suite_validates_its_arguments() -> None:
    with pytest.raises(EvalForgeError):
        Suite([])
    with pytest.raises(EvalForgeError):
        Suite([ExactMatch(name="exact"), ExactMatch(name="exact")])
    with pytest.raises(EvalForgeError):
        Suite([ExactMatch(name="exact")], io_mode="everything")
    with pytest.raises(EvalForgeError):
        Suite([ExactMatch(name="exact")], timeout_seconds=0)


def test_suite_rejects_a_non_callable_target() -> None:
    with pytest.raises(EvalForgeError):
        Suite([ExactMatch(name="exact")]).run(Dataset.from_cases(_cases()), 42)  # type: ignore[arg-type]


def test_compare_refuses_a_changed_dataset_by_default(tmp_path: Path) -> None:
    suite = Suite([ExactMatch(name="exact")])
    baseline = suite.run(Dataset.from_cases(_cases()), _echo, run_root=tmp_path)
    changed = [Case(id="c1", input={"q": "uno"}, expected="one")] + _cases()[1:]
    candidate = suite.run(Dataset.from_cases(changed), _echo, run_root=tmp_path)
    assert compare(baseline, candidate).exit_status == "refused"
    assert compare(baseline, candidate, allow_dataset_change=True).exit_status != "refused"


def test_compare_accepts_run_ids_and_paths(tmp_path: Path) -> None:
    suite = Suite([ExactMatch(name="exact")])
    run = suite.run(Dataset.from_cases(_cases()), _echo, run_root=tmp_path)
    assert compare(str(run.path), run.run_id, run_root=tmp_path).exit_status == "pass"


def test_thresholds_are_the_regression_settings() -> None:
    assert evalforge.Thresholds is RegressionSettings


# Configuration-driven helpers -------------------------------------------------------------------


def test_run_from_config_matches_the_command_line(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    run = run_from_config(project.config)
    assert isinstance(run, Run)
    assert run.summary.counts["PASS"] == 5
    assert run.path is not None


def test_load_config_validates_without_running(project: Project) -> None:
    config = load_config(project.config)
    assert config.target.callable_ref == "cli_target:answer"
    assert config.regression == DEFAULT_THRESHOLDS
