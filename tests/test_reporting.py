# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Reporting: sanitised text, JSON reports, the published schema, golden output, claims scan.

Test IDs: TST-CLI-011 (golden text), TST-SEC-010 (sanitisation), TST-SEC-013 (default
export has no case content), TST-SEC-014 (list view hides I/O), TST-DOC-003 (banned claims),
PRD-F-024, PRD-F-025.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, cast

import pytest

from evalforge.canon import JSONValue
from evalforge.config import config_from_mapping
from evalforge.datasets import Dataset, parse_dataset_bytes
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import fingerprint_of
from evalforge.evaluators.builtin import ExactMatch
from evalforge.reader import StoredRun, load_run
from evalforge.reporting.footer import FOOTER_TEXT
from evalforge.reporting.json_report import build_run_report, report_bytes
from evalforge.reporting.sanitize import sanitize_text
from evalforge.reporting.schema import load_schema, schema_path
from evalforge.reporting.text import render_case_detail, render_case_list, render_run
from evalforge.runner import RunOptions, run_cases
from evalforge.store import RunContext, persist_outcome
from evalforge.targets import from_callable
from minimal_schema import validate

GOLDEN = Path(__file__).parent / "golden"
WEIRD = "\x1b[2Jcleared\x00nul‮flip\x7fdel\u009bc1"
SECRET = "sk-" + "A1b2C3d4E5f6G7h8I9j0"


def _dataset() -> Dataset:
    records = (
        b'{"id": "c1", "input": {"q": "one"}, "expected": "echo: one"}\n'
        b'{"id": "c2", "input": {"q": "two"}, "expected": "wrong"}\n'
        b'{"id": "c3", "input": {"q": "three"}}\n'
    )
    return parse_dataset_bytes(records, fmt="jsonl", source_label="datasets/report.jsonl")


def _config(config_dir: Path, *, io_mode: str = "full", redaction: bool = True) -> Any:
    return config_from_mapping(
        {
            "schema_version": "1.0",
            "run": {"io_mode": io_mode, "redaction": redaction},
            "dataset": {"path": "datasets/report.jsonl"},
            "target": {"callable": "example:answer", "name": "echo"},
            "evaluators": [{"name": "exact", "type": "exact_match"}],
        },
        config_dir=config_dir,
    )


def _stored(
    tmp_path: Path, *, io_mode: str = "full", redaction: bool = True, target: Any = None
) -> StoredRun:
    def echo(case_input: JSONValue) -> JSONValue:
        assert isinstance(case_input, dict)
        if target is not None:
            result: JSONValue = target(case_input)
            return result
        return f"echo: {case_input['q']}"

    dataset = _dataset()
    evaluators = (ExactMatch(name="exact"),)
    context = RunContext(
        dataset=dataset,
        config=_config(tmp_path, io_mode=io_mode, redaction=redaction),
        options=RunOptions(),
        io_mode=io_mode,
        redaction=redaction,
        target_name="echo",
        fingerprints=tuple(fingerprint_of(item) for item in evaluators),
    )
    outcome = run_cases(dataset, from_callable(echo, name="echo"), evaluators, context.options)
    run_dir = persist_outcome(outcome, context, tmp_path / "runs")
    return load_run(run_dir)


# TST-SEC-010 sanitisation -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("plain text", "plain text"),
        ("tab\tand newline\n", "tab\tand newline\n"),
        ("\x1b[31m", "\\u001b[31m"),
        ("a\x00b", "a\\u0000b"),
        ("carriage\r", "carriage\\u000d"),
        ("del\x7f", "del\\u007f"),
        ("c1\u009b", "c1\\u009b"),
        ("flip‮", "flip\\u202e"),
        ("isolate⁦", "isolate\\u2066"),
    ],
)
def test_control_and_bidi_characters_are_shown_as_escapes(raw: str, expected: str) -> None:
    assert sanitize_text(raw) == expected


def test_sanitisation_is_idempotent() -> None:
    once = sanitize_text(WEIRD)
    assert sanitize_text(once) == once


def test_sanitised_text_contains_no_raw_control_characters() -> None:
    cleaned = sanitize_text(WEIRD)
    assert not re.search(r"[\x00-\x08\x0b-\x1f\x7f-\x9f‪-‮⁦-⁩]", cleaned)


