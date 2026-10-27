# EvalForge — Execution Plan for the Next Milestones

Status: **Proposed execution plan for Milestones 5 to 11.** Companion to
[IMPLEMENTATION_PLAN](../IMPLEMENTATION_PLAN.md) §8. Requirements and decisions are not changed here.

Baseline: commit `1fc4789` (Milestone 4 complete, approved). Test suite: 194 passing on Python 3.11,
3.12, and 3.13 (macOS).

---

## 1. How every milestone runs

Each milestone follows the same cycle. This is what makes the work reviewable.

1. **Preconditions.** Check that the milestone's blocking decisions are recorded in OPEN_DECISIONS.md.
2. **Tests first.** Write the tests named in the milestone from the test strategy (TEST_STRATEGY §4).
   Expected values are literals, or come from an independent reference. They must never be computed
   by the code under test (TRD-235).
3. **Implement.** Write the smallest code that makes the tests pass. Keep public names aligned with
   API_DESIGN §2.
4. **Checks.** Run, and record the exact output of:
   - `uv run --locked --python {3.11,3.12,3.13} pytest -q`
   - `uv run --locked ruff check .` and `uv run --locked ruff format --check .`
   - `uv run --locked mypy --strict`
5. **Record.** Write `docs/MILESTONE_n_RECORD.md` in the format of IMPLEMENTATION_PLAN §5. Include
   deviations, decisions taken, and anything not run.
6. **Stop for approval.** Do not start the next milestone without the owner's approval.
7. **Commit.** Only after approval, and only when the owner asks. One commit per approved milestone.

Rules that apply throughout:

- No dependency is added without a G-1 style verification record (licence, version, status).
- No code runs from dataset content (CLAUDE.md, Security).
- Every exception message that could persist is redacted first (CO-1 in IMPLEMENTATION_PLAN §8.1).
- Nothing is described as tested unless the test ran (CLAUDE.md, "Never invent test results").

---

## 2. Milestone 5 — Deterministic evaluators and registry

### 2.1 Preconditions

| Item | Status | Action |
|---|---|---|
| PRE-1: re-lock with uv 0.13.6 | Open | Run `uv lock` with uv 0.13.6. Record the old and new lock hashes. Tests must pass before any evaluator code is written. |
| PRE-2: OD-07 (JSON Schema evaluator) | Open | Owner decides. Recommended: not in MVP, so no new dependency. |

### 2.2 Module layout

| File | Contents |
|---|---|
| `src/evalforge/evaluators/__init__.py` | Public names only |
| `src/evalforge/evaluators/base.py` | `Evaluator` protocol; `EvaluatorContext`; `apply_evaluator` (runs the NO_EXPECTED rule, catches exceptions) |
| `src/evalforge/evaluators/builtin.py` | The six built-in evaluators |
| `src/evalforge/evaluators/custom.py` | Loader for `module:attribute` custom evaluators |
| `src/evalforge/evaluators/registry.py` | Type name to factory; builds evaluators from `EvaluatorSettings` |
| `src/evalforge/evaluators/fingerprint.py` | Fingerprints for built-in and custom evaluators |
| `src/evalforge/evaluators/json_paths.py` | Dotted-path lookup used by `required_fields` |

Splitting into a package keeps each file small enough to review. `models.py` stays free of evaluator logic.

### 2.3 Design decisions

- **Purity.** `evaluate` receives a `Case`, a copy of the output, and the duration. It must not
  mutate them (TRD-081). The adapter passes deep copies, and a test checks that a mutating evaluator
  leaves the stored output unchanged.
- **NO_EXPECTED handled before the call.** If `requires_expected` is true and the case has no
  `expected`, the adapter returns SKIPPED with `NO_EXPECTED` without calling `evaluate` (TRD-083).
  A spy test proves the call does not happen.
- **Exceptions and malformed results.** An exception becomes `EVALUATOR_EXCEPTION`. A result that is
  not an `EvaluatorResult`, has the wrong status, or has an out-of-range score becomes
  `EVALUATOR_RESULT_INVALID` (TRD-084). Both are ERROR, and the run continues.
- **Reason codes are checked** by `EvaluatorResult` itself (Milestone 2), so a built-in cannot return an
  unregistered code.
- **Built-ins never return INCONCLUSIVE** (TST-EV-029). Only custom evaluators may do so.
- **Messages carry no case content** (DATA_HANDLING §3.3). Built-in messages are fixed text. Details hold
  structural facts only, such as paths and limits. A test searches the messages for planted markers.
- **Regex input cap.** A regex is applied to at most 1 MiB of output (TRD-091). Longer output is an
  ERROR with code `EVALUATOR_EXCEPTION` and detail `input_too_long`. It is not a FAIL, so a resource limit is
  never reported as a quality judgement. *Decision D-5 in §2.6.*

