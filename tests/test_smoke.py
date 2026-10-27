# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for the Milestone 1 skeleton."""

import evalforge


def test_package_imports_and_reports_version() -> None:
    assert evalforge.__version__ == "0.0.0.dev0"


def test_public_names_are_declared() -> None:
    assert evalforge.__all__ == ["__version__"]
