# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Traceability check (TST-DOC-004; docs/TRACEABILITY.md).

Every requirement ID in the PRD and TRD must be cited by a test file or listed in the register with
a status. A test name given as evidence for a *Verified* or *Partly* row must exist.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO: Final = Path(__file__).resolve().parent.parent
STATUSES: Final = frozenset(
    {
        "Verified",
        "Partly",
        "Open",
        "Deferred",
        "Documented",
        "Not in MVP",
        "Non-goal",
        "Not applicable",
    }
)
ROW: Final = re.compile(r"^\| ((?:PRD-[A-Z]+|TRD)-\d+) \| ([A-Za-z -]+?) \| (.*) \|$", re.M)


def _requirement_ids() -> set[str]:
    text = (REPO / "docs" / "PRD.md").read_text(encoding="utf-8")
    text += (REPO / "docs" / "TRD.md").read_text(encoding="utf-8")
    return set(re.findall(r"\b(?:PRD-[A-Z]+-\d+|TRD-\d+)\b", text))


def _test_sources() -> str:
    return " ".join(path.read_text(encoding="utf-8") for path in (REPO / "tests").rglob("*.py"))


def _register() -> dict[str, tuple[str, str]]:
    text = (REPO / "docs" / "TRACEABILITY.md").read_text(encoding="utf-8")
    return {match.group(1): (match.group(2), match.group(3)) for match in ROW.finditer(text)}


def test_every_requirement_is_cited_by_a_test_or_listed_in_the_register() -> None:  # TST-DOC-004
    sources = _test_sources()
    register = _register()
    uncovered = sorted(
        requirement
        for requirement in _requirement_ids()
        if not re.search(r"(?<![A-Za-z0-9-])" + re.escape(requirement) + r"(?![0-9])", sources)
        and requirement not in register
    )
    assert uncovered == []


def test_register_rows_use_known_statuses_and_only_real_requirements() -> None:  # TST-DOC-004
    register = _register()
    assert {status for status, _ in register.values()} <= STATUSES
    assert set(register) <= _requirement_ids()


def test_evidence_names_for_verified_and_partly_rows_exist() -> None:  # TST-DOC-004
    sources = _test_sources()
    missing: list[str] = []
    for requirement, (status, evidence) in _register().items():
        if status not in {"Verified", "Partly"}:
            continue
        names = re.findall(r"\btest_[a-z0-9_]+", evidence)
        if not names:
            missing.append(f"{requirement}: no test named")
        for name in names:
            if not re.search(r"^def " + re.escape(name) + r"\b", sources, re.M):
                missing.append(f"{requirement}: {name}")
    assert missing == []
