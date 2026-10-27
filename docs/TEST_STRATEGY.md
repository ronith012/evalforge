# EvalForge — Test Strategy

Status: **Proposed — awaiting approval.** No tests exist yet. No coverage figure or test
result is claimed in this document.

Implements: TRD §17. Requirements: [PRD](PRD.md), [TRD](TRD.md).

---

## 1. Goals

1. Prove each MVP requirement with at least one automated test or a documented manual
   verification (PRD §14 acceptance coverage).
2. Catch regressions in the evaluation semantics, which are the product's core promise.
3. Verify that security controls work, using hostile inputs.
4. Verify that documentation examples are accurate.
5. Verify behaviour on Linux, macOS, and Windows.

Non-goals for testing: measuring the quality of any real AI system; benchmarking
against other tools.

## 2. Test levels and tools (proposed)

| Level | Scope | Tool | Location |
|---|---|---|---|
| Unit | Single function or class with no filesystem except `tmp_path` | pytest | `tests/unit/` |
| Property-style | Generated inputs checking invariants (for example canonicalization idempotence) | pytest with hand-written generators (no extra dependency) | `tests/unit/` |
| Integration | Multiple modules together without the CLI | pytest | `tests/integration/` |
| CLI | Installed `evalforge` entry point run as a subprocess | pytest + subprocess | `tests/cli/` |
| API | Python API directly | pytest | `tests/api/` |
| Security | Hostile and malformed inputs; static checks | pytest; grep-based static check in CI | `tests/security/` |
| End-to-end | Quick start and CI example from a clean environment | pytest + shell in CI | `tests/e2e/` |
| Documentation | Code blocks marked runnable; banned-claims scan | pytest | `tests/docs/` |
| Performance | Benchmarks with recorded environment | pytest-benchmark or script (proposed) | `benchmarks/` (not run in default CI) |

Test dependencies: `pytest`, `pytest-timeout` (proposed, TRD §3.2). No mocking framework
beyond `unittest.mock` from the standard library (proposed).

## 3. Test data principles

| Principle | Rule |
|---|---|
| Synthetic only | All datasets are authored for tests. No real user data. |
| Independent expectations | Expected results are literals written by hand. A test must never compute its expected value with the production function under test (TRD-235). |
| Hand-verified values | For statistics (Wilson interval, percentiles), expected values are computed by hand or by a separate script reviewed by a person, and recorded with the calculation. |
| Named fixtures | Each fixture file has a README line stating its purpose and what it is designed to trigger. |
| Hostile corpus | A dedicated directory holds malicious and malformed inputs, labelled by threat ID. |
| Determinism | Tests do not depend on wall-clock time, network, or random values unless the random source is seeded and the seed is in the test. |

## 4. Test catalogue

Test IDs use the form `TST-<area>-<nnn>`. Each entry lists the requirements it verifies.

### 4.1 Dataset loading and validation

| ID | Test | Verifies |
|---|---|---|
| TST-DS-001 | JSON array and JSONL with the same three cases load to equal case lists and equal canonical hashes | PRD-F-001, TRD-051 |
| TST-DS-002 | BOM-prefixed UTF-8 is accepted; UTF-16 is rejected with `DATASET_ENCODING_INVALID` | TRD-030 |
| TST-DS-003 | Unsupported extension (`.csv`) rejected with `DATASET_FORMAT_UNSUPPORTED`, exit 3 | TRD-033 |
| TST-DS-004 | Missing `id`, missing `input`, `id` with spaces, `id` > 128 characters each produce field-specific errors | PRD-F-002, TRD-041 |
| TST-DS-005 | Unknown key `expcted` rejected with field path | TRD-043 |
| TST-DS-006 | Duplicate `id` reports both line numbers | PRD-F-003, TRD-042 |
| TST-DS-007 | Duplicate IDs differing only in case (`A1` and `a1`) are accepted (case-sensitive) | TRD-042 |
| TST-DS-008 | `expected` absent vs `"expected": null` produce distinct case representations | DATA_MODELS §1, TRD-044 |
| TST-DS-009 | `metadata` that is not an object is rejected | TRD-045 |
| TST-DS-010 | Tags with duplicates or more than 32 items rejected | TRD-046 |
| TST-DS-011 | Blank lines in JSONL are ignored and counted | TRD-031 |
| TST-DS-012 | Empty file (zero bytes) yields a valid dataset with zero cases, and the run path reports "no cases selected" rather than success | PRD-F-001; §5 edge cases |
| TST-DS-013 | File with only whitespace or only `[]` handled as documented (zero cases) | §5 edge cases |
| TST-DS-014 | Errors are collected to cap of 100 and reported in file order | TRD-047 |
| TST-DS-015 | Line limit, file limit, case-count limit, string limit, depth limit each trigger `DATASET_LIMIT_EXCEEDED` at boundary + 1 and pass at boundary | TRD-211, TRD §4.2 |
| TST-DS-016 | Raw-byte hash changes when whitespace changes; canonical hash does not | TRD-050, TRD-051, TRD-052 |
| TST-DS-017 | `NaN`, `Infinity`, `-Infinity` rejected | TRD-034 |
| TST-DS-018 | Unicode (combining marks, emoji, RTL text, zero-width characters) preserved in input and hashed consistently in NFC | Unicode edge case; TRD-051 |
| TST-DS-019 | Validation performs no target execution (spy target records zero calls) | TRD-040 |

