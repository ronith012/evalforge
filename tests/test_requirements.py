# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Tests that tie technical requirements (TRD §3 to §11) to behaviour; see docs/TRACEABILITY.md.

Each test names the requirement IDs it verifies. The traceability check (tests/test_traceability.py)
reads these names, so the register cannot claim a test that does not exist.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import evalforge
from cli_project import Project
from evalforge import api, cli
from evalforge.canon import JSONValue
from evalforge.config import config_from_mapping
from evalforge.datasets import Dataset
from evalforge.errors import (
    ConfigError,
    DatasetValidationError,
    EngineError,
    EvalForgeError,
    IntegrityError,
    RunNotFoundError,
    SchemaVersionError,
    StorageError,
    TargetLoadError,
)
from evalforge.evaluators.builtin import ExactMatch
from evalforge.models import Case
from evalforge.objects import Suite
from evalforge.targets import Target, from_callable, invoke_target

SRC = Path(evalforge.__file__).parent


def _base_config(**regression: object) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "dataset": {"path": "d.jsonl"},
        "target": {"callable": "m:f", "name": "t"},
        "evaluators": [{"name": "exact", "type": "exact_match"}],
        "regression": regression,
    }


# Packaging and layout (TRD-003, TRD-171, TRD-173) --------------------------------------------


def test_package_is_pure_python_with_no_compiled_extensions() -> None:  # TRD-003, PRD-NF-006
    compiled = [path for path in SRC.rglob("*") if path.suffix in {".so", ".pyd", ".dylib"}]
    assert compiled == []


def test_package_ships_the_typed_marker() -> None:  # TRD-171
    assert (SRC / "py.typed").is_file()


def test_every_error_derives_from_evalforge_error() -> None:  # TRD-173, TRD-200, TRD-201
    for cls in (
        ConfigError,
        DatasetValidationError,
        EngineError,
        IntegrityError,
        RunNotFoundError,
        SchemaVersionError,
        StorageError,
        TargetLoadError,
    ):
        assert issubclass(cls, EvalForgeError)


# Exit codes (TRD-161, TRD-200) --------------------------------------------------------------


def test_exit_codes_match_the_specification() -> None:  # TRD-161, TRD-200, CLI §1.4
    assert (cli.EXIT_OK, cli.EXIT_REGRESSION, cli.EXIT_REFUSED, cli.EXIT_INFRASTRUCTURE) == (
        0,
        1,
        5,
        4,
    )
    assert evalforge.errors.ERROR_CODES["USAGE_ERROR"].exit_code == 2
    assert evalforge.errors.ERROR_CODES["DATASET_INVALID"].exit_code == 3
    assert evalforge.errors.ERROR_CODES["STORAGE_ERROR"].exit_code == 4
    assert evalforge.errors.ERROR_CODES["RUN_INCOMPLETE"].exit_code == 5


# Configuration (TRD-140, TRD-141, TRD-182, TRD-183, TRD-184) ---------------------------------


def test_unknown_threshold_key_is_a_configuration_error() -> None:  # TRD-140, TRD-182
    with pytest.raises(ConfigError) as exc:
        config_from_mapping(_base_config(max_newly_faling=1))
    assert exc.value.errors[0].code == "CONFIG_UNKNOWN_KEY"


@pytest.mark.parametrize(
    ("value", "accepted"), [(0.0, True), (0.05, True), (1.0, True), (1.5, False)]
)
def test_pass_rate_drop_is_an_absolute_fraction(value: float, accepted: bool) -> None:  # TRD-141
    if accepted:
        assert (
            config_from_mapping(
                _base_config(max_pass_rate_drop=value)
            ).regression.max_pass_rate_drop
            == value
        )
    else:
        with pytest.raises(ConfigError):
            config_from_mapping(_base_config(max_pass_rate_drop=value))


