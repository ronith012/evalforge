# EvalForge — Product Requirements Document

Status: **Approved decisions incorporated (see OPEN_DECISIONS.md).** No requirement here is implemented.
License target: Apache-2.0 (per project owner).

Companion documents: [TRD](TRD.md), [ARCHITECTURE](ARCHITECTURE.md),
[DATA_MODELS](DATA_MODELS.md), [CLI_SPECIFICATION](CLI_SPECIFICATION.md),
[API_DESIGN](API_DESIGN.md), [TEST_STRATEGY](TEST_STRATEGY.md),
[OPEN_DECISIONS](../OPEN_DECISIONS.md).

Requirement IDs: `PRD-F-nnn` functional, `PRD-NF-nnn` non-functional,
`PRD-G-nnn` goals, `PRD-NG-nnn` non-goals, `PRD-US-nnn` user stories.

---

## 1. Executive summary

EvalForge is an open-source, model-agnostic framework for evaluating AI
applications, recording the results of each run, and detecting regressions between
a baseline and a candidate version of an application. The MVP is a local Python
package with a CLI and a Python API. It requires no paid API, no external model,
no hosted database, and no network access.

## 2. Problem statement

Teams that ship AI features often evaluate them by hand, with ad hoc scripts, or
with tools whose results are hard to reproduce. Common failures:

- A prompt or model change silently breaks cases that previously worked.
- Scores from one run cannot be traced to the dataset, evaluator, or code version
  that produced them.
- Infrastructure problems (timeouts, exceptions, crashed evaluators) are reported
  as if they were quality failures, which distorts both pass rates and trust in them.
- Two runs are compared even though their datasets or evaluator definitions differ,
  so the comparison is meaningless without anyone noticing.

## 3. Product vision

Make AI evaluation **repeatable, inspectable, and comparable**. A developer should
be able to point EvalForge at a dataset and a target function, run it locally or in
CI, and get per-case results they can trust, plus a clear answer to "did this change
make things worse?"

EvalForge does not claim that a passing score proves an AI system is safe, correct,
or reliable in general. It reports what the configured evaluators measured on the
provided cases.

## 4. Target users

| Segment | Need |
|---|---|
| AI application developers | Fast local feedback when changing prompts, retrieval, or code |
| AI engineers | Repeatable experiments with traceable configuration |
| LLM application developers | Regression coverage for known-good behaviour |
| Developers maintaining AI agents | Case-level visibility into what changed |
| Software engineering teams | Gate pull requests on regressions without vendor lock-in |
| Researchers | Re-runnable experiments with preserved individual results |

## 5. User personas

**P1 — Dana, application developer (primary).** Builds a support assistant in
Python. Changes prompts weekly. Wants `evalforge run` to show which cases broke,
and wants the CI job to fail when a previously passing case now fails.

**P2 — Ravi, AI engineer (primary).** Maintains a RAG pipeline and runs experiments
across configurations. Needs stored run artifacts, metadata about each run, and
confidence that two runs used the same dataset.

**P3 — Mei, engineering lead (secondary).** Reviews whether a release is safe to
ship. Needs a short, accurate summary and the list of regressed cases. Does not
want a single score presented as proof of quality.

**P4 — Sam, open-source contributor (secondary).** Writes a custom evaluator or
target adapter. Needs a documented, stable interface and clear compatibility rules.

## 6. User stories

- PRD-US-001 As Dana, I want to load my evaluation cases from a JSONL file so that
  I can version them with my code.
- PRD-US-002 As Dana, I want validation errors that name the file, line, and field,
  so that I can fix a dataset quickly.
- PRD-US-003 As Dana, I want to point EvalForge at a Python function so that I can
  evaluate my application without wrapping it in a server.
- PRD-US-004 As Dana, I want a case that raises an exception to be recorded as an
  error on that case, so that the rest of the run still completes.
- PRD-US-005 As Dana, I want exact, normalized, JSON, and rule-based checks available
  without writing code.
- PRD-US-006 As Ravi, I want each run to have a unique ID and a manifest recording
  the dataset hash, evaluator definitions, and configuration, so that I can reproduce
  it later.
- PRD-US-007 As Ravi, I want to compare a candidate run against a baseline and be
  told when the datasets or evaluator definitions differ, so that I do not draw
  conclusions from an invalid comparison.
