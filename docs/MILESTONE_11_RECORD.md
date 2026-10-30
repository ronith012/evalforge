# Milestone 11 Completion Record — CLI and Python API

Status: **Implemented and checked locally on macOS. Not committed. Awaiting owner approval.**
Date of checks: 2026-10-27. Python 3.11, 3.12, 3.13 (macOS, arm64).

Authorised by "Proceed" (after Milestone 10 was delivered). Milestone 10 approval is still pending, so this
milestone was built on the Milestone 10 code as delivered.

## Decisions applied

| ID | Value applied | Status |
|---|---|---|
| OD-25 | `run` exits 0 on completion; 1 only when `--fail-on` matches; 4 for an aborted or failed run (CLI §3.3) | Applied from the CLI specification. **Please confirm.** |
| OD-26 | `inspect` of an incomplete (`RUNNING`) run exits 0 and reports `incomplete`; `compare` refuses it (exit 5) | Applied from the CLI specification. **Please confirm.** Note that the two OPEN_DECISIONS tables disagree on OD-26 (one says exit 4). |
| Dataset paths | Relative paths in a configuration resolve against the configuration file's directory (TRD-184) | Specified; implemented. |
| Exit codes | Each error code carries its exit status (`ERROR_CODES`). Each command stops at its first fatal condition, so the precedence rule (4, 5, 3, 2, 1, 0) holds by construction. | Implemented. |

## Scope delivered

| Item | Where |
|---|---|
| `config validate` (`--check-imports`, `--check-dataset`) | `api.validate_config`, `cli.py` |
| `dataset validate` | `api.validate_dataset`, `cli.py` |
| `run` (`--config`, `--out`, `--case`, `--tag`, `--timeout`, `--io-mode`, `--no-redaction`, `--fail-on`) | `api.run_configured`, `cli.py` |
| `inspect` (`--case`, `--status`, `--limit`, `--show-io`; run ID prefix; ambiguity listed) | `api.inspect_run`, `api.inspect_document`, `cli.py` |
| `compare` (`--config`, `--allow-*`, `--strict`, `--out`, never overwrites) | `api.compare_stored`, `cli.py` |
| `report export` (run or comparison file; `--include-io`; never overwrites) | `api.export_bytes`, `api.write_new`, `cli.py` |
| Text and JSON output; JSON on stdout only; diagnostics on stderr | `cli.py` |
| Public names listed in `__all__` | `src/evalforge/__init__.py` |
| Console script `evalforge`, and `python -m evalforge` | `pyproject.toml`, `__main__.py` |

## Requirements covered by tests

- `tests/test_cli.py` (34 tests): validation success and failure at each exit code; JSON failures as one document;
  run exit codes (0, 1 with `--fail-on`, 2 for unknown cases and mutually exclusive selection); `--no-redaction`
  recorded and warned; run ID prefix resolution and ambiguity; `inspect` filtering and detail; comparison exit codes
  (0, 1, 5), override display, `--strict`, `--out` never overwriting; report export; an unexpected fault exits 4 with
  no detail (the message text is not printed).
- `tests/test_api.py` (14 tests): parity between the command line and the Python API for dataset, configuration,
  run counts, inspect, compare (after removing `comparison_id` and `created_at`) and export bytes; API-only input
  validation; no execution when the dataset is invalid.
- `tests/test_smoke.py`: `__all__` checked as sorted and containing the public operations. The milestone 1 assertion
  that `__all__ == ["__version__"]` no longer applies, by design.

## Deviations from the plan and the specification

1. **API is a subset of API_DESIGN §2.** Implemented: functions (`validate_config`, `validate_dataset`,
   `run_configured`, `inspect_run`, `inspect_document`, `compare_stored`, `export_bytes`, `write_new`). Not
   implemented: the `Dataset`, `Case`, `Suite`, `Run`, `Thresholds` classes; `Dataset.from_cases`; `Target.from_callable`
   and `Target.from_reference` as methods; `CustomEvaluator.from_reference`. Each of these is listed as deferred;
   none is needed by the CLI.
