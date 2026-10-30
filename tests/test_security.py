# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Security verification (TEST_STRATEGY §4.8, TST-SEC-001 to TST-SEC-018).

The mapping from threats to these tests is in docs/SECURITY_VERIFICATION_MATRIX.md.

Static checks read the source tree; behavioural checks run the real code paths in a temporary
project. Planted secrets are assembled from fragments, so this file contains no credential-shaped
literal.
"""

from __future__ import annotations

import ast
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Final, cast

import pytest

from cli_project import Project, invoke
from evalforge import api, cli
from evalforge.canon import JSONValue
from evalforge.config import config_from_mapping
from evalforge.datasets import DatasetLimits, parse_dataset_bytes
from evalforge.errors import ConfigError, DatasetValidationError, EvalForgeError, StorageError
from evalforge.evaluators.builtin import RuleBased
from evalforge.models import Case, ValidationError
from evalforge.reporting.json_report import build_run_report
from evalforge.store import acquire_lock

SRC: Final = Path(__file__).resolve().parent.parent / "src" / "evalforge"
SECRET: Final = "sk-" + "TEST" + "0123456789abcdefXYZ"
FORBIDDEN_CALLS: Final = frozenset({"eval", "exec"})
FORBIDDEN_IMPORTS: Final = frozenset({"pickle", "shelve", "marshal", "yaml", "subprocess"})
NETWORK_MODULES: Final = frozenset(
    {"socket", "http", "urllib", "ftplib", "smtplib", "ssl", "xmlrpc", "telnetlib", "requests"}
)


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _parsed() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), str(path))) for path in _source_files()
    ]


def _is_os_system(func: ast.expr) -> bool:
    """True for ``os.system`` only; ``platform.system`` and similar calls are not matched."""
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "system"
        and isinstance(func.value, ast.Name)
        and func.value.id == "os"
    )


def _imported_top_levels(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


# Static checks ---------------------------------------------------------------------------------


def test_no_code_execution_primitives_in_source() -> None:  # TST-SEC-003, TRD-216
    found: list[str] = []
    for path, tree in _parsed():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    found.append(f"{path.name}:{node.lineno} {node.func.id}()")
                if _is_os_system(node.func):
                    found.append(f"{path.name}:{node.lineno} os.system()")
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                        if keyword.value.value is True:
                            found.append(f"{path.name}:{node.lineno} shell=True")
    assert found == []


def test_no_unsafe_deserialisation_or_process_modules_in_source() -> None:  # TST-SEC-003
    found: list[str] = []
    for path, tree in _parsed():
        for name in _imported_top_levels(tree) & FORBIDDEN_IMPORTS:
            found.append(f"{path.name} imports {name}")
    assert found == []


def test_core_imports_only_the_standard_library_and_itself() -> None:  # TST-SEC-005
    allowed = set(sys.stdlib_module_names) | {"evalforge"}
    unexpected = sorted(
        f"{path.name}: {name}"
        for path, tree in _parsed()
        for name in _imported_top_levels(tree) - allowed
    )
    assert unexpected == []


def test_core_source_has_no_network_modules() -> None:  # TST-SEC-004 (static), THR-016
    found = sorted(
        f"{path.name}: {name}"
        for path, tree in _parsed()
        for name in _imported_top_levels(tree) & NETWORK_MODULES
    )
    assert found == []


# Network isolation -----------------------------------------------------------------------------


class _NoSockets:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise OSError("network access is disabled for this test")


def test_quick_start_completes_with_sockets_disabled(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:  # TST-SEC-004, PRD-NF-001
    monkeypatch.setattr(socket, "socket", _NoSockets)
    monkeypatch.setattr(socket, "create_connection", _NoSockets)
    monkeypatch.setattr(socket, "getaddrinfo", _NoSockets)
    code, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    assert code == 0
    run_id = str(json.loads(out)["run_id"])
    code, _, _ = invoke(
        capsys,
        ["compare", run_id, run_id, "--run-root", str(project.run_root)],
    )
    assert code == 0


# Dataset content ---------------------------------------------------------------------------------


def test_dataset_strings_are_never_executed(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:  # TST-SEC-001, SR-01
    calls: list[object] = []
    payload = "__import__('os').system('echo x')"
    line = json.dumps({"id": "c1", "input": {"id": "c1", "q": payload}, "expected": payload})
    (project.root / "dataset.jsonl").write_text(line + "\n", encoding="utf-8")
    monkeypatch.setattr(os, "system", lambda command: calls.append(command))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append(a))
    code, _, _ = invoke(capsys, ["run", "--config", str(project.config)])
    assert code == 0
    assert calls == []


def test_yaml_tags_and_pickle_like_text_load_as_plain_strings() -> None:  # TST-SEC-002
    lines = (
        b'{"id": "c1", "input": {"q": "!!python/object/apply:os.system [\\"echo x\\"]"}}\n'
        b'{"id": "c2", "input": {"q": "\\u0080\\u0004\\u0095\\u0000"}}\n'
    )
    dataset = parse_dataset_bytes(lines, fmt="jsonl")
    for case in dataset.cases:
        assert isinstance(case.input, dict)
        assert isinstance(case.input["q"], str)


def test_case_ids_with_traversal_are_rejected(tmp_path: Path) -> None:  # TST-SEC-006, THR-007
    with pytest.raises(ValidationError):
        Case(id="../../etc/passwd", input={"q": "x"})
    line = b'{"id": "../escape", "input": {"q": "x"}}\n'
    with pytest.raises(DatasetValidationError):
        parse_dataset_bytes(line, fmt="jsonl")


def test_run_directory_is_named_by_a_uuid_under_the_root(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-006
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    stored = Path(json.loads(out)["stored"])
    assert stored.parent == project.run_root
    uuid.UUID(stored.name)  # raises if the name is not a UUID


# Run references ---------------------------------------------------------------------------------


def test_run_reference_outside_the_root_is_refused(
    project: Project, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:  # TST-SEC-007, THR-007
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_dir = Path(json.loads(out)["stored"])
    outside = tmp_path / "outside-copy"
    shutil.copytree(run_dir, outside)
    relative = os.path.relpath(outside, project.run_root)
    with pytest.raises(EvalForgeError) as exc:
        api.resolve_run(relative, project.run_root)
    assert exc.value.code == "RUN_NOT_FOUND"
    code, _, err = invoke(capsys, ["inspect", "../../etc", "--run-root", str(project.run_root)])
    assert code == 2
    assert "RUN_NOT_FOUND" in err


# Secrets and disclosure --------------------------------------------------------------------------


def test_planted_secret_in_target_output_is_not_stored_in_clear(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-008, SR-05
    line = json.dumps({"id": "c1", "input": {"id": "c1", "q": SECRET}, "expected": SECRET})
    (project.root / "dataset.jsonl").write_text(line + "\n", encoding="utf-8")
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_dir = Path(json.loads(out)["stored"])
    for path in run_dir.iterdir():
        assert SECRET not in path.read_text(encoding="utf-8"), path.name


def test_unknown_config_key_does_not_echo_its_value(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-008
    project.config.write_text(
        project.config.read_text(encoding="utf-8") + f'\n[target.secrets]\napi_key = "{SECRET}"\n',
        encoding="utf-8",
    )
    code, out, err = invoke(capsys, ["config", "validate", str(project.config)])
    assert code == 2
    assert SECRET not in out + err


def test_terminal_output_has_no_raw_escape_or_bidi_characters(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-010, SR-08
    hostile = "\x1b[2J‮owned"
    line = json.dumps({"id": "c1", "input": {"id": "c1", "q": hostile}, "expected": "x"})
    (project.root / "dataset.jsonl").write_text(line + "\n", encoding="utf-8")
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_id = str(json.loads(out)["run_id"])
    _, text, _ = invoke(
        capsys,
        ["inspect", run_id, "--run-root", str(project.run_root), "--show-io", "--status", "fail"],
    )
    assert "\x1b" not in text
    assert "‮" not in text


def test_regex_pattern_length_is_limited(tmp_path: Path) -> None:  # TST-SEC-011, SR-03
    data = {
        "schema_version": "1.0",
        "dataset": {"path": "d.jsonl"},
        "target": {"callable": "m:f", "name": "t"},
        "evaluators": [{"name": "r", "type": "rule_based", "regex": ["a" * 600]}],
    }
    with pytest.raises(ConfigError):
        config_from_mapping(data, config_dir=tmp_path)


@pytest.mark.parametrize("pattern", ["(a+)+$", "(\\w*)*x", "(ab+)*c"])
def test_nested_repeat_patterns_are_refused_at_configuration(tmp_path: Path, pattern: str) -> None:
    # TST-SEC-011, SR-03: a repeated group that contains a repeat can take exponential time (RR-03).
    data = {
        "schema_version": "1.0",
        "dataset": {"path": "d.jsonl"},
        "target": {"callable": "m:f", "name": "t"},
        "evaluators": [{"name": "r", "type": "rule_based", "regex": [pattern]}],
    }
    with pytest.raises(ConfigError):
        config_from_mapping(data, config_dir=tmp_path)


@pytest.mark.parametrize("pattern", ["\\d+", "(ab)+", "(a|b)+", "[a-z]+@[a-z]+"])
def test_ordinary_patterns_are_accepted(tmp_path: Path, pattern: str) -> None:  # TST-SEC-011
    data = {
        "schema_version": "1.0",
        "dataset": {"path": "d.jsonl"},
        "target": {"callable": "m:f", "name": "t"},
        "evaluators": [{"name": "r", "type": "rule_based", "regex": [pattern]}],
    }
    config = config_from_mapping(data, config_dir=tmp_path)
    assert config.evaluators[0].name == "r"


def test_rule_based_input_is_capped_before_matching() -> None:  # TST-SEC-011, THR-003
    evaluator = RuleBased(name="r", regex=("a+",))
    oversized = "a" * (1024 * 1024 + 1)
    result = evaluator.evaluate(Case(id="c1", input={"q": "x"}), oversized, 1.0)
    assert result.status.value == "ERROR"


# Integrity and disclosure ------------------------------------------------------------------------


def test_tampered_cases_file_is_an_integrity_error(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-012, THR-013
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_dir = Path(json.loads(out)["stored"])
    cases = run_dir / "cases.jsonl"
    cases.write_bytes(cases.read_bytes().replace(b'"PASS"', b'"FAIL"', 1))
    run_id = run_dir.name
    code, _, err = invoke(capsys, ["inspect", run_id, "--run-root", str(project.run_root)])
    assert code == 4
    assert "INTEGRITY_MISMATCH" in err
    code, _, err = invoke(capsys, ["compare", run_id, run_id, "--run-root", str(project.run_root)])
    assert code == 4


def test_default_export_has_no_case_input_or_output(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-013, SR-06
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_id = str(json.loads(out)["run_id"])
    report = build_run_report(api.inspect_run(run_id, project.run_root))
    for case in cast(list[dict[str, object]], report["cases"]):
        assert "input" not in case
        assert "output" not in case


def test_inspect_listing_hides_case_io_without_show_io(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-014, SR-06
    _, out, _ = invoke(capsys, ["run", "--config", str(project.config), "--format", "json"])
    run_id = str(json.loads(out)["run_id"])
    _, listing, _ = invoke(capsys, ["inspect", run_id, "--run-root", str(project.run_root)])
    assert "input:" not in listing
    assert "output:" not in listing
    document = api.inspect_document(api.inspect_run(run_id, project.run_root))
    for row in cast(list[dict[str, object]], document["cases"]):
        assert "input" not in row


def test_symlinked_dataset_warns_and_is_read_only(
    project: Project, capsys: pytest.CaptureFixture[str]
) -> None:  # TST-SEC-015, THR-005
    target = project.root / "real.jsonl"
    target.write_bytes((project.root / "dataset.jsonl").read_bytes())
    link = project.root / "linked.jsonl"
    link.symlink_to(target)
    before = target.read_bytes()
    code, out, err = invoke(capsys, ["dataset", "validate", str(link)])
    assert code == 0
    assert "symbolic link" in err.lower() or "symlink" in err.lower()
    assert target.read_bytes() == before


def test_export_never_overwrites_an_existing_file(project: Project) -> None:  # TST-SEC-016
    # Covered by tests/test_cli.py::test_report_export_never_overwrites; asserted here as well.
    existing = project.root / "keep.json"
    existing.write_text("keep", encoding="utf-8")
    with pytest.raises(EvalForgeError):
        api.write_new(existing, b"new")
    assert existing.read_text(encoding="utf-8") == "keep"


def test_second_writer_on_a_locked_run_directory_fails(tmp_path: Path) -> None:  # TST-SEC-017
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    acquire_lock(run_dir)
    with pytest.raises(StorageError) as exc:
        acquire_lock(run_dir)
    assert exc.value.code == "STORAGE_LOCKED"


def _malformed_lines(seed: int, count: int) -> list[bytes]:
    rng = random.Random(seed)
    alphabet = '{}[]":,\\ \t\n\x00\x7fé\U0001f600ab01'
    lines: list[bytes] = []
    for _ in range(count):
        body = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 80)))
        if rng.random() < 0.3:
            body = '{"id": "c' + str(rng.randint(0, 9)) + '", "input": ' + body
        lines.append(body.encode("utf-8", errors="surrogatepass"))
    return lines


def test_seeded_malformed_corpus_raises_only_validation_errors() -> None:  # TST-SEC-018, THR-002
    limits = DatasetLimits()
    for line in _malformed_lines(seed=20261030, count=200):
        try:
            parse_dataset_bytes(line + b"\n", fmt="jsonl", lim=limits)
        except DatasetValidationError:
            continue
        except EvalForgeError:
            continue


def test_cli_never_prints_unexpected_fault_detail(
    project: Project, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:  # TST-SEC-008 (exception text), TST-IO-005
    def explode(*args: object, **kwargs: object) -> JSONValue:
        raise RuntimeError(SECRET)

    monkeypatch.setattr(api, "validate_dataset", explode)
    code, _, err = invoke(capsys, ["dataset", "validate", str(project.root / "dataset.jsonl")])
    assert code == 4
    assert SECRET not in err
    assert cli.EXIT_INFRASTRUCTURE == 4


def test_config_validate_does_not_import_the_target(
    project: Project,
) -> None:  # THR-004, TST-CLI-009
    sys.modules.pop("cli_target", None)
    api.validate_config(project.config)
    assert "cli_target" not in sys.modules
    api.validate_config(project.config, check_imports=True)
    assert "cli_target" in sys.modules


BANNED_CLAIMS: Final = (
    "guarantees safety",
    "proves correctness",
    "certified",
    "bias-free",
    "hallucination-free",
    "is safe",
    "is correct",
)


def test_user_facing_text_contains_no_banned_claims() -> None:  # TST-DOC-003, THR-019, PRD-NF-013
    root = SRC.parent.parent
    documents = [*_source_files(), root / "README.md"]
    found: list[str] = []
    for path in documents:
        for line in path.read_text(encoding="utf-8").lower().splitlines():
            for phrase in BANNED_CLAIMS:
                position = line.find(phrase)
                if position >= 0 and not _negated_before(line, position):
                    found.append(f"{path.name}: {phrase}")
    assert found == []


def _negated_before(line: str, position: int) -> bool:
    """True when a negation words the phrase, for example "do not establish that it is safe"."""
    window = line[max(0, position - 30) : position]
    return any(word in window for word in ("not ", "no ", "never ", "without "))


def test_every_test_named_in_the_matrix_exists() -> (
    None
):  # Traceability of docs/SECURITY_VERIFICATION_MATRIX.md
    matrix = (SRC.parent.parent / "docs" / "SECURITY_VERIFICATION_MATRIX.md").read_text(
        encoding="utf-8"
    )
    named = set(re.findall(r"(?<![/\w])test_[a-z0-9_]+(?!\.py)", matrix))
    defined: set[str] = set()
    for path in (SRC.parent.parent / "tests").glob("test_*.py"):
        defined.update(
            re.findall(r"^def (test_[a-z0-9_]+)", path.read_text(encoding="utf-8"), re.M)
        )
    missing = sorted(named - defined)
    assert missing == []
