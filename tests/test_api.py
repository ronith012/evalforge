# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Python API and command-line parity (TEST_STRATEGY TST-CLI; CLI_SPECIFICATION §1.2).

For identical inputs, the command line's JSON output and the Python API must describe the same
result. Comparison identifiers and timestamps differ between calls by design and are removed before
comparing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import evalforge
from cli_project import Project, invoke
from evalforge import api
from evalforge.errors import EvalForgeError
from evalforge.reporting.comparison_text import render_comparison

VOLATILE = ("comparison_id", "created_at")


def _stable(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key not in VOLATILE}


def test_dataset_validate_matches_the_api(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project.root / "dataset.jsonl"
    _, out, _ = invoke(capsys, ["dataset", "validate", str(path), "--format", "json"])
    assert json.loads(out) == api.dataset_document(api.validate_dataset(path))


def test_config_validate_matches_the_api(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, _ = invoke(
        capsys, ["config", "validate", str(project.config), "--check-dataset", "--format", "json"]
    )
    expected = api.validate_config(project.config, check_dataset=True)
    assert json.loads(out) == expected


def test_run_matches_the_api_in_counts(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    project.target.WRONG.add("c4")
    _, out, _ = invoke(
        capsys, ["run", "--config", str(project.config), "--format", "json", "--fail-on", "fail"]
    )
    cli = json.loads(out)
    result = api.run_configured(project.config, fail_on=["fail"])
    assert result.stored.summary is not None
    assert cli["counts"] == result.stored.summary["counts"]
    assert cli["fail_on_matches"] == result.fail_on_matches


def test_inspect_matches_the_api(project: Project, capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_id = str(json.loads(out)["run_id"])
    root = project.run_root
    _, out, _ = invoke(
        capsys, ["inspect", run_id, "--run-root", str(root), "--format", "json", "--status", "pass"]
    )
    expected = api.inspect_document(api.inspect_run(run_id, root), status="pass")
    assert json.loads(out) == expected


def test_compare_matches_the_api(project: Project, capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    baseline = str(json.loads(out)["run_id"])
    project.target.WRONG.add("c1")
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    candidate = str(json.loads(out)["run_id"])
    project.target.WRONG.clear()

    _, out, _ = invoke(
        capsys,
        ["compare", baseline, candidate, "--run-root", str(project.run_root), "--format", "json"],
    )
    result = api.compare_stored(baseline, candidate, run_root=project.run_root)
    assert _stable(json.loads(out)) == _stable(result.to_dict())
    assert result.comparison.exit_status == "regression"


def test_report_export_matches_the_api(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_id = str(json.loads(out)["run_id"])
    target = project.root / "export.json"
    invoke(
        capsys,
        ["report", "export", run_id, "--run-root", str(project.run_root), "--out", str(target)],
    )
    assert target.read_bytes() == api.export_bytes(
        run_id, run_root=project.run_root, fmt="json", include_io=False
    )


# API-only behaviour -----------------------------------------------------------------------------


def test_api_run_rejects_an_unknown_io_mode(project: Project) -> None:
    with pytest.raises(EvalForgeError) as exc:
        api.run_configured(project.config, io_mode="everything")
    assert exc.value.code == "USAGE_ERROR"


def test_api_run_rejects_case_and_tag_selection_together(project: Project) -> None:
    with pytest.raises(EvalForgeError) as exc:
        api.run_configured(project.config, case_ids=["c1"], tags=["smoke"])
    assert exc.value.code == "USAGE_ERROR"


def test_api_run_rejects_an_unknown_fail_on_status(project: Project) -> None:
    with pytest.raises(EvalForgeError) as exc:
        api.run_configured(project.config, fail_on=["passed"])
    assert exc.value.code == "USAGE_ERROR"


def test_api_run_does_not_execute_an_invalid_dataset(project: Project) -> None:
    (project.root / "dataset.jsonl").write_text("not json\n", encoding="utf-8")
    with pytest.raises(EvalForgeError) as exc:
        api.run_configured(project.config)
    assert exc.value.code.startswith("DATASET")
    assert not project.run_root.exists()


def test_api_resolve_run_requires_a_long_enough_prefix(project: Project) -> None:
    with pytest.raises(EvalForgeError) as exc:
        api.resolve_run("abc", project.run_root)
    assert exc.value.code == "RUN_NOT_FOUND"


def test_api_checked_limit_bounds() -> None:
    assert api.checked_limit(0) == api.INSPECT_LIMIT_MAX
    assert api.checked_limit(7) == 7
    with pytest.raises(EvalForgeError):
        api.checked_limit(api.INSPECT_LIMIT_MAX + 1)


def test_api_export_refuses_io_for_a_comparison_file(tmp_path: Path) -> None:
    comparison = tmp_path / "comparison.json"
    comparison.write_text(
        json.dumps(
            {"schema_version": "1.0", "baseline": {}, "candidate": {}, "cases": [], "findings": []}
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalForgeError) as exc:
        api.export_bytes(str(comparison), run_root=tmp_path, fmt="json", include_io=True)
    assert exc.value.code == "IO_NOT_STORED"


def test_package_exports_the_public_operations() -> None:
    for name in evalforge.__all__:
        assert hasattr(evalforge, name), name
    assert evalforge.__version__ == "0.0.0.dev0"


def test_compare_text_matches_the_shared_renderer(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    baseline = str(json.loads(out)["run_id"])
    project.target.WRONG.add("c2")
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    candidate = str(json.loads(out)["run_id"])
    project.target.WRONG.clear()
    _, text, _ = invoke(
        capsys, ["compare", baseline, candidate, "--run-root", str(project.run_root)]
    )
    result = api.compare_stored(baseline, candidate, run_root=project.run_root)
    assert text == render_comparison(result.to_dict())
