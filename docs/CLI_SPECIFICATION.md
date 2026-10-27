# EvalForge — CLI Specification

Status: **Proposed. All examples are proposals and are not implemented or verified.**

Command name: `evalforge`. Concepts match [API_DESIGN](API_DESIGN.md) and
[DATA_MODELS](DATA_MODELS.md). Requirements: PRD-F-023, PRD-F-024 to PRD-F-026,
PRD-F-029, TRD §10.

---

## 1. Global conventions

The CLI is implemented with `argparse` from the standard library (TRD-165). Option names below
are proposals until implemented and verified.

### 1.1 Global options

| Option | Type | Default | Description |
|---|---|---|---|
| `--version` | flag | — | Print version and exit 0 |
| `--help`, `-h` | flag | — | Print help for the command and exit 0 |
| `--run-root PATH` | path | `.evalforge/runs` relative to config directory, or current directory when no config | Directory containing run directories |
| `--format {text,json}` | choice | `text` | Output format where applicable |
| `--no-color` | flag | off | Disable ANSI colour. Also honoured via `NO_COLOR` environment variable (standard convention). |
| `--quiet`, `-q` | flag | off | Suppress non-essential output; errors still shown |
| `--verbose`, `-v` | count | 0 | `-v` INFO logs, `-vv` DEBUG logs (IDs and timings only, TRD-192) |

### 1.2 Output streams

- Results (tables, JSON) go to **stdout**.
- Diagnostics, warnings, and errors go to **stderr**.
- With `--format json`, stdout is always one valid JSON document; diagnostics stay on stderr (TRD-164).

### 1.3 Error message shape (text)

```
error[DATASET_INVALID]: datasets/support.jsonl:14: field "expected": expected JSON value, got NaN
```

Format: `error[CODE]: <location>: <message>`. Location is present when known. Messages
never contain secret values (TRD-202).

### 1.4 Exit codes

| Code | Name | Used by | Meaning |
|---|---|---|---|
| 0 | `OK` | all | Success. For `compare`: no findings with severity `error`. For `run`: completed and no `--fail-on` status occurred. |
| 1 | `REGRESSION` | `compare`; `run` with `--fail-on` | `compare`: at least one finding with severity `error`. `run`: at least one case with a status listed in `--fail-on`. |
| 2 | `USAGE_OR_CONFIG` | all | Invalid arguments, invalid configuration, unknown run, target or custom evaluator could not be loaded |
| 3 | `DATASET_INVALID` | `dataset validate`, `run`, `config validate` when it checks dataset | Dataset failed validation |
| 4 | `INFRASTRUCTURE` | all | Storage failure, lock conflict, engine error, aborted run (`run` only), integrity mismatch, unsupported schema version, report write failure |
| 5 | `REFUSED` | `compare` | Comparison refused: incompatible or incomplete runs (without the allowing flag) |

Rules:

- Codes are stable (TRD-161). Regression codes (1) are never used for infrastructure faults (4) (PRD-F-023).
- If several conditions apply, the highest-precedence applies in this order: 4, 5, 3, 2, 1, 0. (Infrastructure faults take precedence because results may be unreliable.)
- A `run` in which individual cases ERROR is still exit 0 unless `--fail-on error` is given (EVALUATION_METHODOLOGY §3.4).

### 1.5 Run references

Commands that take `RUN` accept either:

- a run ID (UUIDv4 or unique prefix of at least 8 characters, resolved within `--run-root`), or
- a path to a run directory.

Ambiguous prefixes → exit 2 with `RUN_NOT_FOUND` and the list of matches.

## 2. Configuration file

### 2.1 Discovery

`evalforge.toml` in the current directory unless `--config PATH` is given (available on
`run`, `compare`, `config validate`). A `--config` path that does not exist is exit 2.

### 2.2 Shape

See DATA_MODELS §4. Summary of tables: `[run]`, `[dataset]`, `[target]`,
`[[evaluators]]`, `[regression]`.

### 2.3 Validation rules