### 4.2 Malformed input (dataset and artifacts)

| ID | Test | Verifies |
|---|---|---|
| TST-MF-001 | Invalid UTF-8 byte sequence reports line and byte offset, no crash | THR-002 |
| TST-MF-002 | Truncated JSON line reports line number | PRD-F-002 |
| TST-MF-003 | Deeply nested JSON (depth 65) rejected without `RecursionError` | THR-002, TRD §4.2 |
| TST-MF-004 | Mixed line endings (CRLF and LF) parse identically | TRD-004 |
| TST-MF-005 | Artifact with unknown major schema version rejected with `SCHEMA_VERSION_UNSUPPORTED` | PRD-NF-009 |
| TST-MF-006 | Artifact with unknown minor version reads known fields and warns | TRD-241 |
| TST-MF-007 | Manifest JSON truncated mid-write detected as incomplete run | PRD-F-017 |
| TST-MF-008 | Result line with non-finite number rejected on read | TRD-034 |

### 4.3 Target execution

| ID | Test | Verifies |
|---|---|---|
| TST-TG-001 | Callable invoked once per selected case in dataset order (recording spy) | PRD-F-005 |
| TST-TG-002 | Output and duration recorded; duration non-negative | PRD-F-006 |
| TST-TG-003 | Exception on case 2 of 5 → case 2 ERROR `TARGET_EXCEPTION`; cases 3–5 still executed | PRD-F-007 |
| TST-TG-004 | Target sleeping beyond timeout → ERROR `TARGET_TIMEOUT`; duration equals timeout; run continues | PRD-F-007, TRD-070 |
| TST-TG-005 | Target returning a set, a bytes object, or NaN → ERROR `TARGET_OUTPUT_INVALID` | TRD-062 |
| TST-TG-006 | Target mutating its input does not change the stored case | TRD-064 |
| TST-TG-007 | Target returning `None` is recorded as JSON null output, not an error | §5 edge cases |
| TST-TG-008 | Empty string output is recorded as empty string, not an error | §5 edge cases |
| TST-TG-009 | Timed-out thread increments `threads_possibly_running` | THR-010, SR-11 |
| TST-TG-010 | `module:attribute` reference resolves to a fixture module; unknown module → `TARGET_LOAD_FAILED`, exit 2 | TRD-061 |
| TST-TG-011 | Class-based target with `name` attribute uses that name in manifest | TRD-060 |
| TST-TG-012 | `KeyboardInterrupt` during a case → run finalized as `ABORTED`; remaining cases not written | TRD-103 |
| TST-TG-013 | Target raising `BaseException` subclass other than `Exception` (for example `SystemExit`) is handled as ERROR, not as process exit (proposed behaviour; confirm during implementation) | Failure isolation; OD-06 |
| TST-TG-014 | Docs, CLI help, and API docstrings state that timeouts are best-effort; a banned-phrase scan finds no claim that a timed-out target was stopped or reliably terminated | TRD-072, PRD-NF-016 |

### 4.4 Deterministic evaluators

For each evaluator: pass, fail, edge cases, and invalid configuration.

| ID | Test | Verifies |
|---|---|---|
| TST-EV-001 | `exact_match`: `{"a": 1, "b": 2}` equals `{"b": 2, "a": 1}` after canonicalization → PASS | PRD-F-008 |
| TST-EV-002 | `exact_match`: `"Hello"` vs `"hello"` → FAIL `VALUE_MISMATCH` | PRD-F-008 |
| TST-EV-003 | `exact_match`: case with no `expected` → SKIPPED `NO_EXPECTED` without calling evaluate (spy) | TRD-083 |
| TST-EV-004 | `normalized_text`: `"Hello  World\n"` vs `"hello world"` → PASS with defaults; FAIL with all options off | PRD-F-009 |
| TST-EV-005 | `normalized_text`: NFC vs NFD `"é"` → PASS with `nfc=true`, FAIL with `nfc=false` | PRD-F-009 |
| TST-EV-006 | `normalized_text`: Turkish dotted `İ` casefold behaviour documented and asserted (limitation test) | EVALUATION_METHODOLOGY §4 |
| TST-EV-007 | `normalized_text`: non-string output → FAIL `OUTPUT_NOT_TEXT` | PRD-F-009 |
| TST-EV-008 | `json_structure`: `"{not json"` → FAIL `NOT_JSON`; `"{\"a\": 1}"` → PASS | PRD-F-010 |
| TST-EV-009 | `json_structure` with `top_level_type = array` on object output → FAIL `JSON_TYPE_MISMATCH` | PRD-F-010 |
| TST-EV-010 | Output wrapped in code fences → FAIL `NOT_JSON` (documented false negative) | EVALUATION_METHODOLOGY §9 |
| TST-EV-011 | `required_fields` with `paths = ["a.b"]`: `{"a": {"b": null}}` → FAIL `REQUIRED_FIELD_MISSING`; `{"a": {"b": 0}}` → PASS | PRD-F-011 |
| TST-EV-012 | `required_fields` on non-JSON output → FAIL `NOT_JSON` | PRD-F-011 |
| TST-EV-013 | `rule_based` `contains` missing → FAIL `RULE_CONTAINS_MISSING` naming the rule | PRD-F-012 |
| TST-EV-014 | `rule_based` `not_contains` present → FAIL `RULE_NOT_CONTAINS_PRESENT` | PRD-F-012 |
| TST-EV-015 | `rule_based` regex non-match → FAIL `RULE_REGEX_NO_MATCH` | PRD-F-012 |
| TST-EV-016 | `rule_based` length bounds: exactly min and max PASS; min−1 and max+1 FAIL | PRD-F-012 |
| TST-EV-017 | `rule_based` with multiple failing rules reports the first in configuration order | TRD §5.5 |
| TST-EV-018 | `latency`: duration equal to `max_ms` → PASS; `max_ms + 0.001` → FAIL `LATENCY_EXCEEDED` | PRD-F-013 |
| TST-EV-019 | Invalid evaluator configuration (`latency` without `max_ms`) → `CONFIG_INVALID` | TRD §5.5 |
| TST-EV-020 | Regex pattern of 513 characters rejected at configuration time | TRD-090 |
| TST-EV-021 | Output of 2 MiB passed to regex evaluator → skipped with clear reason or ERROR per design; verified against TRD-091 | TRD-091 |
| TST-EV-022 | Custom evaluator returns valid FAIL → recorded with its reason code | PRD-F-014 |
| TST-EV-023 | Custom evaluator raises → ERROR `EVALUATOR_EXCEPTION`; other evaluators still run | PRD-F-014, TRD-084 |
| TST-EV-024 | Custom evaluator returns a dict instead of result object → ERROR `EVALUATOR_RESULT_INVALID` | TRD-084 |
| TST-EV-025 | Custom evaluator mutating the output does not change the stored output | TRD-081 |
| TST-EV-026 | Custom evaluator fingerprint changes when its source file changes | TRD-085 |
| TST-EV-027 | Custom evaluator with unsupported `interface_version` rejected | §10.3 in ARCHITECTURE |
| TST-EV-028 | Evaluator that returns score outside [0, 1] → ERROR `EVALUATOR_RESULT_INVALID` | DATA_MODELS §8 |
| TST-EV-029 | No evaluator returns INCONCLUSIVE for built-in types across the full fixture corpus | EVALUATION_METHODOLOGY §3.1 |

