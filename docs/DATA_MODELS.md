# EvalForge — Data Models

Status: **Proposed — awaiting approval.** Examples are proposals, not captured output.

Implements: TRD §4–§9 and PRD-NF-008, PRD-NF-009. Models are implemented as frozen dataclasses with validation
functions (TRD §3.2; no third-party validation library), and the JSON shapes below are the
persisted and reported forms.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Encoding | UTF-8 JSON. |
| Identifiers | Case `id`: user-provided string per TRD-041. Run `run_id`: UUIDv4 string. Evaluator `name`: `^[a-z][a-z0-9_]{0,63}$`. |
| Timestamps | RFC 3339 in UTC with a `Z` suffix and millisecond precision, for example `2026-10-18T14:03:22.415Z`. |
| Durations | Float milliseconds, non-negative, rounded to 3 decimal places. |
| Hashes | String `sha256:<64 lowercase hex>`. |
| Numbers | Finite only. `NaN`, `Infinity` are invalid everywhere (TRD-034). |
| Absence vs null | In case files, an absent `expected` means "no expected value"; `"expected": null` means expected value is JSON null. These are distinct. |
| Versioning | Every persisted top-level object has `schema_version` in `MAJOR.MINOR` form. Current: `"1.0"`. |
| Unknown keys | Rejected in input files (TRD-043, TRD-182). Tolerated in persisted artifacts when the major version matches (forward compatibility, TRD-241). |
| Null policy | Optional fields are omitted rather than set to null in persisted output, except where `null` is meaningful (for example `pass_rate` when executed = 0). |

## 2. Evaluation case

Input file entry (one JSON object per JSONL line, or one element of a JSON array).

| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `id` | string | yes | TRD-041, unique (TRD-042) | Stable identifier across versions of the dataset |
| `input` | JSON value | yes | Size limits (TRD-211). Object recommended. | Passed to the target |
| `expected` | JSON value | no | Any JSON value including null | Used by reference-based evaluators |
| `metadata` | object | no | JSON object (TRD-045) | Free-form; not interpreted by evaluators |
| `tags` | array of strings | no | Unique; ≤ 32 items; each ≤ 64 characters | For filtering with `--case` or future selectors |

Example:

```json
{"id": "refund-001", "input": {"question": "Can I get a refund after 30 days?"}, "expected": {"answer": "No, refunds are available within 30 days."}, "metadata": {"category": "refunds", "source": "synthetic"}, "tags": ["smoke"]}
```

Canonical case content (used for `changed_input` detection, TRD-132): the JSON object
with keys `id`, `input`, `expected` (present only if present in file), `metadata`,
`tags`, serialized canonically (TRD §4.4). Its hash is `case_sha256`.

## 3. Evaluation dataset

In-memory object and manifest-level fingerprint. The dataset file itself is not a
wrapper object; it is the case list.

| Field | Type | Description |
|---|---|---|
| `source_path` | string | Path as given, stored relative to the configuration file directory, or as given for API-created datasets. Absolute paths are never stored (DATA_HANDLING §5). Recorded for traceability; not used for trust decisions. |
| `format` | `"json"` \| `"jsonl"` | From extension (TRD-033) |
| `sha256` | hash | Raw file bytes (TRD-050) |
| `canonical_sha256` | hash | Canonical case list (TRD-051) |
| `case_count` | integer | Number of cases |
| `tags_summary` | object | Map of tag → count (optional, for report readability) |

Manifest fragment:

```json
{"source_path": "datasets/support.jsonl", "format": "jsonl", "sha256": "sha256:4f1c…", "canonical_sha256": "sha256:9ab2…", "case_count": 5}
```

Path rule: `source_path` is recorded for humans. Comparison uses hashes, never paths.

## 4. Configuration file (`evalforge.toml`)

Mapped to the `EvalForgeConfig` model. Unknown keys are errors (TRD-182).