| Rule | Error code |
|---|---|
| `schema_version` present and supported | `CONFIG_INVALID` |
| Unknown key anywhere | `CONFIG_UNKNOWN_KEY` (exit 2) |
| `dataset.path` present | `CONFIG_INVALID` |
| `target.callable` present and of form `module:attribute` | `CONFIG_INVALID` |
| At least one `[[evaluators]]` | `CONFIG_INVALID` |
| Evaluator `name` unique, pattern valid | `CONFIG_INVALID` |
| Evaluator type-specific required fields present (for example `paths` for `required_fields`) | `CONFIG_INVALID` |
| `run.timeout_seconds` > 0 and ≤ 3600 | `CONFIG_INVALID` |
| `run.fail_on` values in {fail, error, inconclusive} | `CONFIG_INVALID` |
| `regression.missing_case_policy` in {fail, warn, ignore} | `CONFIG_INVALID` |
| `regression.max_pass_rate_drop` in [0, 1] | `CONFIG_INVALID` |
| `regression.max_p95_latency_ratio` > 1 when present | `CONFIG_INVALID` |

`config validate` does **not** import the target or custom evaluators unless
`--check-imports` is given. Import executes module code (THR-004), so validation is
opt-in for imports.

## 3. Commands

### 3.1 `evalforge config validate`

**Purpose:** Check a configuration file without running anything.

**Synopsis:** `evalforge config validate [CONFIG] [--check-imports] [--format text|json]`

| Argument / option | Description |
|---|---|
| `CONFIG` | Path to configuration file. Default: `evalforge.toml`. |
| `--check-imports` | Also import the target and custom evaluator modules to confirm they resolve. Executes module code; only use on trusted projects. |

**Exit codes:** 0 valid; 2 invalid configuration or unresolvable imports (with flag); 3 if the referenced dataset file is missing or fails validation when `--check-dataset` is given (see below).

Additional option: `--check-dataset` runs dataset validation too (exit 3 on failure).

**Error behaviour:** Lists all errors found (up to 100), each with key path and code.

**Example (proposed):**

```
$ evalforge config validate
Configuration valid: evalforge.toml
  evaluators: 5 (exact_match, required_fields, normalized_text, rule_based, latency)
  target: examples.support_bot:answer (imports not checked)
```

**Failure example (proposed):**

```
$ evalforge config validate
error[CONFIG_UNKNOWN_KEY]: evalforge.toml:[regression]: unknown key "max_newly_faling"
error[CONFIG_INVALID]: evalforge.toml:[[evaluators]][2]: "paths" is required for type "required_fields"
2 errors found.
$ echo $?
2
```

### 3.2 `evalforge dataset validate`

**Purpose:** Validate a dataset file against the schema and limits.

**Synopsis:** `evalforge dataset validate PATH [--format text|json]`

| Argument / option | Description |
|---|---|
| `PATH` | `.json` or `.jsonl` dataset file |

**Behaviour:** Validates encoding, format, each case, ID uniqueness, and limits (TRD §4).
Collects up to 100 errors. Reports counts and both hashes on success.

**Exit codes:** 0 valid; 3 invalid, including an unsupported file extension (`DATASET_FORMAT_UNSUPPORTED`, DATA_MODELS §9.2); 2 file not found or path is not a regular file (`USAGE_OR_CONFIG`).

**Example (proposed) — success:**

```
$ evalforge dataset validate datasets/support.jsonl
Dataset valid: datasets/support.jsonl
  format:            jsonl
  cases:             5
  tags:              smoke (2), refunds (3)
  sha256:            sha256:4f1c…
  canonical sha256:  sha256:9ab2…
```

**Example (proposed) — failure:**

```
$ evalforge dataset validate datasets/support.jsonl
error[DATASET_DUPLICATE_ID]: datasets/support.jsonl:9: id "refund-001" already defined at line 1
error[DATASET_INVALID]: datasets/support.jsonl:14: field "input": expected object, got string
2 errors found (validation stopped at 100 errors or end of file).
$ echo $?
3
```

**JSON output:** `{"valid": false, "errors": [{"code": "...", "line": 9, "field": "id", "message": "..."}]}`

### 3.3 `evalforge run`

**Purpose:** Execute the configured target against the selected cases, evaluate, and persist a run.

**Synopsis:**

```
evalforge run [--config CONFIG] [--out RUN_ROOT] [--case ID]... [--tag TAG]...
              [--timeout SECONDS] [--io-mode {full,hashes,none}] [--no-redaction]
              [--fail-on STATUS[,STATUS...]] [--format text|json] [--quiet]
```

