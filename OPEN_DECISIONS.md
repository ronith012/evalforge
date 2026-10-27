# EvalForge — Decision Record

Status: **Approved by the owner in the final confirmation.** Milestone 1 has not started.
Implementation requires explicit authorisation.

Status values: **Approved** (owner decision recorded), **Provisional** (approved for local use
with conditions), **Open** (no decision yet), **Gate** (a condition that must be met before a
specific action).

Total: 32 decisions. OD-01 to OD-26 are the original decisions. OD-27 to OD-30 were added in the
revised planning. OD-31 (DCO policy) was approved. OD-32 (DCO enforcement method) is open.
Two gates (G-1, G-2) are listed in §3 and are not counted as decisions.

## 1. Approved decisions (owner, final confirmation)

| ID | Decision | Approved position | Where applied |
|---|---|---|---|
| OD-01 | Copyright holder, licence, notices | Copyright holder **Bodepudi Ronith**. Licence **Apache-2.0**. A `NOTICE` file and a short header in each source file. Copyright notices use the **actual initial publication year**. | TRD-011; IMPLEMENTATION_PLAN M1; RELEASE_CHECKLIST §2; PRD-NF-012 |
| OD-02 | Python support | **3.11, 3.12, and 3.13** initially, with **all three tested in CI**. | TRD-001; TRD-237; PRD-NF-005; PRD A-01; TEST_STRATEGY §8 |
| OD-03 | CLI, build backend, development tooling | CLI **argparse**. Build backend **Hatchling**. Development environment management and lock-file generation **uv**. | TRD §3.2, TRD-010, TRD-020, TRD-165; ARCHITECTURE AD-012; IMPLEMENTATION_PLAN M1 |
| OD-04 | Configuration file format | **TOML** (`evalforge.toml`). | TRD-180; ARCHITECTURE AD-007; DATA_MODELS §4 |
| OD-05 | Run-directory persistence | **JSON/JSONL** run-directory persistence. **SQLite deferred.** | TRD §7; ARCHITECTURE AD-002; IMPLEMENTATION_PLAN M12 (deferred) |
| OD-06 | Target timeouts and process isolation | **Best-effort timeouts in the MVP. Reassess process isolation in M13.** | TRD §5.3; SECURITY §10; ARCHITECTURE §11.1, AD-003; IMPLEMENTATION_PLAN M13 |
| OD-15 | Runtime dependencies, validation, type checking | **Zero third-party runtime dependencies.** **Standard-library validation.** **`mypy --strict` is a required CI gate.** | TRD §3.2, TRD-024; ARCHITECTURE §14, AD-009; TEST_STRATEGY §8; RELEASE_CHECKLIST §8; PRD-NF-006 |
| OD-31 | Contributor policy | **Require DCO sign-off for external contributions and automate enforcement before accepting them.** Enforcement method is OD-32. | RELEASE_CHECKLIST §11; SECURITY §12; IMPLEMENTATION_PLAN M15; TEST_STRATEGY §4.13 (TST-CI-001) |

## 1a. Provisional decision (approved for local use with conditions)

| ID | Decision | Approved position | Conditions |
|---|---|---|---|
| OD-10 | Package name | **"EvalForge" may be used as a provisional local package name.** | **Publication is blocked** until package-index availability and trademark checks have been completed. These checks have **not** been run. See G-2. |

Notes on approved items:

- **OD-01:** Copyright notices use the year of initial publication. That year is unknown until
  the first publication. Until then, files carry a placeholder that must be replaced before any
  publication (see §4, item 1).
- **OD-02:** "Initially" means this is the first supported set. Adding or removing versions needs
  a new decision. Each version must pass the CI matrix.
- **OD-03:** uv is a development tool. Contributors need it installed. It is not a runtime dependency.
  Hatchling and uv are subject to gate G-1 before installation.
- **OD-06:** This is the owner's approval of the MVP behaviour. No isolation is implemented in the MVP.
  M13 must produce a written reassessment.
- **OD-15:** `mypy --strict` must pass before merge. This applies to the public package in `src/evalforge`.

## 2. Open decisions

