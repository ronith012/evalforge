# Release Checklist: Status and Evidence

Status: **Prepared on 2026-10-30. Nothing has been released.** Each item from [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md)
is listed with its status and evidence, using that file's vocabulary: `Done (evidence: …)`, `Blocked (reason: …)`,
`Not started`, `Not applicable (reason: …)`. An item that is only partly true is marked `Blocked` or `Not started`
with the missing part named.

## 1. Approval gate

| Item | Status | Evidence or reason |
|---|---|---|
| All milestones have approved completion records | Blocked (reason: Milestones 13 to 16 await owner approval; M12 deferred) | docs/MILESTONE_*_RECORD.md |
| Specifications approved; OPEN_DECISIONS resolved or deferred | Blocked (reason: OD-01, OD-17, OD-20, OD-23, OD-24, OD-32 open) | OPEN_DECISIONS.md |
| Release scope matches PRD §12 | Not started | Requires an owner review of scope |
| Owner approval for release preparation | Blocked (reason: not given) | — |
| Package-index and trademark checks (G-2, OD-10) | Blocked (reason: `evalforge` is used on PyPI; trademark check not done) | docs/TOOLING_VERIFICATION.md |
| Owner approval per publication step | Not started | — |

## 2. Licensing and notices

| Item | Status | Evidence or reason |
|---|---|---|
| LICENSE is the unmodified Apache-2.0 text | Done (evidence: LICENSE tracked in git; canonical text recorded in MILESTONE_1 record) | git ls-files |
| NOTICE names the copyright holder | Done (evidence: NOTICE) | NOTICE |
| SPDX header in every Python file | Done (evidence: checked by `grep` over src, tests, scripts, examples: none missing) | — |
| Copyright year is the year of initial publication | Blocked (reason: placeholder `YEAR_OF_INITIAL_PUBLICATION`; year unknown until publication; OD-01) | — |
| Package metadata declares Apache-2.0 | Done (evidence: `pyproject.toml` `license = "Apache-2.0"`) | pyproject.toml |
| Licence of bundled examples and fixtures | Partly (reason: examples are project-owned and synthetic; the owner has not reviewed them) | examples/*/README.md |
| No copied code without attribution | Done (evidence: research used documentation only; RESEARCH_NOTES §1). The Contributor Covenant text is attributed (CC BY 4.0) in CODE_OF_CONDUCT.md. | CODE_OF_CONDUCT.md |

## 3. Dependencies and licences

| Item | Status | Evidence or reason |
|---|---|---|
| Gate G-1 before installing dependencies | Done (evidence: docs/TOOLING_VERIFICATION.md for Hatchling and uv). The checklist's "Not yet run" note is out of date. | docs/TOOLING_VERIFICATION.md |
| Lock file committed | Done (evidence: `uv.lock` tracked in git) | git ls-files |
| Runtime dependency licences | Done (evidence: zero runtime dependencies; `test_runtime_dependencies_are_empty`) | tests/test_dependencies.py |
| Development dependency licences recorded | Partly (evidence: pip-audit 2.10.1 verified on PyPI, Apache Software License; pytest, ruff, mypy not re-verified in this record) | MILESTONE_13_RECORD |
| Dependency count matches TRD §3.2 | Done (evidence: `test_runtime_dependencies_are_empty`) | tests/test_dependencies.py |
| No dependency with network telemetry by default | Partly (evidence: core imports no network module. pip-audit, a development dependency, uses the network when run.) | tests/test_security.py |

## 4. Supply chain and vulnerabilities

| Item | Status | Evidence or reason |
|---|---|---|
| pip-audit run on the lock file; output recorded | Done (evidence: `uv run pip-audit`: "No known vulnerabilities found", exit 0; MILESTONE_13_RECORD) | — |
| Build in clean CI | Blocked (reason: CI not run; no remote) | .github/workflows/ci.yml, `build` job |
| Artifacts built from a tagged commit | Not started (reason: no release approved) | — |
| SHA-256 checksums for sdist and wheel | Not started (reason: no release approved) | — |
| Publication method reviewed | Not started | — |
| Name availability and trademark checks | Blocked (see §1) | — |
| Two-person review of release changes | Not started (reason: one maintainer; OD-17) | — |

## 5. Secret scanning

| Item | Status | Evidence or reason |
|---|---|---|
| Scanner run over full history | Blocked (reason: gitleaks download denied by the environment's safety policy; pending owner permission) | MILESTONE_13_RECORD |
| Findings investigated | Blocked (reason: no scan yet) | — |
| Confirmed secrets rotated | Not applicable (reason: no findings yet) | — |
| Planted-secret fixtures are fake and labelled | Done (evidence: `tests/test_security.py` builds planted values from fragments; no credential-shaped literal in the file) | tests/test_security.py |
| `.gitignore` excludes run directories, environments, builds, local secrets | Done (evidence: `.gitignore` lines for `.evalforge/`, `.venv/`, `dist/`, `.env`) | .gitignore |

## 6. Versions and support

| Item | Status | Evidence or reason |
|---|---|---|
| Version chosen | Blocked (reason: version `0.0.0.dev0`; owner decision) | pyproject.toml |
| CHANGELOG entry | Done (evidence: CHANGELOG.md, Unreleased). Known limitations are listed in the release notes (§12). | CHANGELOG.md |
| Supported-version statement | Done (evidence: SECURITY.md "Supported versions") | SECURITY.md |
| Artifact schema versions documented | Done (evidence: DATA_MODELS §1 and §13) | docs/DATA_MODELS.md |
| Deprecations listed | Not applicable (reason: no deprecations yet) | — |

## 7. Documentation

| Item | Status | Evidence or reason |
|---|---|---|
| README: purpose, limits, install, quick start, links | Done (evidence: README.md) | README.md |
| Installation verified from clean environments | Partly (evidence: clean venv install of the wheel on macOS. Linux and Windows not run.) | MILESTONE_15_RECORD |
| Quick start executed by a test | Done (evidence: `test_quick_start_from_a_clean_environment`) | tests/test_e2e.py |
| API documentation matches API_DESIGN §2 | Partly (evidence: `test_every_name_in_the_api_surface_table_is_exported`; the reference is hand-written from the installed signatures) | docs/API_REFERENCE.md |
| CLI reference matches CLI_SPECIFICATION | Done (evidence: `test_every_cli_example_parses_with_the_real_parser`; reference written from `--help`) | docs/CLI_REFERENCE.md |
| EVALUATION_METHODOLOGY available | Done (evidence: in docs/; linked from README). It is not inside the wheel. | docs/EVALUATION_METHODOLOGY.md |
| Security documentation linked from README | Done (evidence: README "Limits" section) | README.md |
| Known-limitations section in release notes | Done (evidence: MILESTONE_16_RECORD, release notes draft §Known limitations) | docs/MILESTONE_16_RECORD.md |
| ARTIFACT_INTEGRITY scope matches the manifest | Done (evidence: `test_integrity_scope_table_matches_the_manifest_hash_fields`) | tests/test_docs.py |
| Sensitive-data defaults documented | Done (evidence: DATA_HANDLING §3 and §7; README limits) | docs/DATA_HANDLING.md |
| Banned-claims scan passes | Done (evidence: `test_user_facing_text_contains_no_banned_claims`) | tests/test_security.py |
| Documentation link check passes | Done (evidence: `test_every_relative_link_in_the_documentation_resolves`) | tests/test_docs.py |
| Synthetic-data notice in each example README | Done (evidence: examples/quickstart/README.md, examples/regression_pair/README.md) | examples/ |

## 8. Tests and CI

| Item | Status | Evidence or reason |
|---|---|---|
| Full suite on Linux, macOS, Windows × Python 3.11, 3.12, 3.13 | Partly (evidence: macOS × 3 versions: 546 passed on each. Linux and Windows not run.) | MILESTONE_14_RECORD |
| Security tests pass | Done (evidence: 33 tests in tests/test_security.py pass locally) | — |
| Static checks pass | Done (evidence: `test_no_code_execution_primitives_in_source`, `test_no_unsafe_deserialisation_or_process_modules_in_source`) | — |
| Network-disabled tests pass | Done (evidence: `test_quick_start_completes_with_sockets_disabled`) | — |
| Lint and format pass | Done (evidence: `ruff check .` passed; `ruff format --check .`: 72 files) | — |
| mypy --strict passes | Done (evidence: 67 source files, no issues) | — |
| Traceability check reports no unlinked requirement | Done (evidence: `test_every_requirement_is_cited_by_a_test_or_listed_in_the_register` passes). 19 requirements are listed as Open and need a test or a decision. | docs/TRACEABILITY.md |
| Benchmark results recorded or marked not measured | Partly (reason: not measured; to be stated in release notes) | TRD §16 |
| Coverage reported | Not started (reason: coverage is not measured; TRD-236) | — |

## 9. Packaging validation

| Item | Status | Evidence or reason |
|---|---|---|
| sdist and wheel build; install in clean environments on each OS | Partly (evidence: both built with `uv build`; wheel installed in a clean venv on macOS. Other OSes not run.) | MILESTONE_15_RECORD |
| Installed `evalforge --version` reports the release version | Partly (evidence: prints `0.0.0.dev0` on macOS; no release version yet) | — |
| Package contents inspected | Done (evidence: `scripts/check_artifacts.py` passes for both artifacts; sdist keeps tests and synthetic examples, wheel excludes them; owner to confirm the sdist rule) | scripts/check_artifacts.py |
| `py.typed` included | Done (evidence: `test_package_ships_the_typed_marker`; the artifact check requires it) | — |
| Metadata reviewed; project URLs point to owner repositories | Not started (reason: no URLs are set; no remote exists) | pyproject.toml |

## 10. Synthetic example data

| Item | Status | Evidence or reason |
|---|---|---|
| Each example dataset is synthetic and says so | Done (evidence: both example READMEs; every case tagged `synthetic`) | examples/ |
| No real or personal data | Partly (evidence: by construction; owner review not done) | — |
| Examples reviewed by another person | Not started (proposed) | — |
| Hostile corpus labelled as test material | Done (evidence: tests/fixtures/datasets/README.md) | tests/fixtures/datasets/ |

## 11. Community and project files

| Item | Status | Evidence or reason |
|---|---|---|
| CONTRIBUTING: DCO requirement; security rule; test requirements | Done (evidence: CONTRIBUTING.md). The enforcement method is proposed (OD-32); CI has not run it. | CONTRIBUTING.md |
| CODE_OF_CONDUCT: text selected and attributed | Partly (evidence: Contributor Covenant 2.1, attributed. Enforcement contact is a placeholder.) | CODE_OF_CONDUCT.md; OD-17 |
| SECURITY.md: reporting channel defined and published | Blocked (reason: the channel is not set; OD-20) | SECURITY.md |
| Issue and pull-request templates | Not started (proposed; optional) | — |

## 12. Known limitations

All items are in the release notes draft (docs/MILESTONE_16_RECORD.md) and in README "Limits":
RR-01 to RR-08; the best-effort timeouts; the regex limit; the integrity scope; overrides and `--strict`; trusted
code; the unmeasured performance targets; and the absence of model-based evaluators. **Done (evidence: MILESTONE_16_RECORD).**

## 13. Release verification and final decision

| Item | Status | Evidence or reason |
|---|---|---|
| Every item Done or Not applicable | Blocked (see the items above) | — |
| Release verification record | Not started (reason: needs CI and the release commit) | — |
| Residual risks RR-01 to RR-08 accepted in writing | Blocked (reason: not accepted; `docs/RESIDUAL_RISK_ACCEPTANCE.md`) | — |
| Release notes draft reviewed | Partly (evidence: draft in MILESTONE_16_RECORD; owner review pending) | — |
| Decision request submitted | Done (evidence: MILESTONE_16_RECORD, "Decision request") | — |
