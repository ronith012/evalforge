# EvalForge

**Status: pre-alpha. This is a development skeleton. It does not evaluate anything yet.**

EvalForge is planned as an open-source, model-agnostic framework for evaluating AI applications,
comparing runs, and detecting regressions. The planned MVP runs locally, has no third-party
runtime dependencies, and does not claim that evaluation scores prove safety or correctness.

Specifications live in [`docs/`](docs/), starting with [`docs/PRD.md`](docs/PRD.md).
Development status and decisions are in [`DEVELOPMENT_TASKS.md`](DEVELOPMENT_TASKS.md) and
[`OPEN_DECISIONS.md`](OPEN_DECISIONS.md).

## Name

"EvalForge" is a provisional local name. The PyPI name `evalforge` is already in use by another
project, so this package **cannot be published under that name**. Publication is blocked until the
name is decided (OPEN_DECISIONS OD-10). See [`docs/TOOLING_VERIFICATION.md`](docs/TOOLING_VERIFICATION.md).

## Development setup

Requirements: Python 3.11, 3.12, or 3.13, and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict
```

## Licence

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
Contributions require DCO sign-off; see [`CONTRIBUTING.md`](CONTRIBUTING.md).
