# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Error types and the stable code registries (DATA_MODELS §9; TRD §9.2).

Codes are stable strings. A code is never renamed. Unknown codes are a programming error and
raise ``ValueError`` immediately.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from evalforge.limits import MAX_ERROR_MESSAGE_CHARS
from evalforge.status import Status


@dataclass(frozen=True, slots=True)
class CodeInfo:
    """Registry entry for one code."""

    code: str
    description: str
    status: Status | None = None
    exit_code: int | None = None


_REASON_TABLE: Final[tuple[tuple[str, Status, str], ...]] = (
    ("VALUE_MISMATCH", Status.FAIL, "Output differs from the expected value."),
    ("OUTPUT_NOT_TEXT", Status.FAIL, "A text evaluator received non-string output."),
    ("NOT_JSON", Status.FAIL, "Output does not parse as JSON."),
    ("JSON_TYPE_MISMATCH", Status.FAIL, "Top-level JSON type differs from configuration."),
    ("REQUIRED_FIELD_MISSING", Status.FAIL, "A required path is absent or null."),
    ("RULE_CONTAINS_MISSING", Status.FAIL, "A required substring is absent."),
    ("RULE_NOT_CONTAINS_PRESENT", Status.FAIL, "A forbidden substring is present."),
    ("RULE_REGEX_NO_MATCH", Status.FAIL, "A regular expression did not match."),
    ("RULE_LENGTH_OUT_OF_BOUNDS", Status.FAIL, "Output length is outside the configured bounds."),
    ("LATENCY_EXCEEDED", Status.FAIL, "Duration is above the configured maximum."),
    ("CUSTOM_FAIL", Status.FAIL, "A custom evaluator returned FAIL."),
    ("CUSTOM_UNCERTAIN", Status.INCONCLUSIVE, "A custom evaluator reported uncertainty."),
    ("TARGET_EXCEPTION", Status.ERROR, "The target raised an exception."),
    ("TARGET_TIMEOUT", Status.ERROR, "The target exceeded its timeout (best-effort)."),
    ("TARGET_CRASHED", Status.ERROR, "Reserved for post-MVP process isolation."),
    ("TARGET_OUTPUT_INVALID", Status.ERROR, "The target output is not JSON-serialisable."),
    ("EVALUATOR_EXCEPTION", Status.ERROR, "An evaluator raised an exception."),
    ("EVALUATOR_RESULT_INVALID", Status.ERROR, "An evaluator returned a malformed result."),
    ("NO_EXPECTED", Status.SKIPPED, "The case has no expected value and the evaluator needs one."),
    ("TARGET_ERROR", Status.SKIPPED, "The evaluator was not run because the target failed."),
    ("NO_EVALUATORS", Status.SKIPPED, "No evaluators are configured."),
    ("USER_FILTER", Status.SKIPPED, "Excluded by a case or tag selection."),
    ("NOT_APPLICABLE", Status.SKIPPED, "The evaluator does not apply to this output."),
    ("NOT_EXECUTED", Status.SKIPPED, "The run was aborted before the case was reached."),
)

_ERROR_TABLE: Final[tuple[tuple[str, int, str], ...]] = (
    ("CONFIG_INVALID", 2, "The configuration is invalid."),
    ("CONFIG_UNKNOWN_KEY", 2, "The configuration contains an unknown key."),
    ("USAGE_ERROR", 2, "Invalid command-line usage or a missing input file."),
    ("TARGET_LOAD_FAILED", 2, "The target reference could not be imported."),
    ("EVALUATOR_LOAD_FAILED", 2, "A custom evaluator could not be imported."),
    ("RUN_NOT_FOUND", 2, "The run reference is unknown or ambiguous."),
    ("DATASET_INVALID", 3, "The dataset failed validation."),
    ("DATASET_DUPLICATE_ID", 3, "A case identifier is defined more than once."),
    ("DATASET_LIMIT_EXCEEDED", 3, "A dataset limit was exceeded."),
    ("DATASET_ENCODING_INVALID", 3, "The dataset is not valid UTF-8."),
    ("DATASET_FORMAT_UNSUPPORTED", 3, "The dataset file extension is not supported."),
    ("STORAGE_ERROR", 4, "A run artifact could not be read or written."),
    ("STORAGE_LOCKED", 4, "The run directory is locked by another writer."),
    ("ENGINE_ERROR", 4, "An unexpected engine fault stopped the run."),
    ("RUN_ABORTED", 4, "The run was interrupted by the user."),
    ("SCHEMA_VERSION_UNSUPPORTED", 4, "The artifact major schema version is not supported."),
    ("INTEGRITY_MISMATCH", 4, "A stored hash does not match the file it covers."),
    ("RUN_INCOMPLETE", 5, "The run is not completed and cannot be compared."),
    ("DATASET_CHANGED", 5, "The canonical dataset hashes differ."),
    ("EVALUATOR_CHANGED", 5, "The evaluator fingerprints differ."),
    ("IO_NOT_STORED", 2, "The export requires case I/O that was not stored."),
)

