# EvalForge — Implementation Plan

Status: **Proposed — awaiting approval. No milestone has started.** Nothing in this
plan authorises implementation before the specifications are approved (CLAUDE.md,
"Development workflow").

Requirements: [PRD](docs/PRD.md), [TRD](docs/TRD.md). Tests: [TEST_STRATEGY](docs/TEST_STRATEGY.md).

---

## 1. Principles

- Each milestone ends with passing tests for its scope, a written verification record,
  and an approval gate before the next milestone starts.
- No milestone depends on a later milestone's unapproved design.
- Security-relevant work is not deferred to the end. Milestone 13 hardens and
  re-verifies; threat-specific tests are written with the feature that introduces the threat.
- Effort ranges are rough planning estimates for relative sizing. They are not
  commitments, deadlines, or measured data (CLAUDE.md, quality rules; brief §13).

## 2. Sequence and adjustments

The brief's sequence is kept, with one documented change.

**Change CH-01 — persistence moves earlier.** The brief places "optional persistence" at
milestone 12. The MVP requires persisted runs for `inspect`, `compare`, and integrity checks
(PRD-F-017, PRD-F-018, PRD-F-026, PRD-F-021), and reporting (milestone 8) reads stored
results. File-based persistence is therefore part of milestone 7. Milestone 12 becomes an
**optional SQLite backend**, which is deferred under OD-05 (approved: JSON/JSONL first, SQLite deferred).

**Change CH-02 — zero runtime dependencies.** The earlier plan used Pydantic and Typer. Pydantic's core
is compiled, which conflicts with TRD-003 (pure Python). The MVP uses the standard library only (TRD §3.2,
ARCHITECTURE AD-009). Impact: milestone 2 and milestone 11 effort increase; the dependency list
becomes empty; a fallback is documented (TRD §3.2).

**Change CH-03 — process isolation deferred.** Isolation is not in the MVP. M13 produces a written
decision. An optional milestone M17 exists only if the owner approves it (ARCHITECTURE §11.1). Impact:
timeouts remain best-effort in the MVP, and this is documented in every relevant place.

Dependency graph:

```
1 → 2 → 3 ─┐
     2 → 4 ─┼→ 6 → 7 → 8 ──────────────┐
     2 → 5 ─┘           7 → 9 → 10 ──────┼→ 11 → 13 → 14 → 15 → 16
                                12 (optional, after 7)
```

Milestones 12 and 13 may run in either order after 11; 13 must complete before 14.

## 3. Traceability

Each milestone lists the PRD and TRD requirements it delivers. Requirements not listed
under any milestone are a plan defect and must be fixed before approval.

| Milestone | PRD requirements delivered | TRD sections |
|---|---|---|
| 1 Foundation | PRD-NF-004, PRD-NF-005, PRD-NF-012 (scaffolding) | §2, §3.1, §3.3 |
| 2 Data models & validation | PRD-F-002, PRD-F-003, PRD-F-004 (model), PRD-F-029 (partial), PRD-NF-009 (model) | §4.3, §4.4, §12, DATA_MODELS |
| 3 Dataset loading | PRD-F-001, PRD-F-002, PRD-F-003, PRD-F-004, PRD-NF-003 | §4.1, §4.2, §4.4 |
| 4 Target interface | PRD-F-005, PRD-F-006, PRD-F-028 (interface) | §5.2, §5.3 |
| 5 Deterministic evaluators & registry | PRD-F-008 … PRD-F-014 | §5.4, §5.5, §5.6 |
| 6 Evaluation runner | PRD-F-007, PRD-F-016, PRD-F-018 (engine part), PRD-F-015 (manifest) | §6 |
| 7 Normalization & persistence | PRD-F-015, PRD-F-016, PRD-F-017, PRD-F-018, PRD-NF-002, PRD-NF-008, PRD-NF-014 (I/O and redaction), PRD-NF-015 (integrity scope) | §7, §4.4 |
| 8 Reporting | PRD-F-024, PRD-F-025, PRD-F-020 (display), PRD-NF-013 | §10 (reporting), SECURITY §6 |
| 9 Run comparison | PRD-F-019, PRD-F-020, PRD-F-021, PRD-NF-015 (overrides) | §8 |
| 10 Regression detection | PRD-F-022, PRD-F-023 (codes) | §9 |
| 11 CLI & Python API | PRD-F-023, PRD-F-026, PRD-F-027, PRD-F-029, PRD-F-030 (partial), PRD-F-024 | §10, §11, CLI, API |
| 12 Optional SQLite (deferred) | PRD-F-102 (post-MVP) | TRD §7 (alternative) |
| 13 Security hardening | PRD-NF-001, PRD-NF-003, PRD-NF-011, PRD-NF-006 (enforcement), PRD-NF-014, PRD-NF-016 | §15, THREAT_MODEL, SECURITY, ARTIFACT_INTEGRITY |
| 14 Integration & E2E tests | PRD-NF-002, PRD-NF-010 (executable docs), PRD-F-030 (verify) | TRD §17 |
| 15 Packaging & docs | PRD-NF-010, PRD-NF-012, PRD-F-030 | TRD §3.1, RELEASE_CHECKLIST |
| 16 Release readiness | All MVP requirements (final verification) | RELEASE_CHECKLIST |