### 4.5 Status aggregation (table-driven)

Each row of EVALUATION_METHODOLOGY §3.3 has at least one test. Table:

| Scenario | Target | Evaluators | Expected case status | Expected reason |
|---|---|---|---|---|
| T1 | ERROR `TARGET_TIMEOUT` | exact → SKIPPED | ERROR | `TARGET_TIMEOUT` |
| T2 | OK | none configured | SKIPPED | `NO_EVALUATORS` |
| T3 | OK | exact ERROR, rule FAIL | ERROR | `EVALUATOR_EXCEPTION` (first error) |
| T4 | OK | custom INCONCLUSIVE, rule FAIL | INCONCLUSIVE | `CUSTOM_UNCERTAIN` |
| T5 | OK | exact FAIL, latency PASS | FAIL | `exact` |
| T6 | OK | all SKIPPED (`NO_EXPECTED`) | SKIPPED | `NO_EXPECTED` |
| T7 | OK | exact PASS, latency SKIPPED | PASS | — |
| T8 | OK | exact PASS, rule PASS | PASS | — |
| T9 | ERROR | ERROR-precedence check: target ERROR and an evaluator would FAIL | ERROR (not FAIL) | target code |
| T10 | OK | evaluator ERROR and evaluator FAIL on same case | ERROR (not FAIL) | evaluator error |

Test names: `test_status_aggregation[T1]` … `[T10]`.

### 4.6 Statistics

| ID | Test | Verifies |
|---|---|---|
| TST-ST-001 | Pass rate with n = 0 is null; no division error | PRD-F-020 |
| TST-ST-002 | Pass rate 3/5 = 0.6 | PRD-F-020 |
| TST-ST-003 | Wilson interval for 3/5 at 95% equals `[0.2307, 0.8824]` (to 4 dp) — see worked example below | EVALUATION_METHODOLOGY §7 |
| TST-ST-004 | Wilson interval for 0/10 lower bound is 0.0 (clipped) | §7.1 |
| TST-ST-005 | Wilson interval for 10/10 upper bound is 1.0 (clipped) | §7.1 |
| TST-ST-006 | Nearest-rank p95 over 20 values is the 19th sorted value | DATA_MODELS §10 |
| TST-ST-007 | Latency percentiles exclude cases without output | DATA_MODELS §10 |

Worked example for TST-ST-003 (values recorded from a script run on 2026-10-18 using
the formula in EVALUATION_METHODOLOGY §7.1, not from hand calculation):

- Input: k = 3, n = 5, z = 1.959963984540054
- Result: lower = 0.2307, upper = 0.8824

**These values must be independently re-derived (by a second person or a second,
separately written implementation) during milestone 2 before they are used as expected
values in tests.** Until then they are recorded inputs to that check, not verified results.

### 4.7 Comparison and regression

