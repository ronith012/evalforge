# Contributing to EvalForge

EvalForge is in pre-alpha. Read [`DEVELOPMENT_TASKS.md`](DEVELOPMENT_TASKS.md) and the
specifications in [`docs/`](docs/) first. Changes that alter approved requirements or scope need
an approved decision recorded in [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) first.

## Developer Certificate of Origin (DCO)

External contributions require a DCO sign-off on every commit. Add it with `git commit -s`, which
appends a `Signed-off-by:` trailer. The text of the certificate is at
<https://developercertificate.org>.

Automated enforcement of this requirement is planned for CI (milestone 15, OD-31). **Until that
check is running, external contributions are not accepted.** The enforcement method is still open
(OD-32).

## Rules

- Do not commit secrets or real evaluation data. Test data must be synthetic.
- Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv run mypy --strict` before opening a pull request.
- Keep runtime dependencies at zero unless a new decision approves otherwise (TRD §3.2).
- Report security issues privately. The reporting channel is not yet defined (OD-20).
