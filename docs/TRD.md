# EvalForge — Technical Requirements Document

Status: **Approved decisions incorporated (see OPEN_DECISIONS.md).** Every technical choice in this document is
a proposal until approved (see [OPEN_DECISIONS](../OPEN_DECISIONS.md)).

Implements: [PRD](PRD.md). Architecture: [ARCHITECTURE](ARCHITECTURE.md).

---

## 1. Scope

This document specifies how the MVP must be built and verified: supported platforms,
packaging, data formats, interfaces, persistence, comparison, configuration, security
controls, and testing requirements. Behavioural definitions (what statuses mean) live
in [EVALUATION_METHODOLOGY](EVALUATION_METHODOLOGY.md); exact field definitions live in
[DATA_MODELS](DATA_MODELS.md).

Requirement IDs: `TRD-nnn`. Each cites the PRD requirements it supports.

## 2. Platform and language support (proposed)

| ID | Requirement | Supports |
|---|---|---|
| TRD-001 | Python 3.11, 3.12, and 3.13 are supported. Python 3.10 and earlier are not. Approved (OD-02; initial support set; all three tested in CI). | PRD-NF-005 |
| TRD-002 | Operating systems: Linux (x86_64), macOS (arm64 and x86_64), Windows (x86_64). Each is tested in CI. | PRD-NF-004 |
| TRD-003 | The package is pure Python. No compiled extensions in the MVP. | PRD-NF-006 |
| TRD-004 | Paths are handled with `pathlib`. Output files use UTF-8 with LF line endings; the terminal layer handles platform newlines. | PRD-NF-004 |

Rationale for 3.11 minimum: `tomllib` is in the standard library from 3.11, which
avoids a TOML parsing dependency (see §3). Python version support is approved (OD-02).

## 3. Packaging, dependencies, and installation

### 3.1 Packaging

| ID | Requirement |
|---|---|
| TRD-010 | Distributed as an sdist and a wheel built with a PEP 517 backend. Backend: Hatchling (approved, OD-03). |
| TRD-011 | Metadata includes `license = "Apache-2.0"`, a `NOTICE` file naming Bodepudi Ronith as copyright holder, and a `LICENSE` file. Each source file carries a short Apache-2.0 header (approved, OD-01). The copyright year is the year of initial publication (approved, OD-01). |
| TRD-012 | Project layout uses a `src/` layout (`src/evalforge/`). |
| TRD-013 | Console entry point `evalforge` maps to the CLI application. |
| TRD-014 | Package name `evalforge` must be checked for availability before first publication. Provisional local name approved (OD-10). Publication is blocked until package-index and trademark checks are completed (gate G-2). |
| TRD-015 | Installation from a clean virtual environment must succeed with `pip install .` and with `pip install dist/*.whl` (verified in CI). |

### 3.2 Dependencies (approved; OD-03, OD-15)

**Runtime dependencies: none beyond the Python standard library.** This replaces the earlier
proposal of Pydantic and Typer. Reasons:

- TRD-003 requires a pure-Python package. Pydantic v2's core is a compiled extension, so it
  conflicts with TRD-003 as originally written. The conflict was found during the final planning
  review.
- The MVP needs JSON, TOML (`tomllib`, 3.11+), hashing (`hashlib`), UUIDs, and simple
  validation. The standard library covers all of these.
- Zero runtime dependencies removes a supply-chain path (THREAT_MODEL THR-014, THR-015).

Consequences:

- Validation is implemented as frozen dataclasses plus validation functions. This is more
  code to write and test (milestone 2 effort increases; see IMPLEMENTATION_PLAN §4).
- The CLI uses `argparse`. Help output and subcommand structure are written by hand and
  covered by CLI tests (TST-CLI-001).
- JSON Schema files for published artifacts are written by hand and validated by tests
  (TST-SEC-013 and PRD-F-025 test, milestone 8).

Fallback: if the owner rejects zero dependencies, Pydantic is an option only with an explicit
TRD-003 amendment, a recorded justification, and a note in the release that the core includes
compiled code. *(OD-03, OD-15.)*

Dependencies deliberately **not** included in the MVP:

- Any LLM or provider SDK (openai, anthropic, etc.) — PRD-NG-010.
- `pandas`, `numpy`, `scipy` — statistics are counts, percentiles, and a Wilson interval.
- Any web framework or database driver — PRD-NG-002. SQLite comes from the standard library (`sqlite3`) if approved later.
- `jsonschema` — deferred; would be an optional extra if approved (OD-07).
- Any telemetry or analytics client.
- Pydantic, Typer, Click, Rich — see the fallback above.

Development-only dependencies (not installed for users):

| Dependency | Purpose |
|---|---|
| `pytest` | Test runner |
| `ruff` | Linting and formatting |
| `pytest-timeout` (proposed) | Enforcing a maximum runtime for tests that exercise timeouts |
| `mypy` (required CI gate, `--strict`; approved OD-15) | Static type checking of the public package |
| `pip-audit` (proposed) | Dependency vulnerability scan in CI |

### 3.3 Dependency management

| ID | Requirement |
|---|---|
| TRD-020 | A lock file (`uv.lock`) is committed for development and CI. Tool: uv (approved, OD-03). |
| TRD-021 | CI installs from the uv lock file and records the resolved versions in the job log. |
| TRD-022 | Dependency licences are reviewed before each release; the review is recorded in the release checklist. |
| TRD-023 | `pip-audit` runs in CI; a known high-severity vulnerability blocks release until addressed or documented. |
| TRD-024 | `mypy --strict` runs in CI as a required gate on the public package in `src/evalforge` (approved, OD-15). Build backend is Hatchling and the development environment is managed with uv (approved, OD-03). |
| TRD-025 | Before any dependency is installed, the Hatchling and uv versions to be used are verified, and their licences and maintenance status are recorded (gate G-1; OPEN_DECISIONS §3). |
| TRD-026 | No publication (package index, release, or public repository push) until package-index and trademark checks are complete (gate G-2; OD-10). |

## 4. Input formats and dataset handling

### 4.1 Accepted formats

| ID | Requirement | Supports |
|---|---|---|
| TRD-030 | Datasets are UTF-8 encoded. A leading UTF-8 BOM is accepted and removed. Any other encoding is a validation error. | PRD-F-001 |
| TRD-031 | `.jsonl`: one JSON object per line. Blank lines are ignored and counted. | PRD-F-001 |
| TRD-032 | `.json`: a top-level JSON array of case objects. | PRD-F-001 |
| TRD-033 | Other extensions are rejected with a validation error. Format is determined by extension, not content sniffing. | PRD-F-001 |
| TRD-034 | JSON parsing uses the standard library `json` module with `parse_constant` set to reject `NaN`, `Infinity`, and `-Infinity`. | PRD-NF-003 |

### 4.2 Limits (proposed; configurable with safe defaults)

| Limit | Default (proposed) | Rationale |
|---|---|---|
| Maximum dataset file size | 50 MiB | Bounds memory and parse time (THR-006) |
| Maximum number of cases | 100,000 | Bounds run duration and artifact size |
| Maximum line length (JSONL) | 1 MiB | Prevents single-line memory spikes |
| Maximum JSON nesting depth | 64 | Prevents stack exhaustion in recursive processing |
| Maximum string length in a case | 1 MiB | Same as line length |
| Maximum tags per case | 32 | Keeps filtering predictable |
| Maximum length of a tag | 64 characters | Same |

Limits are enforced before full materialization where practical (for JSONL, streaming
line by line). Exceeding a limit is a validation error with code `DATASET_LIMIT_EXCEEDED`.

### 4.3 Validation (see DATA_MODELS for field definitions)

| ID | Requirement |
|---|---|
| TRD-040 | Validation runs before any target is executed. A dataset that fails validation never starts a run. |
| TRD-041 | Case `id` must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. |
| TRD-042 | Case IDs are unique within a dataset (case-sensitive). |
| TRD-043 | Unknown top-level keys in a case are a validation error (strict mode, proposed; avoids silently ignored typos such as `expcted`). |
| TRD-044 | `expected`, when present, may be any JSON value, including `null`. Absence and `null` are distinct. |
| TRD-045 | `metadata` must be a JSON object; its values are unconstrained JSON. |
| TRD-046 | `tags` must be a list of unique strings. |
| TRD-047 | Validation collects all errors up to a cap (proposed: 100) before reporting, so users can fix several issues at once. |
| TRD-048 | Validation errors are returned as structured objects (DATA_MODELS §10) and rendered for humans by the CLI. |

