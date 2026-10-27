# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Deterministic evaluators, custom loading, fingerprints, and the registry (TEST_STRATEGY §4.4)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from evalforge.canon import JSONValue
from evalforge.config import EvaluatorSettings
from evalforge.errors import EvalForgeError
from evalforge.evaluators.base import Evaluator, apply_evaluator, fingerprint_of
from evalforge.evaluators.builtin import (
    ExactMatch,
    JsonStructure,
    Latency,
    NormalizedText,
    RequiredFields,
    RuleBased,
)
from evalforge.evaluators.custom import load_custom_evaluator
from evalforge.evaluators.registry import build_evaluator, build_evaluators
from evalforge.models import ABSENT, Case, EvaluatorResult
from evalforge.status import Status

FIXTURES = Path(__file__).parent / "fixtures" / "evaluators"


@pytest.fixture(autouse=True)
def _fixtures_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(FIXTURES))


def case_with(expected: JSONValue | None | object = ABSENT) -> Case:
    if expected is ABSENT:
        return Case(id="c1", input={"q": "x"})
    return Case(id="c1", input={"q": "x"}, expected=expected)  # type: ignore[arg-type]


def run(
    evaluator: Evaluator,
    output: JSONValue,
    expected: JSONValue | object = ABSENT,
    duration: float = 1.0,
) -> EvaluatorResult:
    return apply_evaluator(evaluator, case_with(expected), output, duration)


# TST-EV-001 / 002 / 003 exact_match -----------------------------------------------------


def test_exact_match_passes_on_canonically_equal_values() -> None:
    result = run(ExactMatch(name="exact"), {"b": 2, "a": 1}, {"a": 1, "b": 2})
    assert result.status is Status.PASS
    assert result.reason_code is None


def test_exact_match_fails_on_different_case() -> None:
    result = run(ExactMatch(name="exact"), "hello", "Hello")
    assert result.status is Status.FAIL
    assert result.reason_code == "VALUE_MISMATCH"


def test_exact_match_distinguishes_one_from_one_point_zero() -> None:
    assert run(ExactMatch(name="exact"), 1.0, 1).status is Status.FAIL


