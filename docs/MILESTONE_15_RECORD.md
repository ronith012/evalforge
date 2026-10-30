# Milestone 15 Completion Record: Packaging and Documentation

Status: **Complete locally. CI has not run on GitHub.** Awaiting owner approval. Date: 2026-10-30. Not committed.

## Scope (IMPLEMENTATION_PLAN §8.12)

| Item | Result | Where |
|---|---|---|
| 1. README, API reference, CLI reference | Done. The README was rewritten with the limits statement. The API reference was written from the installed names and signatures. The CLI reference was written from `--help`. | `README.md`; `docs/API_REFERENCE.md`; `docs/CLI_REFERENCE.md` |
| 2. CI: Python matrix on Linux, macOS, Windows; mypy, lint, tests, audit, build, dco | Written. Jobs: `test` (matrix), `lint`, `audit`, `build`, `dco`, `secret-scan`. Parsed as YAML. **Not run on GitHub.** No remote is connected. | `.github/workflows/ci.yml` |
| 3. Example workflow that uploads summaries only (OD-23) | Written. It uploads `summary.json` and `manifest.json`, never `cases.jsonl`. Its action versions were not re-checked. | `examples/github-actions/evalforge-summary.yml` |
| 4. Code of conduct (OD-17); vulnerability contact (OD-20); secret scanner (OD-24) | Code of conduct: Contributor Covenant 2.1 text fetched and checked; attribution kept; **enforcement contact is a placeholder**. Security policy: **reporting channel is a placeholder**. Secret scanner: gitleaks v8.30.1 chosen (MIT, verified); **not run locally** (download denied). | `CODE_OF_CONDUCT.md`; `SECURITY.md`; `.github/workflows/ci.yml` |
| 5. Synthetic example datasets, labelled | Done. Quick start and regression pair each have a README stating the data is synthetic; every case is tagged `synthetic`. | `examples/` |
| 6. CHANGELOG and `.gitignore` template | CHANGELOG written. The existing `.gitignore` was reviewed; it excludes `.evalforge/`, virtual environments, build output, and `.env` files. No separate template was added. | `CHANGELOG.md`; `.gitignore` |

## Additional work

- **DCO enforcement (OD-31, OD-32).** `scripts/check_dco.py` checks each commit in a range for a `Signed-off-by:` line.
  Tested against a real git repository. Its use in CI is the proposed OD-32 method; the owner has not confirmed it.
- **Artifact contents (TST-E2E-005).** `scripts/check_artifacts.py` checks the built artifacts. Built with `uv build`. Result:
  both artifacts passed.
- **Clean-environment install (TST-E2E-004, macOS).** A wheel was installed into a new virtual environment. `evalforge
  --version` printed `evalforge 0.0.0.dev0`.

## Decision made in this milestone: sdist contents

TST-E2E-005 says "no test data" in package contents. The source distribution keeps `tests/` and `examples/`, so that it
can be tested from the sdist. The wheel excludes both. The check script enforces this split. **Owner to confirm.**

## Checks and exact results

| Check | Command | Result |
|---|---|---|
| Lint, whole repository | `uv run ruff check .` | All checks passed! |
| Format, whole repository | `uv run ruff format --check .` | 72 files already formatted |
| Types | `uv run mypy --strict` | Success: no issues found in 67 source files |
| Tests | `uv run pytest -q` on 3.11, 3.12, 3.13 | 546 passed on each |
| Build | `uv build` | sdist and wheel built |
| Artifact check | `uv run python scripts/check_artifacts.py <dist>` | Artifacts passed |
| Clean install | `uv venv`, `uv pip install <wheel>`, `evalforge --version` | `evalforge 0.0.0.dev0` |
| Workflow parse | YAML parse of `ci.yml` and the example | Parsed; 6 jobs listed |

## Not done

- No CI run on GitHub, so the Linux and Windows matrix is unverified.
- The secret scan has not been run (see Milestone 13).
- The example workflow's `install` step uses placeholders (`OWNER/REPO/COMMIT_SHA`) that you must replace.
- Action versions in CI: `actions/checkout@v4` and `astral-sh/setup-uv@v6` are the pinned versions. Newer releases
  exist (checkout v7.0.1, setup-uv v10.3.3). Choosing a version is an owner decision.
- Project URLs in `pyproject.toml` are not set (RELEASE_CHECKLIST §9 requires them to point at owner repositories).

## Requested approval

Approve Milestone 15 for the local state. Decide: the sdist contents rule, the DCO method (OD-32), action versions,
and the secret-scan job. Provide a remote to run CI.
