# EvalForge — Release Checklist

Status: **Planning checklist. No release has been prepared, tagged, published, or pushed.**

Rule: nothing in this checklist authorises publication, pushing, tagging, or creating a
release. Each of those actions requires explicit approval from the project owner, given
for that specific action (CLAUDE.md, "Approval requirements"; PRD §8 non-goal PRD-NG-011).

Each item has a status. Allowed statuses: `Not started`, `In progress`, `Done (evidence: …)`,
`Blocked (reason: …)`, `Not applicable (reason: …)`. An item marked "Done" without evidence
is not done.

---

## 1. Approval gate

- [ ] All milestones M1–M15 have approved completion records (IMPLEMENTATION_PLAN §5).
- [ ] Specifications have been approved (PLANNING_SUMMARY, OPEN_DECISIONS resolved or
      explicitly deferred).
- [ ] Release candidate scope matches PRD §12 (no unapproved additions).
- [ ] Project owner has given explicit approval for release preparation.
- [ ] Package-index and trademark checks completed and recorded (gate G-2, OD-10). Publication blocked until then.
- [ ] Project owner has given explicit approval for each of: tagging, publishing to a
      package index, pushing to a public remote, and creating a public release page.

## 2. Licensing and notices (PRD-NF-012)

- [ ] `LICENSE` contains the full Apache License 2.0 text, unmodified.
- [ ] `NOTICE` names Bodepudi Ronith as copyright holder and includes required third-party notices, if any (OD-01).
- [ ] Short Apache-2.0 header present in every source file (OD-01). Copyright year is the year of initial publication; the placeholder is replaced before publication (OD-01; placeholder approach to be confirmed, OPEN_DECISIONS §4).
- [ ] Package metadata declares `Apache-2.0` (TRD-011).
- [ ] Licence of every bundled file (examples, fixtures, documentation images) is confirmed as project-owned or permissively licensed.
- [ ] No copied code from other projects without attribution and licence compatibility review. (Research used documentation only; RESEARCH_NOTES §1.)

## 3. Dependency and licence review (TRD-022)
- [ ] Gate G-1 completed before installing dependencies: Hatchling and uv versions, licences, maintenance status, and check dates recorded (OPEN_DECISIONS §3). **Not yet run.**

- [ ] Lock file committed; resolved versions recorded in the release record.
- [ ] Each runtime dependency's licence reviewed and recorded (expected to be permissive; verify).
- [ ] Each development dependency's licence reviewed (recorded; not distributed).
- [ ] Dependency count matches TRD §3.2 approved list (PRD-NF-006 test passes).
- [ ] No dependency with network telemetry by default.

## 4. Supply chain and vulnerabilities (THREAT_MODEL THR-014, THR-015)

- [ ] `pip-audit` run on the lock file; output recorded. Any high-severity finding resolved or documented as accepted.
- [ ] Build performed in a clean CI environment, not on a developer workstation.
- [ ] Artifacts built from a tagged commit (after approval) with recorded commit hash.
- [ ] Checksums (SHA-256) generated for sdist and wheel and published with the release notes (when approved).
- [ ] Publication method reviewed (trusted publishing preferred; method recorded).
- [ ] Package name availability and trademark checks completed (OD-10). Name is provisional until then.
- [ ] Two-person review of release-related changes (proposed; applies if a second maintainer exists — OD-17).

## 5. Secret scanning (SECURITY §8, OD-24)

- [ ] Secret scanner run over the full repository history (not just the working tree).
- [ ] Any finding investigated; confirmed false positives recorded with justification.
- [ ] Confirmed secrets rotated and removed from history (history rewrite requires explicit approval).
- [ ] Planted-secret test fixtures are clearly fake and excluded from the scanner's reporting if necessary, with reason recorded.
- [ ] `.gitignore` excludes `.evalforge/`, virtual environments, build outputs, and any local credentials files.

## 6. Versions and support (SECURITY §2)

- [ ] Version number chosen (semantic versioning, TRD-240); pre-1.0 status stated.
- [ ] `CHANGELOG.md` entry written: added, changed, fixed, security, known limitations.
- [ ] Supported-version statement written (which versions receive fixes).
- [ ] Schema versions of artifacts documented (DATA_MODELS §1, §13).
- [ ] Deprecations listed with the minimum period (TRD-243).

## 7. Documentation

- [ ] README: purpose, the limits statement, installation, quick start, link to docs.
- [ ] Installation instructions verified from clean environments (TST-E2E-004).
- [ ] Quick start executed by a test (TST-E2E-001).
- [ ] API documentation generated from public names; matches API_DESIGN §2 (TST-API-004).
- [ ] CLI reference matches CLI_SPECIFICATION (TST-DOC-002).
- [ ] EVALUATION_METHODOLOGY published with the package or linked (status semantics, limitations).
- [ ] Security documentation linked from README (SECURITY, THREAT_MODEL summary, DATA_HANDLING).
- [ ] Known-limitations section (§12 below) included in release notes.
- [ ] ARTIFACT_INTEGRITY.md published with the package documentation; its scope table matches the manifest (TST-DOC-007).
- [ ] Sensitive-data defaults documented: `io_mode`, redaction, and how to disable them (DATA_HANDLING §3, §7).
- [ ] Banned-claims scan passes (TST-DOC-003).
- [ ] Documentation link check passes (TST-DOC-005).
- [ ] Synthetic-data notice present in each example README (DATA_HANDLING §10).

