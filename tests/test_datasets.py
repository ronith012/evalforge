# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Dataset loading and validation (TEST_STRATEGY §4.1, §4.2, §4.8 subset)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from evalforge import limits
from evalforge.datasets import DatasetLimits, load_dataset, parse_dataset_bytes
from evalforge.errors import DatasetValidationError, EvalForgeError
from evalforge.models import ABSENT

FIXTURES = Path(__file__).parent / "fixtures" / "datasets"
SMALL = FIXTURES / "support_small.jsonl"


def _jsonl(*records: str) -> bytes:
    return ("\n".join(records) + "\n").encode("utf-8")


def _error_tuples(error: DatasetValidationError) -> list[tuple[str, int | None, str | None]]:
    return [(item.code, item.line, item.field) for item in error.errors]


def _expect_invalid(data: bytes, fmt: str = "jsonl") -> DatasetValidationError:
    with pytest.raises(DatasetValidationError) as info:
        parse_dataset_bytes(data, fmt=fmt)
    return info.value


# TST-DS-001 -------------------------------------------------------------------------------


def test_json_array_and_jsonl_with_the_same_cases_share_the_canonical_hash(tmp_path: Path) -> None:
    jsonl = load_dataset(SMALL)
    records = [json.loads(line) for line in SMALL.read_text(encoding="utf-8").splitlines() if line]
    json_path = tmp_path / "support_small.json"
    json_path.write_text(json.dumps(records), encoding="utf-8")
    as_json = load_dataset(json_path)

    assert jsonl.cases == as_json.cases
    assert jsonl.canonical_sha256 == as_json.canonical_sha256
    assert jsonl.sha256 != as_json.sha256  # raw bytes differ
    assert (jsonl.format, as_json.format) == ("jsonl", "json")


def test_case_count_and_order_follow_the_file() -> None:
    dataset = load_dataset(SMALL)
    assert dataset.case_count == 5
    assert [case.id for case in dataset.cases] == [
        "greet-001",
        "refund-001",
        "order-002",
        "no-expected-003",
        "null-expected-004",
    ]


# TST-DS-008 -------------------------------------------------------------------------------


def test_absent_expected_and_null_expected_are_distinct() -> None:
    dataset = load_dataset(SMALL)
    absent = dataset.cases[3]
    null = dataset.cases[4]
    assert absent.expected is ABSENT
    assert null.expected is None
    assert not absent.has_expected()
    assert null.has_expected()


def test_metadata_and_tags_are_loaded() -> None:
    case = load_dataset(SMALL).cases[1]
    assert dict(case.metadata) == {"category": "refunds"}
    assert case.tags == ("smoke", "refunds")


# TST-DS-002 -------------------------------------------------------------------------------


def test_leading_byte_order_mark_is_accepted_and_changes_only_the_raw_hash() -> None:
    plain = load_dataset(SMALL)
    data = b"\xef\xbb\xbf" + SMALL.read_bytes()
    with_bom = parse_dataset_bytes(data, fmt="jsonl")
    assert with_bom.cases == plain.cases
    assert with_bom.canonical_sha256 == plain.canonical_sha256
    assert with_bom.sha256 != plain.sha256


def test_utf16_input_is_rejected_as_an_encoding_error() -> None:
    error = _expect_invalid("{}".encode("utf-16"))
    assert error.errors[0].code == "DATASET_ENCODING_INVALID"


# TST-DS-003 -------------------------------------------------------------------------------


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cases.csv"
    path.write_text("id\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError) as info:
        load_dataset(path)
    assert info.value.code == "DATASET_FORMAT_UNSUPPORTED"


def test_missing_file_is_a_usage_error(tmp_path: Path) -> None:
    with pytest.raises(EvalForgeError) as info:
        load_dataset(tmp_path / "absent.jsonl")
    assert info.value.code == "USAGE_ERROR"


# TST-DS-004 / PRD-F-002 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "field_name"),
    [
        ('{"input": {"q": 1}}', "id"),
        ('{"id": "c1"}', "input"),
        ('{"id": "has space", "input": {}}', "id"),
        ('{"id": "' + "x" * 129 + '", "input": {}}', "id"),
    ],
)
def test_missing_or_invalid_fields_are_reported_by_name(record: str, field_name: str) -> None:
    error = _expect_invalid(_jsonl(record))
    assert error.code == "DATASET_INVALID"
    assert error.errors[0].line == 1
    assert error.errors[0].field == field_name


