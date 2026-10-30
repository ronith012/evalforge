#!/usr/bin/env python3
# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Check the contents of the built sdist and wheel (TST-E2E-005; PRD-NF-012; TRD-011).

Usage: python scripts/check_artifacts.py DIST_DIR

Required: LICENSE and NOTICE in each artifact; py.typed and the report schema in the wheel.
Forbidden everywhere: run directories, virtual environments, build output, and version control data.
Forbidden in the wheel only: tests and examples. A source distribution keeps them, so the tests
can be run from it. The examples are synthetic (see examples/*/README.md).
Exit status 0 means every artifact passed; 1 means at least one check failed; 2 means bad arguments.
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

ALWAYS_FORBIDDEN: frozenset[str] = frozenset({".evalforge", ".venv", ".git", "dist"})
WHEEL_ONLY_FORBIDDEN: frozenset[str] = frozenset({"tests", "examples"})


def _names(artifact: Path) -> list[str]:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            return archive.namelist()
    with tarfile.open(artifact) as archive:
        return archive.getnames()


def check_names(artifact: str, names: Iterable[str]) -> list[str]:
    """Problems found in one artifact's file names. An empty list means it passed."""
    listed = list(names)
    problems: list[str] = []
    basenames = {Path(name).name for name in listed}
    for required in ("LICENSE", "NOTICE"):
        if required not in basenames:
            problems.append(f"{artifact}: {required} is missing")
    if artifact.endswith(".whl"):
        for required in ("py.typed", "run-report-1.0.schema.json"):
            if required not in basenames:
                problems.append(f"{artifact}: {required} is missing")
    forbidden = ALWAYS_FORBIDDEN
    if artifact.endswith(".whl"):
        forbidden = forbidden | WHEEL_ONLY_FORBIDDEN
    for name in listed:
        if set(Path(name).parts) & forbidden:
            problems.append(f"{artifact}: forbidden path {name}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: check_artifacts.py DIST_DIR\n")
        return 2
    artifacts = sorted(Path(argv[0]).glob("*.whl")) + sorted(Path(argv[0]).glob("*.tar.gz"))
    if not artifacts:
        sys.stderr.write("error: no artifacts found\n")
        return 1
    problems: list[str] = []
    for artifact in artifacts:
        problems.extend(check_names(artifact.name, _names(artifact)))
    for problem in problems:
        sys.stderr.write(f"error: {problem}\n")
    if problems:
        return 1
    sys.stdout.write(f"Artifacts passed: {', '.join(item.name for item in artifacts)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