# Run summary text -------------------------------------------------------------------------


def test_run_summary_shows_counts_rate_and_integrity(tmp_path: Path) -> None:
    text = render_run(_stored(tmp_path))
    assert "Status: COMPLETED" in text
    assert "Integrity: ok" in text
    # c3 has no expected value, so its exact check is skipped and the case is SKIPPED.
    assert "Executed: 2" in text
    assert "PASS 1" in text
    assert "FAIL 1" in text
    assert "SKIPPED 1" in text
    assert "Pass rate: 0.500" in text
    assert "95% interval" in text


def test_footer_appears_exactly_once(tmp_path: Path) -> None:
    text = render_run(_stored(tmp_path))
    assert text.count(FOOTER_TEXT) == 1


def test_redaction_disabled_is_shown_as_a_warning(tmp_path: Path) -> None:
    text = render_run(_stored(tmp_path, redaction=False))
    assert "Warning: redaction was disabled for this run." in text


def test_io_none_is_described_as_status_only(tmp_path: Path) -> None:
    text = render_run(_stored(tmp_path, io_mode="none", redaction=False))
    assert "Stored content: none (status and reasons only)." in text


def test_summary_text_sanitises_stored_identifiers(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    poisoned = StoredRun(
        path=stored.path,
        manifest={**stored.manifest, "run_id": "\x1b[2Jrun"},
        summary=stored.summary,
        status=stored.status,
        integrity_ok=stored.integrity_ok,
        problems=stored.problems,
    )
    assert "\x1b" not in render_run(poisoned)


# TST-SEC-010 / TST-SEC-014 / case views -----------------------------------------------------


def test_case_detail_sanitises_output_and_shows_its_evaluators(tmp_path: Path) -> None:
    stored = _stored(tmp_path, redaction=False, target=lambda case_input: WEIRD)
    detail = render_case_detail(next(iter(stored.cases())))
    assert "\x1b" not in detail
    assert "\\u001b" in detail
    assert "exact" in detail
    assert "Traceback" not in detail


def test_case_list_hides_content_by_default(tmp_path: Path) -> None:  # TST-SEC-014
    stored = _stored(tmp_path)
    listing = render_case_list(stored.cases())
    assert "c1" in listing
    assert "echo: one" not in listing
    assert '"q"' not in listing


def test_case_list_can_filter_by_status(tmp_path: Path) -> None:
    listing = render_case_list(_stored(tmp_path).cases(), status="FAIL")
    assert "c2" in listing
    assert "c1" not in listing


# TST-CLI-011 golden text --------------------------------------------------------------------

FIXED_SUMMARY: dict[str, object] = {
    "schema_version": "1.0",
    "run_id": "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
    "counts": {"PASS": 3, "FAIL": 1, "ERROR": 1, "SKIPPED": 0, "INCONCLUSIVE": 0},
    "executed": 5,
    "pass_rate": 0.6,
    "pass_rate_ci95": [0.2307, 0.8824],
    "error_codes": {"TARGET_TIMEOUT": 1},
    "fail_by_evaluator": {"exact": 1},
    "latency_ms": {"p50": 380.1, "p95": 30000.0, "max": 30000.0},
    "not_executed": 0,
}


def _fixed_run(tmp_path: Path) -> StoredRun:
    stored = _stored(tmp_path)
    return StoredRun(
        path=tmp_path / "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
        manifest={
            "run_id": "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
            "status": "COMPLETED",
            "io_mode": "hashes",
            "redaction": True,
            "dataset": {
                "source_label": "datasets/support.jsonl",
                "format": "jsonl",
                "canonical_sha256": "sha256:" + "9" * 64,
                "case_count": 5,
            },
            "counts": {"threads_possibly_running": 0},
        },
        summary=FIXED_SUMMARY,
        status=stored.status,
        integrity_ok=True,
        problems=(),
    )


def test_golden_run_summary_text(tmp_path: Path) -> None:  # TST-CLI-011
    text = render_run(_fixed_run(tmp_path))
    golden = GOLDEN / "run_summary.txt"
    if os.environ.get("EVALFORGE_UPDATE_GOLDEN") == "1":
        golden.write_text(text, encoding="utf-8")
    assert text == golden.read_text(encoding="utf-8")


# JSON report and PRD-F-025 ------------------------------------------------------------------


def test_default_json_report_carries_no_case_content_or_messages(
    tmp_path: Path,
) -> None:  # TST-SEC-013
    report = build_run_report(_stored(tmp_path))
    text = report_bytes(report).decode("utf-8")
    for forbidden in ('"input"', '"expected"', '"output"', '"message"', "echo: one"):
        assert forbidden not in text


def test_json_report_includes_content_only_when_io_is_full(tmp_path: Path) -> None:
    report = build_run_report(_stored(tmp_path, io_mode="full", redaction=False), include_io=True)
    cases = cast(list[dict[str, Any]], report["cases"])
    first = cases[0]
    assert first["input"] == {"q": "one"}
    assert first["output"] == "echo: one"


def test_include_io_on_a_hashes_run_is_refused(tmp_path: Path) -> None:
    with pytest.raises(EvalForgeError) as info:
        build_run_report(_stored(tmp_path, io_mode="hashes", redaction=False), include_io=True)
    assert info.value.code == "IO_NOT_STORED"


def test_json_report_validates_against_the_published_schema(tmp_path: Path) -> None:  # PRD-F-025
    report = build_run_report(_stored(tmp_path))
    assert validate(report, load_schema("run-report-1.0.schema.json")) == []


def test_json_report_with_io_also_validates(tmp_path: Path) -> None:
    report = build_run_report(_stored(tmp_path, redaction=False), include_io=True)
    assert validate(report, load_schema("run-report-1.0.schema.json")) == []


def test_schema_rejects_a_report_missing_a_required_field(tmp_path: Path) -> None:
    report = build_run_report(_stored(tmp_path))
    del report["footer"]
    assert validate(report, load_schema("run-report-1.0.schema.json"))


def test_json_report_bytes_are_deterministic(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    assert report_bytes(build_run_report(stored)) == report_bytes(build_run_report(stored))


def test_json_report_keeps_hostile_text_as_valid_json_escapes(tmp_path: Path) -> None:
    stored = _stored(tmp_path, redaction=False, target=lambda case_input: WEIRD)
    report = build_run_report(stored, include_io=True)
    decoded = json.loads(report_bytes(report))
    assert decoded["cases"][0]["output"] == WEIRD  # JSON carries data; sanitisation is for text


def test_schema_file_is_published_inside_the_package() -> None:
    assert schema_path("run-report-1.0.schema.json").is_file()
    schema = load_schema("run-report-1.0.schema.json")
    assert str(schema["$id"]).endswith("run-report-1.0.schema.json")
    properties = cast(dict[str, Any], schema["properties"])
    assert properties["schema_version"]["const"] == "1.0"


# TST-DOC-003 banned claims ------------------------------------------------------------------

BANNED = (
    "guarantees safety",
    "proves safety",
    "proves correctness",
    "is safe",
    "is correct",
    "bias-free",
    "hallucination-free",
    "certified",
    "100% safe",
)
NEGATION_WINDOW = 40


def _banned_hits(text: str) -> list[str]:
    hits: list[str] = []
    lowered = text.lower()
    for phrase in BANNED:
        for match in re.finditer(re.escape(phrase), lowered):
            window = lowered[max(0, match.start() - NEGATION_WINDOW) : match.start()]
            if re.search(r"\b(not|no|never|nor)\b", window):
                continue  # a quoted negation, as in the footer
            hits.append(phrase)
    return hits


def test_footer_uses_only_negated_forms_of_banned_claims() -> None:
    assert _banned_hits(FOOTER_TEXT) == []


def test_rendered_outputs_contain_no_banned_claims(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    assert _banned_hits(render_run(stored)) == []
    assert _banned_hits(render_case_list(stored.cases())) == []


def test_reporting_source_contains_no_banned_claims() -> None:
    root = Path(__file__).resolve().parent.parent / "src" / "evalforge" / "reporting"
    for path in sorted(root.glob("*.py")):
        assert _banned_hits(path.read_text(encoding="utf-8")) == [], path.name


def test_footer_matches_the_documented_draft_wording() -> None:
    # EVALUATION_METHODOLOGY §12. Wording approved under OD-18; a change needs a new decision.
    assert FOOTER_TEXT == (
        "EvalForge reports results of the configured evaluators on the provided cases. "
        "These results do not establish that the system is safe, correct, or reliable in general."
    )
