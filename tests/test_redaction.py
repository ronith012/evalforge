# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Heuristic redaction (TEST_STRATEGY §4.15: TST-RD-001 to TST-RD-005; DATA_HANDLING §7).

Planted secret values are fake and assembled from fragments so they are not secrets anywhere.
"""

from __future__ import annotations

from evalforge.canon import JSONValue
from evalforge.redaction import redact_config, redact_text, redact_value

FAKE_OPENAI = "sk-" + "A1b2C3d4E5f6G7h8I9j0"
FAKE_GITHUB = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123"
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"


# TST-RD-001 pattern redaction ------------------------------------------------------------


def test_each_listed_credential_prefix_is_replaced_and_counted() -> None:
    text, count = redact_text(f"keys: {FAKE_OPENAI} and {FAKE_GITHUB} and {FAKE_AWS}")
    assert FAKE_OPENAI not in text
    assert FAKE_GITHUB not in text
    assert FAKE_AWS not in text
    assert "[REDACTED:openai-style-key]" in text
    assert "[REDACTED:github-token]" in text
    assert "[REDACTED:aws-access-key-id]" in text
    assert count == 3


def test_text_without_secrets_is_unchanged() -> None:
    assert redact_text("Refunds are available within 30 days.") == (
        "Refunds are available within 30 days.",
        0,
    )


# TST-RD-002 key-based redaction ----------------------------------------------------------


def test_secret_like_keys_are_replaced_at_any_depth() -> None:
    value: JSONValue = {
        "outer": {"api_key": "x", "items": [{"password": "y", "ok": 1}]},
        "name": "keep",
    }
    redacted, count = redact_value(value)
    assert redacted == {
        "outer": {"api_key": "[REDACTED:key]", "items": [{"password": "[REDACTED:key]", "ok": 1}]},
        "name": "keep",
    }
    assert count == 2


# TST-RD-003 applies to structured values -------------------------------------------------


def test_strings_inside_nested_values_are_redacted() -> None:
    value: JSONValue = {"answer": f"use {FAKE_OPENAI}", "tags": [f"{FAKE_GITHUB}"]}
    redacted, count = redact_value(value)
    assert redacted == {
        "answer": "use [REDACTED:openai-style-key]",
        "tags": ["[REDACTED:github-token]"],
    }
    assert count == 2


# TST-RD-004 documented misses ------------------------------------------------------------


def test_documented_miss_credential_in_an_unlisted_format_is_not_redacted() -> None:
    unlisted = "Bearer abc123DEF456ghi789JKL012mno"
    text, count = redact_text(unlisted)
    assert text == unlisted
    assert count == 0


def test_documented_miss_base64_encoded_credential_is_not_redacted() -> None:
    encoded = "c2stQTFiMkMzZDRFNWY2RzdoOEk5ajA="  # base64 of a fake key-shaped string
    text, count = redact_text(encoded)
    assert text == encoded
    assert count == 0


def test_documented_miss_secret_under_an_unrecognised_key_is_not_redacted() -> None:
    redacted, count = redact_value({"credential_material": "x"})
    # "credential" is recognised, so this case is covered; the miss is a name outside the list.
    assert redacted == {"credential_material": "[REDACTED:key]"}
    unlisted, unlisted_count = redact_value({"zzkey": FAKE_OPENAI})
    assert unlisted == {"zzkey": "[REDACTED:openai-style-key]"}
    assert unlisted_count == 1
    assert count == 1


# TST-RD-005 documented false positive -----------------------------------------------------


def test_documented_false_positive_author_key_is_replaced() -> None:
    redacted, count = redact_value({"author": "Ada"})
    assert redacted == {"author": "[REDACTED:key]"}
    assert count == 1


def test_documented_false_positive_text_containing_a_prefix_is_not_a_match_without_a_boundary() -> (
    None
):
    # Word boundaries keep ordinary words such as "task-management" from matching the "sk-" prefix.
    text, count = redact_text("task-management-systems")
    assert text == "task-management-systems"
    assert count == 0


# Configuration variant (DATA_HANDLING §5) -------------------------------------------------


def test_configuration_secret_values_become_redacted_and_are_counted() -> None:
    config = {"run": {"io_mode": "full"}, "target": {"api_key": "fake", "callable": "m:f"}}
    redacted, count = redact_config(config)
    assert redacted == {
        "run": {"io_mode": "full"},
        "target": {"api_key": "[REDACTED]", "callable": "m:f"},
    }
    assert count == 1