### 4.4 Dataset identity

| ID | Requirement |
|---|---|
| TRD-050 | `dataset.sha256` is the SHA-256 of the raw file bytes (after BOM removal is **not** applied; raw bytes are hashed). |
| TRD-051 | A canonical hash (`dataset.canonical_sha256`) is also computed over the canonical JSON serialization of the parsed cases in file order. It ignores whitespace and key order differences. |
| TRD-052 | Comparison uses the canonical hash by default; a raw-byte change with the same canonical hash is reported as a warning (formatting-only change). |

Canonical JSON (proposed): UTF-8, object keys sorted, separators `,` and `:` with no
whitespace, strings in Unicode NFC form, numbers serialized as Python `json` does for
finite values. Full RFC 8785 conformance is not claimed.

## 5. Evaluation case and target interfaces

### 5.1 Case

Defined in DATA_MODELS §2. Summary: `id`, `input` (any JSON value; object recommended),
optional `expected`, optional `metadata`, optional `tags`.

### 5.2 Target interface (Python)

| ID | Requirement |
|---|---|
| TRD-060 | A target is any object with a `name: str` attribute and a `__call__(input: JSONValue) -> JSONValue` method, or a plain callable. The runner wraps plain callables in an adapter that uses the function's qualified name as `name`. |
| TRD-061 | Targets are resolved either from a Python object passed to the API, or from a `module:attribute` string in configuration. Resolution imports the module, which executes module-level code; this is documented as trusted-code loading (THR-004). Targets and custom evaluators are trusted code (SECURITY §10.1). |
| TRD-062 | The target's return value must be JSON-serializable under canonical rules. Otherwise the case is ERROR with code `TARGET_OUTPUT_INVALID`. |
| TRD-063 | The runner measures duration with `time.perf_counter()` around the call. |
| TRD-064 | Targets receive a deep copy of the case input so that a target mutating its argument cannot change the stored case. |

### 5.3 Timeouts (best-effort) and isolation

| ID | Requirement |
|---|---|
| TRD-070 | Each target call has a timeout (default 30 seconds, proposed). Timeouts are configurable per run and per target. |
| TRD-071 | MVP mechanism: the call runs in a worker thread. On timeout the runner records ERROR `TARGET_TIMEOUT` and proceeds. Python cannot forcibly stop a thread, so the thread may continue running. |
| TRD-072 | Timeouts are **best-effort**. Documentation, CLI help, and API docstrings state this. No document may claim that a timed-out target has been stopped or that arbitrary Python execution can be reliably terminated. |
| TRD-073 | A timeout alone does not provide execution isolation. Memory, filesystem, network, and CPU-bound loops are not contained, and side effects are not undone. |
| TRD-074 | **Process isolation is not part of the MVP.** The feasibility analysis is in ARCHITECTURE §11.1. Milestone 13 produces a written decision. Implementation requires a separate approved milestone (M17). |
| TRD-075 | A run with `counts.threads_possibly_running > 0` is reported with a warning in the terminal summary and in the manifest. |
| TRD-076 | Targets and custom evaluators are trusted code (SECURITY §10.1). Timeouts do not change that trust model. |

### 5.4 Evaluator interface (Python)

| ID | Requirement |
|---|---|
| TRD-080 | An evaluator is an object with: `name: str`, `version: str`, `requires_expected: bool`, and `evaluate(case: Case, output: JSONValue, duration_ms: float) -> EvaluatorResult`. |
| TRD-081 | `evaluate` should be pure with respect to the case and output. Evaluators must not mutate the case or output. The runner passes copies. |
| TRD-082 | Returned `EvaluatorResult` contains `status` (PASS, FAIL, ERROR, SKIPPED, INCONCLUSIVE), optional `score` in `[0, 1]`, `message` (≤ 500 characters), `reason_code` (from the registry in DATA_MODELS §9), and optional `details` (JSON object). |
| TRD-083 | If `requires_expected` is true and the case has no `expected`, the runner records SKIPPED with reason `NO_EXPECTED` without calling `evaluate`. |
| TRD-084 | Evaluator exceptions and invalid return values are recorded as ERROR with `EVALUATOR_EXCEPTION` or `EVALUATOR_RESULT_INVALID`. The run continues. |
| TRD-085 | Evaluator definitions are fingerprinted: built-in evaluators by their type plus parameters; custom evaluators by module, qualified name, declared `version`, and the SHA-256 of the defining source file. |