```toml
schema_version = "1.0"

[run]
run_root = ".evalforge/runs"        # relative to this file (TRD-184)
io_mode = "full"                    # "full" | "hashes" | "none" (OD-12; DATA_HANDLING §3)
redaction = true                    # DATA_HANDLING §7; disabling is recorded (OD-27)
timeout_seconds = 30.0              # per target call; > 0 and ≤ 3600
fail_on = []                        # subset of ["fail", "error", "inconclusive"]; used by `run` exit code (CLI §4)

[dataset]
path = "datasets/support.jsonl"

[target]
callable = "examples.support_bot:answer"   # module:attribute; trusted code (THR-004)
name = "support-bot-v2"                    # optional label; default derived from callable

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
collapse_whitespace = true

[[evaluators]]
name = "no_placeholder"
type = "rule_based"
not_contains = ["TODO", "lorem ipsum"]
max_length = 2000

[[evaluators]]
name = "fast_enough"
type = "latency"
max_ms = 2000

[[evaluators]]
name = "domain_rule"
type = "custom"
callable = "evalforge_checks.domain:RefundRule"   # trusted code

[regression]
max_newly_failing = 0
max_newly_errored = 0
inconclusive_as_regression = false
max_pass_rate_drop = 0.0
min_executed_for_rate_check = 30
max_p95_latency_ratio = 1.5
missing_case_policy = "fail"
```

Validation rules (summary; full list in CLI §2.3):

- At least one evaluator is required.
- Evaluator `name` values are unique.
- `timeout_seconds` > 0.
- `io_mode = "hashes"` or `"none"`: `inspect --case` shows no input or output content. This is documented behaviour, not an error.
- Relative paths resolve against the configuration file directory.

### 4.1 Evaluator configuration fields

| Field | Applies to | Type | Required | Default |
|---|---|---|---|---|
| `name` | all | string | yes | — |
| `type` | all | enum: `exact_match`, `normalized_text`, `json_structure`, `required_fields`, `rule_based`, `latency`, `custom` | yes | — |
| `requires_expected` | derived | bool | derived from type | `exact_match`: true; `normalized_text`: true; others: false |
| `nfc`, `casefold`, `collapse_whitespace`, `strip` | `normalized_text` | bool | no | true |
| `top_level_type` | `json_structure` | enum or absent | no | absent |
| `paths` | `required_fields` | list of dotted paths (≤ 32, each ≤ 256 chars) | yes | — |
| `contains`, `not_contains`, `regex` | `rule_based` | list of strings (regex ≤ 512 chars) | at least one rule | — |
| `min_length`, `max_length` | `rule_based` | non-negative integers | no | absent |
| `max_ms` | `latency` | positive number | yes | — |
| `callable` | `custom` | `module:attribute` string | yes | — |

Evaluator fingerprint (persisted in manifest, TRD-085):

```json
{"name": "exact", "type": "exact_match", "version": "1.0", "requires_expected": true, "parameters": {}, "fingerprint": "sha256:7d2e…"}
```

For custom evaluators, `fingerprint` also includes the SHA-256 of the defining source file, and `module` and `qualname` are recorded.

## 5. Target configuration

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes (derived if absent) | Human label; appears in reports and comparisons |
| `callable` | `module:attribute` string or object reference (API only) | yes | Target to call |
| `timeout_seconds` | positive number | no | Overrides run timeout |
| `seed` | JSON scalar | no | Opaque value recorded if the target uses one (TRD-105) |
| `adapter` | string | no | Reserved; `"callable"` in MVP |

Persisted form (in manifest):

```json
{"name": "support-bot-v2", "adapter": "callable", "callable": "examples.support_bot:answer", "timeout_seconds": 30.0, "seed": null}
```

## 6. Run manifest

