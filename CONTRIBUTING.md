# Contributing to EvalForge

EvalForge is in pre-alpha. Read [`DEVELOPMENT_TASKS.md`](DEVELOPMENT_TASKS.md) and the
specifications in [`docs/`](docs/) first. Changes that alter approved requirements or scope need
an approved decision recorded in [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md) first.

## Developer Certificate of Origin (DCO)

External contributions require a DCO sign-off on every commit. Add it with `git commit -s`, which
appends a `Signed-off-by:` trailer. The text of the certificate is at
<https://developercertificate.org>.

CI enforces the sign-off with `scripts/check_dco.py`, in the `dco` job of `.github/workflows/ci.yml`. The
script checks each commit in a pull request for a `Signed-off-by:` line. It does not verify the
certificate's content. **The workflow has not run on GitHub yet, so the check is not proven; external
contributions are not accepted until it is.** The choice of this method for OD-32 is proposed and is
awaiting owner confirmation.

## Rules

- Do not commit secrets or real evaluation data. Test data must be synthetic.
- Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv run mypy --strict` before opening a pull request. The CI workflow runs the same commands.
- Keep runtime dependencies at zero unless a new decision approves otherwise (TRD §3.2).
- Report security issues privately, as described in [`SECURITY.md`](SECURITY.md). The reporting channel is
  not yet defined (OD-20).
- The code of conduct is in [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Its enforcement contact is not yet set (OD-17).
