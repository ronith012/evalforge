# EvalForge — Tooling Verification Record (Gates G-1 and G-2)

Status: **G-1 recorded. G-2 not complete.**
Checks performed on **2026-10-27** using the PyPI JSON API (read-only) and the packages'
own wheel metadata. No package was installed to make these checks.

## G-1: verification before installing dependencies

| Tool | Role | Version checked | Licence (from wheel metadata) | Latest upload | Releases | Build/runtime requirements | Result |
|---|---|---|---|---|---|---|---|
| Hatchling | Build backend (dev and build time only) | 1.32.4 | MIT | 2026-09-20 | 85 | Requires Python ≥ 3.10; build-time dependencies: packaging, pathspec, pluggy, tomlkit, trove-classifiers | Verified |
| uv | Development environment and lock-file tool | 0.13.6 (latest on PyPI at check time) | MIT OR Apache-2.0 | 2026-10-27 | 330 | Requires Python ≥ 3.8 | Verified. Installed on this machine: uv 0.11.10 (Homebrew). Version mismatch recorded. |
| pytest | Test runner (development) | 9.1.1 | MIT | 2026-06-19 | 192 | Requires Python ≥ 3.10 | Verified |
| ruff | Linter and formatter (development) | 0.17.3 | MIT | 2026-10-27 | 430 | Requires Python ≥ 3.7 | Verified |
| mypy | Static type checker, `--strict` gate (development) | 2.4.0 | MIT | 2026-10-01 | 141 | Requires Python ≥ 3.10; dependencies: typing_extensions, mypy_extensions, pathspec, librt, tomli (< 3.11 only) | Verified |

Notes:

- Hatchling's and mypy's dependencies are **not** EvalForge runtime dependencies. They are
  development or build-time only. EvalForge's own runtime dependency list stays empty (TRD §3.2).
- Licence was read from the `License-Expression` field of each package's wheel metadata.
  No licence text was compared with a second source, beyond the wheels' own licence files.
- Maintenance status is the upload history from PyPI. It is not an assessment of code quality.
- uv 0.13.6 is newer than the installed uv 0.11.10. Update before relying on lock behaviour, or pin
  the version used for the lock file in the release record.
- **Not verified:** pip-audit (planned for CI, TRD-023) and pytest-timeout (planned, TRD §3.2).
  Verify before adding them.

## G-2: publication checks (NOT COMPLETE)

| Check | Result |
|---|---|
| PyPI project name `evalforge` | **Already in use.** Project "evalforge", version 1.0.0, licence MIT, summary "Framework-agnostic LLM agent evaluation harness", 12 releases, latest upload 2026-04-11, repository https://github.com/heManKuMAR6/evalforge. |
| Trademark search for "EvalForge" | **Not performed.** |
| Other package indexes or registries | **Not performed.** |

Consequences:

- The distribution name `evalforge` cannot be published to PyPI while this project exists.
- A different distribution name is needed for publication. The import name, the directory name, and the
  CLI command also need a decision, because `import evalforge` and the `evalforge` command would
  collide with that project if both were installed in one environment.
- This needs an **owner decision** (OD-10). It is not decided here. Local development under the
  provisional name is permitted, as approved. Nothing will be published under this name.
