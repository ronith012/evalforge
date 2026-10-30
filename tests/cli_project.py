# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Shared test project for the command line and the API (TEST_STRATEGY TST-CLI).

A temporary project holds a configuration, a five-case dataset, and a target module. The target's
``WRONG`` set chooses which cases answer incorrectly, so a test can build a regressed run from the
same dataset. The ``project`` fixture is registered in ``conftest.py``.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

from evalforge.cli import main

TARGET_SOURCE = """\
WRONG: set[str] = set()


def answer(case_input):
    if case_input["id"] in WRONG:
        return "x"
    return case_input["q"]
"""

CONFIG = """\
schema_version = "1.0"

[run]
io_mode = "full"

[dataset]
path = "dataset.jsonl"

[target]
callable = "cli_target:answer"
name = "echo"

[[evaluators]]
name = "exact"
type = "exact_match"
"""

DATASET = "".join(
    f'{{"id": "c{index}", "input": {{"id": "c{index}", "q": "{word}"}}, "expected": "{word}"}}\n'
    for index, word in enumerate(["one", "two", "three", "four", "five"], start=1)
)


class Project:
    def __init__(self, root: Path, target: ModuleType) -> None:
        self.root = root
        self.config = root / "evalforge.toml"
        self.run_root = root / ".evalforge" / "runs"
        self.target = target


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Project:
    (tmp_path / "cli_target.py").write_text(TARGET_SOURCE, encoding="utf-8")
    (tmp_path / "evalforge.toml").write_text(CONFIG, encoding="utf-8")
    (tmp_path / "dataset.jsonl").write_text(DATASET, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("cli_target", None)
    module = importlib.import_module("cli_target")
    monkeypatch.chdir(tmp_path)
    return Project(tmp_path, module)


def invoke(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, str, str]:
    """Run the command line and return (exit status, stdout, stderr)."""
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err