Written as `manifest.json` (TRD-112).

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | `"1.0"` |
| `run_id` | UUIDv4 string | yes | TRD-110 |
| `status` | enum: `RUNNING`, `COMPLETED`, `ABORTED`, `FAILED` | yes | Run-level status (EVALUATION_METHODOLOGY §3.4) |
| `started_at` | timestamp | yes | |
| `finished_at` | timestamp | when finalized | |
| `tool` | object `{name, version}` | yes | `name` = `"evalforge"` |
| `environment` | object `{evalforge_version, python, os_family, machine}` | yes | TRD-106; DATA_HANDLING §6 |
| `dataset` | Dataset fragment (§3) | yes | |
| `target` | Target configuration (§5) | yes | |
| `evaluators` | array of evaluator fingerprints (§4.1) | yes | Order as configured |
| `regression_config` | object | no | Thresholds used when the run was created, if any |
| `config_snapshot` | object | yes | Configuration with secret-like values removed and paths relative (DATA_HANDLING §5; SECURITY §4.3) |
| `timeout_seconds` | number | yes | Effective run default |
| `persisted` | bool | yes | Always `true` for CLI runs (TRD-117) |
| `io_mode` | `"full"` \| `"hashes"` \| `"none"` | yes | Stored content mode (DATA_HANDLING §3) |
| `redaction` | bool | yes | Whether redaction was enabled. `false` produces a warning in outputs (DATA_HANDLING §7.5) |
| `case_selection` | object `{mode, ids?, tags?}` | yes | `mode` = `all` \| `ids` \| `tags` |
| `counts` | object | when finalized | `{selected, executed, skipped_not_executed, threads_possibly_running}` (`threads_possibly_running` counts timed-out target calls whose worker thread may still be alive; THREAT_MODEL THR-010) |
| `cases_sha256` | hash | when finalized | SHA-256 of the exact bytes of `cases.jsonl` (TRD-114; ARTIFACT_INTEGRITY §3) |
| `summary_sha256` | hash | when finalized | SHA-256 of the exact bytes of `summary.json` (ARTIFACT_INTEGRITY §3). The manifest itself is not hashed. |
| `error` | Error object (§9) | when `FAILED` | |

Example (finalized):

```json
{
  "schema_version": "1.0",
  "run_id": "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
  "status": "COMPLETED",
  "started_at": "2026-10-18T14:03:22.000Z",
  "finished_at": "2026-10-18T14:03:24.812Z",
  "tool": {"name": "evalforge", "version": "0.0.0-planning"},
  "environment": {"evalforge_version": "0.0.0-planning", "python": "3.12.4", "os_family": "Darwin", "machine": "arm64"},
  "dataset": {"source_path": "datasets/support.jsonl", "format": "jsonl", "sha256": "sha256:4f1c…", "canonical_sha256": "sha256:9ab2…", "case_count": 5},
  "target": {"name": "support-bot-v2", "adapter": "callable", "callable": "examples.support_bot:answer", "timeout_seconds": 30.0, "seed": null},
  "evaluators": [
    {"name": "exact", "type": "exact_match", "version": "1.0", "requires_expected": true, "parameters": {}, "fingerprint": "sha256:7d2e…"}
  ],
  "config_snapshot": {"run": {"io_mode": "full", "redaction": true, "timeout_seconds": 30.0}, "dataset": {"path": "datasets/support.jsonl"}},
  "timeout_seconds": 30.0,
  "persisted": true,
  "io_mode": "full",
  "redaction": true,
  "case_selection": {"mode": "all"},
  "counts": {"selected": 5, "executed": 5, "skipped_not_executed": 0},
  "cases_sha256": "sha256:c01e…",
  "summary_sha256": "sha256:5d7a…"
}
```

(The `0.0.0-planning` version string is a placeholder; no version has been released.)

## 7. Case result

