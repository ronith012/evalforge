# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Canonical JSON and SHA-256 hashing (TRD §4.4).

Canonical form:

- UTF-8 encoding; no insignificant whitespace;
- object keys sorted by code point; strings and keys in Unicode NFC;
- numbers written as Python's ``json`` module writes them. Integers and floats are distinct:
  ``1`` and ``1.0`` have different canonical forms, and ``-0.0`` differs from ``0.0``;
- NaN and infinities are rejected.

Full RFC 8785 conformance is not claimed (TRD §4.4).
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Mapping
from typing import Final, TypeAlias

from evalforge import limits

JSONValue: TypeAlias = "None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]"

HASH_PREFIX: Final = "sha256:"


class JsonValueError(ValueError):
    """A value is not representable as canonical JSON."""


class JsonLimitError(JsonValueError):
    """A value exceeds a depth or size limit."""


def check_json_value(value: object, *, path: str = "$", depth: int = 0) -> None:
    """Raise ``JsonValueError`` unless ``value`` is JSON-safe and within limits.

    ``depth`` counts enclosing containers. The root container has nesting level 1, and a
    container more than ``MAX_JSON_DEPTH`` levels deep is rejected.
    """
    if value is None or isinstance(value, bool | int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise JsonValueError(f"{path}: non-finite number")
        return
    if isinstance(value, str):
        try:
            size = len(value.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise JsonValueError(f"{path}: string is not valid Unicode") from exc
        if size > limits.MAX_STRING_BYTES:
            raise JsonLimitError(f"{path}: string exceeds {limits.MAX_STRING_BYTES} bytes")
        return
    if isinstance(value, list | tuple):
        _check_depth(depth, path)
        for index, item in enumerate(value):
            check_json_value(item, path=f"{path}[{index}]", depth=depth + 1)
        return
    if isinstance(value, Mapping):
        _check_depth(depth, path)
        for key, item in value.items():
            if not isinstance(key, str):
                raise JsonValueError(f"{path}: object keys must be strings")
            check_json_value(item, path=f"{path}.{key}", depth=depth + 1)
        return
    raise JsonValueError(f"{path}: unsupported type {type(value).__name__}")


def _check_depth(depth: int, path: str) -> None:
    if depth + 1 > limits.MAX_JSON_DEPTH:
        raise JsonLimitError(f"{path}: nesting exceeds {limits.MAX_JSON_DEPTH} levels")


def normalize_json(value: object) -> object:
    """Return a copy with NFC strings and keys, and tuples converted to lists.

    Raises ``JsonValueError`` if two distinct keys become equal after NFC normalisation.
    """
    check_json_value(value)
    return _normalize(value)


def _normalize(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            normal_key = unicodedata.normalize("NFC", key)
            if normal_key in result:
                raise JsonValueError(f"keys collide after NFC normalisation: {normal_key!r}")
            result[normal_key] = _normalize(item)
        return result
    return value


def canonical_json(value: object) -> str:
    """Return the canonical JSON text of ``value``."""
    normal = normalize_json(value)
    return json.dumps(
        normal,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_bytes(value: object) -> bytes:
    return canonical_json(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bytes_sha256(data: bytes) -> str:
    """Return ``sha256:<hex>`` for raw bytes (used for file-level hashes)."""
    return HASH_PREFIX + sha256_hex(data)


def canonical_sha256(value: object) -> str:
    """Return ``sha256:<hex>`` over the canonical JSON of ``value``."""
    return bytes_sha256(canonical_bytes(value))
