# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Canonical JSON and hashing (TRD §4.4).

Expected values are literals. The SHA-256 reference values were computed outside the package with
the shell tool ``shasum -a 256`` over the literal canonical strings, so they do not depend on the
code under test.
"""

from __future__ import annotations

import pytest

from evalforge.canon import (
    JsonLimitError,
    JsonValueError,
    canonical_json,
    canonical_sha256,
    check_json_value,
)
from evalforge.limits import MAX_JSON_DEPTH

# Canonical text of {"b": 1, "a": [True, None, "é"]} with é as U+00E9 (composed).
VECTOR_VALUE = {"b": 1, "a": [True, None, "é"]}
VECTOR_TEXT = '{"a":[true,null,"é"],"b":1}'
VECTOR_SHA256 = "sha256:17c8c6f7f948ee1c9b93b1bc35f6edc29cbaf3022bff7d076d1c4831dd8a44a2"


def _nested(depth: int) -> list[object]:
    value: list[object] = []
    for _ in range(depth - 1):
        value = [value]
    return value


def test_canonical_text_matches_hand_written_vector() -> None:
    assert canonical_json(VECTOR_VALUE) == VECTOR_TEXT


def test_canonical_hash_matches_independent_reference() -> None:
    assert canonical_sha256(VECTOR_VALUE) == VECTOR_SHA256


def test_key_order_does_not_change_the_canonical_form() -> None:
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_nfc_and_nfd_text_are_identical() -> None:
    composed = "é"
    decomposed = "é"
    assert canonical_json(composed) == canonical_json(decomposed) == '"é"'


def test_integers_and_floats_are_distinct() -> None:
    assert canonical_json(1) == "1"
    assert canonical_json(1.0) == "1.0"
    assert canonical_sha256(1) != canonical_sha256(1.0)


def test_negative_zero_is_distinct_from_zero() -> None:
    assert canonical_json(-0.0) == "-0.0"
    assert canonical_json(0.0) == "0.0"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(JsonValueError, match="non-finite"):
        canonical_json(value)


def test_non_string_keys_are_rejected() -> None:
    with pytest.raises(JsonValueError, match="must be strings"):
        check_json_value({1: "x"})


def test_unsupported_types_are_rejected() -> None:
    with pytest.raises(JsonValueError, match="unsupported type set"):
        check_json_value({"a": {1, 2}})


def test_lone_surrogate_is_rejected() -> None:
    with pytest.raises(JsonValueError, match="not valid Unicode"):
        check_json_value("\ud800")


def test_keys_that_collide_after_nfc_are_rejected() -> None:
    with pytest.raises(JsonValueError, match="collide"):
        canonical_json({"é": 1, "é": 2})


def test_nesting_at_the_limit_is_accepted() -> None:
    check_json_value(_nested(MAX_JSON_DEPTH))


def test_nesting_beyond_the_limit_is_rejected() -> None:
    with pytest.raises(JsonLimitError, match="nesting exceeds"):
        check_json_value(_nested(MAX_JSON_DEPTH + 1))


def test_tuples_serialise_as_arrays() -> None:
    assert canonical_json((1, "a")) == canonical_json([1, "a"]) == '[1,"a"]'


def test_hash_has_the_documented_format() -> None:
    digest = canonical_sha256({"x": 1})
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
    assert digest == digest.lower()