### 5.5 Built-in evaluators (MVP)

| Type | Parameters | Behaviour summary | Limitations (must be documented) |
|---|---|---|---|
| `exact_match` | none | PASS if canonical JSON of output equals canonical JSON of `expected`. | Sensitive to formatting; a correct answer phrased differently will FAIL. |
| `normalized_text` | `nfc` (default true), `casefold` (default true), `collapse_whitespace` (default true), `strip` (default true) | Compares normalized strings. Non-string output is a FAIL with reason `OUTPUT_NOT_TEXT`. | Does not understand meaning; paraphrases FAIL; some languages need locale-aware folding not provided. |
| `json_structure` | `top_level_type` (optional: object, array, string, number, boolean, null) | PASS if output is JSON text that parses and (if set) matches the top-level type. | Checks syntax and shape only, not field semantics. |
| `required_fields` | `paths` (list of dotted paths) | PASS if the output parses as JSON and every path resolves to a non-null value. | Presence is not correctness. Dotted paths do not support array indexing in the MVP. |
| `rule_based` | `contains` (list), `not_contains` (list), `regex` (list), `min_length`, `max_length` | Each configured rule is checked; PASS only if all pass. Reports the first failing rule name. | Substring and regex checks are brittle to wording; regex can be expensive (see §9.4). |
| `latency` | `max_ms` | PASS if `duration_ms ≤ max_ms`, else FAIL. | Depends on the environment; not comparable across different machines. |
| `custom` | `callable` (module:attribute) | Calls the user's evaluator. | Trusted code. Results are only as reliable as the user's code. |

Text similarity, ROUGE, BLEU, embeddings, and LLM judges are **not** in the MVP
(PRD-NG-001, PRD-NG-009). They are not represented in any output field.

### 5.6 Regex safety

| ID | Requirement |
|---|---|
| TRD-090 | Regex patterns from configuration are compiled with `re`. Pattern length is limited to 512 characters. |
| TRD-091 | Regex is applied to output strings of at most the configured maximum length (default 1 MiB). |
| TRD-092 | The documentation states that Python's `re` module has no timeout and that catastrophic backtracking is a risk; a pattern-review checklist is provided (SECURITY). |

## 6. Execution engine

| ID | Requirement |
|---|---|
| TRD-100 | MVP executes cases **sequentially** in dataset order. Parallel execution is post-MVP (PRD-F-104). |
| TRD-101 | For each case: copy input → call target under timeout → validate output → run each evaluator → aggregate case status → append case record. |
| TRD-102 | A case record is written to `cases.jsonl` as soon as it is complete, with a flush after each line. |
| TRD-103 | On `KeyboardInterrupt`, the run finishes the current case if it completes within a grace period (proposed: 5 seconds), records remaining cases as not executed, and sets run status to `ABORTED`. |
| TRD-104 | Unhandled exceptions in the engine (not in target or evaluator code) set run status to `FAILED` with code `ENGINE_ERROR` and exit code 4. |
| TRD-105 | Random seeds: EvalForge does not set global random state. If a target accepts a seed in its configuration, the seed is recorded in the manifest as an opaque value. |
| TRD-106 | Environment capture is limited to the EvalForge version, Python version (major.minor.micro), OS family, and machine architecture (DATA_HANDLING §6). The full platform string, hostnames, usernames, paths, environment variables, and installed package versions are not captured in the MVP. |

## 7. Result schema and run persistence

Field-level definitions are in DATA_MODELS. This section defines storage behaviour.

### 7.1 Layout (JSON/JSONL, approved OD-05; SQLite deferred)