One JSON object per line in `cases.jsonl` (TRD-102). Dataset order.

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | `"1.0"` |
| `run_id` | UUIDv4 | yes | Traceability (PRD-NF-008) |
| `case_id` | string | yes | Dataset case ID |
| `case_sha256` | hash | yes | Canonical case content hash |
| `status` | enum | yes | PASS, FAIL, ERROR, SKIPPED, INCONCLUSIVE (EVALUATION_METHODOLOGY §3.3) |
| `status_reason` | string or null | yes | Reason code for FAIL/ERROR/INCONCLUSIVE/SKIPPED; null for PASS |
| `target` | object | yes | See below |
| `evaluators` | array of EvaluatorResult (§8) | yes | One per configured evaluator, in configured order |
| `input_sha256` | hash | when `io_mode` is `full` or `hashes` | Raw input hash (ARTIFACT_INTEGRITY §2) |
| `input` | JSON value | when `io_mode = "full"` | Stored input, redacted if redaction is enabled |
| `expected_sha256` | hash | when `io_mode` is `full` or `hashes` and `expected` is present | Raw expected hash |
| `expected` | JSON value | when `io_mode = "full"` and present in case | Stored expected value, redacted if enabled |
| `output` | JSON value | when `io_mode = "full"` and target ran | Stored output, redacted if enabled |
| `output_sha256` | hash | when target produced output and `io_mode` is `full` or `hashes` | Hash of canonical output as returned by the target, before redaction (ARTIFACT_INTEGRITY §2) |
| `redactions` | integer | yes | Count of replacements applied to stored values. 0 when redaction is disabled or nothing matched. |

`target` object:

| Field | Type | Description |
|---|---|---|
| `status` | `"OK"` \| `"ERROR"` | Target execution status |
| `error_code` | string or null | `TARGET_EXCEPTION`, `TARGET_TIMEOUT`, `TARGET_OUTPUT_INVALID`, or null |
| `error` | Error object or null | Exception type and message, with message truncated to 500 characters, redacted when redaction is enabled (DATA_HANDLING §4). Tracebacks are never stored. |
| `duration_ms` | number | Measured even on timeout (equals timeout value) |

Example (FAIL):

```json
{
  "schema_version": "1.0",
  "run_id": "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
  "case_id": "refund-001",
  "case_sha256": "sha256:aa10…",
  "status": "FAIL",
  "status_reason": "exact",
  "target": {"status": "OK", "error_code": null, "error": null, "duration_ms": 412.337},
  "evaluators": [
    {"name": "exact", "status": "FAIL", "score": 0.0, "reason_code": "VALUE_MISMATCH", "message": "Output differs from expected value.", "details": {}},
    {"name": "has_answer", "status": "PASS", "score": 1.0, "reason_code": null, "message": "All required paths present.", "details": {"paths": ["answer"]}}
  ],
  "input": {"question": "Can I get a refund after 30 days?"},
  "expected": {"answer": "No, refunds are available within 30 days."},
  "output": {"answer": "Yes, within 45 days."},
  "output_sha256": "sha256:6e0d…"
}
```

Example (ERROR, timeout):

```json
{
  "schema_version": "1.0",
  "run_id": "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
  "case_id": "slow-017",
  "case_sha256": "sha256:bb21…",
  "status": "ERROR",
  "status_reason": "TARGET_TIMEOUT",
  "target": {"status": "ERROR", "error_code": "TARGET_TIMEOUT", "error": {"type": "TimeoutError", "message": "Target exceeded 30.0 s"}, "duration_ms": 30000.0},
  "evaluators": [
    {"name": "exact", "status": "SKIPPED", "score": null, "reason_code": "TARGET_ERROR", "message": "Target did not produce output.", "details": {}}
  ]
}
```

Rules:

- `evaluators` always lists every configured evaluator, even when skipped.
- A case result is written once; it is never edited after writing.

## 8. Evaluator result