| ID | Test | Verifies |
|---|---|---|
| TST-CM-001 | Seeded transitions (PASS→FAIL, FAIL→PASS, PASS→PASS, FAIL→ERROR, ERROR→PASS, missing, new) categorized exactly | PRD-F-019 |
| TST-CM-002 | Identical run compared with itself: zero regressions, zero findings with severity error | PRD-NF-002 (false regression rate target) |
| TST-CM-003 | Changed dataset canonical hash → refusal exit 5 listing `DATASET_CHANGED` | PRD-F-021, TRD-132 |
| TST-CM-004 | Same with `--allow-dataset-change` → comparison proceeds, warning present, `changed_input` categories | TRD-132 |
| TST-CM-005 | Changed evaluator fingerprint → refusal, lists evaluator name | PRD-F-021, TRD-133 |
| TST-CM-006 | Changed dataset formatting only (raw hash changes, canonical same) → no refusal, warning `RAW_BYTES_CHANGED` (informational) | TRD-052 |
| TST-CM-007 | Candidate with status `ABORTED` → refusal `RUN_INCOMPLETE` | TRD-130 |
| TST-CM-008 | Refusal lists all incompatibilities, not only the first | TRD-135 |
| TST-CM-009 | Missing case in candidate with `missing_case_policy = fail` → error finding; `warn` → warning; `ignore` → none | TRD §9.2 |
| TST-CM-010 | Pass rate drop of exactly `max_pass_rate_drop` → no finding; drop above → finding | PRD-F-022 |
| TST-CM-011 | Newly failing count above `max_newly_failing` → `CASE_REGRESSED_TO_FAIL` with case IDs sorted | PRD-F-022 |
| TST-CM-012 | Infrastructure ERROR regression (PASS→ERROR) → `CASE_REGRESSED_TO_ERROR`, never `CASE_REGRESSED_TO_FAIL` | TRD §9.2, PRD-F-023 |
| TST-CM-013 | Rate check skipped when executed < `min_executed_for_rate_check`, with `RATE_CHECK_SKIPPED` | TRD-142 |
| TST-CM-014 | Latency p95 ratio above threshold → finding; baseline p95 null → skipped with reason | TRD-143 |
| TST-CM-015 | Golden-output tests for each finding message template (§9.2 codes) | PRD-F-022 |
| TST-CM-016 | Comparison output byte-identical for the same inputs (excluding `comparison_id`, `created_at`) | DATA_MODELS §11 |
| TST-CM-017 | Comparison of runs with 0 executed cases: rate-based checks report `RATE_CHECK_SKIPPED`, no crash | PRD-F-020 |
| TST-CM-018 | Comparison refuses run whose `cases_sha256` or `summary_sha256` mismatches (exit 4) | PRD-F-017, TRD-114 |

### 4.8 Security

| ID | Test | Verifies |
|---|---|---|
| TST-SEC-001 | Dataset with `"input": "__import__('os').system('echo x')"` as a string is never executed (spy on `os.system` and `subprocess`) | THR-001, SR-01 |
| TST-SEC-002 | Dataset containing YAML tags (`!!python/object`) and pickle-like bytes is loaded as plain strings | THR-001 |
| TST-SEC-003 | Static check: no `eval(`, `exec(`, `pickle`, `yaml.load(` (not `safe_load`), `shell=True` in `src/` | TRD-216 |
| TST-SEC-004 | Network disabled (socket creation patched to raise): quick-start completes | PRD-NF-001, THR-016 |
| TST-SEC-005 | Dependency import test: core imports succeed with no optional extras installed | ARCHITECTURE §10.4 |
| TST-SEC-006 | Case IDs containing `../` or absolute paths are not used as file paths; run directory name is UUID | THR-007, TRD-213 |
| TST-SEC-007 | Run reference `../../etc` is rejected with `RUN_NOT_FOUND` | THR-007 |
| TST-SEC-008 | Planted secrets in config (`api_key = "sk-TEST…"`) do not appear in manifest, logs, or error messages (search all output files) | THR-011, SR-05 |
| TST-SEC-009 | Exception message containing a planted secret: document current behaviour (not redacted per SECURITY §4.2) and assert the documented behaviour | RR-05 |
| TST-SEC-010 | Terminal output with ANSI clear-screen and bidi overrides is sanitized; JSON output unchanged | THR-009, SECURITY §6 |
| TST-SEC-011 | Regex with known catastrophic pattern: document behaviour; verify pattern-length limit and output-length limit apply | THR-003, RR-03 |
| TST-SEC-012 | Tampered `cases.jsonl` (one byte changed) → `INTEGRITY_MISMATCH` on inspect and compare | THR-013 |
| TST-SEC-013 | Default `report export` contains no `input` or `output` keys | THR-012, SR-06 |
| TST-SEC-014 | `inspect` list view contains no input/output without `--show-io` | SR-06 |
| TST-SEC-015 | Symlinked dataset emits a warning; reading does not follow to write | THR-005 |
| TST-SEC-016 | Output path `report export --out` pointing at an existing file is refused | CLI §3.6 |
| TST-SEC-017 | Two processes writing one run directory: second fails with `STORAGE_LOCKED` | TRD-121 |
| TST-SEC-018 | Fuzz-style corpus (fixed list of 200 generated malformed JSON lines, seeded) never raises an unhandled exception | THR-002 |

### 4.9 CLI and API parity

