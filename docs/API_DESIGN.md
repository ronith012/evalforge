# EvalForge — Python API Design

Status: **Proposed. All code is illustrative and not implemented or tested.**

The API exposes the same operations as the CLI (PRD-F-027). Concepts, names, and
outcomes must match [CLI_SPECIFICATION](CLI_SPECIFICATION.md) and
[DATA_MODELS](DATA_MODELS.md). Requirements: TRD §11.

---

## 1. Design principles

1. **Same concepts as the CLI.** A dataset, a target, evaluators, a run, a comparison,
   thresholds, and findings mean the same thing in both interfaces.
2. **Errors are exceptions; outcomes are values.** Invalid input and infrastructure
   faults raise `EvalForgeError` subclasses. Case failures, errors, and regressions are
   returned as data, not raised.
3. **Immutable results.** Returned objects are frozen.
4. **No hidden I/O.** Persistence happens only when a run root is given (or defaulted by
   the CLI). The API never writes to the working directory silently.
5. **Explicit trust.** Passing a Python object as target or evaluator means the caller
   provides trusted code by definition. String references (`module:attribute`) are
   resolved only when the caller passes them.

## 2. Public names

Exported from `evalforge` (listed in `__all__`, TRD-170):

| Name | Kind | Purpose |
|---|---|---|
| `Dataset` | class | Loaded, validated set of cases with fingerprints |
| `Case` | class | One case |
| `Suite` | class | Evaluators, timeouts, and run settings; executes against a dataset |
| `Run` | class | Handle to a run (in memory or on disk) |
| `RunSummary` | class | Aggregates (DATA_MODELS §10) |
| `Comparison` | class | Result of comparing two runs |
| `RegressionFinding` | class | One finding |
| `Thresholds` | class | Regression thresholds (same keys as `[regression]`) |
| `Status` | enum | PASS, FAIL, ERROR, SKIPPED, INCONCLUSIVE |
| `ExactMatch`, `NormalizedText`, `JsonStructure`, `RequiredFields`, `RuleBased`, `Latency` | classes | Built-in evaluators |
| `Evaluator` | Protocol | Interface for custom evaluators |
| `Target` | Protocol | Interface for custom targets |
| `EvaluatorResult` | class | Returned by evaluators |
| `load_config`, `run_from_config`, `compare` | functions | Config-driven convenience and comparison |
| `EvalForgeError` and subclasses | exceptions | See §9 |

Anything not listed is private, including `evalforge._internal`.

## 3. Creating a dataset

```python
import evalforge as ef

dataset = ef.Dataset.load("datasets/support.jsonl")   # validates; raises DatasetValidationError

print(dataset.case_count)          # 5
print(dataset.sha256)              # "sha256:4f1c…"
print(dataset.canonical_sha256)    # "sha256:9ab2…"

for case in dataset.cases:         # tuple[Case, ...] in file order
    print(case.id, case.tags)
```

Construction from memory (for tests and generated data):

```python
dataset = ef.Dataset.from_cases(
    [
        ef.Case(id="greet-001", input={"message": "hi"}, expected={"reply": "hello"}, tags=("smoke",)),
    ],
    source_label="inline-test",          # recorded; not a path
)
```

`from_cases` applies the same validation rules as file loading (duplicate IDs, ID pattern,
limits, JSON-safety of values). Its `sha256` is the hash of the canonical serialization,
since there is no raw file; this is documented and differs from file-based hashes.

Validation errors:

```python
try:
    ef.Dataset.load("datasets/broken.jsonl")
except ef.DatasetValidationError as err:
    for e in err.errors:           # tuple[ErrorInfo, ...], up to 100
        print(e.code, e.line, e.field, e.message)
```

## 4. Registering a target

A target is any callable that accepts the case input (a JSON value) and returns a JSON
value, or an object implementing `Target` (TRD-060).

```python
def answer(case_input: dict) -> dict:
    return {"answer": my_app.respond(case_input["question"])}

# Plain callable; name derived from qualname unless given
suite_target = ef.Target.from_callable(answer, name="support-bot-v2")
```

Class-based target:

```python
class SupportBot:
    name = "support-bot-v2"

    def __call__(self, case_input: dict) -> dict:
        return {"answer": self.model.respond(case_input["question"])}

target = SupportBot()
```

Target from configuration string (trusted; imports the module):

```python
target = ef.Target.from_reference("examples.support_bot:answer", name="support-bot-v2")
```

Timeout per target: `ef.Target.from_callable(answer, name=..., timeout_seconds=10)` overrides the suite default (TRD-070). Timeouts are best-effort: a timed-out call may keep running in its thread (TRD-071, TRD-072). Targets are trusted code (TRD-076).

