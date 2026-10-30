# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""End-to-end tests (TEST_STRATEGY §4.9: TST-E2E-001 and TST-E2E-002).

The quick start runs the real command line as a subprocess, in a copy of the example directory and
with a minimal environment. The seeded regression pair is compared with its expected findings
manifest.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from evalforge import api

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"
SRC = REPO / "src"


def _evalforge(workdir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the command line in a clean environment: only PATH and the source tree on PYTHONPATH."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(SRC),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, "-m", "evalforge", *args],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_quick_start_from_a_clean_environment(tmp_path: Path) -> None:  # TST-E2E-001, PRD-G-001
    workdir = tmp_path / "quickstart"
    shutil.copytree(EXAMPLES / "quickstart", workdir)

    validated = _evalforge(workdir, "config", "validate")
    assert validated.returncode == 0, validated.stderr
    assert "Configuration valid" in validated.stdout

    dataset = _evalforge(workdir, "dataset", "validate", "dataset.jsonl")
    assert dataset.returncode == 0, dataset.stderr

    first = _evalforge(workdir, "run", "--format", "json")
    assert first.returncode == 0, first.stderr
    first_id = json.loads(first.stdout)["run_id"]
    assert json.loads(first.stdout)["counts"]["PASS"] == 5

    second = _evalforge(workdir, "run", "--format", "json")
    assert second.returncode == 0, second.stderr
    second_id = json.loads(second.stdout)["run_id"]

    inspected = _evalforge(workdir, "inspect", first_id, "--format", "json")
    assert inspected.returncode == 0, inspected.stderr

    compared = _evalforge(workdir, "compare", first_id, second_id, "--format", "json")
    assert compared.returncode == 0, compared.stderr
    document = json.loads(compared.stdout)
    assert document["exit_status"] == "pass"
    assert [item["code"] for item in document["findings"] if item["severity"] == "error"] == []


def test_seeded_regression_pair_produces_the_expected_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # TST-E2E-002, PRD-F-022
    pair = EXAMPLES / "regression_pair"
    monkeypatch.syspath_prepend(str(pair))
    for name in ("baseline_bot", "candidate_bot"):
        sys.modules.pop(name, None)

    baseline = api.run_configured(pair / "baseline.toml", run_root=tmp_path)
    candidate = api.run_configured(pair / "candidate.toml", run_root=tmp_path)
    result = api.compare_stored(
        str(baseline.stored.manifest["run_id"]),
        str(candidate.stored.manifest["run_id"]),
        run_root=tmp_path,
    )
    document = result.to_dict()
    expected = json.loads((pair / "expected_findings.json").read_text(encoding="utf-8"))
    findings = cast(list[dict[str, object]], document["findings"])
    actual = [
        {"code": item["code"], "severity": item["severity"], "case_ids": item["case_ids"]}
        for item in findings
    ]
    assert actual == expected["findings"]
    assert document["exit_status"] == expected["exit_status"]