| ID | Test | Verifies |
|---|---|---|
| TST-CLI-001 | Every command accepts `--help` and exits 0 | TRD-160 |
| TST-CLI-002 | `--format json` output is valid JSON on stdout; stderr contains diagnostics only | TRD-164 |
| TST-CLI-003 | Exit codes for each row of CLI §4 (table-driven) | PRD-F-023 |
| TST-CLI-004 | `run` on invalid dataset exits 3 and creates no run directory | TRD-040 |
| TST-CLI-005 | `run --fail-on error` with one ERROR case → exit 1; without flag → exit 0 | CLI §3.3 |
| TST-CLI-006 | `run --case unknown-id` → exit 2 listing unknown IDs | CLI §3.3 |
| TST-CLI-007 | `inspect` with ambiguous prefix → exit 2 with matches | CLI §1.5 |
| TST-CLI-008 | `config validate` lists all errors (up to 100) with key paths | PRD-F-029 |
| TST-CLI-009 | `config validate` does not import target unless `--check-imports` (import spy) | THR-004 |
| TST-CLI-010 | `NO_COLOR` set → no ANSI codes in output | CLI §1.1 |
| TST-CLI-011 | Text table golden-output tests for run, inspect, compare, refused | PRD-F-024 |
| TST-CLI-012 | Interrupt (SIGINT) during run → exit 4, status ABORTED on disk (POSIX-only; Windows equivalent proposed) | TRD-103 |
| TST-API-001 | `Dataset.load` and CLI `dataset validate` produce identical error lists for the same file | PRD-F-027 |
| TST-API-002 | `suite.run` and `evalforge run` produce identical case results for the same config (parity) | PRD-F-027, TRD-174 |
| TST-API-003 | `compare` function and CLI `compare` produce identical findings | TRD-174 |
| TST-API-004 | Public names in `__all__` match CLI_SPECIFICATION and API_DESIGN §2 (lint test) | TRD-170 |
| TST-API-005 | `Run` objects are immutable (assignment raises) | TRD-172 |
| TST-API-006 | Custom target via `Target.from_callable` and via config reference produce the same manifest target entry except for `callable` | TRD-060 |

### 4.10 Documentation and claims

| ID | Test | Verifies |
|---|---|---|
| TST-DOC-001 | Every code block in API_DESIGN marked runnable is executed | PRD-NF-010 |
| TST-DOC-002 | Every CLI example in CLI_SPECIFICATION marked as runnable matches actual output (golden) | PRD-NF-010 |
| TST-DOC-003 | Banned-claims scan on user-facing strings and documents: phrases such as "guarantees safety", "proves correctness", "certified", "bias-free", "hallucination-free" are absent except inside quoted negations | PRD-NF-013, THR-019 |
| TST-DOC-004 | Every requirement ID in PRD and TRD is referenced by at least one test or verification item (traceability check, §10) | PRD-NF-010 |
| TST-DOC-005 | Every link in planning docs resolves to an existing file or anchor | Documentation integrity |
| TST-DOC-006 | Every reason code in DATA_MODELS §9 is produced by at least one test or is marked "reserved" | DATA_MODELS §9 |

### 4.11 Persistence and storage failures

| ID | Test | Verifies |
|---|---|---|
| TST-PS-101 | Atomic manifest replacement: simulated failure during `os.replace` leaves previous manifest intact | TRD-112 |
| TST-PS-102 | Run directory not writable → exit 4 `STORAGE_ERROR`, no partial run reported as complete | PRD-F-018 |
| TST-PS-103 | Disk full during `cases.jsonl` append (simulated write error) → run FAILED, exit 4 | TRD-104 |
| TST-PS-104 | Summary write failure after all cases written → run FAILED, cases preserved | TRD-113 |
| TST-PS-105 | Crash simulated mid-run (kill process after N cases) → manifest RUNNING; `inspect` reports incomplete; `compare` refuses | PRD-F-017 |
| TST-PS-106 | Lock file present from crash → new run to same directory impossible (new UUID dir is fine); `inspect` reports stale lock | TRD-122 |
| TST-PS-107 | Read-only `cases.jsonl` on comparison side does not block reading | Robustness |
| TST-PS-108 | Long path (> 260 characters) on Windows handled or reported clearly | TRD-002 (Windows) |
| TST-PS-109 | Two runs in one run root do not interfere (unique directories) | TRD-120 |

### 4.12 End-to-end and quick start

| ID | Test | Verifies |
|---|---|---|
| TST-E2E-001 | Quick start from clean virtual environment: install wheel, write example config, validate dataset, run, inspect, compare identical runs (no regressions) | PRD-G-001, PRD-F-030 |
| TST-E2E-002 | Seeded regression scenario: baseline and candidate targets differ by one fixture behaviour → expected findings exactly | Success metric "regression detection accuracy" |
| TST-E2E-003 | Example CI workflow commands executed in project CI against the synthetic example | PRD-F-030 |
| TST-E2E-004 | Installation from sdist and wheel in clean environments on all supported platforms | PRD-NF-004, TRD-015 |
| TST-E2E-005 | Package contents check: no test data, no real datasets, LICENSE and NOTICE present | PRD-NF-012 |

### 4.13 Cross-platform and environment