| ID | Decision | Status | Current position | Blocks M1? | Needed by |
|---|---|---|---|---|---|
| OD-07 | JSON Schema evaluator in MVP | Open | Not in MVP; optional extra later | No | M5 |
| OD-08 | Default regression thresholds | Open | Zero tolerance for new failures and errors; 0.0 rate drop; min 30 executed; missing-case policy fail | No | M10 |
| OD-09 | Changed datasets and evaluators in comparisons | Open | Refuse by default; visible explicit overrides | No | M9 |
| OD-11 | Default run root | Open | `.evalforge/runs/` beside the config file; gitignored | No | M7 |
| OD-12 | Default `io_mode` | Open | `full` locally; `hashes` in the example CI workflow | No | M7 |
| OD-13 | ERROR in pass-rate denominator; FAIL → ERROR gating | Open | ERROR counted; FAIL → ERROR is `changed`, not regression, unless configured | No | M9 |
| OD-14 | Model-based evaluators | Open | Defer past MVP | No | Post-MVP |
| OD-16 | User research | Open | Small study before release; no figures assumed | No | M16 |
| OD-17 | Governance: maintainers, code of conduct, release review | Open | Maintainer names needed; code of conduct text to be verified before inclusion | No | M15 |
| OD-18 | Report footer wording | Open | Approve the draft in EVALUATION_METHODOLOGY §12 or amend it | No | M8 |
| OD-19 | CI annotations (SARIF etc.) | Open | Defer past MVP | No | Post-MVP |
| OD-20 | Vulnerability reporting channel | Open | Private channel the owner controls. No address published. | No | M15 |
| OD-21 | Redaction of exception messages | Open | Apply the heuristic; document misses | No | M7 |
| OD-22 | Run-directory permissions | Open | Owner-only on POSIX; Windows ACLs documented | No | M7 |
| OD-23 | CI example uploads `cases.jsonl` | Open | No | No | M15 |
| OD-24 | Secret-scanning tool | Open | Choose at M15 from permissive tools; not selected or verified | No | M15 |
| OD-25 | Exit behaviour of `evalforge run` | Open | Exit 0 on completion unless `--fail-on` is given | No | M11 |
| OD-26 | Exit code for `inspect` of an incomplete run | Open | Exit 0 with an "incomplete" line; `compare` refuses | No | M11 |
| OD-27 | Config may disable redaction | Open | Allowed; recorded and warned | No | M7 |
| OD-28 | Overrides in CI: `--strict` default or opt-in | Open | `--strict` opt-in; CI recipe recommends it | No | M9 |
| OD-29 | Manifest signing after MVP | Open | Defer; document external anchors | No | Post-MVP |
| OD-30 | Store full platform string | Open | Do not store; store minimal environment set | No | M7 |
| OD-32 | DCO enforcement method | **Open** | Approved requirement: automated enforcement before accepting external contributions (OD-31). Tool or method not chosen (for example a CI check or a hosted DCO check). | No | Before the first external contribution |

## 3. Effect on Milestone 1

All decisions needed to start Milestone 1 are approved. Milestone 1 has not started and needs
explicit authorisation. Two gates apply.

### Gate G-1: verify tooling before installation

Before any dependency is installed, the versions of **Hatchling** and **uv** to be used must be
verified and recorded: version, licence, maintenance status, and the date of the check.
**No installation has been performed, and these checks have not been run.**

### Gate G-2: publication checks

Before any publication, package-index availability and trademark checks for "EvalForge" must be
completed and recorded. Until then, publication is blocked (OD-10). **These checks have not been run.**
Scaffolding under the provisional name does not publish anything.

## 4. Unresolved issues after the final confirmation

1. **Copyright year placeholder (OD-01).** The approved rule is the year of initial publication.
   Source headers and `NOTICE` need a placeholder until then. *Proposed, not yet approved:* a single
   token such as `YEAR_OF_INITIAL_PUBLICATION`, plus a release check (M16) that fails if any
   placeholder remains. Please confirm this approach or give another.
2. **DCO enforcement method (OD-32).** Automated enforcement is approved. The tool or method is not chosen.
3. **Package name and trademark checks (OD-10, G-2)** have not been run. Publication stays blocked.
4. **Hatchling and uv verification (G-1)** has not been run. Versions, licences, and maintenance
   status are unknown in this record.
5. **Python 3.11–3.13 compatibility** has not been verified. It will be tested in CI once the matrix exists (OD-02).
6. **`mypy --strict` cost.** Every module needs full type annotations from Milestone 1 on (OD-15).

## 5. Recording a further decision

When a decision is made, change its status here, record the owner's wording, and update every
document that cites its ID. Citing documents are listed in PLANNING_SUMMARY §10.

## 6. Analysis: alternatives, rationale, and consequences

Retained from the revised planning review so the reasoning stays on record. For approved
decisions, the alternatives are the ones the owner did not choose.

