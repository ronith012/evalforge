# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Dataset loading and validation (TRD §4; DATA_MODELS §3; PRD-F-001 to PRD-F-004).

Datasets are untrusted input (CLAUDE.md, Security). They are parsed as data only. Nothing in a
dataset is imported, evaluated, or executed.

Two formats are accepted, selected by file extension:

- ``.jsonl``: one JSON object per line. Blank lines are ignored.
- ``.json``: one top-level JSON array of objects.

Validation collects errors in file order, up to ``DatasetLimits.max_errors``, and then raises one
``DatasetValidationError``. File-level checks (extension, size, whole-file encoding) stop at once.

Hashes (TRD-050, TRD-051):

- ``sha256`` is the SHA-256 of the raw file bytes, including any byte order mark.
- ``canonical_sha256`` is the canonical hash of the case contents in file order. It ignores
  whitespace, key order, and line endings, so the same cases in JSON and JSONL share it.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final, NoReturn, cast

from evalforge import limits
from evalforge.canon import JSONValue, bytes_sha256, canonical_sha256
from evalforge.errors import DatasetValidationError, ErrorInfo, EvalForgeError
from evalforge.models import ABSENT, Case, ValidationError, _Absent

BOM: Final = b"\xef\xbb\xbf"
CASE_KEYS: Final = frozenset({"id", "input", "expected", "metadata", "tags"})
FORMATS_BY_SUFFIX: Final[dict[str, str]] = {".json": "json", ".jsonl": "jsonl"}


@dataclass(frozen=True, slots=True)
class DatasetLimits:
    """Bounds for one load. Defaults are the TRD §4.2 proposals (not yet approved values)."""

    max_bytes: int = limits.MAX_DATASET_BYTES
    max_cases: int = limits.MAX_CASES
    max_line_bytes: int = limits.MAX_LINE_BYTES
    max_depth: int = limits.MAX_JSON_DEPTH
    max_errors: int = limits.MAX_VALIDATION_ERRORS


DEFAULT_LIMITS: Final = DatasetLimits()


@dataclass(frozen=True, slots=True)
class Dataset:
    """A validated dataset. Equality ignores where it was read from (``source_label``)."""

    format: str
    sha256: str
    canonical_sha256: str
    cases: tuple[Case, ...]
    source_label: str = field(default="", compare=False)
    warnings: tuple[str, ...] = field(default=(), compare=False)

    @property
    def case_count(self) -> int:
        return len(self.cases)

    @classmethod
    def load(cls, path: str | Path) -> Dataset:
        """Read and validate a dataset file (see ``load_dataset``)."""
        return load_dataset(path)

    @classmethod
    def from_cases(cls, cases: Iterable[Case], *, source_label: str = "") -> Dataset:
        """Build a dataset from in-memory cases, with the same ID rules and limits as file loading.

        There is no raw file, so ``sha256`` is the hash of the canonical content. That differs
        from a file hash and is documented (API_DESIGN §3).
        """
        items = tuple(cases)
        if not all(isinstance(item, Case) for item in items):
            raise _single_error("DATASET_INVALID", "every item must be a Case.", source_label)
        if len(items) > limits.MAX_CASES:
            raise _single_error(
                "DATASET_LIMIT_EXCEEDED",
                f"a dataset may hold at most {limits.MAX_CASES} cases.",
                source_label,
            )
        seen: set[str] = set()
        for item in items:
            if item.id in seen:
                raise _single_error(
                    "DATASET_DUPLICATE_ID", f"case ID {item.id!r} is repeated.", source_label
                )
            seen.add(item.id)
        digest = canonical_sha256([item.canonical_content() for item in items])
        return cls(
            format="inline",
            sha256=digest,
            canonical_sha256=digest,
            cases=items,
            source_label=source_label or "<inline>",
        )


class _Collector:
    """Gathers errors in file order and stops collecting once the cap is reached."""

    def __init__(self, label: str, max_errors: int) -> None:
        self.label = label
        self.max_errors = max_errors
        self.errors: list[ErrorInfo] = []

    @property
    def full(self) -> bool:
        return len(self.errors) >= self.max_errors

    def add(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        field_name: str | None = None,
    ) -> None:
        if not self.full:
            self.errors.append(
                ErrorInfo(code=code, message=message, path=self.label, line=line, field=field_name)
            )


def _reject_constant(name: str) -> NoReturn:
    raise ValueError(f"non-finite number {name} is not allowed")


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _max_nesting(text: str) -> int:
    """Return the deepest bracket nesting outside JSON strings, without recursion.

    The standard ``json`` module recurses on nested input and raises ``RecursionError`` on very
    deep documents, so this pre-scan runs first (TRD-034; TST-MF-003).
    """
    depth = 0
    deepest = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            deepest = max(deepest, depth)
        elif char in "]}":
            depth -= 1
    return deepest


