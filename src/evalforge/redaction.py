# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Heuristic redaction (DATA_HANDLING §7; SECURITY §4.6).

Redaction is **heuristic and incomplete**. It does not guarantee that sensitive information is
removed. Known misses, asserted by tests (TST-RD-004): credentials in unlisted formats, secrets
split or encoded, and personal data. Known false positives (TST-RD-005): text that matches a
pattern is replaced, and any key containing "auth" (for example "author") is replaced.

Replacements are visible: ``[REDACTED:<category>]`` for text, ``[REDACTED:key]`` for a secret-like
key. Each function returns the number of replacements, so the count can be stored without the
replaced text.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

from evalforge.canon import JSONValue

KEY_PATTERN: Final = re.compile(
    r"api[_-]?key|token|secret|password|passwd|credential|auth|private[_-]?key|session",
    re.IGNORECASE,
)

TEXT_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("stripe-live-key", re.compile(r"\bsk_live_[A-Za-z0-9]{8,}")),
    ("github-token", re.compile(r"\bghp_[A-Za-z0-9]{20,}")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
)


def redact_text(text: str) -> tuple[str, int]:
    """Replace credential-shaped substrings. Returns the new text and the number of replacements."""
    count = 0
    for category, pattern in TEXT_PATTERNS:
        text, made = pattern.subn(f"[REDACTED:{category}]", text)
        count += made
    return text, count


def redact_value(value: JSONValue) -> tuple[JSONValue, int]:
    """Redact strings inside a JSON value. Values under secret-like keys are replaced whole."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        total = 0
        items: list[JSONValue] = []
        for item in value:
            new_item, made = redact_value(item)
            items.append(new_item)
            total += made
        return items, total
    if isinstance(value, dict):
        total = 0
        result: dict[str, JSONValue] = {}
        for key, item in value.items():
            if KEY_PATTERN.search(key):
                result[key] = "[REDACTED:key]"
                total += 1
            else:
                result[key], made = redact_value(item)
                total += made
        return result, total
    return value, 0


def _redact_any(value: object) -> tuple[object, int]:
    if isinstance(value, Mapping):
        total = 0
        result: dict[str, object] = {}
        for key, item in value.items():
            if KEY_PATTERN.search(key):
                result[key] = "[REDACTED]"
                total += 1
            else:
                result[key], made = _redact_any(item)
                total += made
        return result, total
    if isinstance(value, list):
        total = 0
        items: list[object] = []
        for entry in value:
            new_entry, made = _redact_any(entry)
            items.append(new_entry)
            total += made
        return items, total
    return value, 0


def redact_config(mapping: Mapping[str, object]) -> tuple[dict[str, object], int]:
    """Configuration variant (DATA_HANDLING §5): secret-like keys become ``[REDACTED]``."""
    redacted, count = _redact_any(mapping)
    assert isinstance(redacted, dict)
    return redacted, count