## 4. Milestones

Each milestone uses the same fields. "Required approval" means the user must approve
the milestone's completion record before the next milestone starts.

### M1 — Project foundation

- **Objective:** Create a reproducible empty project skeleton with tooling, without application features.
- **Scope:** `pyproject.toml` (metadata, Apache-2.0, Python range), `src/evalforge/__init__.py` (version only), `tests/` skeleton, lint config, uv-managed lock file `uv.lock` (OD-03), Hatchling build configuration (OD-03), `.gitignore` (includes `.evalforge/`), `LICENSE` (Apache-2.0), `NOTICE` naming Bodepudi Ronith (OD-01), short source-file headers (OD-01), `CONTRIBUTING.md` stating the DCO sign-off requirement (OD-31), `README.md` placeholder marked "not yet usable". Package name is provisional (OD-10); publication is blocked until gate G-2. Before any dependency is installed, gate G-1 applies (verify Hatchling and uv versions, licences, and maintenance status, and record them).
- **Deliverables:** Installable empty package; ruff passes; one smoke test; Git initialisation **only after separate authorisation**.
- **Dependencies:** Approved: TRD §3.2, OD-01 to OD-06, OD-15, OD-31. Gate G-1 applies before installation. The runtime dependency list is empty (approved).
- **Acceptance criteria:** Package builds sdist and wheel; `import evalforge` works on the three OSes in CI; dependency list equals approved list (PRD-NF-006 test).
- **Tests:** Smoke test; dependency-list test; build test; `mypy --strict` passes on the skeleton (OD-15); CI runs Python 3.11, 3.12, and 3.13 (OD-02).
- **Security implications:** Establishes no-network and no-exec lint rules (TRD-216) as CI checks.
- **Risks:** Name collision on PyPI. The name is provisional until OD-10 checks are complete (before M16).
- **Effort (rough):** 1–3 days.
- **Verification evidence:** Build log; ruff output; test output; lock file hash.
- **Required approval:** Yes.

### M2 — Data models and validation

- **Objective:** Define all models in DATA_MODELS (case, config, manifest, case result, evaluator result, summary, comparison, finding, error) and the validation rules for them.
- **Scope:** Frozen dataclasses with validation functions (no third-party validation library, TRD §3.2); canonical JSON and hashing (`canon/`); reason-code and error registries; config model with unknown-key rejection; limits constants (TRD §4.2).
- **Deliverables:** `models/`, `canon/`, `errors.py`, `config/` (model and validation only; no file loading yet).
- **Dependencies:** M1.
- **Acceptance criteria:** Models round-trip the DATA_MODELS examples exactly; canonical hash test vectors pass (hand-written); NaN rejected; PRD-NF-009 version check implemented.
- **Tests:** TST-DS-016, TST-DS-017 (model level), TST-MF-005, TST-MF-006, TST-MF-008; TST-PS-101-series schema tests if needed; PRD-NF-007 benchmark baseline (BM-001 harness only).
- **Security implications:** Strict model config (`extra="forbid"`); no coercion of unexpected types.
- **Risks:** Model drift from DATA_MODELS. Mitigation: DOC-to-model check (M14).
- **Effort (rough):** 3–5 days.
- **Verification evidence:** Test output; canonical hash vectors recorded with their derivation.
- **Required approval:** Yes.

### M3 — Dataset loading

- **Objective:** Load JSON and JSONL files with encoding, format, and limit enforcement; produce `Dataset` objects and both file hashes.
- **Scope:** `datasets/loader.py`, `datasets/validator.py`; streaming JSONL; error collection (cap 100); `dataset validate` core function (no CLI yet).
- **Deliverables:** Loader, validator, fixture corpus for valid and invalid datasets (synthetic).
- **Dependencies:** M2.
- **Acceptance criteria:** PRD-F-001 to PRD-F-004 acceptance criteria (PRD §18) pass; limit tests at boundary and boundary+1 pass; validation performs no execution.
- **Tests:** TST-DS-001 … TST-DS-019; TST-MF-001 … TST-MF-004; TST-SEC-001, TST-SEC-002 (loading level).
- **Security implications:** THR-001, THR-002, THR-005, THR-006 controls first implemented here.
- **Risks:** Memory use with large JSON arrays (JSON arrays are not streamed; cap enforced before parse by byte size). Mitigation: documented limit; JSONL recommended.
- **Effort (rough):** 3–5 days.
- **Verification evidence:** Test output; limit-test table.
- **Required approval:** Yes.

### M4 — Target interface

