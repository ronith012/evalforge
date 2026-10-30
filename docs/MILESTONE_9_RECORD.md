# Milestone 9 Completion Record — Run comparison

Status: **Implemented and checked locally on macOS. Not committed. Awaiting owner approval before Milestone 10.**
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

Authorised by "Proceed" (after Milestone 8 approval). OD-09 is confirmed by the owner (refuse by default). OD-13 and
OD-28 were not decided; the recommended values below were applied. **Please confirm them.**

## Decisions applied

| ID | Value | Status |
|---|---|---|
| OD-09 | Refuse by default; explicit flags allow the difference | Confirmed by owner |
| OD-13 | ERROR counts toward the pass-rate denominator. FAIL to ERROR is `changed`, not a regression. | Recommended value applied. **Please confirm.** |
| OD-28 | `strict` is a parameter, default False. The command-line default is decided in Milestone 11. | Recommended value applied. **Please confirm.** |

## Scope delivered (IMPLEMENTATION_PLAN §8.6; EVALUATION_METHODOLOGY §5; TRD §8)

| Item | Delivered | Where |
|---|---|---|
| Compatibility checks | Both runs COMPLETED; dataset canonical hash; evaluator fingerprints; every refusal listed | `src/evalforge/compare.py` |
| Case categories | regressed (with sub-type), recovered, unchanged, changed, missing in candidate, new in candidate, changed_input | `compare.py` |
| Overrides | Recorded only when needed, with the flag and what was observed; banner data; `COMPARISON_OVERRIDDEN` warning | `compare.py` |
| `strict` | Refuses any overridden comparison (exit 5 in Milestone 11) | `compare.py` |
| Metrics | Pass rate, error rate, inconclusive rate, counts, latency p50 and p95, each with a delta | `compare.py` |
| Deterministic output | Cases sorted by code point; only `comparison_id` and `created_at` vary | `compare.py` |
| Warnings | DATASET_CHANGED, EVALUATOR_CHANGED, COMPARISON_OVERRIDDEN, IO_UNAVAILABLE, RAW_BYTES_CHANGED (information) | `compare.py` |

## Requirements covered by tests (`tests/test_compare.py`, 22 tests)

TST-CM-001 (transitions), TST-CM-002 (identical runs, categories only), TST-CM-003 (refusal by default),
TST-CM-004 (allowed change is an override with a warning), TST-CM-005 (evaluator change refused; allowed with flag),
TST-CM-006 (raw bytes change is information only), TST-CM-007 (incomplete run refused), TST-CM-008 (all refusals
listed), TST-CM-016 (deterministic output), TST-CM-017 (no executed cases: no rates), TST-CM-018 (tampered run refused by
the reader), TST-CM-021 (strict refuses overrides). Missing-case policy (TST-CM-009) and regression thresholds
(TST-CM-010 to 015) are Milestone 10. The override-key rejection (TST-CM-022) is covered by the configuration tests.

Fault checks, restored afterwards:
- Never refusing a dataset change fails 2 tests.
- Classifying FAIL to ERROR as a regression fails 1 test.

## Limits and notes

1. **`exit_status` is `refused` or `compared`.** The data model (DATA_MODELS §11) lists `pass`, `regression`, or `refused`.
   The regression verdict is Milestone 10. The data model must be amended then. Not changed in this milestone.
2. **Output-level categories depend on io_mode.** With `io_mode = none`, output changes are unknown (`IO_UNAVAILABLE`).
3. **A case that becomes unknown.** A case that is `changed_input` is not compared on status, by design.
4. **Metrics come from each run's summary.** They are not recomputed from cases.

## Deviations from the plan

- The plan named the comparison as a separate CLI step. The command is Milestone 11; this milestone provides the
  function and its data.
- `--out` (writing the comparison file) is Milestone 11.

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 389 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 389 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 389 passed | 0 |
| Comparison tests | `pytest tests/test_compare.py` | 22 passed | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 48 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | No issues in 48 source files | 0 |

Not run: Linux, Windows, and CI.

## Defects found and fixed

1. Wrong expected pass rates in a metrics test (3 of 4, not 2 of 4). Corrected by hand-deriving the statuses.
2. A changed-input test would have raised an error: the target could not map the changed query back to a case.
   Fixed so unknown queries are treated as having no behaviour setting.
3. One docstring line was too long. Rewrapped.

## Requested approval

Approve Milestone 9. Confirm OD-13 and OD-28 (recommended values applied). Note the `exit_status` amendment due in Milestone 10.
