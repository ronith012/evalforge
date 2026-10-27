# Milestone 2 Completion Record — Data models and validation

Status: **Approved by the owner on 2026-10-27, with the deviations below accepted.** Implemented and checked locally on macOS.

Accepted: (1) the dataset, manifest, summary, comparison, and finding models are built in Milestones 3, 7, 9, and 10; (2) serialisation moves to Milestone 7; (3) `io_mode = "full"` is the development default (OD-12 remains open for the final decision).
Date of checks: 2026-10-27. Python 3.11.0, 3.12.13, 3.13.5 (macOS, arm64).

## Scope delivered

| Plan item | Delivered | Where |
|---|---|---|
| 15 Frozen dataclasses | Case, ErrorObject, TargetResult, EvaluatorResult, CaseResult, and configuration dataclasses | `models.py`, `config.py` |
| 16 Validation functions | Validation on construction for every model; `ValidationError` names the field | `models.py`, `config.py` |
| 17 Canonical JSON and SHA-256 | NFC normalisation, sorted keys, finite numbers only, integer/float distinction, depth and size limits | `canon.py` |
| 18 Reason-code and error registries | 24 reason codes with statuses, 20 error codes with exit codes, 14 finding codes | `errors.py` |
| 19 Configuration validation | TOML loading via `tomllib`; unknown-key and override-key rejection; per-evaluator parameter checks; collected errors capped at 100 | `config.py` |
| 20 Limit constants | Values from TRD §4.2 and DATA_MODELS §4.1 | `limits.py` |
| 21 Hand-written canonical hash vectors | Literal canonical text; SHA-256 reference computed with `shasum -a 256`, outside the code | `tests/test_canon.py` |

## Scope not delivered (deviations)

1. **Dataset fingerprint, run manifest, run summary, comparison, and regression finding models** are not implemented. They depend on Milestone 3 (dataset), 7 (persistence and summary), 9 (comparison), and 10 (findings). The plan's objective said "define all models in DATA_MODELS". I have implemented the models needed now and deferred the rest to the milestone that uses them. **Needs your approval.**
2. **JSON serialisation and deserialisation** of records is not implemented. It belongs with persistence in Milestone 7.
3. **Round-trip of DATA_MODELS examples** is checked by construction, not by serialise-and-compare, because serialisation is deferred. The FAIL and TIMEOUT examples are accepted (`tests/test_models.py`). Their hashes are abbreviated in the document, so full-length placeholders are used.

## Pulled forward from Milestone 6

- `aggregate_case_status` (EVALUATION_METHODOLOGY §3.3) is implemented in M2, because `CaseResult` must reject any status that contradicts its evaluators. The ten-row table (T1–T10) is tested. Milestone 6 still owns the runner that calls it.

## Defaults applied (open decisions, recommended values)

- `io_mode = "full"` (OD-12 is open; recommended default applied). **Please confirm.**
- `redaction = true`; `timeout_seconds = 30.0`; regression defaults from OD-08 (`max_newly_failing = 0`, `max_pass_rate_drop = 0.0`, `min_executed_for_rate_check = 30`, `missing_case_policy = "fail"`). OD-08 is open.
- Override keys are rejected in configuration (TRD-136).

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --locked --python 3.11 pytest -q` | 116 passed | 0 |
| Tests, Python 3.12 | `uv run --locked --python 3.12 pytest -q` | 116 passed | 0 |
| Tests, Python 3.13 | `uv run --locked --python 3.13 pytest -q` | 116 passed | 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 13 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | Success: no issues in 13 source files | 0 |

Test counts per file: `test_canon.py` 17, `test_config.py` 30, `test_dependencies.py` 4, `test_errors.py` 11, `test_models.py` 52, `test_smoke.py` 2.

Not run: Linux and Windows; the GitHub Actions workflow (not executed; no remote exists).

## Issues found during the milestone

1. **Stale editable install.** Switching interpreters with `uv run --python` recreated `.venv` and left the editable `.pth` unused, so `import evalforge` failed. Fixed by `pythonpath = ["src"]` in pytest configuration, so tests no longer depend on an editable install. `uv run --python` still recreates `.venv` when the interpreter changes.
2. **Overlap of two codes.** `DATASET_CHANGED` and `EVALUATOR_CHANGED` are both error codes and finding codes, as the specification requires. An initial test assumed no overlap; the test was corrected to assert exactly this overlap.
3. **Long lines** in generated messages were wrapped. No behaviour changed.

## Requested approval

Approve Milestone 2 as complete. Decide deviation 1 (remaining models in later milestones), and confirm the default `io_mode = "full"` (OD-12).