- PRD-US-008 As Dana, I want the CI job to fail with a specific reason when a
  previously passing case now fails, so that I can see which case regressed.
- PRD-US-009 As Mei, I want a summary that separates failures, errors, skipped cases,
  and inconclusive results, so that I can judge the run accurately.
- PRD-US-010 As Sam, I want to write a custom evaluator in Python against a documented
  interface, so that I can check domain-specific rules.

## 7. Product goals

- PRD-G-001 Make a complete local evaluation runnable in under five commands from a
  fresh install (measured in the quick-start test; see TEST_STRATEGY).
- PRD-G-002 Make every reported result traceable to a run ID, dataset hash, and
  evaluator definition.
- PRD-G-003 Make incompatible comparisons impossible to perform silently.
- PRD-G-004 Keep the core free of paid services, external models, and network calls.
- PRD-G-005 Provide documented, versioned public interfaces for targets and evaluators.

## 8. Explicit non-goals (MVP and near-term)

- PRD-NG-001 No model-based (LLM-as-judge) evaluators in the MVP.
- PRD-NG-002 No hosted service, web dashboard, multi-user accounts, or team
  permissions.
- PRD-NG-003 No automatic generation of evaluation datasets.
- PRD-NG-004 No execution of arbitrary code embedded in datasets.
- PRD-NG-005 No sandboxing of custom evaluators or targets in the MVP. They are
  trusted code.
- PRD-NG-006 No claim that scores measure safety, truthfulness, or fairness.
- PRD-NG-007 No statistical significance testing in the MVP beyond reporting counts
  and an uncertainty interval for pass rates (see EVALUATION_METHODOLOGY).
- PRD-NG-008 No distributed or parallel execution across machines.
- PRD-NG-009 No built-in semantic similarity metrics. Text overlap metrics are not
  proof of semantic correctness and are excluded from the MVP.
- PRD-NG-010 No provider integrations (OpenAI, Anthropic, etc.) in the MVP.
- PRD-NG-011 No publishing, pushing, or release automation without explicit approval.
- PRD-NG-012 No process isolation or sandboxing of targets or evaluators in the MVP. Timeouts are best-effort (ARCHITECTURE §11.1; TRD §5.3).
- PRD-NG-013 No claim that redaction removes all sensitive information (DATA_HANDLING §7.4).

## 9. Functional requirements

Each requirement is an MVP requirement unless marked post-MVP.

### 9.1 Datasets

- PRD-F-001 Load evaluation datasets from UTF-8 JSON (array of cases) and JSONL
  (one case per line).
- PRD-F-002 Validate dataset structure and types. Errors identify the file, line
  (or array index), field, and reason.
- PRD-F-003 Detect duplicate case identifiers within a dataset and fail validation.
- PRD-F-004 Support optional `expected` output, free-form `metadata` object, and
  `tags` list on each case.

### 9.2 Target execution

- PRD-F-005 Execute a Python callable as the target for each case.
- PRD-F-006 Record for each case: target output (JSON-serializable), execution status,
  and duration in milliseconds.
- PRD-F-007 Treat a target exception, a timeout, or a non-serializable output as an
  ERROR for that case, and continue with the remaining cases.
- PRD-F-028 Publish a documented target interface so that other adapters can be
  added without changing core code.

### 9.3 Evaluators

- PRD-F-008 Exact-match evaluator.
- PRD-F-009 Normalized-text evaluator (Unicode NFC, case folding, whitespace
  collapse; each option individually configurable).
- PRD-F-010 JSON-structure evaluator (output parses as JSON; optional top-level type
  check).
- PRD-F-011 Required-field evaluator (named top-level or dotted-path fields must be
  present and non-null in parsed JSON output).
- PRD-F-012 Rule-based evaluator with `contains`, `not_contains`, `regex`, and
  output length bounds.
- PRD-F-013 Latency evaluator (duration must be at or below a configured threshold).
- PRD-F-014 Custom Python evaluator through a documented interface. Treated as
  trusted code.

### 9.4 Run execution and results

- PRD-F-015 Each run receives a unique run ID and a manifest recording tool version,
  dataset hash, evaluator definitions (with hashes), target identifier, timeout
  settings, start and end times, and a configuration snapshot with secrets removed.