- **Objective:** Implement the target interface, callable adapter, and reference resolution, without timeouts.
- **Scope:** `targets/adapter.py`; input deep copy; output canonicalization check; reference resolution (`module:attribute`); `TargetLoadError`.
- **Scope note:** Timeouts are best-effort and no isolation is added (TRD-072, TRD-074). The interface documentation states trusted-code status (TRD-076).
- **Deliverables:** Target protocol; `Target.from_callable`, `Target.from_reference`; example adapter used for interface conformance (PRD-F-028).
- **Dependencies:** M2.
- **Acceptance criteria:** PRD-F-005, PRD-F-028 acceptance criteria pass; serializability check yields ERROR code via runner stub.
- **Tests:** TST-TG-001, TST-TG-005, TST-TG-006, TST-TG-010, TST-TG-011, TST-CLI-009 (import-spy part).
- **Security implications:** THR-004 — import occurs only when the caller requests it; documented.
- **Risks:** Import side effects in user modules. Documented.
- **Effort (rough):** 2–3 days.
- **Verification evidence:** Test output.
- **Required approval:** Yes.

### M5 — Deterministic evaluators and registry

- **Objective:** Implement the six built-in evaluators, the custom evaluator interface, the registry, and fingerprints.
- **Scope:** `evaluators/builtin/*` (exact, normalized_text, json_structure, required_fields, rule_based, latency); `evaluators/registry.py`; custom evaluator loading; fingerprinting (TRD-085); regex limits (TRD §5.6).
- **Deliverables:** Evaluators with documented limitations (TRD §5.5, EVALUATION_METHODOLOGY §4).
- **Dependencies:** M2 (and M4 for custom loading).
- **Acceptance criteria:** PRD-F-008 … PRD-F-014 acceptance criteria pass; TST-EV-001 … TST-EV-029 pass; no built-in returns INCONCLUSIVE (TST-EV-029).
- **Tests:** TST-EV family; TST-SEC-006 for ID handling not relevant here; fingerprint tests.
- **Security implications:** THR-003 regex limits; THR-004 custom trust boundary.
- **Risks:** Evaluator semantics misunderstood by users. Mitigation: limitations shown in docs and in `inspect`.
- **Effort (rough):** 4–6 days.
- **Verification evidence:** Test output; evaluator behaviour table reviewed against EVALUATION_METHODOLOGY §4.
- **Required approval:** Yes.

### M6 — Evaluation runner

- **Objective:** Execute cases, apply timeouts, capture outcomes, call evaluators, apply aggregation rules, handle interrupts.
- **Scope:** `runner/engine.py`; worker thread timeouts; `threads_possibly_running` counter; status aggregation (EVALUATION_METHODOLOGY §3.3); `KeyboardInterrupt` handling (TRD-103); engine-error boundary.
- **Deliverables:** In-memory run objects; `Suite.run` core (no persistence yet).
- **Dependencies:** M3, M4, M5.
- **Acceptance criteria:** PRD-F-006, PRD-F-007, PRD-F-016 (aggregation table T1–T10), PRD-F-018 engine part.
- **Tests:** TST-TG-002 … TST-TG-004, TST-TG-007 … TST-TG-009, TST-TG-012, TST-TG-013; §4.5 table.
- **Security implications:** THR-010 documented limitation; timeout behaviour tests.
- **Risks:** Thread timeouts leak threads; user-visible in counts. Mitigation: documented as best-effort (TRD-072); isolation decision in M13 (ARCHITECTURE §11.1); opt-in isolation only as M17, if approved.
- **Effort (rough):** 4–6 days.
- **Verification evidence:** Test output; aggregation table results.
- **Required approval:** Yes.

### M7 — Result normalization and file persistence

- **Objective:** Write runs to disk atomically with manifests, case files, summaries, integrity hashes, and locks; read them back with validation.
- **Scope:** `store/` (writer and reader), `results/normalize.py`, `stats/` (percentiles, Wilson interval), run-directory lock (TRD-121), `io_mode` handling (DATA_HANDLING §3), redaction module (DATA_HANDLING §7), `summary_sha256` and integrity checks (ARTIFACT_INTEGRITY), tracebacks never stored (DATA_HANDLING §4).
- **Deliverables:** Run directories per DATA_MODELS §6, §7, §10; `Run.load`.
- **Dependencies:** M6.
- **Acceptance criteria:** PRD-F-015, PRD-F-017, PRD-F-018 (storage part), PRD-F-020 (computation), PRD-NF-002 (determinism of case content), PRD-NF-008; statistics vectors TST-ST-001 … TST-ST-007 (hand-verified) pass.
- **Tests:** TST-PS-101 … TST-PS-109; TST-MF-007; TST-ST-*; TST-SEC-012 (integrity), TST-SEC-017 (lock), TST-SEC-006/007 (path controls).
- **Security implications:** THR-007, THR-011 (snapshot and string redaction), THR-012 (io_mode), THR-013 (integrity limits), THR-018, THR-021 (tracebacks), THR-022 (environment metadata).
- **Risks:** Windows file-replace semantics. Mitigation: tests on Windows in CI (TST-XP-001).
- **Effort (rough):** 4–6 days.
- **Verification evidence:** Test output; integrity test output; independent check of Wilson vectors (see TEST_STRATEGY §4.6).
- **Required approval:** Yes.