def test_configuration_values_are_not_interpolated_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # TRD-183, THR-011
    monkeypatch.setenv("EVALFORGE_TEST_VALUE", "resolved")
    data = _base_config()
    data["target"] = {"callable": "m:f", "name": "${EVALFORGE_TEST_VALUE}"}
    assert config_from_mapping(data).target.name == "${EVALFORGE_TEST_VALUE}"


def test_relative_dataset_path_is_resolved_against_the_configuration_directory(
    project: Project, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # TRD-184
    config = evalforge.load_config(project.config)
    assert api.dataset_path_for(config, project.config) == project.root / "dataset.jsonl"
    monkeypatch.chdir(tmp_path)  # a different working directory must not change the result
    assert api.run_configured(project.config).stored.path.is_dir()


# Run behaviour (TRD-100, TRD-101, TRD-111, TRD-212, TRD-063) --------------------------------


def test_run_writes_only_under_the_run_root(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    # TRD-212: the CLI does not write files outside the run root.
    before = {path.name for path in project.root.iterdir()}
    code, _, _ = _run_quietly(project, capsys)
    assert code == 0
    after = {path.name for path in project.root.iterdir()}
    assert after - before <= {".evalforge"}


def test_each_run_gets_a_new_directory(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TRD-111
    first = api.run_configured(project.config).stored.path
    second = api.run_configured(project.config).stored.path
    assert first != second
    assert first.is_dir() and second.is_dir()


def test_cases_run_sequentially_in_dataset_order(tmp_path: Path) -> None:  # TRD-100, TRD-101
    order: list[str] = []

    def record(case_input: JSONValue) -> JSONValue:
        assert isinstance(case_input, dict)
        order.append(str(case_input["id"]))
        return "x"

    cases = [Case(id=f"c{index}", input={"id": f"c{index}"}, expected="x") for index in (3, 1, 2)]
    Suite([ExactMatch(name="exact")]).run(Dataset.from_cases(cases), record)
    assert order == ["c3", "c1", "c2"]


def test_duration_is_measured_with_the_monotonic_timer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # TRD-063
    ticks = iter([10.0, 10.5])
    monkeypatch.setattr(time, "perf_counter", lambda: next(ticks))
    result = invoke_target(from_callable(lambda value: "ok"), {"q": 1})
    assert result.result.duration_ms == pytest.approx(500.0)


# Comparisons (TRD-134, TRD-137) ----------------------------------------------------------------


def test_target_name_difference_produces_no_warning(tmp_path: Path) -> None:  # TRD-134
    dataset = Dataset.from_cases([Case(id="c1", input={"q": "one"}, expected="one")])
    suite = Suite([ExactMatch(name="exact")])

    def echo(case_input: JSONValue) -> JSONValue:
        assert isinstance(case_input, dict)
        return case_input["q"]

    first = suite.run(dataset, Target.from_callable(echo, name="bot-v1"), run_root=tmp_path)
    second = suite.run(dataset, Target.from_callable(echo, name="bot-v2"), run_root=tmp_path)
    comparison = evalforge.compare(first, second)
    assert comparison.exit_status == "pass"
    assert [item.code for item in comparison.findings] == ["RATE_CHECK_SKIPPED"]


# Output (TRD-162, TRD-202) ---------------------------------------------------------------------


def test_progress_on_stderr_never_shows_case_inputs(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:  # TRD-162
    marker = "PLAINTEXT-MARKER-4471"
    line = f'{{"id": "c1", "input": {{"id": "c1", "q": "{marker}"}}, "expected": "{marker}"}}'
    (project.root / "dataset.jsonl").write_text(line + "\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_stderr_is_terminal", lambda: True)
    code = cli.main(["run", "--config", str(project.config)])  # text mode shows progress
    err = capsys.readouterr().err
    assert code == 0
    assert "[1/1]" in err
    assert marker not in err


def _run_quietly(project: Project, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = cli.main(["run", "--config", str(project.config), "--format", "json"])
    captured = capsys.readouterr()
    return code, captured.out, captured.err