# Finding codes are reported in comparisons (TRD §9.2). They are not errors.
FINDING_CODES: Final[frozenset[str]] = frozenset(
    {
        "CASE_REGRESSED_TO_FAIL",
        "CASE_REGRESSED_TO_ERROR",
        "CASE_REGRESSED_TO_INCONCLUSIVE",
        "PASS_RATE_DROP",
        "LATENCY_P95_INCREASE",
        "CASE_MISSING_IN_CANDIDATE",
        "CASE_NEW_IN_CANDIDATE",
        "CASE_RECOVERED",
        "DATASET_CHANGED",
        "EVALUATOR_CHANGED",
        "RATE_CHECK_SKIPPED",
        "RAW_BYTES_CHANGED",
        "IO_UNAVAILABLE",
        "COMPARISON_OVERRIDDEN",
    }
)

REASON_CODES: Final[Mapping[str, CodeInfo]] = MappingProxyType(
    {
        code: CodeInfo(code=code, description=text, status=status)
        for code, status, text in _REASON_TABLE
    }
)

ERROR_CODES: Final[Mapping[str, CodeInfo]] = MappingProxyType(
    {
        code: CodeInfo(code=code, description=text, exit_code=exit_code)
        for code, exit_code, text in _ERROR_TABLE
    }
)


def truncate(text: str, limit: int = MAX_ERROR_MESSAGE_CHARS) -> str:
    """Return ``text`` shortened to at most ``limit`` characters, marking any cut with '...'."""
    if limit < 4:
        raise ValueError("limit must be at least 4")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def reason_status(code: str) -> Status:
    """Return the status that a registered reason code must accompany."""
    info = REASON_CODES.get(code)
    if info is None or info.status is None:
        raise ValueError(f"unregistered reason code: {code!r}")
    return info.status


def is_error_code(code: str) -> bool:
    return code in ERROR_CODES


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """One structured error, as collected by validators (TRD §4.3)."""

    code: str
    message: str
    path: str | None = None
    line: int | None = None
    field: str | None = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError(f"unregistered error code: {self.code!r}")
        object.__setattr__(self, "message", truncate(self.message))


class EvalForgeError(Exception):
    """Base class for errors that carry a registered code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        errors: tuple[ErrorInfo, ...] = (),
    ) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"unregistered error code: {code!r}")
        self.code = code
        self.message = truncate(message)
        self.errors = errors
        super().__init__(f"{code}: {self.message}")


class ConfigError(EvalForgeError):
    """Configuration is invalid (exit 2)."""


class DatasetValidationError(EvalForgeError):
    """Dataset is invalid (exit 3)."""


class TargetLoadError(EvalForgeError):
    """A target or custom evaluator reference could not be imported (exit 2)."""


class RunNotFoundError(EvalForgeError):
    """A run reference is unknown or ambiguous (exit 2)."""


class StorageError(EvalForgeError):
    """A storage read, write, or lock failed (exit 4)."""


class IntegrityError(EvalForgeError):
    """A stored hash does not match the covered file (exit 4)."""


class SchemaVersionError(EvalForgeError):
    """An artifact has an unsupported major schema version (exit 4)."""


class EngineError(EvalForgeError):
    """An unexpected engine fault (exit 4)."""