### M8 — Reporting

- **Objective:** Terminal and JSON reporting for runs, inspection output, and summaries; publish the JSON Schema for artifacts.
- **Scope:** `report/terminal.py`, `report/json.py`, sanitization (SECURITY §6), JSON Schema generation and publication, footer text (pending OD-18).
- **Deliverables:** Text templates; golden-output fixtures; `schemas/` JSON Schema files (TRD §15 format).
- **Dependencies:** M7.
- **Acceptance criteria:** PRD-F-024, PRD-F-025, PRD-NF-013; sanitization tests pass; JSON Schema validates DATA_MODELS examples.
- **Tests:** TST-CLI-011 (golden), TST-SEC-010, TST-SEC-013, TST-SEC-014, TST-DOC-003 (banned claims), JSON Schema validation test (closes the PRD-F-025 gap noted in TEST_STRATEGY §10).
- **Security implications:** THR-009, THR-012, THR-019.
- **Risks:** Report wording overclaims. Mitigation: banned-claims scan and human review of templates.
- **Effort (rough):** 3–4 days.
- **Verification evidence:** Golden files; schema validation output.
- **Required approval:** Yes, including approval of report wording.

### M9 — Run comparison

- **Objective:** Compare two stored runs, check compatibility, categorize cases, compute metric deltas.
- **Scope:** `compare/engine.py`; compatibility checks (TRD §8.1); overrides as explicit arguments with banner, recorded output, and `--strict` (TRD-136 … TRD-138; ARTIFACT_INTEGRITY §6); categories (EVALUATION_METHODOLOGY §5); missing and new cases; output sorting (DATA_MODELS §11).
- **Deliverables:** `compare()` function returning Comparison objects; comparison JSON writer.
- **Dependencies:** M7.
- **Acceptance criteria:** PRD-F-019, PRD-F-020 (delta), PRD-F-021; TST-CM-001 … TST-CM-008, TST-CM-016, TST-CM-017.
- **Tests:** Table-driven transition tests; refusal tests; determinism (byte-identical output).
- **Security implications:** THR-013 integrity checked before compare.
- **Risks:** Memory for very large comparisons (see ARCHITECTURE §12); measured in BM-005.
- **Effort (rough):** 3–5 days.
- **Verification evidence:** Test output; BM-005 result if measured.
- **Required approval:** Yes.

### M10 — Regression detection

- **Objective:** Apply thresholds to comparisons; produce typed findings with explanations.
- **Scope:** `regression/detector.py`; `[regression]` config handling; finding codes (TRD §9.2); exit status derivation.
- **Deliverables:** Findings with stable messages; `exit_status`.
- **Dependencies:** M9.
- **Acceptance criteria:** PRD-F-022; TST-CM-009 … TST-CM-015; infrastructure errors never reported as `CASE_REGRESSED_TO_FAIL` (TST-CM-012).
- **Tests:** Golden finding messages (TST-CM-015); threshold boundary tests (TST-CM-010).
- **Security implications:** THR-019 — finding wording reviewed.
- **Risks:** Threshold defaults (OD-08) may be wrong for users. Mitigation: documented guidance (EVALUATION_METHODOLOGY §6).
- **Effort (rough):** 2–4 days.
- **Verification evidence:** Golden outputs; threshold table results.
- **Required approval:** Yes, including approval of default thresholds (OD-08).

### M11 — CLI and Python API integration

- **Objective:** Expose all operations through the CLI and the public API with parity.
- **Scope:** `cli/` (argparse, TRD-165; all commands in CLI_SPECIFICATION §3), public names (`__all__`), config-driven `run_from_config`, exit-code mapping (CLI §1.4), progress output.
- **Deliverables:** `evalforge` entry point; API surface per API_DESIGN §2.
- **Dependencies:** M8, M10.
- **Acceptance criteria:** PRD-F-023, PRD-F-026, PRD-F-027, PRD-F-029, PRD-F-030 (command set); all CLI and API tests in TEST_STRATEGY §4.9 pass.
- **Tests:** TST-CLI-001 … TST-CLI-012; TST-API-001 … TST-API-006.
- **Security implications:** Argument handling; no secret printing (TST-SEC-008 on CLI output).
- **Risks:** CLI and API drift. Mitigation: shared implementation and parity tests.
- **Effort (rough):** 4–6 days.
- **Verification evidence:** Test output; example outputs compared with CLI_SPECIFICATION (TST-DOC-002).
- **Required approval:** Yes.

### M12 — Optional SQLite persistence (deferred)

