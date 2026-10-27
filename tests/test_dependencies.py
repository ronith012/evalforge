# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Checks that the packaging metadata matches the approved dependency decisions."""

import tomllib
from pathlib import Path
from typing import Any

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _load() -> dict[str, Any]:
    with PYPROJECT.open("rb") as handle:
        data: dict[str, Any] = tomllib.load(handle)
    return data


def test_runtime_dependencies_are_empty() -> None:
    # TRD §3.2 and OD-15: zero third-party runtime dependencies.
    assert _load()["project"]["dependencies"] == []


def test_no_optional_runtime_extras_are_declared() -> None:
    assert "optional-dependencies" not in _load()["project"]


def test_python_versions_match_approved_support() -> None:
    # OD-02: Python 3.11, 3.12, and 3.13.
    assert _load()["project"]["requires-python"] == ">=3.11,<3.14"


def test_build_backend_is_hatchling() -> None:
    # OD-03: Hatchling as the build backend.
    build = _load()["build-system"]
    assert build["build-backend"] == "hatchling.build"
    assert build["requires"] == ["hatchling==1.32.4"]