def _decode(data: bytes) -> tuple[str | None, int, str]:
    """Strict UTF-8 decode. Returns ``(text, error_line, error_message)``; line is 1-based."""
    try:
        return data.decode("utf-8"), 0, ""
    except UnicodeDecodeError as exc:
        line = data.count(b"\n", 0, exc.start) + 1
        return None, line, f"invalid UTF-8 at byte {exc.start}"


def _case_from_mapping(
    obj: dict[str, object],
    *,
    collector: _Collector,
    prefix: str,
    line: int | None,
) -> Case | None:
    """Build a ``Case`` from one parsed record, recording every problem found."""
    before = len(collector.errors)
    for key in obj:
        if key not in CASE_KEYS:
            collector.add(
                "DATASET_INVALID",
                f"{prefix}unknown key {key!r} (allowed: {', '.join(sorted(CASE_KEYS))}).",
                line=line,
                field_name=key,
            )
    for required in ("id", "input"):
        if required not in obj:
            collector.add(
                "DATASET_INVALID",
                f"{prefix}missing required key {required!r}.",
                line=line,
                field_name=required,
            )
    tags_value = obj.get("tags", [])
    if not isinstance(tags_value, list):
        collector.add(
            "DATASET_INVALID", f"{prefix}tags must be a list.", line=line, field_name="tags"
        )
    if len(collector.errors) > before:
        return None
    expected: JSONValue | _Absent = ABSENT
    if "expected" in obj:
        expected = cast(JSONValue, obj["expected"])
    try:
        return Case(
            id=cast(str, obj["id"]),
            input=cast(JSONValue, obj["input"]),
            expected=expected,
            metadata=cast("dict[str, JSONValue]", obj.get("metadata", {})),
            tags=tuple(cast("list[str]", tags_value)),
        )
    except ValidationError as exc:
        collector.add("DATASET_INVALID", f"{prefix}{exc}", line=line, field_name=exc.field_name)
        return None


def _accept_case(
    case: Case,
    *,
    cases: list[Case],
    seen: dict[str, str],
    collector: _Collector,
    prefix: str,
    location: str,
    line: int | None,
) -> None:
    """Append a valid case, or record a duplicate-identifier error."""
    if case.id in seen:
        collector.add(
            "DATASET_DUPLICATE_ID",
            f"{prefix}id {case.id!r} already defined at {seen[case.id]}.",
            line=line,
            field_name="id",
        )
        return
    seen[case.id] = location
    cases.append(case)


def _parse_record(
    text: str,
    *,
    line: int,
    cases: list[Case],
    seen: dict[str, str],
    collector: _Collector,
    lim: DatasetLimits,
) -> None:
    """Parse one JSONL record (one line of text)."""
    if _max_nesting(text) > lim.max_depth:
        collector.add(
            "DATASET_LIMIT_EXCEEDED", f"nesting exceeds {lim.max_depth} levels.", line=line
        )
        return
    try:
        value = json.loads(
            text, parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys
        )
    except ValueError as exc:
        collector.add("DATASET_INVALID", f"invalid JSON: {exc}", line=line)
        return
    if not isinstance(value, dict):
        collector.add("DATASET_INVALID", "each record must be a JSON object.", line=line)
        return
    case = _case_from_mapping(value, collector=collector, prefix="", line=line)
    if case is not None:
        _accept_case(
            case,
            cases=cases,
            seen=seen,
            collector=collector,
            prefix="",
            location=f"line {line}",
            line=line,
        )


def _parse_jsonl(body: bytes, collector: _Collector, lim: DatasetLimits) -> list[Case]:
    cases: list[Case] = []
    seen: dict[str, str] = {}
    for number, raw in enumerate(body.split(b"\n"), start=1):
        if collector.full:
            break
        line_bytes = raw[:-1] if raw.endswith(b"\r") else raw
        if len(line_bytes) > lim.max_line_bytes:
            collector.add(
                "DATASET_LIMIT_EXCEEDED", f"line exceeds {lim.max_line_bytes} bytes.", line=number
            )
            continue
        if not line_bytes.strip():
            continue
        text, _error_line, error_message = _decode(line_bytes)
        if text is None:
            collector.add("DATASET_ENCODING_INVALID", error_message, line=number)
            continue
        _parse_record(text, line=number, cases=cases, seen=seen, collector=collector, lim=lim)
        if len(cases) > lim.max_cases:
            collector.add(
                "DATASET_LIMIT_EXCEEDED", f"more than {lim.max_cases} cases.", line=number
            )
            break
    return cases