### 2.4 Built-in evaluator behaviour

| Evaluator | Rule | Reason on FAIL | Notes |
|---|---|---|---|
| `exact_match` | Canonical JSON of output equals canonical JSON of expected | `VALUE_MISMATCH` | `1` and `1.0` differ (Milestone 2) |
| `normalized_text` | NFC, optional case folding, whitespace collapse, strip, all configurable | `VALUE_MISMATCH`; non-string output `OUTPUT_NOT_TEXT` | Limitation documented (EVALUATION_METHODOLOGY §4) |
| `json_structure` | Text output parses as JSON; optional top-level type | `NOT_JSON`; `JSON_TYPE_MISMATCH` | Non-text output is already a JSON value, so only the top-level type is checked |
| `required_fields` | Each dotted path resolves to a non-null value in the parsed JSON output | `REQUIRED_FIELD_MISSING`; `NOT_JSON` | No array indexing in MVP |
| `rule_based` | Checks in fixed order: contains, not-contains, regex, length. The first failing rule names the reason. | `RULE_CONTAINS_MISSING`, `RULE_NOT_CONTAINS_PRESENT`, `RULE_REGEX_NO_MATCH`, `RULE_LENGTH_OUT_OF_BOUNDS` | Length counts characters of text output |
| `latency` | `duration_ms <= max_ms` | `LATENCY_EXCEEDED` | Details carry `duration_ms` and `max_ms` |

### 2.5 Tests

Named in TEST_STRATEGY §4.4, and written first:

- TST-EV-001 to TST-EV-029, with one hand-written expected result per row.
- A spy test for NO_EXPECTED (TST-EV-003).
- A mutation test: an evaluator that changes its argument does not change the stored case or output.
- A fingerprint test: changing a custom evaluator's source file changes its fingerprint (TST-EV-026).
- A test that loads a custom evaluator that raises, and one that returns a dict, and checks the error codes.

### 2.6 Decisions introduced by this plan (for owner approval)

| ID | Decision | Reason |
|---|---|---|
| D-5 | A regex input over the 1 MiB cap is an ERROR (`EVALUATOR_EXCEPTION`), not a FAIL | A resource limit must not be reported as a quality judgement |
| D-6 | Excluded cases are listed as SKIPPED with `USER_FILTER` (see §3.3a) | Every dataset case keeps a visible outcome |

### 2.7 Exit criteria

- All tests named above pass on three Python versions.
- Lint, format, and `mypy --strict` pass.
- The record lists every reason code produced, and names the tests that produce each.
- Custom evaluator loading is documented as trusted-code loading.

### 2.8 Risks

| Risk | Mitigation |
|---|---|
| Evaluator semantics surprise users (for example `1` vs `1.0`) | Limitations are in the documentation and asserted by tests |
| Custom evaluators read files at import | Documented as trusted; the fingerprint records the source hash |
| Regex performance (ReDoS) | Input cap; pattern length cap at configuration; documented in SECURITY §7 |

---

## 3. Milestone 6 — Evaluation runner

### 3.1 Preconditions

- Milestone 5 approved.
- OD-06 (best-effort timeouts) is applied. No new decision is needed.

### 3.2 Module layout

| File | Contents |
|---|---|
| `src/evalforge/runner.py` | `run_cases(dataset, target, evaluators, options) -> RunOutcome`; the sequential loop |
| `src/evalforge/timeouts.py` | Worker-thread call with a deadline and a live-thread counter |
| `src/evalforge/runner_options.py` | Options: timeout, grace period, selected case IDs or tags |

### 3.3 Design decisions

- **Sequential, dataset order** (TRD-100, TRD-101). A per-case pipeline: copy input, call the target
  under the deadline, check output, run each evaluator through `apply_evaluator`, aggregate with
  `aggregate_case_status`, append the result.
- **Timeouts.** The target runs in a daemon worker thread. The runner waits up to the deadline. On
  timeout it records `TARGET_TIMEOUT` with the measured duration, which equals the deadline. The thread
  keeps running; the runner increments `threads_possibly_running` (TRD-070 to TRD-072). Daemon threads do
  not block process exit.
- **Interruption.** On `KeyboardInterrupt`, the runner finishes the current case if it completes within
  the grace period (5 seconds, TRD-103). Otherwise it records the case as not executed. Remaining cases
  are not written as results; the run is finalised as `ABORTED`.
- **Engine boundary.** Any other unexpected exception becomes `ENGINE_ERROR` and the run is `FAILED`
  (TRD-104). Exit code 4 is decided in Milestone 11.