```
<run_root>/                       default: .evalforge/runs  (OD-11)
  <run_id>/
    manifest.json                 run metadata, dataset and evaluator fingerprints, status
    cases.jsonl                   one CaseResult per line, in dataset order
    summary.json                  aggregate counts, rates, latency statistics, findings from the run itself
```

| ID | Requirement |
|---|---|
| TRD-110 | `run_id` is a UUIDv4 generated with the standard library `uuid` module. |
| TRD-111 | The run directory is created with a new unique name; an existing directory is never reused or overwritten. |
| TRD-112 | `manifest.json` is written at run start with status `RUNNING` and rewritten atomically (write to temporary file in the same directory, then `os.replace`) at the end with status `COMPLETED`, `ABORTED`, or `FAILED`. |
| TRD-113 | `summary.json` is written atomically after `cases.jsonl` is complete. |
| TRD-114 | `manifest.json` contains the SHA-256 of `cases.jsonl` and of `summary.json`, computed at finalization. These detect accidental corruption and unsophisticated edits. They do not provide tamper evidence: the manifest itself is not hashed, and a party who can rewrite the files can rewrite the hashes (THR-013; ARTIFACT_INTEGRITY §3–§5). |
| TRD-119 | The documented integrity scope (what is and is not covered) matches ARTIFACT_INTEGRITY §3.1. A test checks this. |
| TRD-118 | Stored case content is controlled by `io_mode` (`full`, `hashes`, `none`) and redaction. Defaults and behaviour are in DATA_HANDLING §3 and §7. |
| TRD-115 | Readers verify `schema_version`; unknown major versions are rejected (PRD-NF-009). |
| TRD-116 | Run artifacts never contain environment variable values, tracebacks, local variable values, absolute paths, or identifying environment metadata. Credential-like configuration values are removed (DATA_HANDLING §4–§6; SECURITY §4). |
| TRD-117 | Persisting is mandatory for `evalforge run` in MVP; the Python API may run in memory with persistence disabled (flag recorded in the manifest as `persisted: false`, and such runs cannot be compared from disk). |

### 7.2 Concurrency and locking

| ID | Requirement |
|---|---|
| TRD-120 | Two processes writing different runs to the same run root are safe because run directories are unique. |
| TRD-121 | Concurrent writers to the same run directory are not supported and are detected by the presence of a lock file created exclusively (`O_EXCL`); the second writer fails with `STORAGE_ERROR`. |
| TRD-122 | Stale lock files from crashed runs are not removed automatically. `inspect` reports them; users remove them manually. |

## 8. Run comparison

### 8.1 Preconditions

| ID | Requirement |
|---|---|
| TRD-130 | Both runs must have manifest status `COMPLETED`. `ABORTED`, `FAILED`, or `RUNNING` runs are refused with exit code 5 and code `RUN_INCOMPLETE`. |
| TRD-131 | Both runs must have the same major `schema_version`. |
| TRD-132 | Dataset canonical hashes must match, unless `--allow-dataset-change` is given. If allowed, the comparison reports `DATASET_CHANGED` as a warning and compares only cases whose canonical case hash matches; other shared IDs are categorized as `changed_input`. |
| TRD-133 | Evaluator fingerprints must match (same set of evaluator names and definitions), unless `--allow-evaluator-change` is given. If allowed, `EVALUATOR_CHANGED` is a warning and case-level comparison is still performed, with the affected evaluators marked in the output. |
| TRD-134 | Target identifier differences are expected in regression testing and produce no warning by default; the comparison shows both target names. |
| TRD-135 | Comparisons are never performed silently across incompatible runs. A refusal names every incompatibility found, not just the first. |
| TRD-136 | Overrides (`--allow-dataset-change`, `--allow-evaluator-change`) exist only as CLI options or explicit API arguments. They cannot be set in configuration, environment, or artifacts. |
| TRD-137 | An overridden comparison records each override in `compatibility.overrides`, shows a banner before any findings in text output, and produces a `COMPARISON_OVERRIDDEN` warning finding (ARTIFACT_INTEGRITY §6.2). |
| TRD-138 | `--strict` (API: `strict=True`) turns any override into a refusal (exit 5). |