def _parse_json(body: bytes, collector: _Collector, lim: DatasetLimits) -> list[Case]:
    text, error_line, error_message = _decode(body)
    if text is None:
        collector.add("DATASET_ENCODING_INVALID", error_message, line=error_line)
        return []
    if _max_nesting(text) > lim.max_depth:
        collector.add("DATASET_LIMIT_EXCEEDED", f"nesting exceeds {lim.max_depth} levels.")
        return []
    try:
        value = json.loads(
            text, parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys
        )
    except ValueError as exc:
        collector.add("DATASET_INVALID", f"invalid JSON: {exc}", line=getattr(exc, "lineno", None))
        return []
    if not isinstance(value, list):
        collector.add("DATASET_INVALID", "the top-level value must be a JSON array of objects.")
        return []
    if len(value) > lim.max_cases:
        collector.add("DATASET_LIMIT_EXCEEDED", f"more than {lim.max_cases} cases.")
        return []
    cases: list[Case] = []
    seen: dict[str, str] = {}
    for index, item in enumerate(value):
        if collector.full:
            break
        prefix = f"element {index}: "
        if not isinstance(item, dict):
            collector.add("DATASET_INVALID", f"{prefix}each record must be a JSON object.")
            continue
        case = _case_from_mapping(item, collector=collector, prefix=prefix, line=None)
        if case is not None:
            _accept_case(
                case,
                cases=cases,
                seen=seen,
                collector=collector,
                prefix=prefix,
                location=f"element {index}",
                line=None,
            )
    return cases


def _single_error(code: str, message: str, path: str) -> DatasetValidationError:
    return DatasetValidationError(
        code, message, errors=(ErrorInfo(code=code, message=message, path=path),)
    )


def parse_dataset_bytes(
    data: bytes,
    *,
    fmt: str,
    source_label: str = "",
    lim: DatasetLimits = DEFAULT_LIMITS,
) -> Dataset:
    """Validate dataset bytes in the given format (``"json"`` or ``"jsonl"``).

    Raises ``DatasetValidationError`` with every collected error on failure.
    """
    if fmt not in ("json", "jsonl"):
        raise _single_error(
            "DATASET_FORMAT_UNSUPPORTED", f"unsupported dataset format {fmt!r}.", source_label
        )
    if len(data) > lim.max_bytes:
        raise _single_error(
            "DATASET_LIMIT_EXCEEDED", f"dataset exceeds {lim.max_bytes} bytes.", source_label
        )
    raw_sha256 = bytes_sha256(data)
    body = data[len(BOM) :] if data.startswith(BOM) else data
    collector = _Collector(source_label, lim.max_errors)
    cases = (
        _parse_jsonl(body, collector, lim) if fmt == "jsonl" else _parse_json(body, collector, lim)
    )
    if collector.errors:
        raise DatasetValidationError(
            "DATASET_INVALID",
            f"{len(collector.errors)} validation error(s) found.",
            errors=tuple(collector.errors),
        )
    return Dataset(
        format=fmt,
        sha256=raw_sha256,
        canonical_sha256=canonical_sha256([case.canonical_content() for case in cases]),
        cases=tuple(cases),
        source_label=source_label,
    )


def load_dataset(path: str | Path, *, lim: DatasetLimits = DEFAULT_LIMITS) -> Dataset:
    """Read and validate a dataset file. Nothing in the file is executed.

    A symbolic link is accepted and recorded in ``Dataset.warnings`` (TRD-214).
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise EvalForgeError("USAGE_ERROR", f"dataset file not found: {file_path}")
    fmt = FORMATS_BY_SUFFIX.get(file_path.suffix)
    if fmt is None:
        raise _single_error(
            "DATASET_FORMAT_UNSUPPORTED",
            f"unsupported extension {file_path.suffix!r}; use .json or .jsonl.",
            str(file_path),
        )
    warnings: list[str] = []
    if file_path.is_symlink():
        warnings.append(f"dataset path is a symbolic link: {file_path}")
    if file_path.stat().st_size > lim.max_bytes:
        raise _single_error(
            "DATASET_LIMIT_EXCEEDED", f"dataset exceeds {lim.max_bytes} bytes.", str(file_path)
        )
    with file_path.open("rb") as handle:
        data = handle.read(lim.max_bytes + 1)
    dataset = parse_dataset_bytes(data, fmt=fmt, source_label=str(file_path), lim=lim)
    return replace(dataset, warnings=tuple(warnings)) if warnings else dataset


__all__ = [
    "DEFAULT_LIMITS",
    "Dataset",
    "DatasetLimits",
    "load_dataset",
    "parse_dataset_bytes",
]