- **In-memory result.** The run returns a `RunOutcome` holding case results, counts, and the
  `threads_possibly_running` count. Nothing is written to disk until Milestone 7.
- **Selection.** `--case` and `--tag` select cases before the loop. An excluded case is still listed in the
  run as `SKIPPED` with reason `USER_FILTER`, so every dataset case has a visible outcome (DATA_MODELS §9.1).
  *Decision D-6 in §2.6 and §3.3a.*

### 3.4 Tests

- TST-TG-004: a target that sleeps past its deadline is recorded as `TARGET_TIMEOUT`, its duration equals
  the deadline, and the run continues.
- TST-TG-009: a timed-out thread increments `threads_possibly_running`.
- TST-TG-012: `KeyboardInterrupt` mid-run finalises the outcome as `ABORTED` and writes no record for the
  interrupted case.
- The aggregation table T1 to T10 through the runner, not only through the function.
- Deadline tests use short durations (for example 0.05 s), and the sleeping target is a fixture. The
  tests do not assert exact wall-clock times.

### 3.3a Decision D-6 in context

When `--case` or `--tag` excludes a case, the case appears in the run as `SKIPPED` with reason
`USER_FILTER`. The alternative, leaving excluded cases out of the run, would hide them from the
summary. The milestone record must name D-6 for approval.

### 3.5 Exit criteria

- All tests pass on three Python versions.
- The record states clearly that timeouts are best-effort, and that a timed-out target may still be running.
- No test depends on machine speed beyond a generous margin, and the record names the margin used.

### 3.6 Risks

| Risk | Mitigation |
|---|---|
| Flaky timing tests | Generous margins; fixtures with large differences; no exact timing assertions |
| Leaked threads accumulate | Counter and warning; documented; isolation reassessed in M13 |
| Interrupt during a write (not yet possible in M6) | No writes in M6; revisit in M7 |

---

## 4. Milestone 7 — Result normalisation and persistence

Milestone 7 is the largest data-handling milestone. It writes results, so it must not start until CO-1
(redaction) is complete.

### 4.1 Preconditions

- Milestone 6 approved.
- CO-1 and CO-2 from IMPLEMENTATION_PLAN §8.1 are done. CO-2 is JSON round-trip for case, evaluator, and
  target results.
- Owner decisions recorded: OD-11, OD-12 (final), OD-21, OD-22, OD-27, OD-30.

### 4.2 Module layout

| File | Contents |
|---|---|
| `src/evalforge/redaction.py` | Key-based and pattern-based redaction with counted replacements (DATA_HANDLING §7) |
| `src/evalforge/serialise.py` | JSON encoding and decoding of persisted records; schema checks |
| `src/evalforge/store/run_dir.py` | Run directory creation, exclusive lock, atomic writes |
| `src/evalforge/store/writer.py` | Streams case records; writes manifest and summary |
| `src/evalforge/store/reader.py` | `Run.load`; integrity checks; schema checks |
| `src/evalforge/stats.py` | Wilson interval; nearest-rank percentiles |
| `src/evalforge/models_run.py` | `RunManifest`, `RunSummary`, `DatasetFingerprint` (the models deferred from Milestone 2) |
| `src/evalforge/config_snapshot.py` | Configuration snapshot with secret-like values removed |

### 4.3 Design decisions

- **Run directory.** A new UUIDv4 directory under the run root. An existing name is never reused (TRD-111).
  The root directory is created if absent, with owner-only permissions where the platform supports them
  (OD-22).
- **Lock.** Create `.lock` with `O_CREAT | O_EXCL` before the first write. A second writer fails with
  `STORAGE_LOCKED` (TRD-121). A stale lock is reported by `inspect` and is never removed automatically
  (TRD-122).
- **Manifest.** Written at start as `RUNNING`. Rewritten atomically at the end: write a temporary file in
  the same directory, then `os.replace` (TRD-112).
- **Case records.** Appended one per line, flushed after each. An interrupted run leaves a readable prefix.
- **Summary.** Written after `cases.jsonl` is complete (TRD-113).
- **Integrity.** `cases_sha256` and `summary_sha256` are SHA-256 digests of the exact file bytes, stored in
  the manifest (ARTIFACT_INTEGRITY §2 to §3). The manifest itself is not hashed.
- **io_mode.** `full` stores input, expected, and output (redacted). `hashes` stores hashes only. `none`
  stores no I/O and no I/O hashes (DATA_HANDLING §3.1). Case identity hashes are always stored.
- **Redaction.** Applied to stored strings, evaluator messages and details, exception messages, and the
  configuration snapshot. Replacements are counted into `redactions`. Redaction is on by default and can be
  disabled only with the recorded warning (DATA_HANDLING §7.5). The rules are a starting list, and the
  limits in DATA_HANDLING §7.4 are stated in the record.