| ID | Alternatives considered | Rationale | Technical consequences |
|---|---|---|---|
| OD-01 | No per-file headers (NOTICE only); project name as holder | Apache-2.0 notice requirements; consistent attribution | Header check added to lint; each file carries the header |
| OD-02 | 3.10+ (needs a TOML backport); add 3.14 once verified | `tomllib` is in the standard library from 3.11 | CI matrix of 3 Python × 3 OS. Current support status not verified |
| OD-03 | Typer or Click (third-party dependencies); setuptools or flit as backend | Zero runtime dependencies reduce supply-chain exposure (THR-014) | More parser and help code, covered by CLI tests. uv must be installed by contributors |
| OD-04 | YAML (parser dependency, safe loading); JSON (no comments); Python module (executes code) | Standard library; comments supported; configuration cannot execute code | Requires Python 3.11+; hand-written validation (TRD-182) |
| OD-05 | SQLite in MVP; both backends | Inspectable, diffable, no extra dependency | Integrity limits apply (ARTIFACT_INTEGRITY); lock-file concurrency; no query interface |
| OD-06 | Subprocess per call in MVP; POSIX-only signal timeouts; no timeouts | Threads cannot be stopped reliably; subprocess costs (ARCHITECTURE §11.1) | Counter `threads_possibly_running`; warnings; documented limits |
| OD-07 | Include with `jsonschema` as an optional extra; hand-written subset | Not in PRD MVP; avoids a dependency | Schema users write a custom evaluator (PRD-F-106) |
| OD-08 | 0.05 tolerance; latency ratio 1.5 by default | Conservative for deterministic targets; values not validated on data | Noisy targets fail until tuned (EVALUATION_METHODOLOGY §6) |
| OD-09 | Warn and proceed by default; never allow overrides | Silent incomparability is the core failure to prevent (PRD §2) | Re-baselining after changes; overrides recorded (ARTIFACT_INTEGRITY §6) |
| OD-10 | Choose an alternative name now; defer until M16 | A rename after publication is costly | Renaming touches package directory, imports, documentation |
| OD-11 | `./runs/` in project root; user cache directory | Keeps runs with the project; gitignore reduces accidental commits | Project directories hold sensitive data by default |
| OD-12 | `hashes` everywhere; `none` everywhere | Local inspection needs content; shared contexts need less | Local runs store redacted content; CI sets `io_mode` explicitly |
| OD-13 | Exclude ERROR from denominator; treat FAIL → ERROR as regression | Errors should not inflate pass rate but must not be hidden | Pass rate can fall from infrastructure faults; reported as `to_error` |
| OD-14 | Include one provider in MVP; local-model-first | Privacy, cost, reproducibility need design review | No LLM-based check in MVP |
| OD-15 | Pydantic v2 with a TRD-003 amendment; no static type checks | Zero runtime dependencies; CLAUDE.md requires type hints | Hand-written validation; `mypy --strict` as required gate |
| OD-16 | Skip research; maintainer testing only; survey only | No user evidence yet (PRD §14) | Release measures stay undefined until study |
| OD-17 | Single maintainer; community governance model | Release safety; contributor expectations | CONTRIBUTING and code of conduct needed (M15) |
| OD-18 | No footer; shorter footer | Overclaiming risk (THR-019) | Golden-output tests depend on wording |
| OD-19 | GitHub annotations in M11; SARIF | Scope control | CI reads text or JSON output |
| OD-20 | Personal email address in repository files; no channel | SECURITY §3 requires a channel before public release | Must exist before release (M15) |
| OD-21 | Store unredacted with a warning; store type name only | Messages needed for debugging; type-only reduces usefulness | RR-05 residual; TST-RD-003 |
| OD-22 | Process umask default | Run directories may hold sensitive content | Team sharing needs an explicit group setup (documented) |
| OD-23 | Yes, with a warning | DATA_HANDLING §10 | Debugging in CI needs an `io_mode` change |
| OD-24 | Manual review only | RELEASE_CHECKLIST §5 | Extra CI job; triage of false positives |
| OD-25 | Exit 1 on any FAIL or ERROR | Comparison is the gate | CI uses `compare` or `--fail-on` |
| OD-26 | Exit 4 for incomplete runs | `inspect` is diagnostic | Scripts must read the status field |
| OD-27 | Command-line flag only | Explicit and visible | A committed config can disable redaction; warnings mitigate |
| OD-28 | `--strict` as default, with explicit `--allow-*` to proceed | Overrides are already visible; a strict default adds friction | CI teams must add `--strict` |
| OD-29 | Sign manifests in MVP | Authenticity needs key management | No authenticity claim in MVP |
| OD-30 | Store the full platform string | Identifying, little benefit | Less performance-comparison detail |
| OD-31 | Do not require sign-off; contributor licence agreement | DCO is a lightweight, widely used sign-off | Mechanism still to be decided (§4) |
| OD-32 | Manual maintainer review of sign-offs only | An automated check is required by OD-31, so manual review alone does not satisfy it. Tool choice open. | Consistent enforcement across contributors; reduces reviewer load |
