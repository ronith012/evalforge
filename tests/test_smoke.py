# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for the package and its public names."""

import evalforge


def test_package_imports_and_reports_version() -> None:
    assert evalforge.__version__ == "0.0.0.dev0"


def test_public_names_are_declared() -> None:
    # Milestone 11 exposes the public operations (API_DESIGN §2 subset; see the milestone record).
    assert "__version__" in evalforge.__all__
    assert "run_configured" in evalforge.__all__
    assert evalforge.__all__ == sorted(evalforge.__all__)
