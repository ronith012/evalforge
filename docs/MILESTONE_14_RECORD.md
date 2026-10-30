# Milestone 14 Completion Record: Integration and End-to-End Tests

Status: **Complete locally. Awaiting owner approval.** Date: 2026-10-30. Not committed.

## Scope (IMPLEMENTATION_PLAN §8.11)

| Item | Result | Where |
|---|---|---|
| 1. Quick start from a clean environment (TST-E2E-001) | Done. The real command line runs as a subprocess, in a copy of the example, with only `PATH` and the source tree in the environment. Steps: validate, run twice, inspect, compare. Compare exit 0; status `pass`. | `tests/test_e2e.py`; `examples/quickstart/` |
| 2. Seeded regression pair with an expected findings manifest (TST-E2E-002) | Done. The candidate differs from the baseline in one greeting. The findings must match `expected_findings.json` exactly (code, severity, case IDs, exit status). | `tests/test_e2e.py`; `examples/regression_pair/` |
| 3. Traceability check that fails on an untested requirement | Done, with a register. Every PRD and TRD ID is either cited by a test or in `docs/TRACEABILITY.md` with a status. Each *Verified* or *Partly* row must name existing tests. | `tests/test_traceability.py`; `docs/TRACEABILITY.md` |
| 4. Executable checks for API and CLI examples (TST-DOC-001, TST-DOC-002) | Done as parse-level checks. Every name in the API surface table is exported. Every `$ evalforge` example in the CLI specification parses with the real parser. Examples are not executed. | `tests/test_docs.py` |
| 5. Link check (TST-DOC-005) and integrity-scope check (TST-DOC-007) | Done. Links in the root, `docs/`, and `examples/` resolve. The manifest's hash fields match the table in ARTIFACT_INTEGRITY §2. | `tests/test_docs.py` |

## Decisions and deviations

- **TST-E2E-001 runs from the source tree**, not from an installed wheel. The installed-wheel check was run by hand
  (macOS, clean venv) and is repeated in CI (Milestone 15).
- **TST-DOC-007 section.** TST-DOC-007 refers to ARTIFACT_INTEGRITY §3.1. The table of hashes the manifest writes is
  §2, and §3.1 is the not-covered list. The test checks §2 against the manifest and checks §3.1 for the statement that
  the manifest itself is not hashed.
- **Traceability register.** When the traceability work started, 190 of 224 requirement IDs were not cited by any test. The register
  classifies each one. It does not claim tests that do not exist. The current status counts are in
  `docs/TRACEABILITY.md`.
- **Examples are parsed, not executed**, for TST-DOC-002. Executing the examples would need their outputs to match
  byte for byte, which the specification does not yet guarantee.

## Found during this milestone

- An inconsistency in the traceability rule: a *Partly* row with no test name was accepted by the first version of the
  check. The check now requires a test name for *Verified* and *Partly* rows; five rows were corrected to *Open* or
  *Deferred* (TRD-013, TRD-020, TRD-023, TRD-024, TRD-160).

## Not done in this milestone

- TST-E2E-003 (the example CI workflow run in project CI) depends on CI running (Milestone 15).
- TST-E2E-004 (install from sdist and wheel on all platforms) is partly done (macOS only).
- TST-DOC-006 (every reason code is produced by a test or marked reserved) is not done.

## Checks and exact results

| Check | Result |
|---|---|
| `uv run pytest -q` on 3.11, 3.12, 3.13 | 546 passed on each |
| `uv run ruff check .` | All checks passed! |
| `uv run ruff format --check .` | 72 files already formatted |
| `uv run mypy --strict` | Success: no issues found in 67 source files |

## Requested approval

Approve Milestone 14. Decide the TST-DOC-007 section reference (§2 is the source of hashes) and whether the
traceability register's Open rows (see `docs/TRACEABILITY.md`) must close before release.
