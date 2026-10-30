# Python API Reference

Status: **Pre-alpha. Names and signatures below were read from the installed package. The design is in
[API_DESIGN](API_DESIGN.md); where this reference and the design differ, this reference describes the code.**

```python
import evalforge
```

Everything listed here is in `evalforge.__all__`, and a test checks that (`tests/test_api.py`).

## Datasets

```python
Dataset.load(path) -> Dataset                       # JSON or JSONL; raises DatasetValidationError
Dataset.from_cases(cases, *, source_label="") -> Dataset
validate_dataset(path) -> Dataset
```

`Dataset` has `format`, `sha256`, `canonical_sha256`, `cases`, `source_label`, `warnings` and `case_count`.
`Dataset.from_cases` applies the same ID rules and limits as file loading. Its `sha256` is the canonical hash,
because there is no raw file (API_DESIGN §3).

`Case(id, input, expected=ABSENT, metadata={}, tags=())` validates its fields on construction.

## Targets

```python
Target.from_callable(func, *, name=None, timeout_seconds=None)
Target.from_reference("module:attribute", *, name=None, timeout_seconds=None)
```

A target is any object with a `name` and a call taking the case input. `timeout_seconds` overrides the run's timeout
for that target. Timeouts are best-effort: a timed-out call is not stopped (RR-02). **Targets are trusted code.**
`from_reference` imports the module, which runs its top-level code.

## Evaluators

Built-in: `ExactMatch`, `NormalizedText`, `JsonStructure`, `RequiredFields`, `RuleBased`, `Latency`. Each takes a
`name` and its options (see `docs/DATA_MODELS.md` §4).

```python
CustomEvaluator.from_reference("module:Class", name="domain_rule")   # trusted code
EvaluatorResult.passed(message, details=None, *, name="custom")
EvaluatorResult.fail(reason_code, message, details=None, *, name="custom")
EvaluatorResult.error(reason_code, message, *, name="custom")
EvaluatorResult.inconclusive(reason_code, message, *, name="custom")
EvaluatorResult.skipped(reason_code, message, *, name="custom")
```

The factories' `name` is replaced by the configured name when the custom evaluator is loaded. Reason codes must be
registered (`evalforge.errors.REASON_CODES`).

## Running

```python
suite = Suite(evaluators, *, timeout_seconds=30.0, grace_seconds=5.0, io_mode="full", redaction=True)
run = suite.run(dataset, target, *, run_root=None, case_ids=None, tags=None) -> Run
```

- Without `run_root` the run stays in memory. An in-memory run has `path is None` and cannot be compared from disk.
- With `run_root` the run is stored in a new directory under that root.
- `case_ids` and `tags` cannot be combined. Unknown IDs raise `EvalForgeError` (`USAGE_ERROR`).

```python
run_from_config(path, *, run_root=None, case_ids=None, tags=None, timeout_seconds=None,
                io_mode=None, redaction=None, fail_on=None) -> Run
load_config(path) -> EvalForgeConfig
validate_config(path, *, check_imports=False, check_dataset=False) -> dict
```

`run_from_config` behaves exactly like `evalforge run` (same storage, same exit meaning in `RunResult.fail_on_matches`).

`Run` has `run_id`, `status` (`RunStatus`), `summary` (`RunSummary`: `counts`, `executed`, `pass_rate`), `path`,
and the property `stored` (the stored form; raises `RUN_NOT_FOUND` for an in-memory run).

## Comparing

```python
compare(baseline, candidate, *, run_root=None, allow_dataset_change=False,
        allow_evaluator_change=False, strict=False, thresholds=...) -> Comparison
```

`baseline` and `candidate` are `Run` objects, run IDs, or run directory paths. `Comparison.exit_status` is `"pass"`,
`"regression"` or `"refused"`. `Comparison.to_dict()` is the JSON form in DATA_MODELS §11.

`thresholds` takes a `Thresholds` (the `[regression]` settings; `Thresholds` is `RegressionSettings`). The default is the
TRD §9.1 proposed set, pending OD-08.

`RegressionFinding` is the finding type (`code`, `severity`, `message`, `case_ids`, `threshold`, `metric`, `values`).

## Command-line equivalents

| Python | Command line |
|---|---|
| `validate_config(path)` | `evalforge config validate PATH` |
| `validate_dataset(path)` | `evalforge dataset validate PATH` |
| `run_from_config(path)` | `evalforge run --config PATH` |
| `inspect_run(ref, root)`, `inspect_document(...)` | `evalforge inspect REF` |
| `compare(...)`, `compare_stored(...)` | `evalforge compare BASE CAND` |
| `export_bytes(source, ...)`, `write_new(path, data)` | `evalforge report export SOURCE --out PATH` |

The two interfaces call the same operations, so their results agree (`tests/test_api.py`).

## Errors

Every error is an `EvalForgeError` with a `code` from the registry (`evalforge.errors.ERROR_CODES`), a `message`, and
`errors` (a tuple of `ErrorInfo`, for validation problems). The code maps to the command-line exit status.

## Stability

Pre-alpha. Names and behaviour may change before 1.0 (TRD-242). Changes are listed in `CHANGELOG.md`.