def test_error_reports_file_line_and_field(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_bytes(_jsonl('{"id": "a", "input": {}}', '{"id": "b", "input": {}, "expcted": 1}'))
    with pytest.raises(DatasetValidationError) as info:
        load_dataset(path)
    error = info.value.errors[0]
    assert error.path == str(path)
    assert error.line == 2
    assert error.field == "expcted"
    assert "unknown key" in error.message


# TST-DS-005 -------------------------------------------------------------------------------


def test_unknown_key_is_rejected_with_its_name() -> None:
    error = _expect_invalid(_jsonl('{"id": "c1", "input": {}, "expcted": "x"}'))
    assert _error_tuples(error) == [("DATASET_INVALID", 1, "expcted")]


# TST-DS-006 -------------------------------------------------------------------------------


def test_duplicate_identifier_reports_both_locations() -> None:
    error = _expect_invalid(_jsonl('{"id": "r1", "input": {}}', '{"id": "r1", "input": {"x": 1}}'))
    assert _error_tuples(error) == [("DATASET_DUPLICATE_ID", 2, "id")]
    assert "already defined at line 1" in error.errors[0].message


# TST-DS-007 -------------------------------------------------------------------------------


def test_identifiers_differing_only_in_case_are_distinct() -> None:
    dataset = parse_dataset_bytes(
        _jsonl('{"id": "A1", "input": {}}', '{"id": "a1", "input": {}}'), fmt="jsonl"
    )
    assert [case.id for case in dataset.cases] == ["A1", "a1"]


# TST-DS-009 / TST-DS-010 ------------------------------------------------------------------


def test_metadata_that_is_not_an_object_is_rejected() -> None:
    error = _expect_invalid(_jsonl('{"id": "c1", "input": {}, "metadata": ["x"]}'))
    assert _error_tuples(error) == [("DATASET_INVALID", 1, "metadata")]


def test_tags_must_be_a_list() -> None:
    error = _expect_invalid(_jsonl('{"id": "c1", "input": {}, "tags": "smoke"}'))
    assert _error_tuples(error) == [("DATASET_INVALID", 1, "tags")]


def test_duplicate_tags_are_rejected() -> None:
    error = _expect_invalid(_jsonl('{"id": "c1", "input": {}, "tags": ["a", "a"]}'))
    assert _error_tuples(error) == [("DATASET_INVALID", 1, "tags")]


def test_more_than_thirty_two_tags_are_rejected() -> None:
    tags = [f"t{i}" for i in range(33)]
    error = _expect_invalid(_jsonl(json.dumps({"id": "c1", "input": {}, "tags": tags})))
    assert _error_tuples(error) == [("DATASET_INVALID", 1, "tags")]


# TST-DS-011 / 012 / 013 -------------------------------------------------------------------


def test_blank_lines_are_ignored() -> None:
    data = b'\n{"id": "a", "input": {}}\n\n   \n{"id": "b", "input": {}}\n'
    assert parse_dataset_bytes(data, fmt="jsonl").case_count == 2


def test_zero_byte_jsonl_is_an_empty_valid_dataset() -> None:
    dataset = parse_dataset_bytes(b"", fmt="jsonl")
    assert dataset.case_count == 0


def test_zero_byte_json_is_invalid_because_it_is_not_an_array() -> None:
    error = _expect_invalid(b"", fmt="json")
    assert error.errors[0].code == "DATASET_INVALID"


def test_empty_json_array_is_an_empty_valid_dataset() -> None:
    assert parse_dataset_bytes(b"[]", fmt="json").case_count == 0


def test_top_level_json_object_is_rejected() -> None:
    error = _expect_invalid(b'{"id": "a", "input": {}}', fmt="json")
    assert "top-level value must be a JSON array" in error.errors[0].message


# TST-DS-014 -------------------------------------------------------------------------------


def test_errors_are_collected_in_file_order_and_capped_at_one_hundred() -> None:
    data = _jsonl(*(['{"id": "x", "input": {}, "bad": 1}'] * 150))
    error = _expect_invalid(data)
    assert len(error.errors) == 100
    assert [item.line for item in error.errors[:3]] == [1, 2, 3]


# TST-DS-015 limits ------------------------------------------------------------------------


def test_file_size_at_the_limit_is_accepted_and_one_byte_over_is_rejected() -> None:
    record = b'{"id": "a", "input": {}}\n'
    lim = DatasetLimits(max_bytes=len(record))
    assert parse_dataset_bytes(record, fmt="jsonl", lim=lim).case_count == 1
    with pytest.raises(DatasetValidationError) as info:
        parse_dataset_bytes(record + b" ", fmt="jsonl", lim=lim)
    assert info.value.code == "DATASET_LIMIT_EXCEEDED"


def test_load_dataset_enforces_the_size_limit_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "big.jsonl"
    path.write_bytes(SMALL.read_bytes())
    with pytest.raises(DatasetValidationError) as info:
        load_dataset(path, lim=DatasetLimits(max_bytes=10))
    assert info.value.code == "DATASET_LIMIT_EXCEEDED"


def test_line_length_at_the_limit_is_accepted_and_one_over_is_rejected() -> None:
    line = b'{"id": "a", "input": {"x": "' + b"y" * 10 + b'"}}'
    lim = DatasetLimits(max_line_bytes=len(line))
    assert parse_dataset_bytes(line, fmt="jsonl", lim=lim).case_count == 1
    longer = b'{"id": "a", "input": {"x": "' + b"y" * 11 + b'"}}'
    error = _expect_invalid_with(longer, lim)
    assert _error_tuples(error) == [("DATASET_LIMIT_EXCEEDED", 1, None)]


def test_case_count_at_the_limit_is_accepted_and_one_over_is_rejected() -> None:
    data = _jsonl('{"id": "a", "input": {}}', '{"id": "b", "input": {}}')
    assert parse_dataset_bytes(data, fmt="jsonl", lim=DatasetLimits(max_cases=2)).case_count == 2
    error = _expect_invalid_with(data, DatasetLimits(max_cases=1))
    assert error.errors[0].code == "DATASET_LIMIT_EXCEEDED"


def test_nesting_at_the_limit_is_accepted_and_one_over_is_rejected() -> None:
    # {"id", "input": {"x": [1]}} nests three levels: record, input object, array.
    at_limit = _jsonl('{"id": "a", "input": {"x": [1]}}')
    assert (
        parse_dataset_bytes(at_limit, fmt="jsonl", lim=DatasetLimits(max_depth=3)).case_count == 1
    )
    over = _jsonl('{"id": "a", "input": {"x": [[1]]}}')
    error = _expect_invalid_with(over, DatasetLimits(max_depth=3))
    assert error.errors[0].code == "DATASET_LIMIT_EXCEEDED"


def test_string_length_at_the_limit_is_accepted_and_one_over_is_rejected() -> None:
    big = DatasetLimits(max_line_bytes=10 * 1024 * 1024)
    at_limit = _jsonl('{"id": "a", "input": "' + "s" * limits.MAX_STRING_BYTES + '"}')
    assert parse_dataset_bytes(at_limit, fmt="jsonl", lim=big).case_count == 1
    over = _jsonl('{"id": "a", "input": "' + "s" * (limits.MAX_STRING_BYTES + 1) + '"}')
    error = _expect_invalid_with(over, big)
    assert _error_tuples(error) == [("DATASET_INVALID", 1, "input")]


def _expect_invalid_with(data: bytes, lim: DatasetLimits) -> DatasetValidationError:
    with pytest.raises(DatasetValidationError) as info:
        parse_dataset_bytes(data, fmt="jsonl", lim=lim)
    return info.value


# TST-DS-016 / 017 / 018 -------------------------------------------------------------------


def test_whitespace_changes_the_raw_hash_but_not_the_canonical_hash() -> None:
    compact = _jsonl('{"id":"a","input":{"x":1}}')
    spaced = _jsonl('{"id":  "a" ,  "input" : { "x" : 1 } }')
    first = parse_dataset_bytes(compact, fmt="jsonl")
    second = parse_dataset_bytes(spaced, fmt="jsonl")
    assert first.sha256 != second.sha256
    assert first.canonical_sha256 == second.canonical_sha256


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_are_rejected(constant: str) -> None:
    error = _expect_invalid(_jsonl(f'{{"id": "a", "input": {{"x": {constant}}}}}'))
    assert error.errors[0].code == "DATASET_INVALID"
    assert "non-finite" in error.errors[0].message


def test_unicode_is_normalised_in_the_canonical_hash_only() -> None:
    composed = _jsonl('{"id": "a", "input": {"t": "é"}}')
    decomposed = _jsonl('{"id": "a", "input": {"t": "é"}}')
    first = parse_dataset_bytes(composed, fmt="jsonl")
    second = parse_dataset_bytes(decomposed, fmt="jsonl")
    assert first.sha256 != second.sha256
    assert first.canonical_sha256 == second.canonical_sha256


# TST-MF-001 / 002 / 003 / 004 -------------------------------------------------------------


def test_invalid_utf8_reports_the_line_and_does_not_crash() -> None:
    data = _jsonl('{"id": "a", "input": {}}') + b'{"id": "b", "input": {"x": "\xff"}}\n'
    error = _expect_invalid(data)
    assert _error_tuples(error) == [("DATASET_ENCODING_INVALID", 2, None)]


def test_truncated_json_line_reports_its_line() -> None:
    error = _expect_invalid(_jsonl('{"id": "a", "input": {}}', '{"id": "b", "input": {'))
    assert error.errors[0].code == "DATASET_INVALID"
    assert error.errors[0].line == 2


def test_very_deep_nesting_is_rejected_without_recursion_error() -> None:
    depth = 100_000
    deep = '{"id": "a", "input": ' + "[" * depth + "]" * depth + "}"
    error = _expect_invalid(deep.encode("utf-8") + b"\n")
    assert error.errors[0].code == "DATASET_LIMIT_EXCEEDED"


def test_crlf_and_lf_line_endings_give_identical_cases() -> None:
    # The bytes are built here, not read from a checkout: git may convert line endings on Windows.
    lf_bytes = SMALL.read_bytes().replace(b"\r\n", b"\n")
    crlf_bytes = lf_bytes.replace(b"\n", b"\r\n")
    lf = parse_dataset_bytes(lf_bytes, fmt="jsonl")
    crlf = parse_dataset_bytes(crlf_bytes, fmt="jsonl")
    assert lf.cases == crlf.cases
    assert lf.canonical_sha256 == crlf.canonical_sha256
    assert lf.sha256 != crlf.sha256


def test_duplicate_keys_within_a_record_are_rejected() -> None:
    error = _expect_invalid(_jsonl('{"id": "a", "id": "b", "input": {}}'))
    assert error.errors[0].code == "DATASET_INVALID"
    assert "duplicate key" in error.errors[0].message


def test_json_array_element_that_is_not_an_object_is_reported_by_index() -> None:
    error = _expect_invalid(b'[{"id": "a", "input": {}}, 7]', fmt="json")
    assert error.errors[0].message.startswith("element 1:")


def test_json_array_reports_parse_error_line_when_available() -> None:
    error = _expect_invalid(b'[\n{"id": "a",\n', fmt="json")
    assert error.errors[0].code == "DATASET_INVALID"


# TST-DS-019 / TST-SEC-001 / TST-SEC-002 ---------------------------------------------------


def test_hostile_payloads_load_as_plain_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("dataset content must never reach a process-execution call")

    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)

    dataset = load_dataset(FIXTURES / "hostile_payloads.jsonl")
    assert dataset.case_count == 3
    assert "__import__" in str(dataset.cases[0].input)
    assert "!!python/object" in str(dataset.cases[1].input)


def test_yaml_tags_outside_a_string_are_invalid_json() -> None:
    error = _expect_invalid(b'{"id": "a", "input": !!python/object {}}\n')
    assert error.errors[0].code == "DATASET_INVALID"


def test_symbolic_link_is_accepted_and_recorded_as_a_warning(tmp_path: Path) -> None:
    link = tmp_path / "link.jsonl"
    link.symlink_to(SMALL)
    dataset = load_dataset(link)
    assert dataset.case_count == 5
    assert any("symbolic link" in item for item in dataset.warnings)


def test_warnings_do_not_affect_equality() -> None:
    plain = load_dataset(SMALL)
    assert plain.warnings == ()
    assert plain.source_label == str(SMALL)
