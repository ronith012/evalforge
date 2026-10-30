# Milestone 5 Completion Record — Deterministic evaluators and registry

Status: **Implemented and checked locally on macOS. Not committed. Awaiting owner approval before Milestone 6.**
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

## Preconditions

| Item | Result |
|---|---|
| PRE-1: re-lock with uv 0.13.6 | Done. `uvx --from uv==0.13.6 uv lock` produced a `uv.lock` with the same SHA-256 as before (`8b4fdc69…539c6`). The lock was already in the form 0.13.6 writes. Sync and tests pass. |
| PRE-2: OD-07 (JSON Schema evaluator) | Taken as the recommended default under "proceed": not in the MVP. No dependency added. **Please confirm.** |

## Scope delivered (EXECUTION_PLAN §2)

| Item | Delivered | Where |
|---|---|---|
| Evaluator protocol and the NO_EXPECTED rule | `Evaluator` protocol; `apply_evaluator` skips without calling when expected is absent (spy-tested) | `evaluators/base.py` |
| Six built-ins | `ExactMatch`, `NormalizedText`, `JsonStructure`, `RequiredFields`, `RuleBased`, `Latency`. Pure. Fixed messages. Never INCONCLUSIVE. | `evaluators/builtin.py` |
| Custom evaluators | `module:attribute` loading; class instantiated once; interface checks (`interface_version = "1"`, `version`, `requires_expected`, `evaluate`); source-file hash | `evaluators/custom.py` |
| Fingerprints | Built-ins: type, version, parameters. Custom: plus module, qualified name, source SHA-256. Name excluded. | `evaluators/base.py` |
| Registry | Configured type to evaluator; unknown types and bad parameters raise `EVALUATOR_LOAD_FAILED` | `evaluators/registry.py` |
| Public names | `evaluators/__init__.py` | — |

## Requirements covered by tests (`tests/test_evaluators.py`, 57 tests)

TST-EV-001 to TST-EV-018, TST-EV-021 to TST-EV-029 (TST-EV-019 and TST-EV-020 are configuration checks in
Milestone 2). TST-EV-026 (fingerprint changes with the source file) and TST-EV-027 (unsupported interface
version) are tested. TST-EV-029 (no built-in returns INCONCLUSIVE) runs across nine output shapes.

Also tested: messages never echo planted case content; the registry's type and parameter errors.

## Decisions taken under "proceed" — please confirm

| ID | Decision | Why |
|---|---|---|
| D-5 | Regex input over 1 MiB is `ERROR` / `EVALUATOR_EXCEPTION` with `input_too_long`, not a FAIL. | A resource limit must not be reported as a quality judgement. |
| D-7 | A custom reference naming a **class** is instantiated once with no arguments. The target loader (Milestone 4) refuses classes. | The API design shows evaluators as classes. Targets stay strict because a class could be mistaken for a target. **The two rules differ and should be aligned or justified.** |
| D-8 | The configured name is authoritative. A custom result with a different name is re-labelled with the configured name. | A custom evaluator must not choose its own identity. |
| D-9 | `interface_version = "1"` is required of custom evaluators. | TRD §10.3 requires a checked interface version. |
| D-10 | Evaluator exception text is not stored, only the exception type. | Stricter than DATA_HANDLING §4, so it cannot leak content before redaction exists. |

## Exception text and CO-1

Evaluator exceptions are now handled without storing their text. **Target exception text is still stored, truncated
but not redacted** (Milestone 4). CO-1 therefore remains open for targets and must be closed in Milestone 7, before any
result is written to disk.

## Deviations from the plan

1. **Fewer files than planned.** Fingerprints live in `base.py`, and the JSON-path helper lives in `builtin.py`.
   The plan listed separate `fingerprint.py` and `json_paths.py`. The split was not needed at this size.
2. **`apply_evaluator` lives in `base.py`** (the plan put it there too); `make_result` is public so the built-ins can use it.

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 251 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 251 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 251 passed | 0 |
| Evaluator tests only | `uv run --locked pytest tests/test_evaluators.py` | 57 passed | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 26 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | Success: no issues in 26 source files | 0 |

Mutation check, to confirm the tests can fail:
- Removing the NO_EXPECTED guard fails one test (`1 failed, 56 passed`).
- Counting a JSON `null` as present fails one test (`1 failed, 56 passed`).
- Restoring each change returns the suite to 57 passed.

Not run: Linux and Windows; the CI workflow.

## Issues found during the milestone

1. **Name collision in the custom-result check.** The first version rejected a custom result whose name differed from the
   configured name. The fixtures could not satisfy that rule, so the rule became re-labelling (D-8).
2. **Test expectation mismatch.** One test expected a "not a class" message where the code correctly reports a missing
   `evaluate` method. The test was corrected.
3. **Long lines and one redundant cast**, flagged by lint and strict type checks. Fixed.

## Requested approval

Approve Milestone 5. Confirm PRE-2 (OD-07 not in MVP), decisions D-5 and D-7 to D-10, and whether to commit.

## D-7 decision (recorded 2026-10-30)

**Question.** Evaluators may be named by a class, but targets may not. The two rules differ.

**Proposed resolution (owner to confirm).** Keep both rules and document the reason:

- An evaluator class is instantiated once with no arguments. This matches the design in API_DESIGN §5, where the
  evaluator carries its own name, version, and interface. An evaluator is not called with case input at construction.
- A target class is refused. Calling a class with the case input would construct an object, not run the target. The
  mistake is easy to make and hard to see in a report, so targets must be functions or instances.

**Effect.** No code change. The behaviour in `evaluators/custom.py` and `targets.py` is unchanged. The API reference
states both rules.