| Option | Description |
|---|---|
| `--config CONFIG` | Configuration file (default `evalforge.toml`) |
| `--out RUN_ROOT` | Override `--run-root` for this run |
| `--case ID` | Run only this case ID. Repeatable. Unknown IDs → exit 2 `USAGE_OR_CONFIG` with the unknown IDs listed. Cannot combine with `--tag`. |
| `--tag TAG` | Run only cases having this tag. Repeatable; a case matches if it has any of the given tags. |
| `--timeout SECONDS` | Override target timeout |
| `--io-mode {full,hashes,none}` | Override how case inputs, expected values, and outputs are stored (DATA_HANDLING §3; default OD-12). `hashes` stores hashes only; `none` stores no I/O hashes. |
| `--no-redaction` | Disable redaction for this run (DATA_HANDLING §7.5). The manifest records `redaction: false`, and the terminal summary prints a warning line. |
| `--fail-on STATUS[,…]` | Exit 1 if any case has one of the listed statuses. Values: `fail`, `error`, `inconclusive`. Default: none. |

**Behaviour:**

1. Load and validate config (exit 2 on failure).
2. Load and validate dataset (exit 3 on failure). Nothing is executed on failure.
3. Resolve target and custom evaluators (exit 2 on failure with `TARGET_LOAD_FAILED` / `EVALUATOR_LOAD_FAILED`).
4. Create run directory (exit 4 on failure).
5. Execute cases in dataset order (TRD §6).
6. Finalize (exit 4 if finalization fails; the run remains `RUNNING` on disk and is reported).

**Progress:** On a terminal, one line per case with status and duration, updated in place. With `--quiet` or `--format json`, no progress is shown. Progress never prints case inputs or outputs.

**Exit codes:** 0 completed, no `--fail-on` match; 1 completed with a `--fail-on` match; 2 config or load error; 3 dataset error; 4 infrastructure error or aborted run.

**Interrupt (Ctrl-C):** Finishes the current case within the grace period, then finalizes with status `ABORTED`, reports `RUN_ABORTED`, exit 4.

**Example (proposed) — text output:**

```
$ evalforge run
Run 3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90  target=support-bot-v2  dataset=5 cases
  [1/5] refund-001      FAIL   412 ms   exact
  [2/5] greeting-004    PASS    38 ms
  [3/5] order-status-02 PASS   511 ms
  [4/5] slow-017        ERROR  30000 ms  TARGET_TIMEOUT
  [5/5] format-009      PASS   120 ms

Status: COMPLETED
Executed: 5   PASS 3   FAIL 1   ERROR 1   SKIPPED 0   INCONCLUSIVE 0
Pass rate: 0.600  (95% interval 0.231–0.882; n = 5)
Errors: TARGET_TIMEOUT (1)
Failures by evaluator: exact (1)
Stored: .evalforge/runs/3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90
```

The footer sentence from EVALUATION_METHODOLOGY §12 is printed once per run summary
in text output. Its exact wording is pending OD-18.

**Example (proposed) — `--fail-on error`:**

```
$ evalforge run --fail-on error
...
Exit: 1 (cases with status ERROR: 1)
$ echo $?
1
```

### 3.4 `evalforge inspect`

**Purpose:** Show a stored run: manifest essentials, summary, case list, or one case.

**Synopsis:** `evalforge inspect RUN [--case ID] [--status STATUS] [--limit N] [--show-io] [--format text|json]`

| Option | Description |
|---|---|
| `--case ID` | Show detail for one case: input, output, expected, each evaluator result with status, reason, message. |
| `--status STATUS` | Filter the case list by status (PASS, FAIL, ERROR, SKIPPED, INCONCLUSIVE). Case-insensitive. |
| `--limit N` | Limit case list rows (default 50; maximum 1000; `0` means no limit within the max). |
| `--show-io` | Include input and output in case list rows (not only in `--case` detail). Off by default to reduce accidental disclosure in terminals. |

**Integrity:** Verifies `cases_sha256` against `cases.jsonl` and `summary_sha256` against `summary.json` (ARTIFACT_INTEGRITY §4). Mismatch → warning on
stderr and exit 4 `INTEGRITY_MISMATCH` unless `--format json` (then reported in JSON
and exit 4 still applies). Stale `RUNNING` runs are reported as incomplete with exit 0
for `inspect` (inspection is allowed; comparison is not).

