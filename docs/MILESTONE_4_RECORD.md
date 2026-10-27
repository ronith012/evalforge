# Milestone 4 Completion Record — Target interface

Status: **Approved by the owner on 2026-10-27.** Implemented and checked locally on macOS. **Not committed:** commit is pending a separate instruction.

Accepted decisions: (1) importing a target reference runs trusted module code (no sandbox); (2) `SystemExit` from a target is recorded as an error and `KeyboardInterrupt` propagates; (3) classes are refused rather than instantiated.

**Carried forward (binding before Milestone 7 writes any result):** exception messages must be redacted before persistence (DATA_HANDLING §4; IMPLEMENTATION_PLAN §8, item CO-1).
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

## Scope delivered (DEVELOPMENT_TASKS 26–29)

| Plan item | Delivered | Where |
|---|---|---|
| 26 Target protocol and callable adapter | `Target` protocol (name and call); `CallableTarget` adapter; `from_callable` | `src/evalforge/targets.py` |
| 27 `module:attribute` reference resolution | `resolve_target`; errors raised as `TARGET_LOAD_FAILED`; classes are refused, not instantiated; name precedence: explicit, then declared, then reference text | `targets.py` |
| 28 Input deep copy and output check | `invoke_target` copies the input (TRD-064), checks the output is JSON-serialisable (TRD-062), and times the call (TRD-063) | `targets.py` |
| 29 Example adapter for conformance | Synthetic modules under `tests/fixtures/targets/` (test use only) | fixtures |

Acceptance criteria: PRD-F-005 and PRD-F-028 are met by the tests. The serialisability check yields
`TARGET_OUTPUT_INVALID` through `invoke_target`, which the runner in Milestone 6 will call.

## Requirements covered by tests (`tests/test_targets.py`, 30 tests)

TST-TG-001, 002, 003, 005, 006, 007, 008, 010, 011, 013 (the last as a proposal; see decision 2).
Not in this milestone: TST-TG-004 and 009 (timeouts), TST-TG-012 (run interruption), both Milestone 6.

## Decisions to confirm

1. **Trusted-code loading.** Resolving a reference imports the module, which runs its top-level code. This is
   documented in the module and matches SECURITY §10.1. No sandbox exists.
2. **`SystemExit` from a target is recorded as an error** (`TARGET_EXCEPTION`), so a target cannot end the process.
   `KeyboardInterrupt` propagates so the runner can stop the run. TST-TG-013 marked this as proposed.
3. **Classes are refused.** A reference to a class is not instantiated automatically.

## Not yet safe to persist

- **Exception messages are not redacted.** `invoke_target` stores the exception type and message, truncated to 500
  characters. Redaction is Milestone 7 (DATA_HANDLING §4). Nothing is persisted in Milestone 4, so no secret leaves
  the process yet. The gap must close before Milestone 7 writes results.
- Output values are not yet size-limited beyond the string and depth limits in `canon`.

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 194 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 194 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 194 passed | 0 |
| Target tests only | `uv run --locked pytest tests/test_targets.py` | 30 passed | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 19 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | Success: no issues in 19 source files | 0 |

Not run: Linux and Windows; the GitHub Actions workflow.

## Issues found during the milestone

1. **Unused `type: ignore` comments** in the tests, flagged by strict mypy. Removed, because mypy resolves the fixture
   modules without them.
2. **A list literal typed as `dict[str, int]`** was passed where `JSONValue` was expected. Fixed with an explicit type.
3. **A first draft of name resolution was convoluted.** It was simplified before testing. The tests cover the
   resulting precedence rules.

## Requested approval

Approve Milestone 4 as complete. Confirm decisions 1 to 3 above. Confirm whether this milestone should be committed.