Mutation safety: the runner passes a deep copy of the input (TRD-064), so a target that
mutates its argument does not affect the stored case.

## 5. Registering evaluators

Built-in evaluators take keyword arguments matching DATA_MODELS §4.1:

```python
evaluators = [
    ef.ExactMatch(name="exact"),
    ef.RequiredFields(name="has_answer", paths=["answer"]),
    ef.NormalizedText(name="text_norm", casefold=True, collapse_whitespace=True),
    ef.RuleBased(name="no_placeholder", not_contains=["TODO", "lorem ipsum"], max_length=2000),
    ef.Latency(name="fast_enough", max_ms=2000),
]
```

Custom evaluator (trusted code, TRD-080):

```python
class RefundRule:
    name = "domain_rule"
    version = "1.0"
    requires_expected = False

    def evaluate(self, case: ef.Case, output: object, duration_ms: float) -> ef.EvaluatorResult:
        if not isinstance(output, dict) or "answer" not in output:
            return ef.EvaluatorResult.fail("REQUIRED_FIELD_MISSING", "No answer field.")
        if "45 days" in output["answer"]:
            return ef.EvaluatorResult.fail("CUSTOM_FAIL", "Refund window stated as 45 days.")
        return ef.EvaluatorResult.passed("Refund window statement acceptable.")
```

Result constructors (proposed):

| Constructor | Status | Score |
|---|---|---|
| `EvaluatorResult.passed(message, details=None)` | PASS | 1.0 |
| `EvaluatorResult.fail(reason_code, message, details=None)` | FAIL | 0.0 |
| `EvaluatorResult.error(reason_code, message)` | ERROR | null |
| `EvaluatorResult.inconclusive(reason_code, message)` | INCONCLUSIVE | null |
| `EvaluatorResult.skipped(reason_code, message)` | SKIPPED | null |

Invalid returns (wrong type, unknown status, message over 500 characters) become
`EVALUATOR_RESULT_INVALID` (TRD-084).

Custom evaluator registered from configuration string (trusted):

```python
custom = ef.CustomEvaluator.from_reference("evalforge_checks.domain:RefundRule", name="domain_rule")
```

Fingerprint of custom evaluators includes the defining file's hash (TRD-085). Calling
`from_reference` with a module that cannot be found raises `TargetLoadError` (named
for both targets and evaluators; see §9).

## 6. Running an evaluation

```python
suite = ef.Suite(
    evaluators=evaluators,
    timeout_seconds=30.0,
    io_mode="full",           # "full" | "hashes" | "none" (DATA_HANDLING §3)
    redaction=True,           # DATA_HANDLING §7; False is recorded in the run
)

run = suite.run(
    dataset,
    target=target,
    run_root=".evalforge/runs",   # None → in-memory run; cannot be compared from disk
    case_ids=None,                # or ["refund-001", ...]
    tags=None,                    # or ["smoke"]; mutually exclusive with case_ids
)

print(run.run_id)                 # UUIDv4
print(run.status)                 # "COMPLETED"
print(run.summary.counts)         # {"PASS": 3, "FAIL": 1, "ERROR": 1, "SKIPPED": 0, "INCONCLUSIVE": 0}
print(run.summary.pass_rate)      # 0.6
print(run.path)                   # ".evalforge/runs/3f2b8c1e-…"  (None if in-memory)
```

Iterating case results:

```python
for result in run.cases():        # streams from disk when persisted; from memory otherwise
    if result.status is ef.Status.FAIL:
        print(result.case_id, result.status_reason)
```

Case results are the source of truth; `run.summary` is derived from them (DATA_MODELS §10
invariant).

Case results returned by `run.cases()` include `input`, `expected`, and `output` only when `io_mode` is `"full"`. Stored values are redacted if redaction is enabled.

Interrupts: `suite.run` propagates `KeyboardInterrupt` after finalizing the run as
`ABORTED` (TRD-103). The returned value is not produced in that case; the caller can
load the partial run with `ef.Run.load(path)`, whose status is `ABORTED`.

## 7. Loading and inspecting stored runs

```python
run = ef.Run.load(".evalforge/runs/3f2b8c1e-5a7d-4e9b-9c2a-1d0f6e7b8a90")
run.status                 # "COMPLETED"
run.integrity_ok           # True (cases_sha256 and summary_sha256 match; ARTIFACT_INTEGRITY §4)
run.summary.counts
case = run.case("refund-001")
case.evaluators            # tuple[EvaluatorResult, ...]
```

