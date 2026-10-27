# Milestone 7 Completion Record — Normalisation and persistence

Status: **Implemented and checked locally on macOS. Not committed. Awaiting owner approval before Milestone 8.**
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

Authorised by "Proceed with Milestone 7". The owner decisions named in EXECUTION_PLAN §4.1 were **not** stated
in that instruction. The recommended values below were applied. **Each needs confirmation.**

## Preconditions and owner decisions (assumed defaults; please confirm)

| Decision | Value applied | Where |
|---|---|---|
| OD-11 run root | `.evalforge/runs` (from configuration; `persist_outcome` takes the root as an argument) | `config.py`, `store.py` |
| OD-12 `io_mode` (final) | `full` (development default). Unchanged. | `config.py`, `store.py` |
| OD-21 exception redaction | Applied: target and evaluator text is redacted before storage | `records.py` |
| OD-22 permissions | Owner-only on POSIX: directories 0700, files 0600 (verified by a test) | `store.py` |
| OD-27 configuration may disable redaction | Allowed; recorded in the manifest and in the configuration snapshot | `config.py`, `records.py` |
| OD-30 platform string | Not stored: EvalForge version, Python version, OS family, machine architecture only | `records.py` |
| CO-1 redaction before any write | **Complete** for target error text, evaluator messages and details, and stored values | `redaction.py`, `records.py` |
| CO-2 serialisation | **Complete** for case, target, evaluator, and error records, with a round-trip test | `serialise.py` |

## Scope delivered (EXECUTION_PLAN §4.2 to §4.4)

| Item | Delivered | Where |
|---|---|---|
| Redaction | Key-based and pattern-based redaction, counted, visible replacement | `src/evalforge/redaction.py` |
| Serialisation | Case, target, error, evaluator, and fingerprint records; decoding re-runs every validation | `src/evalforge/serialise.py` |
| Statistics | Wilson 95% interval; nearest-rank percentiles; standard library only | `src/evalforge/stats.py` |
| Storage preparation | Applies `io_mode` and redaction to a copy; the in-memory result is unchanged; hashes are computed before redaction | `src/evalforge/records.py` |
| Run directory, lock, atomic writes | UUID directories; exclusive `.lock`; temporary file then `os.replace`; OS errors become `STORAGE_ERROR` | `src/evalforge/store.py` |
| Manifest, summary, configuration snapshot | Built as records; secrets removed; paths portable; environment minimal | `src/evalforge/records.py` |
| Integrity | `cases_sha256` and `summary_sha256` over the exact bytes; the manifest is not hashed | `store.py`, `reader.py` |
| Reader | Schema check; RUNNING reported as incomplete; hash verification; strict and lenient modes | `src/evalforge/reader.py` |

## Deviations from the plan

1. **No `RunManifest`, `RunSummary`, or `DatasetFingerprint` dataclasses.** Manifests and summaries are plain
   records built by `records.py` and validated by the reader's schema and hash checks. The plan called for typed
   models. The typed models would add code without changing behaviour, so I have deferred them. **Needs approval.**
2. **Crash test is simulated, not a real process kill.** TST-PS-105 raises `KeyboardInterrupt` inside the writer. A
   real child-process kill was not run. **Not verified with a real kill.**
3. **Windows was not run.** Atomic replace and locking are written for Windows, but no Windows run has happened.

## A behaviour to note (not changed in this milestone)

Under EVALUATION_METHODOLOGY §3.3 rule 7, a case with at least one PASS and the rest SKIPPED is a **PASS**. A case
with no expected value still PASSes when another evaluator, such as latency, passes. The exact-match check was not run
for that case. This follows the specification as written. If you want skipped checks to block a PASS, that is a change
to §3.3 and needs a decision.

## Defects found and fixed during the milestone

1. **Blank line after every case record.** The writer added a second newline. Found by the test that counts lines.
   Fixed; the file now has one record per line.
2. **Wrong expectation in a summary test.** I had written the expected PASS count without accounting for rule 7 (see
   above). The test now states the rule.
3. **Bare OS error on write.** A `write_atomic` failure surfaced as a bare OS error instead of `STORAGE_ERROR`. Fixed.

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 334 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 334 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 334 passed | 0 |
| Storage tests | `pytest tests/test_store.py` | 34 passed | 0 |
| Statistics and redaction | `pytest tests/test_stats.py tests/test_redaction.py` | 27 passed | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 38 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | No issues in 38 source files | 0 |

Fault checks, to confirm the tests can fail, all restored afterwards:
- Disabling the hash check fails one test.
- Disabling target-error redaction fails one test.

Independent derivation: the Wilson interval closed form agrees with a bisection solution of the defining equation to
within 1e-9, for six cases (3/5, 4/5, 1/3, 30/50, 1/100, 99/100). Zero successes uses the closed form
Z²/(n+Z²) = 0.2775 for the upper bound. The literal 3-of-5 interval is [0.2307, 0.8824].

Not run: Linux, Windows, the CI workflow, and a real process kill.

## Requested approval

Approve Milestone 7. Confirm the six owner-decision defaults above, the deviations 1 to 3, and the rule-7 note.