def test_missing_expected_is_skipped_and_evaluate_is_not_called() -> None:
    calls: list[int] = []

    class Spy(ExactMatch):
        def evaluate(self, case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult:
            calls.append(1)
            return super().evaluate(case, output, duration_ms)

    result = run(Spy(name="exact"), "anything")
    assert result.status is Status.SKIPPED
    assert result.reason_code == "NO_EXPECTED"
    assert calls == []


# TST-EV-004 / 005 / 006 / 007 normalized_text -------------------------------------------


def test_normalized_text_ignores_case_and_whitespace_by_default() -> None:
    assert run(NormalizedText(name="t"), "Hello  World\n", "hello world").status is Status.PASS


def test_normalized_text_is_strict_when_every_option_is_off() -> None:
    evaluator = NormalizedText(
        name="t", nfc=False, casefold=False, collapse_whitespace=False, strip=False
    )
    assert run(evaluator, "Hello  World\n", "hello world").status is Status.FAIL


def test_nfc_option_makes_composed_and_decomposed_text_equal() -> None:
    assert run(NormalizedText(name="t"), "é", "é").status is Status.PASS
    off = NormalizedText(name="t", nfc=False)
    assert run(off, "é", "é").status is Status.FAIL


def test_casefold_is_not_locale_aware_documented_limitation() -> None:
    # Python casefold maps U+0130 (capital I with dot) to "i" + U+0307 with no locale rules.
    assert run(NormalizedText(name="t"), "İ", "i̇").status is Status.PASS


def test_non_string_output_is_not_text() -> None:
    result = run(NormalizedText(name="t"), {"answer": "x"}, "x")
    assert result.status is Status.FAIL
    assert result.reason_code == "OUTPUT_NOT_TEXT"


def test_non_string_expected_is_not_applicable() -> None:
    result = run(NormalizedText(name="t"), "x", {"answer": "x"})
    assert result.status is Status.SKIPPED
    assert result.reason_code == "NOT_APPLICABLE"


# TST-EV-008 / 009 / 010 json_structure --------------------------------------------------


def test_json_structure_accepts_json_text_and_rejects_invalid_text() -> None:
    assert run(JsonStructure(name="j"), '{"a": 1}').status is Status.PASS
    result = run(JsonStructure(name="j"), "{not json")
    assert result.status is Status.FAIL
    assert result.reason_code == "NOT_JSON"


def test_json_structure_checks_the_top_level_type() -> None:
    result = run(JsonStructure(name="j", top_level_type="array"), '{"a": 1}')
    assert result.status is Status.FAIL
    assert result.reason_code == "JSON_TYPE_MISMATCH"


def test_json_wrapped_in_code_fences_is_not_json_documented_false_negative() -> None:
    assert run(JsonStructure(name="j"), '```json\n{"a": 1}\n```').reason_code == "NOT_JSON"


def test_json_structure_treats_non_text_output_as_a_json_value() -> None:
    assert run(JsonStructure(name="j", top_level_type="number"), 7).status is Status.PASS


# TST-EV-011 / 012 required_fields -------------------------------------------------------


def test_required_fields_fail_when_a_nested_value_is_null() -> None:
    result = run(RequiredFields(name="r", paths=("a.b",)), {"a": {"b": None}})
    assert result.status is Status.FAIL
    assert result.reason_code == "REQUIRED_FIELD_MISSING"
    assert result.details["missing"] == ["a.b"]


def test_required_fields_accept_falsy_non_null_values() -> None:
    assert run(RequiredFields(name="r", paths=("a.b",)), {"a": {"b": 0}}).status is Status.PASS


def test_required_fields_on_non_json_text_is_not_json() -> None:
    assert run(RequiredFields(name="r", paths=("a",)), "plain words").reason_code == "NOT_JSON"


def test_required_fields_reports_every_missing_path() -> None:
    result = run(RequiredFields(name="r", paths=("x", "y.z")), {"y": {}})
    assert result.details["missing"] == ["x", "y.z"]


# TST-EV-013 to 017 rule_based ------------------------------------------------------------


def test_rule_contains_missing_names_the_rule() -> None:
    result = run(RuleBased(name="r", contains=("refund",)), "no match here")
    assert result.reason_code == "RULE_CONTAINS_MISSING"
    assert result.details["rule"] == "contains"


def test_rule_not_contains_present_names_the_rule() -> None:
    result = run(RuleBased(name="r", not_contains=("TODO",)), "TODO later")
    assert result.reason_code == "RULE_NOT_CONTAINS_PRESENT"


def test_rule_regex_no_match() -> None:
    result = run(RuleBased(name="r", regex=(r"^\d+$",)), "abc")
    assert result.reason_code == "RULE_REGEX_NO_MATCH"


def test_rule_length_bounds_are_inclusive() -> None:
    evaluator = RuleBased(name="r", min_length=3, max_length=5)
    assert run(evaluator, "abc").status is Status.PASS
    assert run(evaluator, "abcde").status is Status.PASS
    assert run(evaluator, "ab").reason_code == "RULE_LENGTH_OUT_OF_BOUNDS"
    assert run(evaluator, "abcdef").reason_code == "RULE_LENGTH_OUT_OF_BOUNDS"


def test_first_failing_rule_in_fixed_order_is_reported() -> None:
    evaluator = RuleBased(name="r", contains=("absent",), regex=(r"^\d+$",))
    assert run(evaluator, "abc").details["rule"] == "contains"


def test_rule_based_on_non_text_output_is_not_text() -> None:
    assert run(RuleBased(name="r", contains=("x",)), {"a": 1}).reason_code == "OUTPUT_NOT_TEXT"


def test_regex_over_the_input_cap_is_an_error_not_a_fail() -> None:
    # Decision D-5 (EXECUTION_PLAN §2.6): a resource limit is an ERROR.
    big = "a" * (1024 * 1024 + 1)
    result = run(RuleBased(name="r", regex=("a",)), big)
    assert result.status is Status.ERROR
    assert result.reason_code == "EVALUATOR_EXCEPTION"
    assert result.details["input_too_long"] is True


# TST-EV-018 latency ---------------------------------------------------------------------


def test_latency_equal_to_the_maximum_passes() -> None:
    assert run(Latency(name="l", max_ms=2000.0), None, duration=2000.0).status is Status.PASS


def test_latency_just_over_the_maximum_fails_with_details() -> None:
    result = run(Latency(name="l", max_ms=2000.0), None, duration=2000.001)
    assert result.status is Status.FAIL
    assert result.reason_code == "LATENCY_EXCEEDED"
    assert result.details["max_ms"] == 2000.0


# TST-EV-029 no built-in returns INCONCLUSIVE --------------------------------------------


@pytest.mark.parametrize(
    "output",
    [None, "", "text", {"answer": "x"}, [1, 2], 3.5, '{"a": 1}', "{not json", "é"],
)
def test_no_builtin_returns_inconclusive(output: JSONValue) -> None:
    builtins: list[Evaluator] = [
        ExactMatch(name="exact"),
        NormalizedText(name="norm"),
        JsonStructure(name="json"),
        RequiredFields(name="req", paths=("a",)),
        RuleBased(name="rule", contains=("x",)),
        Latency(name="lat", max_ms=1.0),
    ]
    for evaluator in builtins:
        result = run(evaluator, output, expected="x", duration=0.5)
        assert result.status is not Status.INCONCLUSIVE, evaluator.name


# Messages carry no case content (DATA_HANDLING §3.3) ------------------------------------


def test_built_in_messages_never_echo_case_content() -> None:
    marker = "PLANTED-MARKER-7f3a"
    evaluators: list[Evaluator] = [
        ExactMatch(name="exact"),
        NormalizedText(name="norm"),
        JsonStructure(name="json", top_level_type="array"),
        RequiredFields(name="req", paths=("a",)),
        RuleBased(name="rule", contains=("absent",)),
        Latency(name="lat", max_ms=1.0),
    ]
    for evaluator in evaluators:
        result = run(evaluator, {"text": marker}, expected={"text": marker}, duration=5.0)
        assert marker not in result.message
        assert all(marker not in str(value) for value in result.details.values())


# Fingerprints ---------------------------------------------------------------------------


def test_builtin_fingerprint_is_stable_and_parameter_sensitive() -> None:
    a = fingerprint_of(RuleBased(name="r", contains=("x",)))
    b = fingerprint_of(RuleBased(name="r", contains=("x",)))
    c = fingerprint_of(RuleBased(name="r", contains=("y",)))
    assert a.fingerprint == b.fingerprint
    assert a.fingerprint != c.fingerprint
    assert a.type_name == "rule_based"
    assert a.module is None


# Registry -------------------------------------------------------------------------------


def _settings(
    name: str, type_name: str, params: Mapping[str, JSONValue] | None = None
) -> EvaluatorSettings:
    return EvaluatorSettings(
        name=name,
        type_name=type_name,
        requires_expected=type_name in ("exact_match", "normalized_text"),
        params=dict(params or {}),
    )


def test_registry_builds_each_builtin_type() -> None:
    built = build_evaluators(
        (
            _settings("exact", "exact_match"),
            _settings(
                "norm",
                "normalized_text",
                {"nfc": True, "casefold": True, "collapse_whitespace": True, "strip": True},
            ),
            _settings("json", "json_structure", {"top_level_type": "object"}),
            _settings("req", "required_fields", {"paths": ["a.b"]}),
            _settings("rule", "rule_based", {"contains": ["x"], "max_length": 10}),
            _settings("lat", "latency", {"max_ms": 100.0}),
        )
    )
    assert [item.name for item in built] == ["exact", "norm", "json", "req", "rule", "lat"]
    assert [item.type_name for item in built] == [
        "exact_match",
        "normalized_text",
        "json_structure",
        "required_fields",
        "rule_based",
        "latency",
    ]


def test_registry_rejects_an_unknown_type() -> None:
    with pytest.raises(EvalForgeError) as info:
        build_evaluator(_settings("x", "semantic_similarity"))
    assert info.value.code == "EVALUATOR_LOAD_FAILED"


def test_registry_builds_a_custom_evaluator_from_configuration() -> None:
    evaluator = build_evaluator(
        _settings("domain_rule", "custom", {"callable": "custom_checks:RefundRule"})
    )
    assert evaluator.name == "domain_rule"
    assert evaluator.type_name == "custom"


# TST-EV-022 to 028 custom evaluators ----------------------------------------------------


def test_custom_fail_is_recorded_with_its_reason() -> None:
    evaluator = load_custom_evaluator("custom_checks:RefundRule", name="domain_rule")
    result = run(evaluator, {"answer": "Yes, within 45 days."})
    assert result.status is Status.FAIL
    assert result.name == "domain_rule"
    assert result.reason_code == "CUSTOM_FAIL"


def test_custom_inconclusive_is_allowed_for_custom_evaluators() -> None:
    evaluator = load_custom_evaluator("custom_checks:Uncertain", name="u")
    assert run(evaluator, "x").status is Status.INCONCLUSIVE


def test_custom_exception_is_an_error_and_is_named() -> None:
    evaluator = load_custom_evaluator("custom_checks:Raises", name="raises")
    result = run(evaluator, "x")
    assert result.status is Status.ERROR
    assert result.reason_code == "EVALUATOR_EXCEPTION"
    assert result.details["exception_type"] == "RuntimeError"
    assert "evaluator failure" not in result.message


def test_custom_non_result_return_is_an_invalid_result() -> None:
    evaluator = load_custom_evaluator("custom_checks:ReturnsDict", name="d")
    result = run(evaluator, "x")
    assert result.reason_code == "EVALUATOR_RESULT_INVALID"


def test_custom_result_is_relabelled_with_the_configured_name() -> None:
    # The configuration owns the evaluator name, so a custom evaluator cannot choose its identity.
    evaluator = load_custom_evaluator("custom_checks:RefundRule", name="other_name")
    result = run(evaluator, {"answer": "fine"})
    assert result.name == "other_name"
    assert result.status is Status.PASS


def test_custom_mutation_does_not_change_the_stored_output() -> None:
    evaluator = load_custom_evaluator("custom_checks:MutatesOutput", name="m")
    original: dict[str, JSONValue] = {"answer": "x"}
    run(evaluator, original)
    assert original == {"answer": "x"}


def test_missing_interface_version_is_a_load_failure() -> None:
    with pytest.raises(EvalForgeError) as info:
        load_custom_evaluator("custom_checks:NoInterfaceVersion", name="n")
    assert info.value.code == "EVALUATOR_LOAD_FAILED"
    assert "interface_version" in info.value.message


def test_unsupported_interface_version_is_a_load_failure() -> None:
    with pytest.raises(EvalForgeError, match="interface_version"):
        load_custom_evaluator("custom_checks:WrongInterfaceVersion", name="w")


def test_class_whose_constructor_needs_arguments_is_a_load_failure() -> None:
    with pytest.raises(EvalForgeError) as info:
        load_custom_evaluator("custom_checks:NeedsArguments", name="n")
    assert info.value.code == "EVALUATOR_LOAD_FAILED"


@pytest.mark.parametrize(
    ("reference", "fragment"),
    [
        ("no_such_module_for_evalforge:X", "cannot import"),
        ("custom_checks:Missing", "has no attribute"),
        ("custom_checks:not_a_class", "evaluate method"),
        ("not-a-reference", "module:attribute"),
    ],
)
def test_bad_custom_references_are_load_failures(reference: str, fragment: str) -> None:
    with pytest.raises(EvalForgeError) as info:
        load_custom_evaluator(reference, name="x")
    assert info.value.code == "EVALUATOR_LOAD_FAILED"
    assert fragment in info.value.message


def test_custom_fingerprint_includes_the_source_file_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    source = (FIXTURES / "custom_checks.py").read_text(encoding="utf-8")
    (first_dir / "fp_module_a.py").write_text(source, encoding="utf-8")
    (second_dir / "fp_module_b.py").write_text(source + "\n# changed\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(first_dir))
    monkeypatch.syspath_prepend(str(second_dir))
    first = fingerprint_of(load_custom_evaluator("fp_module_a:RefundRule", name="r"))
    second = fingerprint_of(load_custom_evaluator("fp_module_b:RefundRule", name="r"))
    assert first.source_sha256 != second.source_sha256
    assert first.fingerprint != second.fingerprint
    assert first.source_sha256 is not None
    assert first.source_sha256.startswith("sha256:")


def test_custom_fingerprint_records_module_and_qualname() -> None:
    fingerprint = fingerprint_of(
        load_custom_evaluator("custom_checks:RefundRule", name="domain_rule")
    )
    assert fingerprint.module == "custom_checks"
    assert fingerprint.qualname == "RefundRule"
    assert fingerprint.version == "1.0"


# Score and status validation in custom results ------------------------------------------


def test_out_of_range_score_cannot_be_constructed() -> None:
    from evalforge.models import ValidationError

    with pytest.raises(ValidationError):
        EvaluatorResult(name="x", status=Status.PASS, score=1.5, reason_code=None, message="ok")
