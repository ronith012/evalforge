# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Configuration validation (DATA_MODELS §4; CLI_SPECIFICATION §2.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from evalforge.config import config_from_mapping, load_config_file
from evalforge.errors import ConfigError, SchemaVersionError

# Taken from DATA_MODELS §4 (synthetic values).
EXAMPLE_TOML = """
schema_version = "1.0"

[run]
io_mode = "hashes"
timeout_seconds = 30.0

[dataset]
path = "datasets/support.jsonl"

[target]
callable = "examples.support_bot:answer"
name = "support-bot-v2"

[[evaluators]]
name = "exact"
type = "exact_match"

[[evaluators]]
name = "has_answer"
type = "required_fields"
paths = ["answer"]

[[evaluators]]
name = "text_norm"
type = "normalized_text"
casefold = true

[[evaluators]]
name = "no_placeholder"
type = "rule_based"
not_contains = ["TODO", "lorem ipsum"]
max_length = 2000

[[evaluators]]
name = "fast_enough"
type = "latency"
max_ms = 2000

[regression]
max_newly_failing = 0
max_pass_rate_drop = 0.05
"""


def _parse(text: str) -> dict[str, object]:
    import tomllib

    data: dict[str, object] = tomllib.loads(text)
    return data


def _minimal() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "dataset": {"path": "d.jsonl"},
        "target": {"callable": "m:f"},
        "evaluators": [{"name": "exact", "type": "exact_match"}],
    }


def _errors(data: dict[str, object]) -> list[tuple[str, str | None]]:
    with pytest.raises(ConfigError) as info:
        config_from_mapping(data)
    return [(item.code, item.path) for item in info.value.errors]


def test_example_configuration_is_accepted() -> None:
    config = config_from_mapping(_parse(EXAMPLE_TOML))
    assert config.run.io_mode == "hashes"
    assert config.run.redaction is True
    assert config.target.callable_ref == "examples.support_bot:answer"
    assert config.target.name == "support-bot-v2"
    assert [item.name for item in config.evaluators] == [
        "exact",
        "has_answer",
        "text_norm",
        "no_placeholder",
        "fast_enough",
    ]
    assert config.regression.max_newly_failing == 0
    assert config.regression.max_pass_rate_drop == 0.05


def test_requires_expected_is_derived_from_the_evaluator_type() -> None:
    config = config_from_mapping(_parse(EXAMPLE_TOML))
    flags = {item.name: item.requires_expected for item in config.evaluators}
    assert flags == {
        "exact": True,
        "has_answer": False,
        "text_norm": True,
        "no_placeholder": False,
        "fast_enough": False,
    }


def test_defaults_match_the_planning_proposals() -> None:
    config = config_from_mapping(_minimal())
    assert config.run.io_mode == "full"  # OD-12 recommendation, not yet approved
    assert config.run.timeout_seconds == 30.0
    assert config.regression.max_newly_failing == 0
    assert config.regression.missing_case_policy == "fail"
    assert config.target.name == "m:f"


def test_unknown_key_is_reported_with_its_path() -> None:
    data = _minimal()
    data["regression"] = {"max_newly_faling": 0}
    assert _errors(data) == [("CONFIG_UNKNOWN_KEY", "regression.max_newly_faling")]


@pytest.mark.parametrize("flag", ["allow_dataset_change", "allow_evaluator_change", "strict"])
def test_override_flags_cannot_be_set_in_configuration(flag: str) -> None:
    data = _minimal()
    data[flag] = True
    with pytest.raises(ConfigError) as info:
        config_from_mapping(data)
    error = info.value.errors[0]
    assert error.code == "CONFIG_UNKNOWN_KEY"
    assert "command-line or API arguments" in error.message


def test_missing_evaluators_is_an_error() -> None:
    data = _minimal()
    del data["evaluators"]
    assert ("CONFIG_INVALID", "evaluators") in _errors(data)


def test_duplicate_evaluator_names_are_rejected() -> None:
    data = _minimal()
    data["evaluators"] = [
        {"name": "exact", "type": "exact_match"},
        {"name": "exact", "type": "exact_match"},
    ]
    assert ("CONFIG_INVALID", "evaluators[1].name") in _errors(data)


def test_unknown_evaluator_type_is_rejected() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "x", "type": "semantic_similarity"}]
    assert ("CONFIG_INVALID", "evaluators[0].type") in _errors(data)


def test_latency_requires_positive_max_ms() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "fast", "type": "latency", "max_ms": 0}]
    assert ("CONFIG_INVALID", "evaluators[0].max_ms") in _errors(data)


