# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Tests for the scripts in scripts/: the DCO check and the artifact check.

The DCO test builds a real git repository in a temporary directory, so the check runs against real
history. Covers OD-31, OD-32, and TST-E2E-005.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dco = _load("check_dco")
artifacts = _load("check_artifacts")


# DCO ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("message", "signed"),
    [
        ("Add thing\n\nSigned-off-by: Dana Rivera <dana@example.org>\n", True),
        ("Add thing\n\nSigned-off-by: Dana <dana@example>\n", True),
        ("Add thing\n\nReviewed-by: Dana <dana@example.org>\n", False),
        ("Add thing without a trailer\n", False),
    ],
)
def test_signoff_trailer_is_recognised(message: str, signed: bool) -> None:  # OD-31
    assert dco.has_signoff(message) is signed


def _git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.org",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.org",
    }
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_dco_check_fails_for_an_unsigned_commit_and_passes_for_a_signed_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(tmp_path, "init", "-q")
    monkeypatch.chdir(tmp_path)  # the check reads the repository in the current directory
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "unsigned change")
    assert dco.main([base, "HEAD"]) == 1
    _git(
        tmp_path,
        "commit",
        "-q",
        "--amend",
        "--allow-empty",
        "-m",
        "unsigned change\n\nSigned-off-by: Test <test@example.org>",
    )
    assert dco.main([base, "HEAD"]) == 0


def test_dco_check_reports_bad_arguments() -> None:  # OD-32
    assert dco.main(["only-one"]) == 2


# Artifacts ----------------------------------------------------------------------------------------


def _wheel(path: Path, names: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, "x")
    return path


def _sdist(path: Path, names: list[str]) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name in names:
            data = b"x"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, __import__("io").BytesIO(data))
    return path


GOOD_WHEEL = [
    "evalforge/py.typed",
    "evalforge/reporting/schemas/run-report-1.0.schema.json",
    "evalforge-0.0.0.dev0.dist-info/LICENSE",
    "evalforge-0.0.0.dev0.dist-info/NOTICE",
]


def test_a_clean_wheel_passes() -> None:  # TST-E2E-005, PRD-NF-012
    assert artifacts.check_names("w.whl", GOOD_WHEEL) == []


def test_a_wheel_with_tests_or_examples_fails() -> None:  # TST-E2E-005
    problems = artifacts.check_names("w.whl", [*GOOD_WHEEL, "tests/test_x.py", "examples/a/b.py"])
    assert len(problems) == 2


def test_a_wheel_without_licence_or_schema_fails() -> None:  # TRD-011, PRD-NF-012
    problems = artifacts.check_names("w.whl", ["evalforge/py.typed"])
    assert any("LICENSE" in problem for problem in problems)
    assert any("run-report-1.0.schema.json" in problem for problem in problems)


def test_a_source_distribution_may_keep_tests_and_examples() -> None:  # TST-E2E-005
    names = [
        "evalforge-0.0.0.dev0/LICENSE",
        "evalforge-0.0.0.dev0/NOTICE",
        "evalforge-0.0.0.dev0/tests/test_x.py",
        "evalforge-0.0.0.dev0/examples/quickstart/dataset.jsonl",
    ]
    assert artifacts.check_names("s.tar.gz", names) == []


def test_run_directories_are_never_allowed_in_an_artifact() -> None:  # TST-IO-009, THR-012
    names = [*GOOD_WHEEL, "evalforge-0.0.0.dev0/.evalforge/runs/x/manifest.json"]
    assert any(".evalforge" in problem for problem in artifacts.check_names("w.whl", names))


def test_main_checks_real_archives_in_a_directory(tmp_path: Path) -> None:
    _wheel(tmp_path / "evalforge-0.0.0.dev0-py3-none-any.whl", GOOD_WHEEL)
    _sdist(tmp_path / "evalforge-0.0.0.dev0.tar.gz", ["x/LICENSE", "x/NOTICE"])
    assert artifacts.main([str(tmp_path)]) == 0
    _wheel(tmp_path / "bad-0.0.0-py3-none-any.whl", ["tests/a.py"])
    assert artifacts.main([str(tmp_path)]) == 1