2. **Progress lines during `run` are not printed.** CLI §3.3 asks for one line per case on a terminal. The runner has no
   progress hook; adding one is a small change. Deferred and recorded here.
3. **Options after the command name only.** The specification lists global options before the command. They are
   accepted after the command name, which is how they are used in practice. `--format json` placed before the
   command is rejected by argparse with exit 2. Documented here; the specification should be read this way.
4. **`--quiet`, `--verbose`, `--no-color`, `--config` on `inspect`.** Not implemented. There is no logging and no
   colour output, so these have no effect yet. Not added as no-op flags.
5. **`report export` of a comparison file** re-emits the file as JSON and refuses `--include-io` and text. The
   specification allows text export of a comparison; that is deferred.
6. **Comparison output names the thresholds used**: `thresholds_source` is added to the JSON
   (`built-in defaults (TRD §9.1 proposed; OD-08)` or the configuration path). It is not part of DATA_MODELS §11 yet;
   the data model should gain this optional field.
7. **Default run root without a configuration.** `inspect`, `compare` and `report export` look in
   `.evalforge/runs` relative to the current directory. `run` uses `run_root` from its configuration (relative to the
   configuration file) unless `--out` or `--run-root` is given.
8. **Unexpected faults** exit 4 with `ENGINE_ERROR`, print the exception type only, and no traceback. This follows the
   runner's rule (TRD-202).

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Tests, Python 3.11 | `uv run --python 3.11 pytest -q` | 452 passed | 0 |
| Tests, Python 3.12 | `uv run --python 3.12 pytest -q` | 452 passed | 0 |
| Tests, Python 3.13 | `uv run --python 3.13 pytest -q` | 452 passed | 0 |
| Lint | `uv run ruff check src tests` | All checks passed! | 0 |
| Format | `uv run ruff format --check src tests` | 58 files already formatted | 0 |
| Type check | `uv run mypy` (strict) | Success: no issues found in 58 source files | 0 |
| Console script | `uv run evalforge --version` | `evalforge 0.0.0.dev0` | 0 |

Not run: Linux, Windows, CI; the `--locked` flag was not used; the test count of 452 is 404 from Milestone 10 plus 48
new tests.

## Defects found and fixed during the milestone

1. A circular import: the package defined `__version__` after importing the CLI, which read it. The version now lives
   in `_version.py`.
2. The run summary printed the inspect case list. It now prints the run summary only.
3. `CaseResult` has no `to_dict`; the serialiser function is used.
4. Test fixtures were imported into test modules, which pytest reports as redefinitions. The fixture moved to a helper
   module registered in `conftest.py`.

## Requested approval

Approve Milestone 11, and confirm OD-25 and OD-26. Decide whether the deferred items in the deviations list (progress
lines, the full API class surface, text export of comparisons) are needed before Milestone 13, or are accepted as
deferred.

## Update 2026-10-30: deferrals built

The owner approved Milestone 11 and asked for the three deferrals before Milestone 13. They are now built:

- **Per-case progress lines.** `run_cases(..., on_case=...)` and `api.run_configured(..., on_progress=...)`. The CLI prints
  one line per case to stderr in text mode on a terminal. Case IDs are sanitised. No inputs or outputs are printed.
- **Full API class surface.** `Suite`, `Run`, `RunSummary`, `Dataset.load`, `Dataset.from_cases`, `Target.from_callable`,
  `Target.from_reference` (with per-target `timeout_seconds`), `EvaluatorResult` factories, `CustomEvaluator.from_reference`,
  `compare`, `load_config`, `run_from_config`, `Thresholds`, `RegressionFinding`. The names are exported and listed in
  API_REFERENCE. Tests: `tests/test_objects.py`.
- **Text export of comparisons.** `reporting/comparison_text.py` renders a comparison document. The CLI and
  `report export` (for comparison files) use it. `tests/test_api.py::test_compare_text_matches_the_shared_renderer`.

The API design's `Target` was a protocol. It is now `TargetProtocol` (the type) and `Target` (the namespace of constructors),
so that classes satisfying the protocol need not provide the constructors.

Test count after the deferrals: 475 (this record's earlier count was 452).

