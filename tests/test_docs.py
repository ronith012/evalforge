# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Documentation checks (TEST_STRATEGY §4.10: TST-DOC-001, TST-DOC-002, TST-DOC-005, TST-DOC-007).

These read the planning and user documents and check them against the code. They do not run the
examples as programs. The CLI examples are parsed with the real argument parser, which is the same
check the command line applies to its own arguments.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Final

import evalforge
from evalforge.cli import build_parser

REPO: Final = Path(__file__).resolve().parent.parent
DOCS: Final = REPO / "docs"


def _section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def _markdown_files() -> list[Path]:
    files = [*REPO.glob("*.md"), *DOCS.glob("*.md"), *REPO.glob("examples/**/*.md")]
    return sorted(set(files))


# TST-DOC-001: every name in the API surface table is exported ------------------------------------


def test_every_name_in_the_api_surface_table_is_exported() -> None:  # TST-DOC-001, PRD-NF-010
    text = (DOCS / "API_DESIGN.md").read_text(encoding="utf-8")
    table = _section(text, "## 2. Public names", "## 3. Creating a dataset")
    names = {
        token
        for line in table.splitlines()
        if line.startswith("|")
        for token in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", line)
    }
    missing = sorted(name for name in names if name not in evalforge.__all__)
    assert missing == []


# TST-DOC-002: every CLI example line uses arguments the parser accepts ---------------------------


def test_every_cli_example_parses_with_the_real_parser() -> None:  # TST-DOC-002, PRD-NF-010
    text = (DOCS / "CLI_SPECIFICATION.md").read_text(encoding="utf-8")
    parser = build_parser()
    rejected: list[str] = []
    checked = 0
    for line in text.splitlines():
        if not line.startswith("$ evalforge "):
            continue
        if "$?" in line or "|" in line or "..." in line:
            continue
        argv = shlex.split(line[2:])[1:]
        checked += 1
        try:
            parser.parse_args(argv)
        except SystemExit:
            rejected.append(line)
    assert checked > 0
    assert rejected == []


# TST-DOC-005: every relative link in the documentation resolves -----------------------------------

_LINK: Final = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def test_every_relative_link_in_the_documentation_resolves() -> None:  # TST-DOC-005
    broken: list[str] = []
    for document in _markdown_files():
        for target in _LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            if not (document.parent / path_part).exists():
                broken.append(f"{document.relative_to(REPO)} -> {target}")
    assert broken == []


# TST-DOC-007: the integrity scope table matches what the manifest hashes --------------------------


def _manifest_hash_keys(manifest: dict[str, object]) -> set[str]:
    keys: set[str] = set()
    for key, value in manifest.items():
        if key.endswith("sha256"):
            keys.add(key)
        if isinstance(value, dict):
            keys.update(f"{key}.{inner}" for inner in value if inner.endswith("sha256"))
    return keys


def test_integrity_scope_table_matches_the_manifest_hash_fields(
    tmp_path: Path,
) -> None:  # TST-DOC-007
    text = (DOCS / "ARTIFACT_INTEGRITY.md").read_text(encoding="utf-8")
    # §2 lists the hashes that exist. A row located at manifest.json is a manifest hash field.
    listed = _section(text, "## 2. Hashes that exist", "## 3. What the file hashes")
    documented: set[str] = set()
    for line in listed.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) > 2 and "manifest.json" in cells[2]:
            documented.update(re.findall(r"`([a-z_.]*sha256)`", cells[1]))
    manifest_path = _make_run_manifest(tmp_path)
    actual = _manifest_hash_keys(json.loads(manifest_path.read_text(encoding="utf-8")))
    assert documented == actual, (documented, actual)
    # §3.1 must state that the manifest itself is not covered by any hash.
    not_covered = _section(text, "### 3.1 Not covered by any hash", "## 4. Verification performed")
    assert "`manifest.json` itself" in not_covered


def _make_run_manifest(root: Path) -> Path:
    from evalforge.datasets import Dataset
    from evalforge.evaluators.builtin import ExactMatch
    from evalforge.models import Case
    from evalforge.objects import Suite

    run = Suite([ExactMatch(name="exact")]).run(
        Dataset.from_cases([Case(id="c1", input={"q": "x"}, expected="x")]),
        lambda case_input: "x",
        run_root=root,
    )
    assert run.path is not None
    return run.path / "manifest.json"