- PRD-F-016 Each case receives exactly one case status from {PASS, FAIL, ERROR,
  SKIPPED, INCONCLUSIVE}, with the aggregation rules in
  [EVALUATION_METHODOLOGY](EVALUATION_METHODOLOGY.md#3-status-semantics).
- PRD-F-017 Persist runs as local directories containing a manifest, per-case results,
  and a summary, written so that an interrupted run is detectable.
- PRD-F-018 Continue a run after case-level failures and errors. Infrastructure
  faults (for example, the output directory cannot be written) abort the run with a
  distinct status and exit code.

### 9.5 Comparison and regression

- PRD-F-019 Compare a candidate run with a baseline run and classify each case as
  regressed, recovered, unchanged, changed, missing in candidate, or new in candidate.
- PRD-F-020 Compare aggregate metrics: counts per status, pass rate, and latency
  percentiles.
- PRD-F-021 Check runs for compatibility (dataset hash, evaluator definitions, schema
  version) and refuse incompatible comparisons unless the user explicitly allows the
  specific difference, in which case the comparison is labelled. Overrides are CLI or API arguments only, are recorded in the output, and produce a warning finding; `--strict` refuses instead (TRD-136 … TRD-138).
- PRD-F-022 Apply configurable regression thresholds and produce typed findings,
  each with a plain-language explanation and the case IDs or metric values involved.
- PRD-F-023 Return documented exit codes so that CI can distinguish regressions,
  configuration errors, dataset errors, and infrastructure faults.

### 9.6 Reporting and inspection

- PRD-F-024 Readable terminal output for runs and comparisons.
- PRD-F-025 JSON report with a `schema_version` field.
- PRD-F-026 Inspect a stored run: summary, list of cases filtered by status, and
  details for one case.
- PRD-F-029 Validate a configuration file and report errors without running anything.

### 9.7 Interfaces and documentation

- PRD-F-027 A Python API that exposes the same operations as the CLI.
- PRD-F-030 Documented CI usage with an example workflow whose commands are exercised
  by the project's own tests.

### 9.8 Post-MVP functional requirements (not committed)

- PRD-F-101 Model-based evaluators with explicit opt-in, privacy disclosure, and
  recorded judge configuration.
- PRD-F-102 SQLite persistence as an optional storage backend.
- PRD-F-103 Markdown report export.
- PRD-F-104 Parallel case execution with a configurable worker count.
- PRD-F-105 Process-based target isolation (see THREAT_MODEL THR-010).
- PRD-F-106 JSON Schema evaluator, if approved as an optional extra (OD-07).
- PRD-F-107 Dataset registry and dataset import helpers.

## 10. Non-functional requirements

- PRD-NF-001 **Local-first.** The core library and CLI make no network requests during
  dataset validation, evaluation, persistence, comparison, or reporting. Verified by
  a test that disables sockets.
- PRD-NF-002 **Reproducibility.** For a deterministic target and identical dataset and
  configuration, two runs produce identical case statuses, evaluator results, and
  output hashes, excluding timestamps and run IDs.
- PRD-NF-003 **Security of inputs.** Dataset content is never executed, imported, or
  passed to `eval`, `exec`, `pickle`, or unsafe YAML loaders.
- PRD-NF-004 **Cross-platform.** Installs and passes the test suite on Linux, macOS,
  and Windows in CI.
- PRD-NF-005 **Python versions.** Supports the versions in TRD §2 (approved: 3.11–3.13, all tested in CI;
  OD-02).
- PRD-NF-006 **Minimal dependencies.** No third-party runtime dependencies (approved; the ceiling is three;
  see TRD §3 for justification).
- PRD-NF-007 **Performance.** Dataset validation and run persistence overhead must be
  measured and reported in milestone 2 and milestone 8. The proposed initial budget
  is validation of 10,000 cases in under 10 seconds on the CI reference runner. This
  number is a target to be confirmed, not a measured result.
- PRD-NF-008 **Traceability.** Every case result references its run ID, dataset hash,
  and evaluator identifiers.
- PRD-NF-009 **Compatibility.** Persisted artifacts carry `schema_version`. Readers
  reject unknown major versions with a clear error and never silently misread them.
- PRD-NF-010 **Documentation accuracy.** Every example in user-facing documentation is
  executed by the test suite or explicitly marked as a proposal.
- PRD-NF-011 **Log hygiene.** Logs do not include case inputs, outputs, or configuration
  values marked as secrets (see [SECURITY](SECURITY.md)).
- PRD-NF-012 **License compliance.** Copyright notices use the year of initial publication (OD-01). All source files and distributed artifacts carry
  Apache-2.0 notices as required; third-party dependency licences are reviewed
  before release (see RELEASE_CHECKLIST).
- PRD-NF-013 **Honest reporting.** Output text never states or implies that a score
  demonstrates safety, correctness, or reliability.

- PRD-NF-014 **Sensitive-data controls.** Stored input and output are controlled by `io_mode`
  (`full`, `hashes`, `none`). Redaction is enabled by default, is recorded in outputs when
  disabled, and is documented as heuristic and incomplete. Tracebacks are never stored.
  Environment metadata is limited to the set in DATA_HANDLING §6.
- PRD-NF-015 **Artifact integrity scope.** The coverage and limits of the integrity hashes are
  documented precisely (ARTIFACT_INTEGRITY) and are not presented as tamper evidence.
  Incompatible comparisons are refused by default. Overrides are explicit, recorded, and visible.
- PRD-NF-016 **Honest execution limits.** Timeouts are documented as best-effort. No document
  or output claims that arbitrary Python execution can be reliably terminated. Custom targets
  and evaluators are documented as trusted code.

## 11. Core user journeys

**J1 — First evaluation.** Install → write `evalforge.toml` and a 5-case JSONL dataset →
`evalforge dataset validate` → `evalforge run` → read terminal summary → inspect a
failed case.

**J2 — Regression check in CI.** Commit baseline run artifacts (or retrieve them from
a CI cache, see OD-05) → CI runs candidate → `evalforge compare` → non-zero exit code
on regression → job log names the regressed case IDs.

**J3 — Dataset change.** Maintainer adds cases → validation catches duplicate ID →
fixes → new baseline is produced → comparison of old and new dataset is refused by
default and explained.

**J4 — Custom evaluator.** Developer implements the evaluator interface in a Python
module → references it in config → runs → sees evaluator name and version in the
manifest.

**J5 — Infrastructure fault.** Target times out on several cases → those cases are
ERROR with code `TARGET_TIMEOUT` → the run completes → comparison does not count these
as ordinary FAILs and reports them as errors.

## 12. MVP scope

Included: PRD-F-001 to PRD-F-030, PRD-NF-001 to PRD-NF-013.

Explicitly excluded: everything in §8 and §9.8.

Scope rule: any addition must be documented with its impact on milestones, tests,
and security before implementation (CLAUDE.md, "Do not expand approved scope without
explaining the impact").

## 13. Post-MVP roadmap (indicative, not committed)

1. Model-based evaluators as an optional extra, with privacy and cost documentation.
2. SQLite persistence for large run histories.
3. Markdown reports for pull request comments.
4. Parallel execution and process-based isolation for targets.
5. Optional JSON Schema evaluator.
6. Community-contributed datasets with a review process.

Sequencing depends on user feedback and approval. No dates are committed.

## 14. Success metrics

No adoption or market figures are assumed. Measurable product-quality metrics for
the MVP:

| Metric | Definition | Target (proposed) |
|---|---|---|
| Acceptance coverage | Share of PRD-F and PRD-NF requirements with at least one passing automated test or documented verification | 100% before release |
| Traceability completeness | Share of case results that include run ID, dataset hash, evaluator IDs | 100% |
| Regression detection accuracy | On the synthetic regression suite, share of seeded regressions correctly reported | 100% on the seeded suite; the suite's limits are documented |
| False regression rate on identical runs | Regressions reported when comparing a run with itself | 0 |
| Quick-start success | Fresh-environment install and quick-start executed in CI | Passing on all supported OS |
| User-facing evidence | Usability and time-to-first-evaluation measured with real users | Not yet defined; requires user research (OD-16) |

## 15. Competitive analysis

Summary only. Full notes and source limitations are in
[RESEARCH_NOTES.md](../RESEARCH_NOTES.md).

| Project | Focus | Relevant to EvalForge |
|---|---|---|
| promptfoo | Prompt/model testing, assertions, CI gating | Declarative config and deterministic assertion set are a useful reference. Its license was not verified. |
| DeepEval | pytest-style LLM unit tests; many metrics; Apache 2.0 | Strong pytest ergonomics; many metrics are LLM-judged. |
| Ragas | RAG-specific metrics such as faithfulness | Claim-decomposition scoring is instructive; RAG-specific metrics are out of MVP scope. |
| Inspect AI | Task/solver/scorer framework with sandboxing | Clean concepts and sandbox design; broader scope than EvalForge's MVP. |
| OpenAI Evals | Framework and registry; MIT; dashboard option | Registry idea is valuable and deferred; hosted product exists. |

EvalForge's proposed differentiation: local-first, deterministic-first evaluation with
explicit status semantics, and compatibility-checked run comparison as the primary
workflow.

## 16. Risks and assumptions

Risks are also tracked in [PLANNING_SUMMARY](../PLANNING_SUMMARY.md).

| ID | Risk | Mitigation |
|---|---|---|
| R-01 | Users treat pass rate as proof of quality | Honest wording (PRD-NF-013), methodology docs, report disclaimers |
| R-02 | Deterministic checks are too narrow for real AI outputs | Clear limitations; custom evaluators; model-based path post-MVP |
| R-03 | Scope creep into a hosted platform | Non-goals (§8); scope rule (§12) |
| R-04 | Target timeouts cannot kill threads, leaving resource use | Documented limitation; process isolation planned (PRD-F-105) |
| R-05 | Comparison produces misleading results when datasets change | Compatibility checks (PRD-F-021) |
| R-06 | Competitor information is incomplete | Source-limited research notes; no claims beyond sources |
| R-07 | Name availability and trademark not verified; publication blocked until checked | OD-10, G-2 |

Assumptions:

- A-01 Users run Python 3.11 or later (approved; OD-02).
- A-02 Target functions are deterministic enough for regression comparison, or users
  accept that pass-rate changes may reflect variance (see EVALUATION_METHODOLOGY).
- A-03 Users are willing to store run artifacts locally and manage them with their
  version control or CI cache.

## 17. Dependencies

- Python runtime and standard library.
- Runtime dependencies proposed in TRD §3 (pending approval).
- GitHub Actions for CI (proposed).
- Apache-2.0 license (confirmed by project owner).
- No external services.

## 18. Acceptance criteria (MVP)

| Requirement | Acceptance criterion |
|---|---|
| PRD-F-001 | A JSON array file and a JSONL file containing the same three cases load to equal `Dataset` objects with equal content hashes of their canonical form. |
| PRD-F-002 | An invalid JSONL line reports file, 1-based line number, field path, and reason; the validation exit code is 3. |
| PRD-F-003 | A dataset with two cases sharing an `id` fails validation and names the duplicated ID. |
| PRD-F-004 | A case without `expected` is accepted; evaluators that require `expected` report SKIPPED with reason `NO_EXPECTED`. |
| PRD-F-005 | A callable target is invoked once per selected case, in dataset order, with the case input. |
| PRD-F-006 | Each case result includes output, `target_status`, and `duration_ms` (non-negative number). |
| PRD-F-007 | A target that raises on one case yields ERROR with code `TARGET_EXCEPTION` for that case only; all other cases are still executed. A case exceeding the timeout yields ERROR with code `TARGET_TIMEOUT`. |
| PRD-F-008 | Exact match returns PASS only when outputs are equal under Python equality after canonical JSON serialization. |
| PRD-F-009 | Normalized text returns PASS for `"Hello  World\n"` vs `"hello world"` when case folding and whitespace collapse are enabled, and FAIL when they are disabled. |
| PRD-F-010 | JSON evaluator returns FAIL for `"{not json"` and PASS for `"{\"a\": 1}"`. |
| PRD-F-011 | Required-field evaluator returns FAIL, naming the missing path, when a required dotted path is absent or null. |
| PRD-F-012 | Rule evaluator returns FAIL with the matched rule name for each of: missing `contains`, present `not_contains`, regex non-match, length out of bounds. |
| PRD-F-013 | Latency evaluator returns FAIL when `duration_ms` exceeds the threshold and PASS when equal to or below it. |
| PRD-F-014 | A custom evaluator class satisfying the documented interface is loaded and its result recorded with its name and version; a custom evaluator raising an exception produces ERROR with code `EVALUATOR_EXCEPTION`. |
| PRD-F-015 | Two runs of the same config produce different run IDs and identical dataset hashes; the manifest contains all fields listed in DATA_MODELS. |
| PRD-F-016 | The aggregation rules in EVALUATION_METHODOLOGY §3 are covered by a table-driven test with at least one case per row. |
| PRD-F-017 | Killing the process mid-run leaves a manifest in state `RUNNING`; `inspect` reports the run as incomplete and `compare` refuses it. |
| PRD-F-018 | With an unwritable output directory, `run` exits 4 and reports `STORAGE_ERROR`; a single failing case does not change the run's infrastructure status. |
| PRD-F-019 | A fixed pair of runs seeded with known transitions yields exactly the expected categorization in a table-driven test. |
| PRD-F-020 | Pass rate equals PASS count divided by executed count (PASS+FAIL+ERROR+INCONCLUSIVE), and is `null` when executed count is 0. |
| PRD-F-021 | Comparison refuses a changed dataset hash with exit code 5 unless `--allow-dataset-change` is given. When given, the output contains a banner, a `compatibility.overrides` entry, and a `COMPARISON_OVERRIDDEN` warning; `--strict` refuses instead (TST-CM-019 … TST-CM-021). |
| PRD-F-022 | Each finding contains `code`, `severity`, `message`, and the case IDs or metric names involved; the message is verified by a golden-output test. |
| PRD-F-023 | Exit codes match CLI_SPECIFICATION §4 in every tested scenario. |
| PRD-F-024 | Terminal output strips control characters from case outputs (verified by test with ANSI escape input). |
| PRD-F-025 | JSON report validates against the published JSON Schema for its declared `schema_version`. |
| PRD-F-026 | `inspect --case ID` shows input, output, expected, and each evaluator result for that case. |
| PRD-F-027 | Each CLI operation has a Python API equivalent, and both produce identical summary objects for the same inputs (verified by test). |
| PRD-F-028 | A custom target adapter implemented against the documented interface runs without modification of core code (verified by example adapter test). |
| PRD-F-029 | `config validate` reports unknown keys, missing required fields, and invalid evaluator types without executing a target. |
| PRD-F-030 | The example CI workflow's commands run successfully in the project's CI against the synthetic example. |
| PRD-NF-001 | Test with socket creation patched to raise completes the quick-start with no errors. |
| PRD-NF-002 | Two deterministic runs produce identical canonical case result content (excluding timestamps, run IDs, durations). |
| PRD-NF-003 | A dataset containing Python code, pickle bytes, or YAML tags is loaded as plain strings and never executed (security test suite). |
| PRD-NF-004 | CI passes on Linux, macOS, and Windows for the supported Python versions. |
| PRD-NF-006 | `pyproject.toml` declares at most the approved runtime dependencies; a test asserts the list. |
| PRD-NF-009 | A reader given `schema_version: "2.0"` fails with `SCHEMA_VERSION_UNSUPPORTED`. |
| PRD-NF-011 | A secret-pattern value placed in config is absent from logs and manifests (test). |
| PRD-NF-014 | Each `io_mode` stores exactly the content listed in DATA_HANDLING §3.1 (TST-IO-001 … TST-IO-003); redaction behaviour and documented misses match DATA_HANDLING §7 (TST-RD-001 … TST-RD-006). |
| PRD-NF-015 | The integrity scope table matches the manifest writer (TST-DOC-007); deliberate rewriting is documented as undetected (TST-IN-003); incompatible comparisons are refused without flags (TST-CM-019); overrides appear in JSON and banner (TST-CM-020). |
| PRD-NF-016 | Timeout documentation contains the best-effort wording and no forced-termination claim (TST-TG-014). |

## 19. Open product decisions

Tracked in [OPEN_DECISIONS.md](../OPEN_DECISIONS.md). Key ones for the product:

- OD-08 default regression thresholds.
- OD-09 policy for dataset and evaluator changes in comparisons.
- OD-12 whether full inputs and outputs are stored by default.
- OD-13 whether ERROR cases count in the pass-rate denominator.
- OD-16 user research plan and success measures.
- OD-27 whether configuration may disable redaction.
- OD-28 default behaviour of overrides in CI (`--strict` as default or opt-in).
- OD-29 whether to add manifest signing post-MVP.
- OD-30 whether the full platform string may be stored.
