# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Configuration loading and validation (DATA_MODELS §4; CLI_SPECIFICATION §2).

Configuration is TOML (approved, OD-04). Parsing uses the standard library ``tomllib``.
Validation collects errors, up to ``MAX_VALIDATION_ERRORS``, and then raises one ``ConfigError``.
Unknown keys are errors. Override flags are not configuration keys (TRD-136).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final

from evalforge import limits
from evalforge.canon import JSONValue
from evalforge.errors import ConfigError, ErrorInfo
from evalforge.models import SCHEMA_VERSION, ValidationError, check_schema_version

IO_MODES: Final = frozenset({"full", "hashes", "none"})
FAIL_ON_STATUSES: Final = frozenset({"fail", "error", "inconclusive"})
MISSING_CASE_POLICIES: Final = frozenset({"fail", "warn", "ignore"})
EVALUATOR_TYPES: Final = frozenset(
    {
        "exact_match",
        "normalized_text",
        "json_structure",
        "required_fields",
        "rule_based",
        "latency",
        "custom",
    }
)
TOP_LEVEL_TYPES: Final = frozenset({"object", "array", "string", "number", "boolean", "null"})
OVERRIDE_KEYS: Final = frozenset({"allow_dataset_change", "allow_evaluator_change", "strict"})

TOP_LEVEL_KEYS: Final = frozenset(
    {"schema_version", "run", "dataset", "target", "evaluators", "regression"}
)
RUN_KEYS: Final = frozenset({"io_mode", "redaction", "timeout_seconds", "fail_on", "run_root"})
DATASET_KEYS: Final = frozenset({"path"})
TARGET_KEYS: Final = frozenset({"callable", "name"})
REGRESSION_KEYS: Final = frozenset(
    {
        "max_newly_failing",
        "max_newly_errored",
        "inconclusive_as_regression",
        "max_pass_rate_drop",
        "min_executed_for_rate_check",
        "max_p95_latency_ratio",
        "missing_case_policy",
    }
)
EVALUATOR_PARAM_KEYS: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        "exact_match": frozenset(),
        "normalized_text": frozenset({"nfc", "casefold", "collapse_whitespace", "strip"}),
        "json_structure": frozenset({"top_level_type"}),
        "required_fields": frozenset({"paths"}),
        "rule_based": frozenset({"contains", "not_contains", "regex", "min_length", "max_length"}),
        "latency": frozenset({"max_ms"}),
        "custom": frozenset({"callable"}),
    }
)

CALLABLE_RE: Final = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*"
)
DOTTED_PATH_RE: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")
EVALUATOR_NAME_RE: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")


@dataclass(frozen=True, slots=True)
class RunSettings:
    io_mode: str
    redaction: bool
    timeout_seconds: float
    fail_on: tuple[str, ...]
    run_root: str


@dataclass(frozen=True, slots=True)
class DatasetSettings:
    path: str


@dataclass(frozen=True, slots=True)
class TargetSettings:
    callable_ref: str
    name: str


@dataclass(frozen=True, slots=True)
class EvaluatorSettings:
    name: str
    type_name: str
    requires_expected: bool
    params: Mapping[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegressionSettings:
    max_newly_failing: int
    max_newly_errored: int
    inconclusive_as_regression: bool
    max_pass_rate_drop: float
    min_executed_for_rate_check: int
    max_p95_latency_ratio: float | None
    missing_case_policy: str


@dataclass(frozen=True, slots=True)
class EvalForgeConfig:
    schema_version: str
    run: RunSettings
    dataset: DatasetSettings
    target: TargetSettings
    evaluators: tuple[EvaluatorSettings, ...]
    regression: RegressionSettings
    config_dir: Path | None = None


class _Collector:
    """Accumulates validation errors, capped at ``MAX_VALIDATION_ERRORS``."""

    def __init__(self) -> None:
        self.errors: list[ErrorInfo] = []

    def add(self, code: str, message: str, path: str) -> None:
        if len(self.errors) < limits.MAX_VALIDATION_ERRORS:
            self.errors.append(ErrorInfo(code=code, message=message, path=path))


def _unknown_keys(
    table: Mapping[str, object], allowed: frozenset[str], prefix: str, c: _Collector
) -> None:
    for key in table:
        if key in allowed:
            continue
        message = f'unknown key "{key}".'
        if key in OVERRIDE_KEYS:
            message += (
                " Override flags are command-line or API arguments"
                " and cannot be set in configuration."
            )
        c.add("CONFIG_UNKNOWN_KEY", message, f"{prefix}{key}")


def _table(data: Mapping[str, object], key: str, c: _Collector) -> Mapping[str, object]:
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        c.add("CONFIG_INVALID", f'"{key}" must be a table.', key)
        return {}
    return value


def _str(table: Mapping[str, object], key: str, default: str, path: str, c: _Collector) -> str:
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, str) or not value:
        c.add("CONFIG_INVALID", "must be a non-empty string.", path)
        return default
    return value