- **Status:** Deferred (OD-05). Not scheduled. Starts only on a new owner approval.
- **Objective:** Provide an alternative storage backend if approved.
- **Scope:** `store/sqlite.py` behind the same reader/writer interface; migration policy; locking and transaction tests.
- **Deliverables:** Only if OD-05 selects SQLite.
- **Dependencies:** M7, approval.
- **Acceptance criteria:** Same results as file store for the parity suite; no new runtime dependency (uses `sqlite3`).
- **Tests:** TST-PS-* parity; crash-consistency tests.
- **Security implications:** SQLite file permissions and injection (parameterized queries only).
- **Risks:** Two stores to maintain.
- **Effort (rough):** 4–7 days, if approved.
- **Verification evidence:** Parity test output.
- **Required approval:** Yes, and a separate decision to proceed.

### M13 — Security hardening

- **Objective:** Verify every threat with a control has a passing test; close gaps where feasible; document residual risks.
- **Scope:** Full THREAT_MODEL §3 review; SR-01 … SR-12 verification; static checks (TST-SEC-003); network-disabled tests (TST-SEC-004); dependency audit; regex review; secret-pattern review; written decision on process isolation (OD-06; ARCHITECTURE §11.1). M13 produces a decision document only. No isolation code is written in M13.
- **Deliverables:** Security verification record; updated THREAT_MODEL and SECURITY with status per threat; residual-risk acceptance list (RR-01 … RR-08).
- **Dependencies:** M11.
- **Acceptance criteria:** Every SR-* has a passing test or an approved residual; no High-impact threat is "unverified".
- **Tests:** All TST-SEC-*; TST-SEC-018 (seeded corpus).
- **Security implications:** This milestone is the security gate.
- **Risks:** Late discovery of design flaws. Mitigation: earlier per-milestone security tests.
- **Effort (rough):** 3–6 days.
- **Verification evidence:** Security verification record listing each test ID and result.
- **Required approval:** Yes, and explicit acceptance of residual risks.

### M14 — Integration and end-to-end tests

- **Objective:** Prove the complete workflows J1–J5 (PRD §11) from a clean environment.
- **Scope:** E2E tests; seeded regression pair; executable documentation checks (TST-DOC-001, TST-DOC-002); traceability check (TST-DOC-004); documentation-to-model consistency check.
- **Deliverables:** `tests/e2e/`, `examples/regression_pair/`, traceability report.
- **Dependencies:** M13.
- **Acceptance criteria:** TST-E2E-001, TST-E2E-002 pass with expected findings matching the fixture manifest; traceability check reports zero unlinked requirements.
- **Tests:** TST-E2E-*; TST-DOC-*.
- **Security implications:** Network-disabled E2E run.
- **Risks:** Flaky timing-based tests (latency evaluator). Mitigation: fixture latencies far from thresholds; no timing assertions on wall-clock beyond fixture design.
- **Effort (rough):** 3–5 days.
- **Verification evidence:** E2E output; traceability report.
- **Required approval:** Yes.

### M15 — Packaging and documentation

- **Objective:** Make the package installable and documented for users and contributors.
- **Scope:** README (installation, quick start, limits), API documentation, CLI reference, CI workflow files (project CI per TEST_STRATEGY §8), example GitHub Actions workflow (PRD-F-030), CONTRIBUTING with DCO sign-off requirement (OD-31), an automated DCO check in CI that must be running before any external contribution is accepted (OD-31; method OD-32), CODE_OF_CONDUCT (OD-17), CHANGELOG, SECURITY.md contact (OD-20), `.gitignore` template.
- **Deliverables:** Release candidate package; documentation set; CI configuration (not yet executed for release).
- **Dependencies:** M14.
- **Acceptance criteria:** TST-E2E-004, TST-E2E-005 pass; README quick start executed by TST-E2E-001; documentation link check passes (TST-DOC-005).
- **Tests:** Packaging tests; link checks; documentation tests.
- **Security implications:** Secret scan (OD-24); licence headers; no real data in package.
- **Risks:** Documentation drift. Mitigation: executable docs.
- **Effort (rough):** 3–5 days.
- **Verification evidence:** Build logs; install logs in clean environments; link check output.
- **Required approval:** Yes.

### M16 — Release readiness

- **Objective:** Verify the release candidate against the full checklist and prepare for an approval decision. **No publication or push without explicit approval.** Publication also requires gate G-2 (package-index and trademark checks completed) and replacement of the copyright-year placeholder with the year of initial publication (OD-01).
- **Scope:** RELEASE_CHECKLIST §1 … §13; final test run on the full matrix; dependency and licence review; secret scan; known-limitations review.
- **Deliverables:** Release verification record; release notes draft; decision request.
- **Dependencies:** M15.
- **Acceptance criteria:** Every checklist item marked complete with evidence; zero failing tests; all residual risks accepted in writing.
- **Tests:** Full suite on the matrix.
- **Security implications:** Supply chain verification (THREAT_MODEL THR-015).
- **Risks:** Last-minute scope pressure. Mitigation: scope rule (PRD §12).
- **Effort (rough):** 2–4 days.
- **Verification evidence:** Complete checklist with evidence links to CI runs and logs.
- **Required approval:** Yes — explicit approval is required before any release action.