`Run.load` raises `RunNotFoundError`, `StorageError`, `IntegrityError`, or
`SchemaVersionError` (§9). It does not raise for `RUNNING` or `ABORTED` status; those are
exposed as `run.status`.

## 8. Comparing runs and detecting regressions

```python
thresholds = ef.Thresholds(
    max_newly_failing=0,
    max_newly_errored=0,
    max_pass_rate_drop=0.05,
    min_executed_for_rate_check=30,
    missing_case_policy="fail",
)

comparison = ef.compare(
    baseline=".evalforge/runs/2b7a9e10-…",     # path or Run object
    candidate=run,                             # Run object or path
    thresholds=thresholds,
    allow_dataset_change=False,
    allow_evaluator_change=False,
    strict=False,                      # True: any override becomes a refusal (TRD-138)
)

comparison.exit_status        # "pass" | "regression" | "refused"
for finding in comparison.findings:
    print(finding.severity, finding.code, finding.message)

comparison.counts             # {"regressed": 1, "recovered": 0, "unchanged": 3, ...}
comparison.compatibility      # Compatibility object: dataset, evaluators, allowed, warnings, refusals
comparison.to_json_dict()     # DATA_MODELS §11 form
```

Equivalent CLI: `evalforge compare <baseline> <candidate> --config evalforge.toml` (CLI §3.5).

Refusals are data, not exceptions:

```python
if comparison.exit_status == "refused":
    for refusal in comparison.compatibility.refusals:
        print(refusal.code, refusal.message)
```

This matches the CLI, which exits 5 in the same situation (CLI §1.4).

Exit code mapping for scripts (convenience, proposed):

```python
comparison.to_exit_code()   # 0, 1, or 5 — same mapping as the CLI for compare
```

## 9. Exceptions

All derive from `EvalForgeError` (TRD-173). Each carries `code` (DATA_MODELS §9) and
`message`.

| Exception | Raised when | CLI exit |
|---|---|---|
| `ConfigError` | Invalid configuration object or file | 2 |
| `DatasetValidationError` | Dataset invalid; carries `errors` tuple | 3 |
| `TargetLoadError` | Target or custom evaluator reference cannot be imported | 2 |
| `RunNotFoundError` | Run reference unknown or ambiguous | 2 |
| `StorageError` | Write, read, lock failure | 4 |
| `IntegrityError` | Stored hashes do not match | 4 |
| `SchemaVersionError` | Unsupported artifact major version | 4 |
| `EngineError` | Unexpected engine fault | 4 |

Not raised for: case errors, case failures, regressions, refusals (returned as data),
or aborted runs (status field).

## 10. Exporting results

```python
comparison.write_json("reports/comparison.json")       # refuses to overwrite (CLI §3.5 rule)
run.write_report("reports/run.json", include_io=False) # JSON report (DATA_MODELS §10)
print(run.to_text())                                   # sanitized text summary
```

Export methods never include case inputs or outputs unless `include_io=True`
(SECURITY §5). `write_*` methods do not create parent directories.

## 11. Config-driven convenience

```python
config = ef.load_config("evalforge.toml")         # validates; does not import target
run = ef.run_from_config(config)                  # same behaviour as `evalforge run`
```

`run_from_config` must produce the same result as the CLI for the same configuration
(TRD-174). This is verified by a parity test (TEST_STRATEGY §4.9).

## 12. Consistency with the CLI

| Concept | CLI | API |
|---|---|---|
| Config | `evalforge.toml` | `load_config` → `EvalForgeConfig` |
| Dataset validation | `dataset validate` | `Dataset.load` |
| Run | `run` | `Suite.run` / `run_from_config` |
| Inspect | `inspect` | `Run.load`, `run.case(...)` |
| Compare | `compare` | `compare` |
| Regression thresholds | `[regression]` | `Thresholds` |
| Export | `report export` | `write_json`, `write_report` |
| Exit codes | §1.4 of CLI spec | `to_exit_code()`, error classes |

## 13. Stability

- Public names and signatures are provisional until 1.0 (TRD-242).
- Override arguments (`allow_dataset_change`, `allow_evaluator_change`, `strict`) are explicit keyword arguments only. There is no way to set them through `load_config` (TRD-136).
- Keyword-only arguments are used for all optional parameters.
- Return types are frozen dataclasses; field additions are minor
  changes (DATA_MODELS §13).

## 14. Examples are tests

Every code block in this document that is marked as runnable must be executed by the
test suite once the API is implemented (PRD-NF-010). Until then, all blocks here are
design illustrations.