def _required_str(table: Mapping[str, object], key: str, path: str, c: _Collector) -> str | None:
    if key not in table:
        c.add("CONFIG_INVALID", f'"{key}" is required.', path)
        return None
    return _str(table, key, "", path, c) or None


def _choice(
    table: Mapping[str, object],
    key: str,
    allowed: frozenset[str],
    default: str,
    path: str,
    c: _Collector,
) -> str:
    value = _str(table, key, default, path, c)
    if value not in allowed:
        c.add("CONFIG_INVALID", f"must be one of {sorted(allowed)}.", path)
        return default
    return value


def _bool(table: Mapping[str, object], key: str, default: bool, path: str, c: _Collector) -> bool:
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        c.add("CONFIG_INVALID", "must be true or false.", path)
        return default
    return value


def _number(
    table: Mapping[str, object],
    key: str,
    default: float | None,
    path: str,
    c: _Collector,
    *,
    low: float | None = None,
    high: float | None = None,
    low_exclusive: bool = False,
) -> float | None:
    if key not in table:
        return default
    value = table[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        c.add("CONFIG_INVALID", "must be a number.", path)
        return default
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        c.add("CONFIG_INVALID", "must be finite.", path)
        return default
    if low is not None and (number <= low if low_exclusive else number < low):
        c.add(
            "CONFIG_INVALID",
            f"must be {'greater than' if low_exclusive else 'at least'} {low}.",
            path,
        )
        return default
    if high is not None and number > high:
        c.add("CONFIG_INVALID", f"must be at most {high}.", path)
        return default
    return number


def _integer(table: Mapping[str, object], key: str, default: int, path: str, c: _Collector) -> int:
    if key not in table:
        return default
    value = table[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        c.add("CONFIG_INVALID", "must be a non-negative integer.", path)
        return default
    return value


def _run(data: Mapping[str, object], c: _Collector) -> RunSettings:
    table = _table(data, "run", c)
    _unknown_keys(table, RUN_KEYS, "run.", c)
    io_mode = _choice(table, "io_mode", IO_MODES, "full", "run.io_mode", c)
    redaction = _bool(table, "redaction", True, "run.redaction", c)
    timeout = _number(
        table,
        "timeout_seconds",
        30.0,
        "run.timeout_seconds",
        c,
        low=0.0,
        high=float(limits.MAX_TIMEOUT_SECONDS),
        low_exclusive=True,
    )
    fail_on: tuple[str, ...] = ()
    if "fail_on" in table:
        raw = table["fail_on"]
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            c.add("CONFIG_INVALID", "must be a list of strings.", "run.fail_on")
        else:
            bad = [item for item in raw if item not in FAIL_ON_STATUSES]
            if bad:
                c.add(
                    "CONFIG_INVALID",
                    f"unknown status values {bad}; allowed: {sorted(FAIL_ON_STATUSES)}.",
                    "run.fail_on",
                )
            fail_on = tuple(raw)
    run_root = _str(table, "run_root", ".evalforge/runs", "run.run_root", c)
    return RunSettings(
        io_mode=io_mode,
        redaction=redaction,
        timeout_seconds=timeout if timeout is not None else 30.0,
        fail_on=fail_on,
        run_root=run_root,
    )


def _dataset(data: Mapping[str, object], c: _Collector) -> DatasetSettings | None:
    table = _table(data, "dataset", c)
    _unknown_keys(table, DATASET_KEYS, "dataset.", c)
    path = _required_str(table, "path", "dataset.path", c)
    return None if path is None else DatasetSettings(path=path)


def _target(data: Mapping[str, object], c: _Collector) -> TargetSettings | None:
    table = _table(data, "target", c)
    _unknown_keys(table, TARGET_KEYS, "target.", c)
    ref = _required_str(table, "callable", "target.callable", c)
    if ref is not None and CALLABLE_RE.fullmatch(ref) is None:
        c.add("CONFIG_INVALID", 'must have the form "module:attribute".', "target.callable")
        ref = None
    if ref is None:
        return None
    name = _str(table, "name", ref, "target.name", c)
    if len(name) > limits.MAX_TARGET_NAME_CHARS:
        c.add(
            "CONFIG_INVALID",
            f"must be at most {limits.MAX_TARGET_NAME_CHARS} characters.",
            "target.name",
        )
    return TargetSettings(callable_ref=ref, name=name)


def _evaluator_params(
    type_name: str, item: Mapping[str, object], path: str, c: _Collector
) -> dict[str, JSONValue]:
    params: dict[str, JSONValue] = {}
    if type_name == "normalized_text":
        for key in ("nfc", "casefold", "collapse_whitespace", "strip"):
            params[key] = _bool(item, key, True, f"{path}.{key}", c)
    elif type_name == "json_structure":
        if "top_level_type" in item:
            params["top_level_type"] = _choice(
                item, "top_level_type", TOP_LEVEL_TYPES, "object", f"{path}.top_level_type", c
            )
    elif type_name == "required_fields":
        raw = item.get("paths")
        if not isinstance(raw, list) or not 1 <= len(raw) <= limits.MAX_REQUIRED_PATHS:
            c.add(
                "CONFIG_INVALID",
                f"paths must be a list of 1 to {limits.MAX_REQUIRED_PATHS} dotted paths.",
                f"{path}.paths",
            )
        else:
            for index, value in enumerate(raw):
                if (
                    not isinstance(value, str)
                    or len(value) > limits.MAX_PATH_CHARS
                    or DOTTED_PATH_RE.fullmatch(value) is None
                ):
                    c.add(
                        "CONFIG_INVALID",
                        "each path must be a dotted identifier path.",
                        f"{path}.paths[{index}]",
                    )
            params["paths"] = list(raw)
    elif type_name == "rule_based":
        for key in ("contains", "not_contains"):
            if key in item:
                raw = item[key]
                if not isinstance(raw, list) or not all(isinstance(value, str) for value in raw):
                    c.add("CONFIG_INVALID", "must be a list of strings.", f"{path}.{key}")
                else:
                    params[key] = list(raw)
        if "regex" in item:
            raw = item["regex"]
            if not isinstance(raw, list) or not all(isinstance(value, str) for value in raw):
                c.add("CONFIG_INVALID", "must be a list of strings.", f"{path}.regex")
            else:
                for index, pattern in enumerate(raw):
                    message = _regex_problem(pattern)
                    if message is not None:
                        c.add("CONFIG_INVALID", message, f"{path}.regex[{index}]")
                params["regex"] = list(raw)
        low = high = None
        if "min_length" in item:
            low = _integer(item, "min_length", 0, f"{path}.min_length", c)
            params["min_length"] = low
        if "max_length" in item:
            high = _integer(item, "max_length", 0, f"{path}.max_length", c)
            params["max_length"] = high
        if low is not None and high is not None and low > high:
            c.add("CONFIG_INVALID", "min_length must not exceed max_length.", f"{path}.min_length")
        if not any(
            key in params
            for key in ("contains", "not_contains", "regex", "min_length", "max_length")
        ):
            c.add("CONFIG_INVALID", "a rule_based evaluator needs at least one rule.", path)
    elif type_name == "latency":
        value = _number(item, "max_ms", None, f"{path}.max_ms", c, low=0.0, low_exclusive=True)
        if value is None:
            c.add("CONFIG_INVALID", '"max_ms" is required and must be positive.', f"{path}.max_ms")
        else:
            params["max_ms"] = value
    elif type_name == "custom":
        ref = _required_str(item, "callable", f"{path}.callable", c)
        if ref is not None:
            if CALLABLE_RE.fullmatch(ref) is None:
                c.add(
                    "CONFIG_INVALID", 'must have the form "module:attribute".', f"{path}.callable"
                )
            else:
                params["callable"] = ref
    return params


def _regex_problem(pattern: str) -> str | None:
    if len(pattern) > limits.MAX_REGEX_CHARS:
        return f"pattern exceeds {limits.MAX_REGEX_CHARS} characters."
    try:
        re.compile(pattern)
    except re.error as exc:
        return f"invalid regular expression: {exc.msg}."
    return None


def _evaluators(data: Mapping[str, object], c: _Collector) -> tuple[EvaluatorSettings, ...]:
    raw = data.get("evaluators")
    if raw is None:
        c.add("CONFIG_INVALID", "at least one [[evaluators]] table is required.", "evaluators")
        return ()
    if not isinstance(raw, list):
        c.add("CONFIG_INVALID", "must be an array of tables.", "evaluators")
        return ()
    result: list[EvaluatorSettings] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        path = f"evaluators[{index}]"
        if not isinstance(item, Mapping):
            c.add("CONFIG_INVALID", "each evaluator must be a table.", path)
            continue
        name = _required_str(item, "name", f"{path}.name", c)
        type_name = _required_str(item, "type", f"{path}.type", c)
        if name is not None and EVALUATOR_NAME_RE.fullmatch(name) is None:
            c.add("CONFIG_INVALID", "must match ^[a-z][a-z0-9_]{0,63}$.", f"{path}.name")
            name = None
        if type_name is not None and type_name not in EVALUATOR_TYPES:
            c.add("CONFIG_INVALID", f"unknown evaluator type {type_name!r}.", f"{path}.type")
            type_name = None
        if type_name is not None:
            allowed = frozenset({"name", "type"}) | EVALUATOR_PARAM_KEYS[type_name]
            _unknown_keys(item, allowed, f"{path}.", c)
        if name is not None:
            if name in seen:
                c.add(
                    "CONFIG_INVALID",
                    f"evaluator name {name!r} is used more than once.",
                    f"{path}.name",
                )
            seen.add(name)
        if name is None or type_name is None:
            continue
        params = _evaluator_params(type_name, item, path, c)
        result.append(
            EvaluatorSettings(
                name=name,
                type_name=type_name,
                requires_expected=type_name in ("exact_match", "normalized_text"),
                params=MappingProxyType(params),
            )
        )
    return tuple(result)


def _regression(data: Mapping[str, object], c: _Collector) -> RegressionSettings:
    table = _table(data, "regression", c)
    _unknown_keys(table, REGRESSION_KEYS, "regression.", c)
    ratio = _number(
        table,
        "max_p95_latency_ratio",
        None,
        "regression.max_p95_latency_ratio",
        c,
        low=1.0,
        low_exclusive=True,
    )
    drop = _number(
        table, "max_pass_rate_drop", 0.0, "regression.max_pass_rate_drop", c, low=0.0, high=1.0
    )
    return RegressionSettings(
        max_newly_failing=_integer(
            table, "max_newly_failing", 0, "regression.max_newly_failing", c
        ),
        max_newly_errored=_integer(
            table, "max_newly_errored", 0, "regression.max_newly_errored", c
        ),
        inconclusive_as_regression=_bool(
            table, "inconclusive_as_regression", False, "regression.inconclusive_as_regression", c
        ),
        max_pass_rate_drop=drop if drop is not None else 0.0,
        min_executed_for_rate_check=_integer(
            table, "min_executed_for_rate_check", 30, "regression.min_executed_for_rate_check", c
        ),
        max_p95_latency_ratio=ratio,
        missing_case_policy=_choice(
            table,
            "missing_case_policy",
            MISSING_CASE_POLICIES,
            "fail",
            "regression.missing_case_policy",
            c,
        ),
    )


def config_from_mapping(
    data: Mapping[str, object], *, config_dir: Path | None = None
) -> EvalForgeConfig:
    """Validate a parsed configuration mapping and return an ``EvalForgeConfig``.

    Raises ``SchemaVersionError`` for an unsupported major version and ``ConfigError`` with all
    collected errors otherwise.
    """
    c = _Collector()
    _unknown_keys(data, TOP_LEVEL_KEYS, "", c)

    raw_version = data.get("schema_version")
    if not isinstance(raw_version, str):
        c.add("CONFIG_INVALID", '"schema_version" is required.', "schema_version")
    else:
        try:
            check_schema_version(raw_version)
        except ValidationError as exc:
            c.add("CONFIG_INVALID", str(exc), "schema_version")

    run = _run(data, c)
    dataset = _dataset(data, c)
    target = _target(data, c)
    evaluators = _evaluators(data, c)
    regression = _regression(data, c)

    if c.errors:
        raise ConfigError(
            "CONFIG_INVALID",
            f"{len(c.errors)} configuration error(s) found.",
            errors=tuple(c.errors),
        )
    assert dataset is not None and target is not None  # guaranteed when no errors were collected
    return EvalForgeConfig(
        schema_version=raw_version if isinstance(raw_version, str) else SCHEMA_VERSION,
        run=run,
        dataset=dataset,
        target=target,
        evaluators=evaluators,
        regression=regression,
        config_dir=config_dir,
    )


def load_config_file(path: str | Path) -> EvalForgeConfig:
    """Read and validate a TOML configuration file.

    Target and evaluator modules are not imported.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise ConfigError("USAGE_ERROR", f"configuration file not found: {file_path}")
    try:
        text = file_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError("CONFIG_INVALID", "configuration file is not valid UTF-8.") from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError("CONFIG_INVALID", f"configuration is not valid TOML: {exc}") from exc
    return config_from_mapping(data, config_dir=file_path.resolve().parent)