**Exit codes:** 0 ok (including incomplete run, reported as such); 2 run not found or ambiguous; 4 integrity or schema error.

**Example (proposed) — summary:**

```
$ evalforge inspect 3f2b8c1e
Run 3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90
  status: COMPLETED   started: 2026-10-18T14:03:22.000Z   duration: 2.8 s
  target: support-bot-v2   dataset: datasets/support.jsonl (sha256:4f1c…)
  evaluators: exact, has_answer, text_norm, no_placeholder, fast_enough, domain_rule
  counts: PASS 3  FAIL 1  ERROR 1  SKIPPED 0  INCONCLUSIVE 0
```

**Example (proposed) — one case:**

```
$ evalforge inspect 3f2b8c1e --case refund-001
Case refund-001  status FAIL  (reason: exact)
  input:     {"question": "Can I get a refund after 30 days?"}
  expected:  {"answer": "No, refunds are available within 30 days."}
  output:    {"answer": "Yes, within 45 days."}
  evaluators:
    exact           FAIL  VALUE_MISMATCH        Output differs from expected value.
    has_answer      PASS  —                     All required paths present.
```

Output is shown after control-character sanitization (SECURITY §6).

### 3.5 `evalforge compare`

**Purpose:** Compare a candidate run with a baseline run, check compatibility, detect regressions.

**Synopsis:**

```
evalforge compare BASELINE CANDIDATE [--config CONFIG]
                  [--allow-dataset-change] [--allow-evaluator-change]
                  [--strict] [--out PATH] [--format text|json]
```

| Argument / option | Description |
|---|---|
| `BASELINE`, `CANDIDATE` | Run references (§1.5) |
| `--config CONFIG` | Read the `[regression]` table. If omitted, built-in defaults are used and the report says so. |
| `--allow-dataset-change` | Permit comparison when canonical dataset hashes differ. Adds `DATASET_CHANGED` warning and `changed_input` categories. |
| `--allow-evaluator-change` | Permit comparison when evaluator fingerprints differ. Adds `EVALUATOR_CHANGED` warning. |
| `--strict` | Treat any override as a refusal (exit 5), so CI never accepts an overridden comparison (ARTIFACT_INTEGRITY §6.2; TRD-138). |
| `--out PATH` | Write the comparison JSON to this path (DATA_MODELS §11). Never overwrites an existing file; exit 4 `STORAGE_ERROR` if the path exists. Parent directories are not created. |

**Behaviour:**

1. Load both manifests. Refuse if either is not `COMPLETED` (exit 5, `RUN_INCOMPLETE`).
2. Check schema major versions (exit 4 `SCHEMA_VERSION_UNSUPPORTED` if unsupported).
3. Verify integrity hashes (exit 4 `INTEGRITY_MISMATCH` if mismatched).
4. Check compatibility (dataset hash, evaluator fingerprints, evaluator names). Refuse unless allowed (exit 5). The refusal lists **all** incompatibilities.
5. Categorize cases, compute metrics, apply thresholds, produce findings.

**Exit codes:** 0 no error-severity findings; 1 error-severity findings present; 2 usage/config error or run not found; 4 infrastructure, integrity, or schema error; 5 refused.

**Example (proposed) — regression:**

```
$ evalforge compare 2b7a9e10 3f2b8c1e --config evalforge.toml
Comparison: baseline 2b7a9e10 (support-bot-v1) → candidate 3f2b8c1e (support-bot-v2)
Dataset: same (canonical sha256:9ab2…)   Evaluators: same (6)

Cases (5):  regressed 1   recovered 0   unchanged 3   changed 0   missing 0   new 0
Pass rate:  0.800 → 0.600   (Δ −0.200)

Findings:
  error    CASE_REGRESSED_TO_FAIL   1 case that passed in the baseline now fails: refund-001.
           threshold: regression.max_newly_failing = 0, observed 1
  error    PASS_RATE_DROP           Pass rate fell from 0.800 to 0.600 (drop 0.200), above the configured maximum of 0.050.
           threshold: regression.max_pass_rate_drop = 0.05, observed 0.200

Result: REGRESSION (2 error findings)
$ echo $?
1
```

**Example (proposed) — refused:**