| ID | Test | Verifies |
|---|---|---|
| TST-XP-001 | Full unit and integration suite on Linux, macOS, Windows × supported Python versions | PRD-NF-004, TRD-237 |
| TST-XP-002 | Path handling tests use `pathlib` and both separators | TRD-004 |
| TST-XP-003 | Newline handling: outputs written with LF; reads accept CRLF | TRD-004 |
| TST-XP-004 | Case-insensitive file system behaviour on macOS and Windows does not cause run-ID collision (UUID-based) | TRD-110 |
| TST-CI-001 | DCO check fails on a commit without a `Signed-off-by` trailer and passes with one (run on a test branch before external contributions are accepted) | OD-31 |
| TST-CI-002 | Gate G-1 record exists for Hatchling and uv (version, licence, maintenance status, check date) before any dependency is installed (manual check) | TRD-025 |
| TST-CI-003 | Publication is refused while the G-2 record (package-index and trademark checks) is absent (release check, M16) | TRD-026, OD-10 |

### 4.14 Performance (benchmarks, not default CI)

| ID | Benchmark | Target status |
|---|---|---|
| BM-001 | Validate 10,000 JSONL cases | TRD-220 (proposed; to measure) |
| BM-002 | Evaluator overhead per case at 10 KiB outputs | TRD-221 (proposed; to measure) |
| BM-003 | Persistence overhead per case | TRD-222 (proposed; to measure) |
| BM-004 | Peak memory validating 50 MiB JSONL | TRD-223 (budget open) |
| BM-005 | Comparison of two runs of 10,000 cases: time and peak memory | ARCHITECTURE §12 (to measure) |

Each benchmark records: hardware, OS, Python version, EvalForge commit, and the command.
Results are not claims until recorded in a benchmark report.

### 4.15 Sensitive data, integrity, and overrides (added in final planning review)

| ID | Test | Verifies |
|---|---|---|
| TST-IO-001 | `io_mode = full` stores input, expected, and output (redacted per rule); input, expected, and output hashes present | DATA_HANDLING §3.1 |
| TST-IO-002 | `io_mode = hashes` stores hashes and no input, expected, or output content | DATA_HANDLING §3.1 |
| TST-IO-003 | `io_mode = none` stores no input, expected, output, or I/O hashes; comparison emits `IO_UNAVAILABLE` | DATA_HANDLING §3.1, ARTIFACT_INTEGRITY §6.3 |
| TST-IO-004 | Built-in evaluator messages and details contain no case content (planted markers searched across the fixture corpus) | DATA_HANDLING §3.3, TRD-219 |
| TST-IO-005 | Target exception: artifact contains exception type and truncated message only; no traceback text and no local variable values | DATA_HANDLING §4 |
| TST-IO-006 | Configuration snapshot: secret-key values removed and counted; paths inside the config directory relative; paths outside stored as `<external>/<basename>` | DATA_HANDLING §5 |
| TST-IO-007 | Manifest environment contains only the DATA_HANDLING §6 fields; no hostname, username, working directory, or environment variable names or values | DATA_HANDLING §6, TRD-106 |
| TST-IO-008 | `report export --include-io` on an `io_mode = hashes` run fails with `IO_NOT_STORED` (exit 2); on a `full` run it exports only stored, redacted values | DATA_HANDLING §8.2 |
| TST-IO-009 | No automatic deletion of run directories | DATA_HANDLING §9 |
| TST-RD-001 | Pattern redaction replaces each listed credential prefix in strings; replacement shows `[REDACTED:<category>]` | DATA_HANDLING §7.2 |
| TST-RD-002 | Key-based redaction removes values under secret-key names at any nesting depth | DATA_HANDLING §7.2 |
| TST-RD-003 | Redaction applies to exception messages, evaluator messages, and log lines | DATA_HANDLING §7.1 |
| TST-RD-004 | Documented miss: a credential in an unlisted format, and a base64-encoded credential, are not redacted (asserts the documented behaviour) | DATA_HANDLING §7.4 |
| TST-RD-005 | Documented false positive: a non-secret string matching a pattern is replaced and counted in `redactions` | DATA_HANDLING §7.4 |
| TST-RD-006 | `redaction = false` is recorded in the manifest and prints a warning in summary and comparison output | DATA_HANDLING §7.5 |
| TST-IN-001 | Manifest `cases_sha256` and `summary_sha256` match the files as written | ARTIFACT_INTEGRITY §4, TRD-114 |
| TST-IN-002 | One byte changed in `summary.json` or in `cases.jsonl` → `INTEGRITY_MISMATCH` on inspect and compare | ARTIFACT_INTEGRITY §5 |
| TST-IN-003 | Rewriting `cases.jsonl` and recomputing `cases_sha256` in the manifest is **not** detected (asserts the documented limitation) | ARTIFACT_INTEGRITY §5 |
| TST-IN-004 | Changing `dataset.canonical_sha256` in the manifest is **not** detected by inspect (asserts the documented limitation) | ARTIFACT_INTEGRITY §3.1 |
| TST-CM-019 | Changed dataset without flags → refusal, exit 5, every incompatibility listed | ARTIFACT_INTEGRITY §6.1 |
| TST-CM-020 | With `--allow-dataset-change`: banner text, `compatibility.overrides` entry, and `COMPARISON_OVERRIDDEN` warning present | ARTIFACT_INTEGRITY §6.2 |
| TST-CM-021 | `--strict` with an override → exit 5 and no findings | TRD-138 |
| TST-CM-022 | Override keys in configuration are rejected as unknown (`CONFIG_UNKNOWN_KEY`); no override can be set through configuration | TRD-136 |
| TST-DOC-007 | The integrity scope table (ARTIFACT_INTEGRITY §3.1) matches the fields the manifest writer hashes (text and field-list comparison) | TRD-119 |

