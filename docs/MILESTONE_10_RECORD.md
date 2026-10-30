# Milestone 10 Completion Record — Regression detection

Status: **Implemented and checked locally on macOS. Not committed. Awaiting owner approval.**
Date of checks: 2026-10-27. Python 3.11, 3.12, 3.13 (macOS, arm64).

Authorised by "Proceed" (after Milestone 9 was delivered). OD-08 is not decided. The TRD §9.1 proposed defaults are
applied, as stated below. **Please confirm them.**

## Decisions applied

| ID | Value | Status |
|---|---|---|
| OD-08 | Thresholds from the `[regression]` table. With no configuration: `max_newly_failing = 0`, `max_newly_errored = 0`, `inconclusive_as_regression = false`, `max_pass_rate_drop = 0.0`, `min_executed_for_rate_check = 30`, `max_p95_latency_ratio` disabled, `missing_case_policy = "fail"` (TRD §9.1). | Proposed defaults applied. **Please confirm.** |
| Finding messages | Fixed templates, pluralised to match DATA_MODELS §12 examples (e.g. "1 case that passed in the baseline now fails"). | Applied; golden tests pin them. |
| Exit status | `refused` if refused; `regression` if any finding has severity `error`; otherwise `pass`. | Matches DATA_MODELS §11. No data-model amendment was needed; the values were already listed there. |

## Scope delivered (IMPLEMENTATION_PLAN §8.7; TRD §9; EVALUATION_METHODOLOGY §6)

| Item | Delivered | Where |
|---|---|---|
| Finding model | `Finding` now carries `case_ids`, `threshold`, `metric`, `values` (DATA_MODELS §12) | `src/evalforge/regression.py` |
| Case-level findings | `CASE_REGRESSED_TO_FAIL`, `CASE_REGRESSED_TO_ERROR`, `CASE_REGRESSED_TO_INCONCLUSIVE` (error or warning form), `CASE_MISSING_IN_CANDIDATE` (per policy), `CASE_NEW_IN_CANDIDATE`, `CASE_RECOVERED` | `regression.py` |
| Rate findings | `PASS_RATE_DROP` (strictly greater than the maximum), `RATE_CHECK_SKIPPED` (below the minimum or no executed cases) | `regression.py` |
| Latency finding | `LATENCY_P95_INCREASE` when `max_p95_latency_ratio` is set; `RATE_CHECK_SKIPPED` when a p95 is missing or the baseline p95 is zero | `regression.py` |
| Comparison | Thresholds parameter on `compare_runs`; regression findings appended; `exit_status` derived | `src/evalforge/compare.py` |
| Warnings list | `compatibility.warnings` now lists only warning-severity codes, so error findings are not listed as warnings | `compare.py` |

## Requirements covered by tests

`tests/test_regression.py` (15 tests) and the existing `tests/test_compare.py` (22 tests):

- TST-CM-002: a run compared with itself has no error findings, and `exit_status` is `pass`.
- TST-CM-009: missing-case policy `fail` gives an error, `warn` gives a warning, `ignore` gives nothing.
- TST-CM-010: a drop equal to `max_pass_rate_drop` is not a finding; a drop above it is.
- TST-CM-011: newly failing cases above the count are listed sorted by case ID, with the threshold recorded.
- TST-CM-012: a PASS to ERROR change is `CASE_REGRESSED_TO_ERROR`, never `CASE_REGRESSED_TO_FAIL`.
- TST-CM-013: a rate check below the minimum is skipped with `RATE_CHECK_SKIPPED`; case checks still apply.
- TST-CM-014: latency ratio above the maximum is a finding; at the maximum it is not; a missing or zero baseline p95 is skipped.
- TST-CM-015: golden messages for every case, rate and latency template, with exact severities and order.
- TST-CM-017: zero executed cases report `RATE_CHECK_SKIPPED` without crashing.

## Changes to existing tests

Milestone 10 changes behaviour that earlier tests asserted. The changed assertions are:

- `tests/test_compare.py`: three `exit_status == "compared"` assertions became `"regression"` (a run with regressions)
  or `"pass"`. The evaluator-override test asserts `in {"pass", "regression"}`, because its `Latency` evaluator
  depends on machine speed and the test is about the override, not the latency verdict.
- Three findings assertions now include `RATE_CHECK_SKIPPED`. Four executed cases are below the default minimum of 30
  (TRD-142), so the warning is correct behaviour, not noise.

## Deviations from the plan and the specification

1. **Module location.** The plan named `regression/detector.py`. The code is in `src/evalforge/regression.py`, which
   matches the flat layout already used for `compare.py` and `reader.py`.
2. **Infrastructure reason codes are not in findings.** TRD §9.2 says infrastructure ERROR findings carry their reason
   codes in `details`. The comparison does not yet carry the per-case reason, so `CASE_REGRESSED_TO_ERROR` names the
   case but not the reason (e.g. `TARGET_EXCEPTION`). The rule that matters for correctness is met: such a case is
   never `CASE_REGRESSED_TO_FAIL`. Adding the reason needs a field on `CaseComparison`; it is not implemented here.
3. **Threshold defaults are defined twice.** `DEFAULT_THRESHOLDS` in `regression.py` repeats the defaults of
   `_regression` in `config.py`. Both follow TRD §9.1. A single source would be cleaner; this is left for review.
4. **`PASS_RATE_DROP` boundary arithmetic.** The drop is rounded to 12 decimal places before comparison, so a drop
   exactly equal to the limit is not reported because of binary floating-point error.

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, default interpreter | `uv run pytest -q` | 404 passed | 0 |
| Tests, Python 3.11 | `uv run --python 3.11 pytest -q` | 404 passed | 0 |
| Tests, Python 3.12 | `uv run --python 3.12 pytest -q` | 404 passed | 0 |
| Tests, Python 3.13 | `uv run --python 3.13 pytest -q` | 404 passed | 0 |
| Lint | `uv run ruff check src tests` | All checks passed! | 0 |
| Format | `uv run ruff format --check src tests` | 50 files already formatted | 0 |
| Type check | `uv run mypy` (strict in `pyproject.toml`) | Success: no issues found in 50 source files | 0 |

The count of 404 is the Milestone 9 total of 389 plus 15 new regression tests. The lock file was not re-verified in
this run (`--locked` was not used).

Not run: Linux, Windows, and CI.

## Defects found and fixed during the milestone

1. Floating-point boundary: `0.75 - 0.5` was compared without rounding, so an exact-limit test was at risk. Fixed by
   rounding to 12 decimal places before comparison.
2. Message templates used "case(s)". Changed to grammatical singular and plural forms to match the DATA_MODELS §12 example.
3. Several lines exceeded 100 characters (lint). Wrapped; message text unchanged except for item 2.

## Requested approval

Approve Milestone 10. Confirm the OD-08 defaults. Decide whether the infrastructure reason codes (deviation 2) are
required before Milestone 11, or deferred with a recorded decision.
