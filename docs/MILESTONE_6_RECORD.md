# Milestone 6 Completion Record — Evaluation runner

Status: **Approved by the owner.** Implemented and checked locally on macOS. Not committed.

Approved with: D-11 (`NOT_RUN` target status) and the interruption decision (grace period applies only while waiting on the target; an interruption during an evaluator drops the case). DATA_MODELS §7 is updated to match (authorised).
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

Milestone 5 was approved by "proceed" on 2026-10-27, with decisions D-5 and D-7 to D-10 as implemented.

## Scope delivered (EXECUTION_PLAN §3)

| Item | Delivered | Where |
|---|---|---|
| Sequential loop in dataset order | `run_cases`: one target call per selected case, in order | `src/evalforge/runner.py` |
| Per-case pipeline | Target call, output check, every evaluator through `apply_evaluator`, aggregation through `aggregate_case_status` | `runner.py` |
| Best-effort timeouts | Daemon worker thread per call; `TARGET_TIMEOUT` with duration equal to the timeout; `threads_possibly_running` counts timed-out threads still alive at the end of the run | `src/evalforge/timeouts.py`, `runner.py` |
| Interruption | `KeyboardInterrupt`: the current case gets the grace period; if it finishes it is recorded, then the run stops as `ABORTED`. If it does not finish it is dropped. | `runner.py` |
| Engine boundary | Any other exception stops the run as `FAILED` with `ENGINE_ERROR`; only the exception type is recorded | `runner.py` |
| Selection (D-6) | `--case` and `--tag` style options; excluded cases are listed as SKIPPED `USER_FILTER` | `runner.py` |
| In-memory run object | `RunOutcome` with case results, counts, and the threads count | `runner.py` |

## Model amendment (decision D-11, needs approval)

To list an excluded case (D-6) without calling the target, the target result needs a status that says "not run".
I added `NOT_RUN` to `TargetResult` with these rules:

- no error code, no error object, and a duration of zero;
- no evaluator results;
- aggregation gives SKIPPED with reason `USER_FILTER`.

DATA_MODELS §7 is now updated to show `NOT_RUN` (done after approval).

## Requirements covered by tests (`tests/test_runner.py`, 22 tests)

- TST-TG-001 (one call per case, in order)
- TST-TG-004 (timeout recorded, duration equal to the timeout, run continues)
- TST-TG-009 (timed-out thread counted; finished threads not counted)
- TST-TG-012 (interruption: grace completes and the case is recorded; grace fails and the case is dropped)
- Status rules through the runner: pass, fail, NO_EXPECTED, target exception with TARGET_ERROR skips, NO_EVALUATORS,
  evaluator precedence
- Engine fault: run is FAILED, cases before the fault are kept, error is recorded without detail
- Selection: IDs, tags, both refused, unknown IDs refused
- Option validation: zero timeout, timeout above one hour, negative grace
- Repeat runs give the same statuses with different run IDs

Mutation check: removing the abort after a successful grace period fails one test. Setting the timeout duration to
zero fails one test. Both were restored, and the suite passed again.

Flakiness check: the runner tests passed 10 out of 10 repeated runs.

## Decisions to confirm

1. **D-11:** the `NOT_RUN` target status (see above).
2. **Interruption during an evaluator.** A `KeyboardInterrupt` raised while an evaluator is running is not inside the
   target wait, so the grace period does not apply. The case is dropped and the run is `ABORTED`. This is the simpler
   reading, and it is documented here.
3. **Timeouts are not measured by the evaluators.** Evaluators run in the main thread after the target returns, so their
   time is not counted against the timeout.

## Deviations from the plan

- `runner_options.py` was merged into `runner.py`, so there are two modules instead of three.

## Carried-forward obligation: CO-1 (still open)

Target exception text is held in memory, truncated to 500 characters, and is **not redacted**. Nothing is written to disk
in this milestone. Milestone 7 must redact it before the first write (EXECUTION_PLAN §4.3).

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 273 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 273 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 273 passed | 0 |
| Runner tests, repeated | 10 runs of `pytest tests/test_runner.py` | 0 failures | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 29 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | No issues in 29 source files | 0 |

Not run: Linux and Windows; the CI workflow. Timeout tests depend on the wall clock, so they were run on this
machine only.

## Issues found during the milestone

1. **Interruption bug.** When the grace period let the interrupted case finish, the run continued as COMPLETED. Fixed:
   the run now stops as ABORTED after recording that case. A test catches it.
2. **Timeout duration recorded as zero.** Fixed; the duration now equals the timeout. A test catches it.
3. **Fault-injection test used a non-exported name.** Changed to a string-based monkeypatch target.

## Requested approval

Approve Milestone 6. Confirm D-11 (`NOT_RUN`) and the interruption decision (item 2 above). Authorise the DATA_MODELS §7
update for `NOT_RUN`.