### 8.2 Case categories

Defined precisely in EVALUATION_METHODOLOGY §5. Summary of categories produced by the
comparison engine:

`regressed`, `recovered`, `unchanged`, `changed`, `missing_in_candidate`,
`new_in_candidate`, `changed_input` (only with `--allow-dataset-change`).

### 8.3 Metrics compared

| Metric | Source | Notes |
|---|---|---|
| Counts by status | summary | Five statuses |
| `pass_rate` | summary | PASS ÷ executed; `null` if executed = 0 |
| `pass_rate` 95% interval | summary | Wilson score interval; see EVALUATION_METHODOLOGY §7 |
| `error_rate`, `inconclusive_rate` | summary | Same denominator |
| `latency_p50_ms`, `latency_p95_ms` | summary | Nearest-rank percentile over executed cases; `null` if none |

## 9. Regression detection

### 9.1 Configuration

Thresholds are read from the `[regression]` table of the configuration file
(CLI_SPECIFICATION §2.3). Defaults are proposed and subject to OD-08.

```toml
[regression]
max_newly_failing = 0
max_newly_errored = 0
inconclusive_as_regression = false
max_pass_rate_drop = 0.0
min_executed_for_rate_check = 30
max_p95_latency_ratio = 1.5     # optional; omit to disable
missing_case_policy = "fail"    # "fail" | "warn" | "ignore"
```

| ID | Requirement |
|---|---|
| TRD-140 | Threshold keys are validated; unknown keys are configuration errors. |
| TRD-141 | `max_pass_rate_drop` is an absolute difference in the range [0, 1] (e.g., 0.05 = five percentage points). |
| TRD-142 | Rate-based checks are skipped and reported as `RATE_CHECK_SKIPPED` when either run's executed count is below `min_executed_for_rate_check`. Case-level checks still apply. |
| TRD-143 | `max_p95_latency_ratio` compares candidate p95 to baseline p95; if baseline p95 is 0 or null, the check is skipped with reason. |

### 9.2 Findings

Each finding (DATA_MODELS §10) has a stable `code`, `severity` (`error` for
threshold violations, `warning` for informational issues), `message`, and references.

Finding codes (MVP):

| Code | Triggered when | Severity |
|---|---|---|
| `CASE_REGRESSED_TO_FAIL` | PASS → FAIL, count > `max_newly_failing` | error |
| `CASE_REGRESSED_TO_ERROR` | PASS → ERROR, count > `max_newly_errored` | error |
| `CASE_REGRESSED_TO_INCONCLUSIVE` | PASS → INCONCLUSIVE and `inconclusive_as_regression` | error |
| `CASE_REGRESSED_TO_INCONCLUSIVE` (warning form) | PASS → INCONCLUSIVE and not `inconclusive_as_regression` | warning |
| `PASS_RATE_DROP` | Drop > `max_pass_rate_drop` | error |
| `LATENCY_P95_INCREASE` | Ratio > `max_p95_latency_ratio` | error |
| `CASE_MISSING_IN_CANDIDATE` | Baseline case absent from candidate, policy `fail` | error (or warning / none per policy) |
| `CASE_NEW_IN_CANDIDATE` | Candidate-only case | warning |
| `CASE_RECOVERED` | FAIL/ERROR/INCONCLUSIVE → PASS | info |
| `DATASET_CHANGED` | Allowed by flag | warning |
| `EVALUATOR_CHANGED` | Allowed by flag | warning |
| `RATE_CHECK_SKIPPED` | Insufficient executed count | warning |
| `RAW_BYTES_CHANGED` | Dataset raw hash differs but canonical hash matches | info |
| `IO_UNAVAILABLE` | One or both runs stored `io_mode = none`; output-level comparison unavailable | warning |
| `COMPARISON_OVERRIDDEN` | An override flag was used (TRD-137) | warning |

Infrastructure-caused ERRORs (`TARGET_TIMEOUT`, `TARGET_EXCEPTION`, `EVALUATOR_EXCEPTION`,
`EVALUATOR_RESULT_INVALID`, `TARGET_OUTPUT_INVALID`) are reported under the
`*_TO_ERROR` findings with their reason codes in `details`. They are **never** reported
as `CASE_REGRESSED_TO_FAIL`. Any run-level infrastructure fault (`STORAGE_ERROR`,
`ENGINE_ERROR`) is not a regression finding; it is an exit code 4 condition.