- **Tracebacks.** Never stored (DATA_HANDLING §4).
- **Environment metadata.** Only EvalForge version, Python version, OS family, and machine architecture
  (DATA_HANDLING §6).
- **Statistics.** Wilson 95% interval; nearest-rank percentiles. Standard library only.
- **Reader.** `Run.load` verifies the schema major version, the hashes, and the run status. An unsupported
  version raises `SCHEMA_VERSION_UNSUPPORTED`. A hash mismatch raises `INTEGRITY_MISMATCH`. The run is
  returned with `integrity_ok = False` only when the caller asks for lenient loading.

### 4.4 Work order inside the milestone

1. Serialisation round-trip tests for every persisted record (CO-2). Stop here until they pass.
2. Redaction module, with its tests (TST-RD-001 to TST-RD-006). Stop here until they pass.
3. Statistics module, checked against vectors computed outside the code. The vector for 3 of 5 at 95% is
   `[0.2307, 0.8824]`, computed with the Python script recorded in the record. A second derivation is
   required before the value is treated as verified (TEST_STRATEGY §4.6).
4. Run directory, lock, and atomic writes, including the Windows tests.
5. Manifest, summary, and integrity hashes (TST-IN-001 to TST-IN-004).
6. `io_mode` handling (TST-IO-001 to TST-IO-009).
7. `Run.load` with the schema and integrity checks (TST-PS-101 to TST-PS-109, TST-MF-005 to TST-MF-008).

### 4.5 Tests

Named in TEST_STRATEGY §4.11, §4.15 and §4.3 (the persistence block). The crash test (TST-ST-105, now
TST-PS-105) kills a child process after N cases, then checks that `inspect` reports the run as incomplete
and `compare` refuses it.

### 4.6 Exit criteria

- All persistence tests pass on Linux (where available), macOS, and Windows in CI. The record states which
  platforms were actually run. Windows is not claimed unless it ran.
- The redaction limits (DATA_HANDLING §7.4) appear in the record.
- Statistics vectors are verified by a second derivation.

### 4.7 Risks

| Risk | Mitigation |
|---|---|
| Windows replace and lock semantics differ | Platform-specific tests; CI on Windows before the milestone closes |
| Redaction gives false confidence | Limits stated; tests assert the documented misses (TST-RD-004) |
| Large runs are slow to write | Streamed writes; performance measured and recorded, not claimed (BM-003) |
| Permission handling differs by platform | Owner-only where supported; documented otherwise (OD-22) |

---

## 5. Milestones 8 to 11 — outline

Detailed plans are written when each milestone begins, so that they reflect what the earlier milestones
actually produced.

| Milestone | Core work | Decisions needed first | Main tests |
|---|---|---|---|
| 8 Reporting | Terminal and JSON reports; JSON Schema files; sanitisation; golden outputs | OD-18 (footer wording) | TST-CLI-011, TST-SEC-010, TST-SEC-013, TST-SEC-014, TST-DOC-003, JSON Schema validation |
| 9 Comparison | Compatibility; categories; overrides with banner and recorded output; `--strict`; byte-identical output | OD-09 (confirm), OD-13, OD-28 | TST-CM-001 to TST-CM-022 |
| 10 Regression detection | Thresholds; finding codes; golden messages; infrastructure errors kept separate | OD-08 | TST-CM-009 to TST-CM-015 |
| 11 CLI and API | `argparse` commands; exit codes 0 to 5; public API; parity; dataset warnings shown | OD-25, OD-26 | TST-CLI-001 to TST-CLI-012, TST-API-001 to TST-API-006 |

---

## 6. Standing items across all milestones

| Item | When | Owner |
|---|---|---|
| G-1 verification for any new dependency (licence, version, status, date) | Before installation | Recorded in `docs/TOOLING_VERIFICATION.md` |
| G-2 publication checks, including the PyPI name conflict | Before Milestone 16 | Owner |
| Copyright-year placeholder convention | Before any publication | Owner confirms the approach |
| Remote repository and permission to push | Before the first CI run on Linux and Windows | Owner |
| DCO enforcement method (OD-32) | Before any external contribution | Owner |
| Performance measurement on the CI reference runner | Milestones 2, 7, and 10 (BM-001 to BM-005) | Recorded, not claimed |

---

## 7. What the owner is asked to do next

1. Approve this plan, or request changes to the order or scope.
2. Decide PRE-2 (OD-07) before Milestone 5 starts.
3. Confirm that uv 0.13.6 may be used for the re-lock (PRE-1).
4. Confirm the regex-input decision in §2.6.
5. Decide OD-11, OD-12 (final), OD-21, OD-22, OD-27, and OD-30 before Milestone 7 starts.