def test_required_fields_requires_dotted_paths() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "f", "type": "required_fields", "paths": ["answer", "a..b"]}]
    assert ("CONFIG_INVALID", "evaluators[0].paths[1]") in _errors(data)


def test_rule_based_needs_at_least_one_rule() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "r", "type": "rule_based"}]
    assert ("CONFIG_INVALID", "evaluators[0]") in _errors(data)


def test_rule_based_min_length_cannot_exceed_max_length() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "r", "type": "rule_based", "min_length": 5, "max_length": 2}]
    assert ("CONFIG_INVALID", "evaluators[0].min_length") in _errors(data)


def test_regex_that_does_not_compile_is_rejected() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "r", "type": "rule_based", "regex": ["(unclosed"]}]
    assert ("CONFIG_INVALID", "evaluators[0].regex[0]") in _errors(data)


def test_regex_longer_than_the_limit_is_rejected() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "r", "type": "rule_based", "regex": ["a" * 513]}]
    assert ("CONFIG_INVALID", "evaluators[0].regex[0]") in _errors(data)


def test_custom_evaluator_needs_module_attribute_reference() -> None:
    data = _minimal()
    data["evaluators"] = [{"name": "c", "type": "custom", "callable": "no_colon_here"}]
    assert ("CONFIG_INVALID", "evaluators[0].callable") in _errors(data)


def test_timeout_bounds_are_enforced() -> None:
    data = _minimal()
    data["run"] = {"timeout_seconds": 0}
    assert ("CONFIG_INVALID", "run.timeout_seconds") in _errors(data)
    data["run"] = {"timeout_seconds": 3601}
    assert ("CONFIG_INVALID", "run.timeout_seconds") in _errors(data)


def test_invalid_io_mode_is_rejected() -> None:
    data = _minimal()
    data["run"] = {"io_mode": "store_everything"}
    assert ("CONFIG_INVALID", "run.io_mode") in _errors(data)


def test_fail_on_accepts_only_known_statuses() -> None:
    data = _minimal()
    data["run"] = {"fail_on": ["fail", "pass"]}
    assert ("CONFIG_INVALID", "run.fail_on") in _errors(data)


def test_max_pass_rate_drop_must_be_a_fraction() -> None:
    data = _minimal()
    data["regression"] = {"max_pass_rate_drop": 1.5}
    assert ("CONFIG_INVALID", "regression.max_pass_rate_drop") in _errors(data)


def test_p95_ratio_must_exceed_one() -> None:
    data = _minimal()
    data["regression"] = {"max_p95_latency_ratio": 1.0}
    assert ("CONFIG_INVALID", "regression.max_p95_latency_ratio") in _errors(data)


def test_booleans_are_not_accepted_as_numbers() -> None:
    data = _minimal()
    data["run"] = {"timeout_seconds": True}
    assert ("CONFIG_INVALID", "run.timeout_seconds") in _errors(data)


def test_errors_are_collected_and_capped_at_one_hundred() -> None:
    data = _minimal()
    data["run"] = {f"bad_key_{index}": index for index in range(150)}
    with pytest.raises(ConfigError) as info:
        config_from_mapping(data)
    assert len(info.value.errors) == 100
    assert all(item.code == "CONFIG_UNKNOWN_KEY" for item in info.value.errors)


def test_unsupported_schema_major_raises_schema_error() -> None:
    data = _minimal()
    data["schema_version"] = "2.0"
    with pytest.raises(SchemaVersionError) as info:
        config_from_mapping(data)
    assert info.value.code == "SCHEMA_VERSION_UNSUPPORTED"


def test_missing_schema_version_is_an_error() -> None:
    data = _minimal()
    del data["schema_version"]
    assert ("CONFIG_INVALID", "schema_version") in _errors(data)


def test_load_config_file_reads_toml_and_records_directory(tmp_path: Path) -> None:
    path = tmp_path / "evalforge.toml"
    path.write_text(EXAMPLE_TOML, encoding="utf-8")
    config = load_config_file(path)
    assert config.config_dir == tmp_path.resolve()
    assert len(config.evaluators) == 5


def test_load_config_file_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as info:
        load_config_file(tmp_path / "absent.toml")
    assert info.value.code == "USAGE_ERROR"


def test_load_config_file_reports_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("schema_version = ", encoding="utf-8")
    with pytest.raises(ConfigError) as info:
        load_config_file(path)
    assert info.value.code == "CONFIG_INVALID"


def test_load_config_file_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_bytes(b"schema_version = \xff\xfe")
    with pytest.raises(ConfigError, match="not valid UTF-8"):
        load_config_file(path)