### 9.3 Exit behaviour

Defined in CLI_SPECIFICATION §4. Regression findings with severity `error` produce exit
code 1.

### 9.4 Detection limits

| ID | Requirement |
|---|---|
| TRD-150 | Reports state that detection is limited to the configured cases and evaluators. |
| TRD-151 | For non-deterministic targets, a changed pass rate may be variance. The report notes the sample size and interval, and the documentation explains how to set thresholds. |

## 10. Command-line interface

Full specification in [CLI_SPECIFICATION](CLI_SPECIFICATION.md). Technical rules:

| ID | Requirement |
|---|---|
| TRD-160 | Every command supports `--help`, `--format text\|json` where output is produced, and `--no-color`. |
| TRD-161 | Exit codes are stable across minor versions and documented. |
| TRD-162 | The CLI never prints case inputs or outputs to stderr unless the user requests inspection. |
| TRD-163 | Text output sanitizes control characters (see SECURITY §6). |
| TRD-164 | `--format json` output is valid JSON on stdout; diagnostics go to stderr. |
| TRD-165 | The CLI is implemented with `argparse` from the standard library (TRD §3.2). |

## 11. Python API

Full specification in [API_DESIGN](API_DESIGN.md). Technical rules:

| ID | Requirement |
|---|---|
| TRD-170 | Public names are exported from `evalforge/__init__.py` and listed in `__all__`. Anything not listed is private. |
| TRD-171 | Public functions and classes are type-annotated. `py.typed` marker is included. |
| TRD-172 | Public models are immutable after construction (frozen dataclasses; TRD §3.2). |
| TRD-173 | Errors derive from `evalforge.errors.EvalForgeError`. |
| TRD-174 | The API and CLI share the same implementation paths; a test asserts equal outputs for equal inputs. |

## 12. Configuration

Specified in CLI_SPECIFICATION §2.3 and DATA_MODELS §4.

| ID | Requirement |
|---|---|
| TRD-180 | Configuration is a TOML file (approved, OD-04). Default name `evalforge.toml`. |
| TRD-181 | Configuration has a `schema_version` key. |
| TRD-182 | Unknown keys are errors. |
| TRD-183 | No environment variable interpolation in the MVP. Values come only from the file or the API. This avoids accidental secret capture (THR-011). |
| TRD-184 | Relative paths in configuration are resolved relative to the configuration file's directory. |
| TRD-185 | A configuration snapshot is stored in the manifest with values removed for secret-like keys, and paths relative to the configuration directory (DATA_HANDLING §5; SECURITY §4.3). |
| TRD-186 | Configuration keys `[run] io_mode` (`full`, `hashes`, `none`) and `[run] redaction` (boolean, default `true`) control stored content. Override flags are not configuration keys (TRD-136). |

## 13. Logging

| ID | Requirement |
|---|---|
| TRD-190 | Uses the standard library `logging` with a `evalforge` logger hierarchy. The library adds a NullHandler; the CLI configures handlers. |
| TRD-191 | Levels: `WARNING` for recoverable issues; `INFO` for run lifecycle (start, finish, counts); `DEBUG` for per-case IDs and timings. |
| TRD-192 | No logging of case inputs, outputs, expected values, or evaluator `details` at any level in MVP. Those appear only in the user's requested output (for example `inspect`). |
| TRD-193 | Exception tracebacks are logged at DEBUG, not INFO. User-facing errors are short. |
| TRD-194 | Text written to logs passes through the redaction rules in DATA_HANDLING §7 when redaction is enabled. Traceback text is logged only at DEBUG. |

## 14. Error handling

| ID | Requirement |
|---|---|
| TRD-200 | Errors are classified into: usage/config (exit 2), dataset (exit 3), engine/storage/infrastructure (exit 4), incompatible comparison (exit 5), and regression (exit 1). |
| TRD-201 | Each error has a stable `code` string from the registry in DATA_MODELS §9 and a human message. |
| TRD-202 | Errors never include secret values; messages that reference config values show key names only. |
| TRD-203 | Partial output is never presented as complete. A run that did not finish is marked `ABORTED` or `FAILED`. |