Embedded in case results.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string | yes | Matches configuration name |
| `status` | enum: PASS, FAIL, ERROR, SKIPPED, INCONCLUSIVE | yes | |
| `score` | number or null | yes | `[0, 1]` or null. Deterministic evaluators return 1.0 for PASS and 0.0 for FAIL, or null for SKIPPED/ERROR. Scores are not averaged in MVP. |
| `reason_code` | string or null | yes | From §9 registry; null for PASS |
| `message` | string | yes | ≤ 500 characters; plain text |
| `details` | object | yes | JSON object; ≤ 16 KiB serialized; may be empty. Built-in evaluators must not place case content here (DATA_HANDLING §3.3). |

Note: the `score` field is an annotation for readability. Status, not score, determines
case status (EVALUATION_METHODOLOGY §3). Latency evaluator may include `details.duration_ms` and `details.max_ms`.

Example (INCONCLUSIVE, custom):

```json
{"name": "domain_rule", "status": "INCONCLUSIVE", "score": null, "reason_code": "CUSTOM_UNCERTAIN", "message": "Rule could not determine refund eligibility from output.", "details": {"missing": "eligibility_window"}}
```

## 9. Error and reason-code registry

Codes are stable strings. New codes may be added in minor versions. Codes are never
renamed; removed codes are deprecated for one minor version (TRD-243).

### 9.1 Case / evaluator reason codes

| Code | Status | Meaning |
|---|---|---|
| `VALUE_MISMATCH` | FAIL | Exact or normalized comparison differed |
| `OUTPUT_NOT_TEXT` | FAIL | Text evaluator received non-string output |
| `NOT_JSON` | FAIL | JSON evaluator received text that does not parse |
| `JSON_TYPE_MISMATCH` | FAIL | Top-level JSON type differs from configuration |
| `REQUIRED_FIELD_MISSING` | FAIL | Required path absent or null |
| `RULE_CONTAINS_MISSING` | FAIL | Required substring absent |
| `RULE_NOT_CONTAINS_PRESENT` | FAIL | Forbidden substring present |
| `RULE_REGEX_NO_MATCH` | FAIL | Regex did not match |
| `RULE_LENGTH_OUT_OF_BOUNDS` | FAIL | Length outside min/max |
| `LATENCY_EXCEEDED` | FAIL | Duration above `max_ms` |
| `CUSTOM_FAIL` | FAIL | Custom evaluator returned FAIL without a more specific code |
| `CUSTOM_UNCERTAIN` | INCONCLUSIVE | Custom evaluator reported uncertainty |
| `TARGET_EXCEPTION` | ERROR | Target raised an exception |
| `TARGET_TIMEOUT` | ERROR | Target exceeded timeout (best-effort; the thread may continue, ARCHITECTURE §11) |
| `TARGET_CRASHED` | ERROR | Reserved for post-MVP process isolation (ARCHITECTURE §11.1). Not produced in MVP. |
| `TARGET_OUTPUT_INVALID` | ERROR | Target output not JSON-serializable |
| `EVALUATOR_EXCEPTION` | ERROR | Evaluator raised |
| `EVALUATOR_RESULT_INVALID` | ERROR | Evaluator returned a malformed result |
| `NO_EXPECTED` | SKIPPED | Case has no `expected` and evaluator requires it |
| `TARGET_ERROR` | SKIPPED | Evaluator not run because the target failed |
| `NO_EVALUATORS` | SKIPPED | No evaluators configured |
| `USER_FILTER` | SKIPPED | Excluded by `--case` or tag selection |
| `NOT_APPLICABLE` | SKIPPED | Evaluator does not apply to this output type |
| `NOT_EXECUTED` | SKIPPED | Run aborted before the case was reached |

### 9.2 Run and tool error codes