### M17 — Optional process isolation (post-MVP; only if approved)

- **Objective:** Provide opt-in isolation for `module:attribute` targets, if the owner approves after M13.
- **Scope:** JSON protocol over a pipe; fresh process per case by default; documented state semantics; crash detection with reason code `TARGET_CRASHED`; stdout and stderr capture; cross-platform tests. Limited to reference targets.
- **Deliverables:** Isolation mode in `runner/`; documentation of the fault-boundary and non-sandbox status.
- **Dependencies:** M13 decision; M11.
- **Acceptance criteria:** Timeouts terminate the direct child process on all three OSes in the test matrix; crashes produce `TARGET_CRASHED`; documentation states that isolation is not a sandbox.
- **Tests:** New family to be defined at approval (TEST_STRATEGY §4.3 extension).
- **Security implications:** Inherited environment reaches the child unless filtered; a subprocess has the same user, filesystem, and network access. No security claim.
- **Risks:** Orphaned grandchild processes; platform differences; startup cost.
- **Effort (rough):** To be estimated after the M13 decision.
- **Verification evidence:** Test output on the matrix.
- **Required approval:** Yes, both to start and to complete.

## 4a. Progress and approvals

| Milestone | Status | Approval | Record | Committed |
|---|---|---|---|---|
| M1 Project foundation | Complete | Approved 2026-10-27 | docs/MILESTONE_1_RECORD.md | Yes (4a144a1) |
| M2 Data models and validation | Complete | Approved 2026-10-27, deviations accepted | docs/MILESTONE_2_RECORD.md | Yes (4a144a1) |
| M3 Dataset loading | Complete | Approved 2026-10-27, decisions 1–4 accepted | docs/MILESTONE_3_RECORD.md | Yes (4a144a1) |
| M4 Target interface | Complete | Approved 2026-10-27, decisions 1–3 accepted | docs/MILESTONE_4_RECORD.md | **No** (pending instruction) |
| M5 Deterministic evaluators and registry | Complete | Approved by "proceed" 2026-10-27; D-7 still open | docs/MILESTONE_5_RECORD.md | No |
| M6 Evaluation runner | Complete | Approved 2026-10-27; D-11 and interruption decision confirmed | docs/MILESTONE_6_RECORD.md | No |
| M7 Normalisation and persistence | Complete | Pending approval; six owner-decision defaults need confirming | docs/MILESTONE_7_RECORD.md | No |

Test status at M4 approval: 194 tests pass on Python 3.11, 3.12, and 3.13 (macOS). Lint and strict type checks pass.

## 5. Milestone completion record (template)

```
Milestone: Mx — name
Scope delivered: …
Requirements verified: PRD-… / TRD-…
Tests run: <command>  →  <exact result: N passed, M failed, K skipped, with reasons>
Security checks: …
Known issues / unresolved: …
Deviations from plan (with impact): …
Approval requested: yes / no
```

Results are recorded exactly as observed. A failing or skipped test is reported, not
omitted (CLAUDE.md, "Report exact test results").

## 6. Overall risks

| Risk | Effect | Mitigation |
|---|---|---|
| Semantics drift from specification during implementation | Results no longer match documented meaning | Milestone gates; table-driven tests of status rules; doc tests |
| Scope expansion | Delay, complexity, security surface | Scope rule (PRD §12); change impact note required |
| Windows-specific file behaviour | Failures on one OS | Windows in CI from M1 |
| Dependency vulnerabilities | Release blocked | Minimal dependencies; `pip-audit` |
| Threads from timeouts | Resource growth | Counter; documentation; OD-06 decision |
| Overclaiming in documentation | Trust and safety impact | Banned-claims test; review gates |

## 7. Open items affecting the plan

See [OPEN_DECISIONS](OPEN_DECISIONS.md).

- **Approved:** OD-01 to OD-06, OD-15, OD-31 (final confirmation).
- **Provisional:** OD-10 (package name). Usable for local scaffolding; publication is blocked until gate G-2.
- **Gates:** G-1 before installing any dependency; G-2 before any publication.
- **Open before M5:** OD-07. **Before M7:** OD-11, OD-12, OD-21, OD-22, OD-27, OD-30. **Before M9:** OD-09, OD-13, OD-28. **Before M10:** OD-08.


## 8. Next steps (from Milestone 5)

The detailed execution plan for Milestones 5 to 11 is in [docs/EXECUTION_PLAN_NEXT_MILESTONES.md](docs/EXECUTION_PLAN_NEXT_MILESTONES.md). The list below is the summary.

Each step has an owner decision, a deliverable, and a check. Work proceeds in this order. Each
milestone still needs its completion record and your approval before the next one starts.

### 8.1 Preconditions and carry-over obligations