## 15. Security requirements

Summarized here; full analysis in [THREAT_MODEL](THREAT_MODEL.md) and [SECURITY](SECURITY.md).

| ID | Requirement |
|---|---|
| TRD-210 | Dataset content is parsed as data only (TRD-034; PRD-NF-003). |
| TRD-211 | Dataset file size, line length, case count, nesting depth, and string length are limited (§4.2). |
| TRD-212 | Output files are written only to the configured run root or the path given to `report export`. The CLI does not write elsewhere. |
| TRD-213 | Case IDs are never used to build file paths. |
| TRD-214 | Symbolic links: dataset and configuration files are opened with normal semantics; the CLI warns when an input path is a symlink (THR-005). |
| TRD-215 | No network access in core (PRD-NF-001). Verified by test. |
| TRD-216 | No `eval`, `exec`, `pickle`, `yaml.load` (unsafe), `subprocess` with shell=True, or dynamic code generation in the codebase. Enforced by a lint rule or grep check in CI (proposed). |
| TRD-217 | Custom evaluators and targets are loaded only from configuration or explicit API calls, never from dataset content. |
| TRD-218 | Stored strings, evaluator messages and details, and exception messages are redacted by the rules in DATA_HANDLING §7 when redaction is enabled. TRD-218 makes no claim that redaction removes all sensitive information (DATA_HANDLING §7.4). |
| TRD-219 | Built-in evaluators place no case content in `message` or `details` (DATA_HANDLING §3.3). |

## 16. Performance requirements (proposed; to be measured)

| ID | Requirement | Status |
|---|---|---|
| TRD-220 | Validate 10,000 JSONL cases in under 10 seconds on the CI reference runner. | Proposed target; not measured |
| TRD-221 | Built-in evaluators add under 1 ms per case on the reference runner for outputs of 10 KiB, excluding regex with unbounded patterns. | Proposed target; not measured |
| TRD-222 | Persisting a case record adds under 5 ms on average on the reference runner. | Proposed target; not measured |
| TRD-223 | Memory: validation of a 50 MiB JSONL file streams and does not hold the whole file as one string. Peak memory budget to be measured. | Requirement; budget open |

Measurements are taken in milestone 2 (validation) and milestone 8 (persistence)
using a benchmark script that is part of the repository. No performance claim is made
in any user-facing document until a measurement exists and is recorded with its
environment.

## 17. Testing requirements

Full strategy in [TEST_STRATEGY](TEST_STRATEGY.md).

| ID | Requirement |
|---|---|
| TRD-230 | Unit tests for every built-in evaluator, including edge cases listed in TEST_STRATEGY. |
| TRD-231 | Integration tests for dataset → run → persist → compare → report. |
| TRD-232 | CLI tests run the installed entry point in a subprocess and assert exit codes and output. |
| TRD-233 | Python API tests assert parity with CLI results. |
| TRD-234 | Security tests include malicious and malformed inputs. |
| TRD-235 | Expected values in tests are written independently (literal, hand-verified). Tests must not compute expected results with the production code under test. |
| TRD-236 | Coverage is measured and reported; no coverage threshold is claimed in advance. Any threshold is an approved decision. |
| TRD-237 | Tests run on all supported OS and Python versions in CI. |

## 18. Compatibility

| ID | Requirement |
|---|---|
| TRD-240 | Semantic versioning for the package (proposed). Pre-1.0 releases may change minor-version behaviour, documented in CHANGELOG. |
| TRD-241 | Artifact `schema_version` uses `MAJOR.MINOR`. Readers accept the same major and any minor; a higher minor than supported produces a warning and reads known fields. |
| TRD-242 | Public API and CLI exit codes are considered stable from 1.0. Before 1.0, changes are announced in CHANGELOG. |
| TRD-243 | Deprecated fields remain readable for at least one minor version (proposed). |

## 19. Traceability

Requirement-level traceability is maintained in TEST_STRATEGY §10 and
IMPLEMENTATION_PLAN §3.