## 5. Edge-case catalogue

Covers the cases requested in the planning brief.

| Category | Case | Tests |
|---|---|---|
| Empty datasets | Zero-byte file; `[]`; JSONL with only blank lines | TST-DS-012, TST-DS-013 |
| Invalid datasets | Bad JSON, wrong types, missing required fields, invalid encoding | TST-DS-002…005, TST-MF-001…002 |
| Duplicate identifiers | Exact duplicates; case-differing duplicates | TST-DS-006, TST-DS-007 |
| Missing outputs | Target returns `None` | TST-TG-007 |
| Empty outputs | Target returns `""` or `{}` or `[]` | TST-TG-008; evaluator behaviour for each in TST-EV family |
| Unicode | NFC/NFD; combining marks; emoji; RTL; zero-width joiner; Turkish dotted I | TST-DS-018, TST-EV-005, TST-EV-006 |
| Structured outputs | Nested objects; arrays; numeric precision; key ordering | TST-EV-001, TST-EV-011 |
| Exceptions | Target raises; evaluator raises | TST-TG-003, TST-EV-023 |
| Timeouts | Target exceeds timeout; thread counter | TST-TG-004, TST-TG-009 |
| Missing cases between runs | Baseline-only and candidate-only cases | TST-CM-009, TST-CM-001 |
| Changed datasets | Canonical hash change; formatting-only change | TST-CM-003, TST-CM-006 |
| Changed evaluator definitions | Parameter change; source file change | TST-CM-005, TST-EV-026 |
| Threshold violations | Exactly at threshold; above; below | TST-CM-010, TST-CM-011 |
| Incomparable runs | Aborted, failed, running, schema mismatch, integrity mismatch | TST-CM-007, TST-CM-018, TST-MF-005 |
| Storage failures | Unwritable dir; disk full; crash mid-run; stale lock | TST-PS-102…106 |
| Malformed results | Artifact with missing fields; wrong types; non-finite numbers | TST-MF-007, TST-MF-008 |
| Sensitive-data redaction | Planted secrets in config and error messages; I/O excluded from exports | TST-SEC-008, TST-SEC-009, TST-SEC-013 |

## 6. Synthetic example data (proposed)

Stored under `examples/` (not `tests/`) so that users can run them. Each dataset has
a README stating that it is synthetic.

| Example | Purpose | Cases |
|---|---|---|
| `examples/support_bot/` | Realistic-shaped but fictional support Q&A for the quick start | 5–10 |
| `examples/regression_pair/` | Two fixture targets (baseline and candidate) differing in known ways | 20 |
| `examples/hostile/` | Malicious and malformed inputs for security tests (not for real evaluation) | Labelled by THR ID |

## 7. Fixtures and independent oracles

- Expected outputs for regression_pair are written in a separate CSV reviewed by a person
  (not generated by running the target).
- Hostile corpus expected behaviours are listed in a manifest file with the threat ID.

## 8. Continuous integration (proposed)

| Job | Trigger | Content |
|---|---|---|
| `lint` | Every push and PR | `ruff check`, `ruff format --check`, `mypy --strict` (required gate, OD-15) |
| `test` | Every push and PR | Unit, integration, CLI, API, security, documentation tests; matrix: OS × Python 3.11, 3.12, 3.13 (OD-02) |
| `audit` | Every push and PR | `pip-audit` on the lock file |
| `dco` | Every pull request from an external contributor | Verifies a `Signed-off-by` trailer on every commit. Automated enforcement is required before external contributions are accepted (OD-31; method OD-32 open). |
| `build` | Tags and manual | sdist, wheel, install test in clean environment |
| `secrets-scan` | Every push and PR | Secret scanner (tool to be approved, OD-24) |
| `e2e` | Pull requests to main | Quick start and CI example |

Workflow files are not created until milestone 15 and are not part of this planning
phase. No CI job is claimed to pass.

## 9. Exit criteria (per milestone and for release)

- All tests in scope for the milestone pass in CI on the required matrix.
- No skipped tests without a documented reason and an open issue reference.
- Any failing test is reported with its exact output in the milestone record.
- Security tests for the milestone's threats pass.
- Coverage is reported, and no coverage threshold is asserted unless approved (TRD-236).

## 10. Requirement traceability

Maps MVP requirements to test groups. A requirement is covered when at least one listed
test exists and passes, or when its verification item is listed in RELEASE_CHECKLIST.