| ID | Step | Deliverable | Check | Owner action |
|---|---|---|---|---|
| PRE-1 | Re-lock the project with uv 0.13.6, the verified version | Updated `uv.lock`; version recorded in the record | `uv lock` succeeds; tests pass | Confirm |
| PRE-2 | Decide OD-07 (JSON Schema evaluator) | OPEN_DECISIONS updated | — | Decide (recommended: not in MVP) |
| CO-1 | **Redact exception messages before any persistence.** Binding before Milestone 7 writes results. | Redaction applied to `ErrorObject` and evaluator messages; test TST-RD-003 | Planted-secret test fails before, passes after | Confirm the redaction rules (SECURITY §4.6) |
| CO-2 | Serialise the records that Milestone 7 persists | JSON round-trip for case, evaluator, and target results | Serialise-and-compare test | — |
| CO-3 | Build the models deferred from Milestone 2 | Dataset fingerprint (M3/M7), manifest and summary (M7), comparison and finding (M9/M10) | Model tests per milestone | — |

### 8.2 Milestone 5 — Deterministic evaluators and registry

1. Define the evaluator protocol: `name`, `version`, `requires_expected`, and a pure `evaluate(case, output, duration_ms)` (TRD-080, TRD-081).
2. Implement the six built-in evaluators: `exact_match`, `normalized_text`, `json_structure`, `required_fields` (dotted-path lookup), `rule_based` (contains, not-contains, regex, length; the first failing rule is reported), and `latency`.
3. Apply the `NO_EXPECTED` skip before an evaluator runs (TRD-083).
4. Load custom evaluators from `module:attribute` references. Check `interface_version`. Map an exception to `EVALUATOR_EXCEPTION` and a malformed result to `EVALUATOR_RESULT_INVALID` (TRD-084).
5. Fingerprints: built-ins hash their type and parameters; custom evaluators hash the module, qualified name, version, and the SHA-256 of the defining source file (TRD-085).
6. A registry maps configured types to factories. It consumes the `EvaluatorSettings` produced by Milestone 2.
7. Runtime limit on regex input length of 1 MiB (TRD-091).
8. Tests: TST-EV-001 to TST-EV-029, including the rule that no built-in returns INCONCLUSIVE (TST-EV-029).
9. Checks: lint, strict type check, tests on all three Python versions.
- **Decision needed:** OD-07.

### 8.3 Milestone 6 — Evaluation runner

1. Run the cases sequentially, in dataset order, using `invoke_target` from Milestone 4.
2. Apply each evaluator with the skip rules, then aggregate with `aggregate_case_status`.
3. Best-effort timeouts in a worker thread. Count threads that may still be alive (`threads_possibly_running`). Warn in the summary (TRD-070 to TRD-075). OD-06 applies.
4. Interruption: on `KeyboardInterrupt`, finish the current case within a grace period of 5 seconds, then mark the run `ABORTED` (TRD-103).
5. Engine error boundary: an unexpected exception becomes `ENGINE_ERROR` with exit 4 (TRD-104).
6. Produce an in-memory run object. Persistence waits for Milestone 7.
7. Tests: TST-TG-004, TST-TG-009, TST-TG-012, and the aggregation table T1 to T10.
- **Decisions needed:** none new. OD-13 is needed by Milestone 9.

### 8.4 Milestone 7 — Normalisation and persistence

1. Create run directories with a UUIDv4 name. Refuse to reuse an existing directory (TRD-110, TRD-111).
2. Exclusive lock file per run (TRD-121).
3. Write `cases.jsonl` by appending and flushing one record at a time. Write the manifest and summary atomically through a temporary file and `os.replace` (TRD-112, TRD-113).
4. Record `cases_sha256` and `summary_sha256` in the manifest (TRD-114; ARTIFACT_INTEGRITY §2).
5. Apply `io_mode` (`full`, `hashes`, `none`) and the redaction module (DATA_HANDLING §3, §7). **Completes CO-1.**
6. Never store tracebacks. Truncate and redact exception messages (DATA_HANDLING §4).
7. Store a configuration snapshot with secret-like values removed. Store only the minimal environment metadata (DATA_HANDLING §5, §6).
8. Statistics: Wilson interval and nearest-rank percentiles. Check the vectors independently (TEST_STRATEGY §4.6). This also re-derives the worked example.
9. `Run.load` with integrity checks. Schema major-version checks (PRD-NF-009).
10. Windows file-replace and locking tests (TST-XP-004 and related).
11. Tests: TST-PS-101 to TST-PS-109, TST-IN-001 to TST-IN-004, TST-IO-001 to TST-IO-009, TST-RD-001 to TST-RD-006.
- **Decisions needed before M7:** OD-11 (run root), OD-12 (final `io_mode` default), OD-21 (exception redaction), OD-22 (permissions), OD-27 (configuration may disable redaction), OD-30 (platform string).

### 8.5 Milestone 8 — Reporting

