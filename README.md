# EvalForge

[![CI](https://github.com/ronith012/evalforge/actions/workflows/ci.yml/badge.svg)](https://github.com/ronith012/evalforge/actions/workflows/ci.yml)
[![Licence: Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-blue.svg)](LICENSE)
![Python 3.11 | 3.12 | 3.13](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-informational.svg)
![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)

**EvalForge** runs a Python function (the *target*) over a set of cases, checks each output with evaluators, stores the
run on disk, and compares runs to find regressions. It is local-first, has **no third-party runtime dependencies**, and
makes **no network calls**.

> EvalForge reports the results of the configured evaluators on the cases you provide. These results do not establish that a system is safe, correct, or reliable in general.

## Why EvalForge

- **Reproducible runs.** Every run has an ID, a manifest, dataset and evaluator fingerprints, and integrity hashes.
- **Safe comparisons.** Incompatible runs are refused by default. Overrides are explicit, recorded, and shown.
- **Honest statuses.** Failures, errors, skipped cases, and inconclusive results are separate. Infrastructure errors are
  never reported as regressions.
- **Plain Python.** Targets and evaluators are ordinary Python callables or classes. Datasets are JSON or JSONL.
- **Scriptable.** A command line with documented exit codes for CI, and a Python API with the same behaviour.

## Quick start

Requirements: Python 3.11, 3.12 or 3.13, and [uv](https://docs.astral.sh/uv/) for development.

```sh
git clone https://github.com/ronith012/evalforge.git
cd evalforge/examples/quickstart        # synthetic example; copy the folder elsewhere before running in place
uv run --project ../.. evalforge config validate
uv run --project ../.. evalforge dataset validate dataset.jsonl
uv run --project ../.. evalforge run
uv run --project ../.. evalforge run --format json     # a second run to compare against
uv run --project ../.. evalforge compare <baseline-run-id> <candidate-run-id>
```

Run IDs are printed by `run`. Runs are stored under `.evalforge/runs` next to the configuration.

## Command line

| Command | Purpose | Exit codes |
|---|---|---|
| `evalforge config validate` | Check a configuration file. Imports your code only with `--check-imports`. | 0, 2, 3 |
| `evalforge dataset validate PATH` | Check a `.json` or `.jsonl` dataset. | 0, 3 |
| `evalforge run` | Run the target and store the run. `--fail-on` makes chosen statuses fail the job. | 0, 1, 2, 3, 4 |
| `evalforge inspect RUN` | Show a stored run, its cases, or one case. | 0, 2, 4 |
| `evalforge compare BASE CAND` | Compare two runs. | 0 no error findings, 1 regression, 5 refused |
| `evalforge report export SOURCE --out PATH` | Write a report. Case inputs and outputs are excluded unless `--include-io`. | 0, 2, 4 |

Full reference: [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md).

## Python API

```python
from evalforge import Dataset, ExactMatch, Suite, Target, compare

dataset = Dataset.load("dataset.jsonl")
suite = Suite([ExactMatch(name="exact")])
baseline = suite.run(dataset, Target.from_callable(my_function), run_root=".evalforge/runs")
candidate = suite.run(dataset, Target.from_callable(my_new_function), run_root=".evalforge/runs")
result = compare(baseline, candidate)
print(result.exit_status)        # "pass", "regression", or "refused"
```

Full reference: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

## Architecture at a glance

```
dataset ──► runner ──► evaluators ──► case results ──► run directory (manifest, cases.jsonl, summary.json)
                                                              │
                                  inspect / report export ◄───┤
                                                              ▼
                                       compare ──► categories, metrics, regression findings
```

- **Datasets** are validated before anything runs. Limits apply to size, lines, cases, nesting, and strings.
- **The runner** calls each target under a best-effort timeout, then applies each evaluator to the output.
- **Storage** writes atomically, holds a lock file while a run is written, and records SHA-256 hashes of the case and
  summary files.
- **Comparison** refuses runs whose dataset or evaluators differ, unless you pass an explicit override.

Design, requirements, and decisions are in [`docs/`](docs/), starting with [`docs/PRD.md`](docs/PRD.md) and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Limits

- **Targets and custom evaluators are trusted code.** EvalForge imports and runs them with your privileges. Do not
  evaluate code you do not trust.
- **Timeouts are best-effort.** A timed-out target is recorded as an error, but the call is not stopped.
- **Redaction is heuristic.** It removes common credential formats. It does not guarantee that sensitive text is removed.
- **Artifacts can be changed** by anyone who can write to them. The hashes detect accidental or careless changes only.
- **Regular expressions can be slow.** Nested repeats are refused; other slow patterns are not detected.

Full details: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), [`docs/SECURITY.md`](docs/SECURITY.md),
[`docs/RESIDUAL_RISK_ACCEPTANCE.md`](docs/RESIDUAL_RISK_ACCEPTANCE.md). To report a vulnerability, see
[`SECURITY.md`](SECURITY.md).

## Status

| Area | State |
|---|---|
| Core library, CLI and Python API | Implemented; tested locally on macOS (Python 3.11 to 3.13) |
| Continuous integration | Linux, macOS and Windows test matrix, lint, type check, audit, build, secret scan |
| Requirements traceability | Register in [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md); open items are listed there |
| Release | **Not published.** The distribution name is undecided (see below) |

Known gaps are listed in [`CHANGELOG.md`](CHANGELOG.md) and in the milestone records under [`docs/`](docs/).

## Name

"EvalForge" is a provisional name. The name `evalforge` is already used on PyPI, so this project cannot be published
under it yet. See [`docs/TOOLING_VERIFICATION.md`](docs/TOOLING_VERIFICATION.md).

## Development

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict
```

Contributions are welcome once the process is in place. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first: it covers the
spec-first workflow, the Developer Certificate of Origin sign-off, and the code of conduct
([`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)).

## Documentation

| Document | Purpose |
|---|---|
| [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md) | Commands, options, exit codes |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Public Python names and signatures |
| [`docs/DATA_MODELS.md`](docs/DATA_MODELS.md) | Run, manifest, comparison, and report formats |
| [`docs/EVALUATION_METHODOLOGY.md`](docs/EVALUATION_METHODOLOGY.md) | Statuses, aggregation, and interpretation limits |
| [`docs/ARTIFACT_INTEGRITY.md`](docs/ARTIFACT_INTEGRITY.md) | What the hashes cover and do not cover |
| [`docs/SECURITY_VERIFICATION_MATRIX.md`](docs/SECURITY_VERIFICATION_MATRIX.md) | Threats mapped to tests |
| [`CHANGELOG.md`](CHANGELOG.md) | Notable changes |

## Licence

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
