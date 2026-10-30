# EvalForge

**Status: pre-alpha.** The command line and Python API work for local evaluation runs, comparisons, and
regression findings. Nothing is published. Several decisions and checks are still open (see below).

EvalForge runs a Python function (the *target*) over a dataset of cases, checks each output with evaluators,
stores the run on disk, and compares runs to find regressions. It has no third-party runtime dependencies and
makes no network calls.

**EvalForge reports the results of the configured evaluators on the cases you provide. These results do not establish that a system is safe, correct, or reliable in general.**

## Quick start

Requirements: Python 3.11, 3.12 or 3.13, and [uv](https://docs.astral.sh/uv/) for development.

```sh
cd examples/quickstart          # a synthetic example; copy it somewhere else before running in place
evalforge config validate
evalforge dataset validate dataset.jsonl
evalforge run
evalforge run --format json     # a second run, to compare against
evalforge compare <baseline-run-id> <candidate-run-id>
```

Run IDs are printed by `run`. A run is stored under `.evalforge/runs` next to the configuration.

## Command line

| Command | Purpose |
|---|---|
| `evalforge config validate` | Check a configuration file. Does not import your code unless `--check-imports` is given. |
| `evalforge dataset validate PATH` | Check a `.json` or `.jsonl` dataset. |
| `evalforge run` | Run the target and store the run. `--fail-on` makes a status exit 1. |
| `evalforge inspect RUN` | Show a stored run, its cases, or one case. |
| `evalforge compare BASE CAND` | Compare two runs. Exit 0 when there are no error findings, 1 when there are, 5 when refused. |
| `evalforge report export SOURCE --out PATH` | Write a report. Case inputs and outputs are excluded unless `--include-io` is given. |

Full reference: [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md).

## Python API

```python
from evalforge import Dataset, Suite, ExactMatch, Target, compare

dataset = Dataset.load("dataset.jsonl")
suite = Suite([ExactMatch(name="exact")])
baseline = suite.run(dataset, Target.from_callable(my_function), run_root=".evalforge/runs")
candidate = suite.run(dataset, Target.from_callable(my_new_function), run_root=".evalforge/runs")
result = compare(baseline, candidate)
print(result.exit_status)       # "pass", "regression", or "refused"
```

Full reference: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

## Limits you need to know

- **Targets and custom evaluators are trusted code.** EvalForge imports them and runs them with your privileges.
  Do not evaluate code you do not trust.
- **Timeouts are best-effort.** A timed-out target is recorded as an error, but the call is not stopped.
- **Redaction is heuristic.** It removes common credential formats. It does not guarantee that sensitive text is
  removed. Do not place secrets in configurations, datasets, or outputs.
- **Stored artifacts can be changed** by anyone who can write to them. Integrity hashes detect accidental or
  careless changes, not deliberate rewrites.
- **Regular expressions can be slow.** Nested repeats are refused, but other slow patterns are not detected.
- **Pass rates are not proof.** Results depend on the cases and evaluators you chose.

The threat model and residual risks are in [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md),
[`docs/SECURITY.md`](docs/SECURITY.md), and [`docs/RESIDUAL_RISK_ACCEPTANCE.md`](docs/RESIDUAL_RISK_ACCEPTANCE.md).

## Not yet done

- No release has been published. Publication is blocked until the distribution name is decided (OD-10; the
  name `evalforge` is already used on PyPI).
- The CI workflow has been written but has not run on GitHub. Linux and Windows have not been tested locally.
- The private security reporting channel and the code of conduct contact are not set (OD-20, OD-17).

## Name

"EvalForge" is a provisional local name. See [`docs/TOOLING_VERIFICATION.md`](docs/TOOLING_VERIFICATION.md).

## Development

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict
```

Specifications live in [`docs/`](docs/), starting with [`docs/PRD.md`](docs/PRD.md). Decisions are in
[`OPEN_DECISIONS.md`](OPEN_DECISIONS.md). Contributions need a DCO sign-off; see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