1. Terminal output with control-character and bidirectional-override sanitisation (SECURITY §6).
2. JSON reports with `schema_version`. Hand-written JSON Schema files, validated by tests (closes the PRD-F-025 gap).
3. Golden-output fixtures for run, inspect, and report output.
4. Footer wording. Owner decision on OD-18.
5. Banned-claims scan over user-facing strings (TST-DOC-003).
- **Decision needed:** OD-18.

### 8.6 Milestone 9 — Run comparison

1. Compatibility checks: dataset hash, evaluator fingerprints, schema version, run status, and integrity (ARTIFACT_INTEGRITY §6.1).
2. Case categories: regressed, recovered, unchanged, changed, missing, new, and changed_input (EVALUATION_METHODOLOGY §5).
3. Overrides as explicit arguments with a banner, `compatibility.overrides`, and a `COMPARISON_OVERRIDDEN` warning (TRD-136 to TRD-137).
4. `--strict` mode (TRD-138).
5. Byte-identical output for identical inputs (TST-CM-016).
6. Tests: TST-CM-001 to TST-CM-022.
- **Decisions needed:** OD-09 (confirmed as refuse by default), OD-13, OD-28.

### 8.7 Milestone 10 — Regression detection

1. Thresholds from the `[regression]` table (TRD §9.1).
2. Finding codes and golden messages (TRD §9.2).
3. Infrastructure errors are never reported as `CASE_REGRESSED_TO_FAIL` (TST-CM-012).
4. Tests: TST-CM-009 to TST-CM-015.
- **Decision needed:** OD-08.

### 8.8 Milestone 11 — CLI and Python API

1. `argparse` commands from CLI_SPECIFICATION §3: `config validate`, `dataset validate`, `run`, `inspect`, `compare`, `report export`.
2. Exit codes 0 to 5 with the precedence rules (CLI §1.4).
3. Public API with `__all__`, matching API_DESIGN §2.
4. Parity tests: CLI and API produce identical results for identical inputs.
5. Show dataset warnings (for example symbolic links) in the CLI output.
- **Decisions needed:** OD-25, OD-26.

### 8.9 Milestone 12 — SQLite (deferred)

No work scheduled. Revisit only with a new owner approval (OD-05).

### 8.10 Milestone 13 — Security hardening

1. Verification matrix: each threat in THREAT_MODEL §3 mapped to a passing test or an approved residual risk.
2. Static checks for `eval`, `exec`, `pickle`, unsafe YAML loading, and `shell=True` (TST-SEC-003).
3. Network-isolation test (TST-SEC-004).
4. Dependency audit. Verify the audit tool before installing it, as for G-1.
5. Regex review (SECURITY §7).
6. Written reassessment of process isolation (OD-06). No isolation code in this milestone.
7. Residual risks RR-01 to RR-08 presented for written acceptance.

### 8.11 Milestone 14 — Integration and end-to-end tests

1. Quick start from a clean environment (TST-E2E-001).
2. Seeded regression pair with an expected findings manifest (TST-E2E-002).
3. Traceability check that fails if any requirement is untested.
4. Executable documentation: API_DESIGN and CLI examples (TST-DOC-001, TST-DOC-002).
5. Link check (TST-DOC-005) and the integrity-scope check against the manifest writer (TST-DOC-007).

### 8.12 Milestone 15 — Packaging and documentation

1. Complete README, API reference, and CLI reference.
2. Complete CI: the Python matrix on Linux, macOS, and Windows, plus mypy, lint, tests, audit, build, and the `dco` job (OD-31 requires the DCO job before external contributions).
3. Example GitHub Actions workflow that uploads summaries only (OD-23).
4. `CODE_OF_CONDUCT.md` (OD-17), `SECURITY.md` contact (OD-20), and a secret-scanning tool (OD-24). Verify the scanner's licence and status before adoption.
5. Synthetic example datasets, each labelled as synthetic.
6. CHANGELOG and `.gitignore` template.
- **Decisions needed:** OD-17, OD-20, OD-23, OD-24, OD-32 (DCO enforcement method).

### 8.13 Milestone 16 — Release readiness (no publication without approval)

1. Complete the release checklist with evidence.
2. Gate G-2: package-index and trademark checks for the distribution name, and a decision on the PyPI name conflict (OD-10). **Owner action required; the name is already used on PyPI.**
3. Replace the copyright-year placeholder with the year of initial publication (OD-01).
4. Record residual risks RR-01 to RR-08 as accepted.
5. Release notes and a decision request. Stop until approved.

### 8.14 Blockers outside the code

| Item | Why it blocks | Owner action |
|---|---|---|
| A git remote and authority to push | The first CI run on Linux and Windows needs a remote | Provide a remote and authorise the push |
| Choice of DCO enforcement method (OD-32) | Required before any external contribution | Choose the method |
| Copyright-year placeholder convention | Needed for headers and NOTICE before any publication | Confirm the placeholder token approach |
| Distribution name (OD-10) | Publication is blocked while `evalforge` is used on PyPI | Choose a distribution name and complete the checks |