| Code | Context | Exit code |
|---|---|---|
| `CONFIG_INVALID` | Config validation | 2 |
| `CONFIG_UNKNOWN_KEY` | Config validation | 2 |
| `USAGE_ERROR` | CLI usage | 2 |
| `DATASET_INVALID` | Dataset validation | 3 |
| `DATASET_DUPLICATE_ID` | Dataset validation | 3 |
| `DATASET_LIMIT_EXCEEDED` | Dataset validation | 3 |
| `DATASET_ENCODING_INVALID` | Dataset validation | 3 |
| `DATASET_FORMAT_UNSUPPORTED` | Dataset validation | 3 |
| `TARGET_LOAD_FAILED` | Target import failed | 2 (config-level) |
| `EVALUATOR_LOAD_FAILED` | Custom evaluator import failed | 2 |
| `STORAGE_ERROR` | Write or read failure | 4 |
| `STORAGE_LOCKED` | Concurrent writer | 4 |
| `ENGINE_ERROR` | Unhandled engine exception | 4 |
| `RUN_ABORTED` | User interrupt recorded | 4 (for `run`) |
| `RUN_INCOMPLETE` | Comparison refused | 5 |
| `RUN_NOT_FOUND` | Inspect/compare | 2 |
| `DATASET_CHANGED` | Comparison (with flag: warning) | 5 (without flag) |
| `EVALUATOR_CHANGED` | Comparison (with flag: warning) | 5 (without flag) |
| `SCHEMA_VERSION_UNSUPPORTED` | Reader | 4 |
| `IO_NOT_STORED` | `report export --include-io` on a run whose `io_mode` is not `full` | 2 |
| `INTEGRITY_MISMATCH` | `cases_sha256` or `summary_sha256` mismatch on inspect/compare | 4 |

### 9.3 Error object

```json
{"code": "STORAGE_ERROR", "message": "Cannot write to run directory.", "path": ".evalforge/runs/3f2b…", "cause": "PermissionError"}
```

Fields: `code` (required), `message` (required, ≤ 500 chars), `path` (optional),
`line` / `field` (optional, for dataset errors), `cause` (optional short type name).
Never contains secret values (TRD-202).

## 10. Run summary

Written as `summary.json` (TRD-113). Also the basis of terminal and JSON report summaries.

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"1.0"` |
| `run_id` | UUIDv4 | |
| `counts` | object | `{PASS, FAIL, ERROR, SKIPPED, INCONCLUSIVE}` integers over cases |
| `executed` | integer | PASS + FAIL + ERROR + INCONCLUSIVE |
| `pass_rate` | number or null | PASS ÷ executed; null if executed = 0 |
| `pass_rate_ci95` | `[lower, upper]` or null | Wilson interval (EVALUATION_METHODOLOGY §7) |
| `error_codes` | object | Map code → count over ERROR cases |
| `fail_by_evaluator` | object | Map evaluator name → count of FAIL results |
| `latency_ms` | object or null | `{p50, p95, max}` over executed cases with output; nearest-rank |
| `not_executed` | integer | Cases not attempted (aborted runs) |

Example:

```json
{
  "schema_version": "1.0",
  "run_id": "3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90",
  "counts": {"PASS": 3, "FAIL": 1, "ERROR": 1, "SKIPPED": 0, "INCONCLUSIVE": 0},
  "executed": 5,
  "pass_rate": 0.6,
  "pass_rate_ci95": [0.2307, 0.8824],
  "error_codes": {"TARGET_TIMEOUT": 1},
  "fail_by_evaluator": {"exact": 1},
  "latency_ms": {"p50": 380.1, "p95": 30000.0, "max": 30000.0},
  "not_executed": 0
}
```

Invariant (PRD guarantee: individual failures remain accessible): every aggregate in
this object is derivable from `cases.jsonl`, and a test recomputes them from the case
file.

## 11. Run comparison

Produced by `compare`. Written only if requested (`--out`) or returned by the API.

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"1.0"` |
| `comparison_id` | UUIDv4 | |
| `created_at` | timestamp | |
| `baseline` | `{run_id, path, dataset_sha256, canonical_sha256, target_name}` | |
| `candidate` | same | |
| `compatibility` | object | `{dataset: "same"\|"changed", evaluators: "same"\|"changed", allowed: [flag names], overrides: [{flag, scope, observed}], io_available: {baseline, candidate}, warnings: [codes], refusals: [codes]}` |
| `counts` | object | Category counts (§5) |
| `cases` | array of CaseComparison | One per case ID in union of both runs, sorted by case ID |
| `metrics` | object | Baseline, candidate, delta for pass_rate, error_rate, inconclusive_rate, counts, latency_p50_ms, latency_p95_ms |
| `findings` | array of RegressionFinding (§12) | |
| `exit_status` | `"pass"` \| `"regression"` \| `"refused"` | Derived from findings and refusals |