| Requirement | Test IDs |
|---|---|
| PRD-F-001 | TST-DS-001, TST-DS-011, TST-DS-013 |
| PRD-F-002 | TST-DS-004, TST-DS-005, TST-DS-014, TST-MF-001, TST-MF-002, TST-CLI-008 |
| PRD-F-003 | TST-DS-006, TST-DS-007 |
| PRD-F-004 | TST-DS-008, TST-DS-009, TST-DS-010 |
| PRD-F-005 | TST-TG-001, TST-TG-010, TST-TG-011 |
| PRD-F-006 | TST-TG-002 |
| PRD-F-007 | TST-TG-003, TST-TG-004, TST-TG-005, TST-TG-013 |
| PRD-F-008 | TST-EV-001, TST-EV-002, TST-EV-003 |
| PRD-F-009 | TST-EV-004, TST-EV-005, TST-EV-006, TST-EV-007 |
| PRD-F-010 | TST-EV-008, TST-EV-009, TST-EV-010 |
| PRD-F-011 | TST-EV-011, TST-EV-012 |
| PRD-F-012 | TST-EV-013 … TST-EV-017, TST-EV-020, TST-EV-021 |
| PRD-F-013 | TST-EV-018, TST-EV-019 |
| PRD-F-014 | TST-EV-022 … TST-EV-028 |
| PRD-F-015 | TST-E2E-001, TST-API-006; manifest field checks in TST-PS-109 |
| PRD-F-016 | TST-EV-029, §4.5 table (T1–T10) |
| PRD-F-017 | TST-PS-101, TST-PS-105, TST-MF-007 |
| PRD-F-018 | TST-PS-102, TST-PS-103, TST-PS-104 |
| PRD-F-019 | TST-CM-001 |
| PRD-F-020 | TST-ST-001, TST-ST-002, TST-CM-017 |
| PRD-F-021 | TST-CM-003, TST-CM-004, TST-CM-005, TST-CM-006 |
| PRD-F-022 | TST-CM-010, TST-CM-011, TST-CM-014, TST-CM-015 |
| PRD-F-023 | TST-CLI-003, TST-CM-012 |
| PRD-F-024 | TST-CLI-011, TST-SEC-010 |
| PRD-F-025 | TST-SEC-013 (default export), JSON Schema validation test (to add in milestone 8) |
| PRD-F-026 | TST-CLI-007, TST-SEC-014 |
| PRD-F-027 | TST-API-001, TST-API-002, TST-API-003 |
| PRD-F-028 | TST-TG-011, TST-EV-022 (interface conformance via example adapter) |
| PRD-F-029 | TST-CLI-008, TST-CLI-009 |
| PRD-F-030 | TST-E2E-001, TST-E2E-003 |
| PRD-NF-001 | TST-SEC-004 |
| PRD-NF-002 | TST-CM-002, TST-CM-016, TST-E2E-002 |
| PRD-NF-003 | TST-SEC-001, TST-SEC-002, TST-SEC-003 |
| PRD-NF-004 | TST-XP-001, TST-E2E-004 |
| PRD-NF-005 | TST-XP-001 |
| PRD-NF-006 | Dependency-list test (to add in milestone 1) |
| PRD-NF-007 | BM-001 … BM-005 |
| PRD-NF-008 | TST-E2E-001 (field presence), TST-CM-016 |
| PRD-NF-009 | TST-MF-005, TST-MF-006 |
| PRD-NF-010 | TST-DOC-001, TST-DOC-002, TST-DOC-004 |
| PRD-NF-011 | TST-SEC-008 |
| PRD-NF-012 | TST-E2E-005, RELEASE_CHECKLIST §2 |
| PRD-NF-013 | TST-DOC-003 |
| PRD-NF-014 | TST-IO-001 … TST-IO-009, TST-RD-001 … TST-RD-006 |
| PRD-NF-015 | TST-IN-001 … TST-IN-004, TST-CM-019 … TST-CM-022, TST-DOC-007 |
| PRD-NF-016 | TST-TG-014 |
| TRD-034 | TST-DS-017, TST-MF-008 |
| TRD-040 | TST-DS-019, TST-CLI-004 |
| TRD-102 | TST-TG-012 (partial results), TST-PS-103 |
| TRD-121 | TST-SEC-017 |
| TRD-132 … TRD-135 | TST-CM-003 … TST-CM-008 |
| TRD-142 | TST-CM-013 |
| TRD-216 | TST-SEC-003 |
| TRD-074, TRD-075, TRD-076 | TST-TG-004, TST-TG-009, TST-TG-014 |
| TRD-106, TRD-116 | TST-IO-005, TST-IO-007 |
| TRD-118, TRD-119 | TST-IO-001 … TST-IO-003, TST-DOC-007 |
| TRD-136 … TRD-138 | TST-CM-019 … TST-CM-022 |
| TRD-186 | TST-RD-006, TST-IO-001 |
| TRD-024 | Lint job with `mypy --strict` (§8) |
| TRD-025, TRD-026, OD-31 | TST-CI-001 … TST-CI-003 |
| OD-02 | TST-XP-001 (matrix: 3.11, 3.12, 3.13) |
| TRD-194, TRD-218, TRD-219 | TST-RD-001 … TST-RD-003, TST-IO-004 |
| THR-001 … THR-023 | See THREAT_MODEL §3; security tests in §4.8 and §4.15 |

Note on PRD-F-025: the JSON Schema validation test depends on publishing the JSON Schema
files, which is a milestone 8 deliverable. Until then this requirement is **not covered**.

## 11. Known gaps in this strategy

- No mutation testing is proposed for the MVP.
- No fuzzing framework is proposed (a seeded corpus is used instead, TST-SEC-018).
- Windows process signal behaviour (TST-CLI-012) needs an alternative test design.
- Concurrency testing is limited to two processes; no stress testing is proposed.
- The Wilson-interval worked example (§4.6) requires independent verification.
- Process isolation is not implemented in the MVP, so no test covers it (ARCHITECTURE §11.1).
- Redaction coverage is limited to the documented pattern and key lists. TST-RD-004 documents misses; it does not measure coverage of real-world secrets.
- Personal-data detection is out of scope, so no test covers it.
