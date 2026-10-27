# Milestone 1 Completion Record — Project foundation

Status: **Approved by the owner on 2026-10-27.** Implemented and checked locally on macOS.

Approval decisions carried forward: the year placeholder stays until initial publication (OD-01); the PyPI name conflict is recorded (OD-10); uv is re-locked with 0.13.6 before Milestone 5 (see IMPLEMENTATION_PLAN §8).
Date of checks: 2026-10-27. Environment: macOS (Darwin, arm64), local uv 0.11.10, Python 3.11.0, 3.12.13, 3.13.

## Scope delivered

- `pyproject.toml`: Hatchling 1.32.4 backend; Apache-2.0; Python `>=3.11,<3.14`; zero runtime dependencies; dev group with mypy, pytest, ruff.
- `src/evalforge/`: version-only `__init__.py` and `py.typed`.
- `LICENSE` (canonical Apache-2.0 text), `NOTICE` (copyright holder Bodepudi Ronith), `README.md`, `CONTRIBUTING.md` (DCO requirement), `.gitignore` (includes `.evalforge/`).
- `uv.lock` (14 packages resolved).
- `tests/`: smoke tests and dependency-metadata tests (6 tests).
- `.github/workflows/ci.yml`: matrix Linux/macOS/Windows × 3.11, 3.12, 3.13 plus a lint/type job. **Not executed on GitHub.**
- Gate records: `docs/TOOLING_VERIFICATION.md` (G-1 recorded; G-2 not complete).

## Requirements touched

| Requirement | Evidence | Status |
|---|---|---|
| PRD-NF-005 (Python versions) | Tests pass on 3.11, 3.12, 3.13 locally (macOS) | Partly verified: macOS only |
| PRD-NF-004 (cross-platform) | CI definition only | **Not verified** on Linux or Windows |
| PRD-NF-006 (zero runtime deps) | `tests/test_dependencies.py` passes; wheel metadata lists no requirements | Verified |
| PRD-NF-012 (licence) | LICENSE and NOTICE present in wheel and sdist | Verified (packaging) |
| TRD-011, TRD-015 (install) | Clean-venv install of the wheel; import prints version `0.0.0.dev0` | Verified locally |
| OD-15 (`mypy --strict` gate) | `mypy --strict`: 3 source files, no issues | Verified locally |

## Checks run and exact results

| Check | Command | Result | Exit |
|---|---|---|---|
| Lock | `uv lock` | Resolved 14 packages | 0 |
| Tests | `uv run --locked pytest` | 6 passed | 0 |
| Tests, per version | `uv run --locked --python {3.11,3.12,3.13} pytest -q` | 6 passed each | 0, 0, 0 |
| Lint | `uv run --locked ruff check .` | All checks passed | 0 |
| Format | `uv run --locked ruff format --check .` | 3 files already formatted | 0 |
| Type check | `uv run --locked mypy --strict` | Success: no issues in 3 source files | 0 |
| Build | `uv build` | sdist and wheel built | 0 |
| Clean install | `uv pip install` of the wheel into a fresh 3.12 venv; import | Import ok, version 0.0.0.dev0 | 0, 0 |

## Not run

- Linux and Windows test runs (no runners available here).
- The GitHub Actions workflow itself. The action versions it uses (`actions/checkout@v4`, `astral-sh/setup-uv@v6`) are **not verified**.
- Git-based checks: no repository is initialised (requires separate authorisation).

## Issues and deviations

1. **Package name conflict.** PyPI `evalforge` is already used by another project (MIT, v1.0.0). Publication is blocked (OD-10, G-2). The local name is kept, as approved.
2. **Copyright year placeholder.** `YEAR_OF_INITIAL_PUBLICATION` appears in source headers, `NOTICE`, and the workflow. The placeholder approach is not yet confirmed. It must be replaced before publication (M16).
3. **uv version mismatch.** The lock was produced with local uv 0.11.10. The latest uv verified in G-1 is 0.13.6. The lock format or resolution may differ. Re-lock with the pinned version (or record 0.11.10) before M2.
4. **Ruff scope.** Ruff is restricted to `*.py` and `*.pyi`. The Markdown code blocks in `docs/` are illustrative and not formatted. This is a deliberate deviation from "format everything".
5. **Git not initialised.** `.gitignore` and CI take effect only once a repository exists.

## Requested approval

Approve Milestone 1 as complete, and decide items 1–3 above before Milestone 2 starts.