CaseComparison:

```json
{"case_id": "refund-001", "category": "regressed", "subtype": "to_fail", "baseline_status": "PASS", "candidate_status": "FAIL", "baseline_output_sha256": "sha256:aa…", "candidate_output_sha256": "sha256:bb…", "output_changed": true, "evaluators_changed": ["exact"]}
```

Rules:

- `cases` is sorted by `case_id` for determinism (PRD-NF-002). Sorting is by Unicode code point.
- Comparisons are reproducible: the same two run directories produce a byte-identical
  comparison file, except `comparison_id` and `created_at`.

## 12. Regression finding

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | yes | From TRD §9.2 table |
| `severity` | `"error"` \| `"warning"` \| `"info"` | yes | `error` counts toward exit code 1 |
| `message` | string | yes | Plain-language explanation; ≤ 500 characters; stable template for golden tests |
| `threshold` | object or null | when applicable | `{key, configured, observed}` |
| `case_ids` | array of strings | when applicable | Sorted |
| `metric` | string or null | for metric findings | e.g. `pass_rate` |
| `values` | object or null | for metric findings | `{baseline, candidate, delta}` |

Example:

```json
{
  "code": "CASE_REGRESSED_TO_FAIL",
  "severity": "error",
  "message": "1 case that passed in the baseline now fails: refund-001.",
  "threshold": {"key": "regression.max_newly_failing", "configured": 0, "observed": 1},
  "case_ids": ["refund-001"]
}
```

Example (metric):

```json
{
  "code": "PASS_RATE_DROP",
  "severity": "error",
  "message": "Pass rate fell from 0.800 to 0.600 (drop 0.200), above the configured maximum of 0.050.",
  "threshold": {"key": "regression.max_pass_rate_drop", "configured": 0.05, "observed": 0.2},
  "metric": "pass_rate",
  "values": {"baseline": 0.8, "candidate": 0.6, "delta": -0.2}
}
```

Explanations must not claim a cause. They report the observed change and the
configured threshold.

## 13. Compatibility rules

| Change | Allowed in minor (1.x) | Requires major |
|---|---|---|
| Add optional field | Yes | No |
| Add enum value to reason codes | Yes (readers must tolerate unknown reason codes, treating them as generic) | No |
| Add new finding code | Yes | No |
| Rename or remove a field | No | Yes |
| Change field type | No | Yes |
| Change status meanings | No | Yes |
| Change hashing or canonicalization | No | Yes (and documented migration) |

Readers:

- Accept same-major artifacts (TRD-241).
- Reject different-major artifacts with `SCHEMA_VERSION_UNSUPPORTED` (PRD-NF-009).
- Use `unknown_code` treatment for unknown reason codes.

## 14. Serialization

- JSON files written with `ensure_ascii=False`, UTF-8, two-space indentation for
  manifest and summary, and one compact object per line for `cases.jsonl`.
- Key order: fixed order by the model definition, which makes diffs reviewable.
- Non-finite numbers are rejected on write.
- Output values are stored as provided after canonicalization for hashing only; the
  stored value is the original JSON value (not reformatted), except that key order
  follows model order for envelope fields only.
