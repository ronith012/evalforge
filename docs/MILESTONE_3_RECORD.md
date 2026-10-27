# Milestone 3 Completion Record — Dataset loading

Status: **Implemented and checked locally on macOS. Awaiting owner approval before Milestone 4.**
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

## Scope delivered (DEVELOPMENT_TASKS 22–25)

| Plan item | Delivered | Where |
|---|---|---|
| 22 JSON and JSONL loaders with limits | Strict UTF-8; BOM accepted; CRLF accepted; line, size, nesting, case-count, and string limits; NaN and Infinity rejected; duplicate object keys rejected | `src/evalforge/datasets.py` |
| 23 Validator collecting up to 100 errors | Errors carry file, line (JSONL) or element index (JSON array), and field; collection stops at the cap | `datasets.py` |
| 24 Duplicate-ID detection | Case-sensitive; the error names both locations | `datasets.py` |
| 25 Synthetic fixture corpus | `tests/fixtures/datasets/` (synthetic, labelled in its README) | fixtures |

Acceptance criteria (PRD §18, PRD-F-001 to PRD-F-004): met by `tests/test_datasets.py`.
PRD-F-004 "no expected accepted" is met here; the `NO_EXPECTED` skip behaviour belongs to Milestone 5.

## Requirements covered by tests

TST-DS-001 to TST-DS-019 (all listed in TEST_STRATEGY §4.1, with the variations below), TST-MF-001 to TST-MF-004,
TST-MF-008 (non-finite numbers), TST-SEC-001 and TST-SEC-002 (hostile payloads loaded as data; process-execution
calls patched to fail), TST-SEC-015 (symbolic link recorded as a warning).

## Deviations and decisions to confirm

1. **TST-DS-012 wording.** The test plan says a zero-byte file is a valid dataset. I applied that to JSONL only. A
   zero-byte `.json` file is invalid, because the format requires a top-level array. Please confirm.
2. **Nesting limit counts the record itself.** The depth check counts the record object, so an `input` can
   nest at most 63 levels inside a record. The limit is a conservative choice (TRD §4.2 says 64 levels).
3. **Duplicate object keys are rejected.** The standard parser keeps the last value silently, which would hide
   mistakes. This goes beyond the TRD text and needs your confirmation.
4. **JSON array errors use an element index** (for example "element 3:"), not a line number, because the standard
   parser does not report positions for each element. PRD-F-002 allows an index for arrays.
5. **Symbolic link warning** is stored in `Dataset.warnings`. The CLI does not display it until Milestone 11.
6. **DatasetLimits** is an explicit argument with the TRD defaults. Tests use small values to check the boundaries.
   The defaults remain proposals until the owner approves them.
7. **Not in this milestone:** the `dataset validate` command (Milestone 11), the `Dataset.from_cases`
   constructor (Milestone 11), and the `NO_EXPECTED` behaviour (Milestone 5).

## Measurement (not a claim against the target)

- Validating 10,000 synthetic JSONL cases (1.26 MB) took 0.164 s on this machine (macOS arm64, Python 3.13), one run.
  The TRD-220 target is 10 s on the CI reference runner, which has not yet been measured.
- The nesting pre-scan is a Python loop over characters, so its cost grows with file size. It has not been
  measured on a 50 MB file.

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 164 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 164 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 164 passed | 0 |
| Dataset tests only | `uv run --locked pytest tests/test_datasets.py` | 48 passed | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed! | 0 |
| Format | `uv run --locked ruff format --check .` | 15 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | Success: no issues found in 15 source files | 0 |

Not run: Linux and Windows; the GitHub Actions workflow.

## Issues found during the milestone

1. **Dataset tests passed on the first run.** I checked that the tests exercise the code: each failure case asserts a
   specific code, line, and field, so a silent pass would not match.
2. **Unused helper removed** from the test file.

## Requested approval

Approve Milestone 3 as complete. Confirm deviations 1 to 3 above.