## 8. Tests and CI

- [ ] Full test suite passes on Linux, macOS, Windows × Python 3.11, 3.12, 3.13 (TST-XP-001; OD-02). Exact results recorded, including any skipped tests and reasons.
- [ ] Security tests pass (TEST_STRATEGY §4.8).
- [ ] Static checks pass (no `eval`, `exec`, `pickle`, unsafe YAML, `shell=True`; TST-SEC-003).
- [ ] Network-disabled tests pass (TST-SEC-004).
- [ ] Lint and format checks pass (ruff).
- [ ] `mypy --strict` passes on the public package (required CI gate, OD-15).
- [ ] Traceability check reports no unlinked PRD or TRD requirement (TST-DOC-004).
- [ ] Benchmark results (BM-001 … BM-005) recorded with environment, or explicitly marked "not measured" in release notes (PRD-NF-007, TRD §16).
- [ ] Coverage reported; no coverage claim beyond the measured number.

## 9. Packaging validation (TST-E2E-004, TST-E2E-005)

- [ ] sdist builds; wheel builds; both install in clean environments on each OS.
- [ ] Installed entry point `evalforge --version` reports the release version.
- [ ] Package contents inspected: no test data containing real content, no `.evalforge/` directories, no credentials, LICENSE and NOTICE included.
- [ ] `py.typed` marker included (TRD-171).
- [ ] Metadata (name, version, description, classifiers, project URLs) reviewed. URLs point to repositories the owner controls.

## 10. Synthetic example data (DATA_HANDLING §10)

- [ ] Each example dataset is synthetic; its README says so.
- [ ] No real user data, personal data, or proprietary text in examples.
- [ ] Examples are reviewed by a person other than the author (proposed).
- [ ] Hostile corpus is clearly labelled as test material, not for evaluation use.

## 11. Community and project files

- [ ] `CONTRIBUTING.md`: how to propose changes, the spec-first workflow, test requirements, the security rule (report privately), and the DCO sign-off requirement for external contributions (OD-31). Automated DCO enforcement must be running before any external contribution is accepted (OD-31). Method is open (OD-32).
- [ ] `CODE_OF_CONDUCT.md`: text selected and attributed (OD-17). Attribution and licence of the chosen text verified before inclusion.
- [ ] `SECURITY.md`: reporting channel defined (OD-20) and published. No personal email in repository files unless the owner chooses it.
- [ ] Issue templates (proposed; optional).
- [ ] Pull request template with checklist (proposed; optional).

## 12. Known limitations (must appear in release notes)

Copied from SECURITY §10 and THREAT_MODEL §6:

- [ ] Custom evaluators and targets are trusted code and are not sandboxed (RR-01).
- [ ] Timeouts do not stop target threads; resource use may continue (RR-02).
- [ ] Regex matching has no timeout (RR-03).
- [ ] Artifacts can be rewritten by a party with write access (RR-04).
- [ ] Secret redaction is heuristic; exception messages are not redacted (RR-05).
- [ ] Users may store sensitive data in run artifacts (RR-06).
- [ ] Scores are not safety or correctness certifications (RR-07; EVALUATION_METHODOLOGY §12).
- [ ] Deterministic evaluators measure form and rules, not meaning (EVALUATION_METHODOLOGY §4).
- [ ] No model-based evaluators in this release.
- [ ] Performance targets listed in TRD §16 are unmeasured unless benchmark results are attached.
- [ ] Dependencies may have vulnerabilities after release (RR-08).
- [ ] Timeouts are best-effort; threads cannot be stopped; no process isolation in this release (RR-02; ARCHITECTURE §11.1).
- [ ] Redaction is heuristic and does not guarantee removal of sensitive information (RR-05; DATA_HANDLING §7.4).
- [ ] Artifact hashes are a consistency check, not tamper evidence; manifest is not hashed (RR-04; ARTIFACT_INTEGRITY §5).
- [ ] Comparison overrides are explicit and recorded; `--strict` available (ARTIFACT_INTEGRITY §6).
- [ ] Custom targets and evaluators are trusted code (RR-01).

## 13. Release verification and final decision

- [ ] Every item above is `Done` with evidence, or `Not applicable` with a reason.
- [ ] Release verification record prepared: commit hash, CI run links, test counts, artifact checksums, known issues.
- [ ] Residual risks RR-01 … RR-08 accepted in writing by the project owner.
- [ ] Release notes draft reviewed.
- [ ] Decision request submitted to the project owner. **Stop here until explicit approval is received.**

After approval, each publication step is performed separately, recorded, and verified
(installation from the published index in a clean environment).
