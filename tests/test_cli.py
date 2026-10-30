# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Command-line behaviour (CLI_SPECIFICATION §3 and §4; TRD §10; TEST_STRATEGY TST-CLI)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cli_project import CONFIG, DATASET, Project, invoke
from evalforge import api, cli
from evalforge.cli import main

# Configuration and dataset validation ---------------------------------------------------------


def test_config_validate_accepts_a_valid_file(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = invoke(capsys, ["config", "validate", str(project.config)])
    assert code == 0
    assert "Configuration valid" in out
    assert "imports not checked" in out


def test_config_validate_reports_unknown_keys_with_exit_2(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    project.config.write_text(CONFIG + "\n[regression]\nmax_newly_faling = 1\n", encoding="utf-8")
    code, out, err = invoke(capsys, ["config", "validate", str(project.config)])
    assert code == 2
    assert out == ""
    assert "error[CONFIG_UNKNOWN_KEY]" in err


def test_config_validate_json_failure_is_one_json_document(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    project.config.write_text(CONFIG + "\n[regression]\nmax_newly_faling = 1\n", encoding="utf-8")
    code, out, _ = invoke(capsys, ["config", "validate", str(project.config), "--format", "json"])
    assert code == 2
    document = json.loads(out)
    assert document["valid"] is False
    assert document["errors"][0]["code"] == "CONFIG_UNKNOWN_KEY"


def test_config_validate_check_dataset_failure_exits_3(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    (project.root / "dataset.jsonl").write_text(
        DATASET + DATASET.splitlines()[0] + "\n", encoding="utf-8"
    )
    code, _, err = invoke(capsys, ["config", "validate", str(project.config), "--check-dataset"])
    assert code == 3
    assert "DATASET_DUPLICATE_ID" in err


def test_dataset_validate_success(project: Project, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = invoke(capsys, ["dataset", "validate", str(project.root / "dataset.jsonl")])
    assert code == 0
    assert "Dataset valid" in out
    assert "cases:             5" in out


def test_dataset_validate_duplicate_id_exits_3(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project.root / "dataset.jsonl"
    path.write_text(DATASET + DATASET.splitlines()[0] + "\n", encoding="utf-8")
    code, _, err = invoke(capsys, ["dataset", "validate", str(path)])
    assert code == 3
    assert "error[DATASET_DUPLICATE_ID]" in err


def test_dataset_validate_json_failure_is_valid_false(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project.root / "dataset.jsonl"
    path.write_text(DATASET + DATASET.splitlines()[0] + "\n", encoding="utf-8")
    code, out, _ = invoke(capsys, ["dataset", "validate", str(path), "--format", "json"])
    assert code == 3
    assert json.loads(out)["valid"] is False


def test_missing_dataset_file_is_a_usage_error(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = invoke(capsys, ["dataset", "validate", str(project.root / "absent.jsonl")])
    assert code == 2
    assert "error[USAGE_ERROR]" in err


# Run -------------------------------------------------------------------------------------------


def test_run_stores_the_run_and_exits_0(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    assert code == 0
    document = json.loads(out)
    assert document["status"] == "COMPLETED"
    assert document["counts"]["PASS"] == 5
    assert Path(document["stored"]).is_dir()


def test_run_fail_on_a_matching_status_exits_1(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    project.target.WRONG.add("c2")
    code, out, _ = invoke(
        capsys, ["run", "--config", str(project.config), "--format", "json", "--fail-on", "fail"]
    )
    assert code == 1
    assert json.loads(out)["fail_on_matches"] == 1


def test_run_fail_on_without_a_match_exits_0(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    project.target.WRONG.add("c2")
    code, _, _ = invoke(capsys, ["run", "--config", str(project.config), "--fail-on", "error"])
    assert code == 0


def test_run_with_an_unknown_case_is_a_usage_error(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = invoke(capsys, ["run", "--config", str(project.config), "--case", "nope"])
    assert code == 2
    assert "unknown case IDs: nope" in err


def test_run_case_and_tag_together_is_a_usage_error(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = invoke(
        capsys, ["run", "--config", str(project.config), "--case", "c1", "--tag", "smoke"]
    )
    assert code == 2
    assert "error[USAGE_ERROR]" in err


def test_run_no_redaction_is_recorded_and_warned(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = invoke(
        capsys, ["run", "--config", str(project.config), "--format", "json", "--no-redaction"]
    )
    assert code == 0
    assert "redaction is disabled" in err
    assert json.loads(out)["redaction"] is False


def test_run_text_output_has_the_summary_and_footer(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = invoke(capsys, ["run", "--config", str(project.config)])
    assert code == 0
    assert "COMPLETED" in out
    assert "do not establish that the system is safe" in out


# Inspect ---------------------------------------------------------------------------------------


def _first_run_id(project: Project, capsys: pytest.CaptureFixture[str]) -> str:
    """Run the configured target once and return the new run's ID."""
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    return str(json.loads(out)["run_id"])


def test_inspect_accepts_a_unique_id_prefix(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id = _first_run_id(project, capsys)
    code, out, _ = invoke(
        capsys, ["inspect", run_id[:8], "--run-root", str(project.run_root), "--format", "json"]
    )
    assert code == 0
    assert json.loads(out)["run_id"] == run_id


def test_inspect_ambiguous_prefix_lists_the_matches(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id = _first_run_id(project, capsys)
    shutil.copytree(project.run_root / run_id, project.run_root / (run_id[:8] + "-copy"))
    code, _, err = invoke(capsys, ["inspect", run_id[:8], "--run-root", str(project.run_root)])
    assert code == 2
    assert "ambiguous" in err


def test_inspect_case_detail_and_status_filter(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    project.target.WRONG.add("c3")
    run_id = _first_run_id(project, capsys)
    _, out, _ = invoke(
        capsys,
        [
            "inspect",
            run_id,
            "--run-root",
            str(project.run_root),
            "--format",
            "json",
            "--status",
            "fail",
        ],
    )
    rows = json.loads(out)["cases"]
    assert [row["case_id"] for row in rows] == ["c3"]
    _, out, _ = invoke(
        capsys,
        [
            "inspect",
            run_id,
            "--run-root",
            str(project.run_root),
            "--format",
            "json",
            "--case",
            "c3",
        ],
    )
    assert json.loads(out)["case"]["case_id"] == "c3"


def test_inspect_unknown_run_is_a_usage_error(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = invoke(
        capsys, ["inspect", "deadbeefdeadbeef", "--run-root", str(project.run_root)]
    )
    assert code == 2
    assert "RUN_NOT_FOUND" in err


def test_inspect_limit_out_of_range_is_a_usage_error(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id = _first_run_id(project, capsys)
    code, _, _ = invoke(
        capsys, ["inspect", run_id, "--run-root", str(project.run_root), "--limit", "5000"]
    )
    assert code == 2


# Compare ---------------------------------------------------------------------------------------


def _pair(project: Project, capsys: pytest.CaptureFixture[str]) -> tuple[str, str]:
    """A passing baseline and a candidate in which case c1 fails."""
    baseline = _first_run_id(project, capsys)
    project.target.WRONG.add("c1")
    candidate = _first_run_id(project, capsys)
    project.target.WRONG.clear()
    return baseline, candidate


def test_compare_identical_runs_exits_0(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = _first_run_id(project, capsys)
    candidate = _first_run_id(project, capsys)
    code, _, _ = invoke(
        capsys, ["compare", baseline, candidate, "--run-root", str(project.run_root)]
    )
    assert code == 0


def test_compare_regression_exits_1(project: Project, capsys: pytest.CaptureFixture[str]) -> None:
    baseline, candidate = _pair(project, capsys)
    code, out, _ = invoke(
        capsys,
        ["compare", baseline, candidate, "--run-root", str(project.run_root), "--format", "json"],
    )
    assert code == 1
    assert json.loads(out)["exit_status"] == "regression"


def test_compare_text_names_the_findings(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline, candidate = _pair(project, capsys)
    code, out, _ = invoke(
        capsys, ["compare", baseline, candidate, "--run-root", str(project.run_root)]
    )
    assert code == 1
    assert "error    CASE_REGRESSED_TO_FAIL" in out
    assert "Result: REGRESSION" in out


def test_compare_refuses_a_changed_dataset_with_exit_5(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = _first_run_id(project, capsys)
    (project.root / "dataset.jsonl").write_text(
        DATASET.replace('"q": "one"', '"q": "uno"'), encoding="utf-8"
    )
    candidate = _first_run_id(project, capsys)
    code, out, _ = invoke(
        capsys, ["compare", baseline, candidate, "--run-root", str(project.run_root)]
    )
    assert code == 5
    assert "refused DATASET_CHANGED" in out


def test_compare_allowed_override_is_shown_and_strict_refuses_it(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = _first_run_id(project, capsys)
    (project.root / "dataset.jsonl").write_text(
        DATASET.replace('"q": "one"', '"q": "uno"'), encoding="utf-8"
    )
    candidate = _first_run_id(project, capsys)
    base_args = ["compare", baseline, candidate, "--run-root", str(project.run_root)]
    code, out, _ = invoke(capsys, [*base_args, "--allow-dataset-change"])
    assert code == 0
    assert "COMPARISON OVERRIDDEN" in out
    code, _, _ = invoke(capsys, [*base_args, "--allow-dataset-change", "--strict"])
    assert code == 5


def test_compare_out_never_overwrites(project: Project, capsys: pytest.CaptureFixture[str]) -> None:
    baseline = _first_run_id(project, capsys)
    candidate = _first_run_id(project, capsys)
    target = project.root / "comparison.json"
    args = [
        "compare",
        baseline,
        candidate,
        "--run-root",
        str(project.run_root),
        "--out",
        str(target),
    ]
    assert invoke(capsys, args)[0] == 0
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["exit_status"] == "pass"
    code, _, err = invoke(capsys, args)
    assert code == 4
    assert "STORAGE_ERROR" in err


def test_compare_json_failure_is_still_one_json_document(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = invoke(
        capsys,
        [
            "compare",
            "deadbeefdeadbeef",
            "cafecafecafecafe",
            "--run-root",
            str(project.run_root),
            "--format",
            "json",
        ],
    )
    assert code == 2
    assert json.loads(out)["error"]["code"] == "RUN_NOT_FOUND"


# Report export ---------------------------------------------------------------------------------


def test_report_export_json_and_text(project: Project, capsys: pytest.CaptureFixture[str]) -> None:
    run_id = _first_run_id(project, capsys)
    out_json = project.root / "run.json"
    code, _, _ = invoke(
        capsys,
        ["report", "export", run_id, "--run-root", str(project.run_root), "--out", str(out_json)],
    )
    assert code == 0
    assert json.loads(out_json.read_text(encoding="utf-8"))["schema_version"] == "1.0"
    out_text = project.root / "run.txt"
    code, _, _ = invoke(
        capsys,
        [
            "report",
            "export",
            run_id,
            "--run-root",
            str(project.run_root),
            "--format",
            "text",
            "--out",
            str(out_text),
        ],
    )
    assert code == 0
    assert "do not establish" in out_text.read_text(encoding="utf-8")


def test_report_export_include_io_for_text_is_refused(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id = _first_run_id(project, capsys)
    code, _, _ = invoke(
        capsys,
        [
            "report",
            "export",
            run_id,
            "--run-root",
            str(project.run_root),
            "--format",
            "text",
            "--include-io",
            "--out",
            str(project.root / "x.txt"),
        ],
    )
    assert code == 2


def test_report_export_never_overwrites(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    run_id = _first_run_id(project, capsys)
    target = project.root / "exists.json"
    target.write_text("keep", encoding="utf-8")
    code, _, _ = invoke(
        capsys,
        ["report", "export", run_id, "--run-root", str(project.run_root), "--out", str(target)],
    )
    assert code == 4
    assert target.read_text(encoding="utf-8") == "keep"


def test_report_export_accepts_a_comparison_file(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = _first_run_id(project, capsys)
    candidate = _first_run_id(project, capsys)
    comparison = project.root / "comparison.json"
    invoke(
        capsys,
        [
            "compare",
            baseline,
            candidate,
            "--run-root",
            str(project.run_root),
            "--out",
            str(comparison),
        ],
    )
    exported = project.root / "exported.json"
    code, _, _ = invoke(capsys, ["report", "export", str(comparison), "--out", str(exported)])
    assert code == 0
    assert json.loads(exported.read_text(encoding="utf-8"))["exit_status"] == "pass"


# Failures and exit codes ----------------------------------------------------------------------


def test_unexpected_faults_exit_4_without_detail(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(path: str) -> None:
        raise RuntimeError("UNEXPECTED-DETAIL-MARKER")

    monkeypatch.setattr(api, "validate_dataset", explode)
    code, _, err = invoke(capsys, ["dataset", "validate", "dataset.jsonl"])
    assert code == 4
    assert "RuntimeError" in err
    assert "UNEXPECTED-DETAIL-MARKER" not in err


def test_version_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert "evalforge" in capsys.readouterr().out


def test_no_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, _ = invoke(capsys, [])
    assert code == 2


# Progress and comparison text (Milestone 11 deferrals) ------------------------------------------


def test_progress_lines_are_printed_on_a_terminal(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "_stderr_is_terminal", lambda: True)
    code, _, err = invoke(capsys, ["run", "--config", str(project.config)])
    assert code == 0
    for position in range(1, 6):
        assert f"[{position}/5]" in err
    assert "c1  PASS" in err


def test_progress_is_not_printed_for_json_output(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "_stderr_is_terminal", lambda: True)
    _, _, err = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    assert "[1/5]" not in err


def test_comparison_file_exports_as_text(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = _first_run_id(project, capsys)
    candidate = _first_run_id(project, capsys)
    comparison = project.root / "comparison.json"
    invoke(
        capsys,
        [
            "compare",
            baseline,
            candidate,
            "--run-root",
            str(project.run_root),
            "--out",
            str(comparison),
        ],
    )
    exported = project.root / "comparison.txt"
    code, _, _ = invoke(
        capsys, ["report", "export", str(comparison), "--format", "text", "--out", str(exported)]
    )
    assert code == 0
    text = exported.read_text(encoding="utf-8")
    assert text.startswith("Comparison: baseline")
    assert "Result: PASS" in text