```
$ evalforge compare 2b7a9e10 9c0d4b21
Comparison refused: runs are not compatible.
  error[DATASET_CHANGED]: canonical dataset hash differs
      baseline sha256:9ab2…   candidate sha256:b7e0…
  error[EVALUATOR_CHANGED]: evaluator "domain_rule" fingerprint differs
Use --allow-dataset-change and/or --allow-evaluator-change to compare anyway.
$ echo $?
5
```

**Example (proposed) — overridden comparison:** The banner appears before any findings. The
override is also recorded in the JSON output (`compatibility.overrides`) and produces a
`COMPARISON_OVERRIDDEN` warning.

```
$ evalforge compare 2b7a9e10 9c0d4b21 --allow-dataset-change
+--------------------------------------------------------------------------+
| COMPARISON OVERRIDDEN                                                    |
| --allow-dataset-change: canonical dataset hash differs                   |
|   baseline sha256:9ab2…   candidate sha256:b7e0…                         |
| Cases whose content changed are not status-compared.                     |
+--------------------------------------------------------------------------+
Cases (5):  regressed 0   recovered 0   unchanged 2   changed 0   changed_input 3
Findings:
  warning  COMPARISON_OVERRIDDEN   Comparison proceeded under --allow-dataset-change.
  warning  DATASET_CHANGED         Canonical dataset hash differs between runs.
Result: NO REGRESSION FINDINGS (1 warning) — comparison overridden
$ echo $?
0
```

With `--strict`, the same command exits 5 and does not produce findings (§1.4).


### 3.6 `evalforge report export`

**Purpose:** Write a run summary or comparison to a file in a machine-readable or readable form.

**Synopsis:** `evalforge report export SOURCE --out PATH [--format json|text] [--include-io]`

| Argument / option | Description |
|---|---|
| `SOURCE` | A run reference, or a path to a comparison JSON file produced by `compare --out` |
| `--out PATH` | Output file. Required. Refuses to overwrite an existing file (exit 4 `STORAGE_ERROR`). |
| `--format` | `json` (default) or `text` |
| `--include-io` | Include stored case inputs and outputs in the export. Off by default. Requires that the source run was stored with `io_mode = full`; otherwise exit 2 `IO_NOT_STORED`. Exports never contain unredacted content (DATA_HANDLING §8.2). |

**Behaviour:** JSON output validates against the published JSON Schema for the artifact
version (PRD-F-025). Text output is sanitized (SECURITY §6). Exports without `--include-io`
contain no case inputs or outputs, and no tracebacks in any case (DATA_HANDLING §8.1).

**Exit codes:** 0 written; 2 usage, source not found, or `IO_NOT_STORED`; 4 write or integrity error.

**Example (proposed):**

```
$ evalforge report export 3f2b8c1e --out reports/run-3f2b8c1e.json
Wrote reports/run-3f2b8c1e.json (schema_version 1.0, case I/O excluded)
```

Note: `--out` paths are relative to the current directory and are not restricted to the
run root (the operator chose the path; TRD-212). Parent directories are not created.

## 4. Summary of exit-code usage by command

| Command | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| `config validate` | valid | — | invalid / import fail | dataset invalid (with `--check-dataset`) | — | — |
| `dataset validate` | valid | — | file missing / unsupported path | invalid | — | — |
| `run` | completed | `--fail-on` match | config / load / case selection error | dataset invalid | infra error / aborted | — |
| `inspect` | shown | — | run not found | — | integrity / schema | — |
| `compare` | no error findings | error findings | usage / run not found | — | infra / integrity / schema | refused |
| `report export` | written | — | usage / source not found | — | write / integrity | — |

## 5. Environment variables

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disables colour (standard convention). |
| `EVALFORGE_CONFIG` | Not supported in MVP (TRD-183 forbids environment-based configuration). Reserved word. |

No other environment variables are read. Environment values are never written to
artifacts.

## 6. Command name stability

Command and option names are stable from 1.0 (TRD-242). Before 1.0, changes are listed
in CHANGELOG. Options marked "proposed" in this document are not final until implemented
and verified.

## 7. Open CLI questions

- Whether `run` should accept `--workers` (post-MVP, PRD-F-104).
- Whether `compare` should write findings in SARIF or GitHub annotation format
  (post-MVP; OD-19).
- Whether `--out` on `compare` should overwrite (current proposal: no; see §3.5).
